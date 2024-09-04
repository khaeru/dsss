import logging
from pathlib import Path
from typing import TYPE_CHECKING, Dict, List, Tuple, cast

import pytest
import sdmx
from sdmx.model import common, v21
from sdmx.model.version import Version

from dsss.store import (
    DictStore,
    FlatFileStore,
    GitStore,
    Store,
    StructuredFileStore,
    UnionStore,
)
from dsss.testing import GHA, assert_le

if TYPE_CHECKING:
    import pathlib

log = logging.getLogger(__name__)


@pytest.fixture(scope="module")
def all_specimens(specimen) -> DictStore:
    """A :class:`.DictStore` with all storable artefacts from sdmx-test-data."""
    s = DictStore()

    s.update_from(specimen.base_path)

    return s


@pytest.fixture
def objects_and_keys() -> List[Tuple[common.AnnotableArtefact, str]]:
    """A collection of storable objects for testing."""
    result: List[Tuple[common.AnnotableArtefact, str]] = []

    a = common.Agency(id="FOO")
    o1: "common.Codelist" = common.Codelist(id="CL", version="1.0", maintainer=a)

    result.append((o1, "urn:sdmx:org.sdmx.infomodel.codelist.Codelist=FOO:CL(1.0)"))

    dfd = v21.DataflowDefinition(id="DFD", maintainer=a)
    dsd = v21.DataStructureDefinition(id="DSD_ID", maintainer=a)
    o2 = v21.DataSet(described_by=dfd, structured_by=dsd)

    result.append((o2, "data-FOO:DFD-adaa503c71ac9574"))

    return result


def before_set_1(*args, **kwargs):
    log.info("\n".join(["hook before_set_1", str(args)[:80], str(kwargs)[:80]]))


def before_set_2(*args, **kwargs):
    log.info("\n".join(["hook before_set_2", str(args)[:80], str(kwargs)[:80]]))


class TestDictStore:
    def test_init_hook(self, caplog) -> None:
        def _(): ...

        # Iterable of callable can be passed to hooks= arg
        s = DictStore(hook={"before set": [before_set_1, before_set_2]})

        # Single callable (not iterable of callable) can be passed to hooks= arg
        s = DictStore(hook={"before set": _})
        assert _ in s.hook["before set"]

        # Message is logged passing hooks for unregistered IDs
        assert 0 == len(caplog.messages)
        DictStore(hook={"not a hook": _})
        assert "No hook ID 'not a hook'; skip" in caplog.messages


class TestStore:
    @pytest.fixture(
        scope="class",
        params=[
            (DictStore, None),
            (FlatFileStore, True),
            (StructuredFileStore, True),
        ],
        ids=lambda p: p[0].__name__,
    )
    def s(self, request, tmp_path_factory, all_specimens) -> Store:
        klass, with_tmp_dir = request.param

        args: Dict[str, str] = dict()
        if with_tmp_dir:
            args.update(path=tmp_path_factory.mktemp(klass.__name__))

        result = klass(**args)
        result.update_from(all_specimens, errors="log")

        return result

    @pytest.fixture
    def N_total(self, s: Store) -> int:
        """Total number of artefacts present in the Store.

        The value is lower for FileStore subclasses which cannot write certain types of
        artefacts to SDMX-ML.
        """
        return (
            907  # NB 907 on GHA, 920 locally
        ) - {
            FlatFileStore: 41,
            StructuredFileStore: 41,
            GitStore: 41,
            UnionStore: 41,
        }.get(type(s), 0)

    def test_assign_version(self, s: Store):
        obj: "common.Codelist" = common.Codelist(
            id="CL_UNIT_MULT", maintainer=common.Agency(id="SDMX")
        )

        assert obj.version is None

        s.assign_version(obj)

        # Next version after 1.1.0 is 1.2.0-dev1
        assert isinstance(obj.version, Version)
        assert "1.2.0-dev1" == obj.version

        # Assign version to a non-existent object yields 0.0.0
        obj = common.Codelist(id="CL_NON_EXISTENT", maintainer=common.Agency(id="SDMX"))
        assert obj.version is None

        s.assign_version(obj)

        assert "0.1.0-dev1" == obj.version

    def test_delete0(self, s: Store):
        # Store an object
        obj = common.ConceptScheme(
            id="FOO", version="1.0", maintainer=common.Agency(id="TO_DELETE")
        )
        key = s.set(obj)

        # Object's key is present in iter_keys()
        assert key in s.iter_keys()

        # Deletion succeeds
        s.delete(key)

        # Key is no longer present
        assert key not in s.iter_keys()

        # Attempting deletion again raises KeyError
        with pytest.raises(KeyError):
            s.delete(key)

    def test_get_set0(
        self,
        caplog,
        s: Store,
        objects_and_keys: List[Tuple[common.AnnotableArtefact, str]],
    ):
        caplog.set_level(logging.INFO)

        # Only DictStore (for now) provides true round-trip identity
        strict = isinstance(s, DictStore)

        for obj, exp_key in objects_and_keys:
            # obj can be stored
            key = s.set(obj)

            # key is as expected
            assert exp_key == key

            # Object can be retrieved
            result = s.get(key)

            # Retrieved object is the same as stored
            assert hasattr(result, "compare")  # TODO For mypy; remove when possible
            assert result.compare(obj, strict=strict)

    def test_iter_keys0(self, s: Store, N_total):
        assert_le(N_total, len(list(s.iter_keys())))

    def test_key0(self, specimen, s: Store):
        """Keys can be generated for certain specimens."""
        with specimen("ECB_EXR/1/M.USD.EUR.SP00.A.xml") as f:
            msg = sdmx.read_sdmx(f)

        # Key contains the ID of the maintainer of the DFD or DSD
        "data-ECB:ECB_EXR1-d8f6df84c6fd4880" == s.key(msg.data[0])

        with specimen("ESTAT/esms.xml") as f:
            msg = sdmx.read_sdmx(f)

        # Key is generated for a MetadataSet containing XHTMLAttributeValue / XML node
        assert "metadata-ESTAT:ESMS-6473b2060169eb77" == s.key(msg.data[0])

    def test_key1(self, s: Store) -> None:
        """:meth:`.key` generates distinct values for MetadataSet."""
        # print("\n".join(sorted(s.list())))

        mdsd = cast(
            v21.MetadataStructureDefinition,
            s.get(
                "urn:sdmx:org.sdmx.infomodel.metadatastructure.MetadataStructure=ESTAT:ESMS_SIMPLE(1.0)"
            ),
        )
        rs = mdsd.report_structure["ESMS_SIMPLE_REPORT"]
        mda = rs.get("CONTACT")

        # Two MetadataSets that are identical (empty) have the same key; the hexdigest
        # part is deterministic
        mds0 = v21.MetadataSet(structured_by=mdsd)
        mds1 = v21.MetadataSet(structured_by=mdsd)
        assert (
            "metadata-ESTAT:ESMS_SIMPLE-adaa503c71ac9574" == s.key(mds0) == s.key(mds1)
        )

        # Add a report with a single ReportedAttribute generates a specific key
        mdr0 = v21.MetadataReport()
        mds0.report.append(mdr0)
        mdr0.metadata.append(
            v21.OtherNonEnumeratedAttributeValue(value_for=mda, value="FOO")
        )

        # Key is deterministic
        assert "metadata-ESTAT:ESMS_SIMPLE-2fce739abdc0c93a" == s.key(mds0)

        # Adding identical content to `mds1` results in the same key
        mdr1 = v21.MetadataReport()
        mds1.report.append(mdr1)
        mdr1.metadata.append(
            v21.OtherNonEnumeratedAttributeValue(value_for=mda, value="FOO")
        )

        assert s.key(mds0) == s.key(mds1)

    @pytest.mark.parametrize(
        "N_exp, klass, kw",
        (
            (85, common.Codelist, {}),  # klass= only
            # NB 85 on GHA, 86 locally, 88 for DictStore
            (15, common.Codelist, dict(maintainer="SDMX")),  # klass= and maintainer=
            (5, common.Codelist, dict(id="CL_UNIT_MULT")),  # klass= and id=
            (14, common.BaseDataSet, {}),  # DataSet
            # NB 14 on GHA, 15 locally, 32 for DictStore
            (1, common.BaseMetadataSet, {}),  # MetadataSet
        ),
    )
    def test_list(self, s: Store, N_exp: int, klass, kw):
        """:meth:`.list` returns the correct number of objects."""
        assert_le(N_exp, len(s.list(klass, **kw)))

    def test_list_versions(self, s: Store):
        result = s.list_versions(common.Codelist, maintainer="SDMX", id="CL_UNIT_MULT")

        assert ("1.0", "1.1") == result

    def test_resolve0(self, s: Store):
        """Resolve an object."""
        obj = common.ConceptScheme(
            id="CROSS_DOMAIN_CONCEPTS",
            maintainer=common.Agency(id="SDMX"),
            version="1.0",
        )

        assert 0 == len(obj)

        result: "common.ConceptScheme" = s.resolve(obj)  # type: ignore [assignment]

        # `result` is a fully populated object and not an external reference
        assert 12 <= len(result)
        assert result.is_external_reference is False

        # Type narrowing so that mypy does not complain about the following assertion
        assert result.maintainer is not None and obj.maintainer is not None

        # Identifiers of `result` match `obj`
        assert (
            (result.id == obj.id)
            and (result.version == obj.version)
            and (result.maintainer.id == obj.maintainer.id)
        )
        assert result.urn == sdmx.urn.make(obj)

    def test_resolve1(self, s: Store):
        """Resolve an attribute of an object."""
        o1: "common.BaseDataflow" = s.get(  # type: ignore [assignment]
            "urn:sdmx:org.sdmx.infomodel.datastructure.Dataflow=FR1:IPI-2010-A21(1.0)"
        )

        # Number of dimensions in the object prior to resolving the reference
        if isinstance(s, (DictStore, UnionStore)) and not GHA:
            # With DictStore or UnionStore dispatching to DictStore, objects all remain
            # in memory and refer to one another; is_external_reference is False
            N_dimensions_pre, is_external_reference_pre = 4, False
        else:
            N_dimensions_pre, is_external_reference_pre = 0, True  # noqa: F841

        # DSD at `structure` attribute has expected number of dimensions
        # assert N_dimensions_pre == len(o1.structure.dimensions)
        # DSD at `structure` attribute is an external reference
        assert o1.structure.is_external_reference is is_external_reference_pre

        s.resolve(o1, "structure")

        # The `structure` attribute is a fully-populated object and not an external
        # reference
        assert 4 == len(o1.structure.dimensions)
        assert o1.structure.is_external_reference is False

    def test_update(self, s: Store):
        # Store an object; record its key
        m = common.Agency(id="DSSS")
        o1: "common.Codelist" = common.Codelist(
            id="TEST_UPDATE", maintainer=m, version="1.0"
        )
        key = s.set(o1)

        del o1

        # The stored object does not have any annotations
        with pytest.raises(KeyError):
            s.get(key).get_annotation(id="test_update")

        # Create a new object with the same key
        o2: "common.Codelist" = common.Codelist(
            id="TEST_UPDATE", maintainer=m, version="1.0"
        )
        # Add an annotation
        o2.annotations.append(common.Annotation(id="test_update", text="FOO"))

        # Update the stored object
        s.update(o2)

        del o2

        # Now the same key retrieves the updated object with the annotation
        assert (
            "FOO"
            == s.get(key).get_annotation(id="test_update").text.localized_default()
        )


class TestStructuredFileStore:
    def test_key_for(self, tmp_path):
        """Test construction of a URN that does not work in SDMX 2.16.0."""
        s = StructuredFileStore(path=tmp_path)
        assert (
            "urn:sdmx:org.sdmx.infomodel.codelist.ValueList=SDMX:VL_CURRENCY_SYMBOL(1.0)"
            == s._key_for(Path("/tmp/EXAMPLE/ValueList=SDMX:VL_CURRENCY_SYMBOL(1.0)"))
        )


class TestGitStore(TestStore):
    """Tests of :class:`.GitStore`."""

    @pytest.fixture(scope="class")
    def remote_repo(self, tmp_path_factory) -> "pathlib.Path":
        """An empty Git repository in a temporary directory with a "main" branch."""
        import git

        path = tmp_path_factory.mktemp("gitstore-remote-repo")
        repo = git.Repo.init(path)

        file1 = path.joinpath("REMOTE_FILE")
        file1.write_text("")

        file2 = path.joinpath("FOO", "README")
        file2.parent.mkdir(exist_ok=True)
        file2.write_text("")

        repo.index.add([file1, file2])

        repo.index.commit("Initial commit")
        repo.create_head("main")

        return path

    @pytest.fixture(scope="class")
    def s(self, request, tmp_path_factory, all_specimens) -> Store:
        result = GitStore(path=tmp_path_factory.mktemp("GitStore"))
        result.update_from(all_specimens, errors="log")

        return result

    def test_clone0(self, tmp_path, remote_repo: str):
        """Test of :meth:`.clone` with nothing in the local directory."""
        s = GitStore(path=tmp_path.joinpath("GitStore0"), remote_url=remote_repo)

        # Clone succeeds without error
        s.clone()

        # Files from the remote `main` branch are checked out in the clone
        assert s.path.joinpath("REMOTE_FILE").exists()

    def test_clone1(self, tmp_path, objects_and_keys, remote_repo: str):
        """Test of :meth:`.clone` with nothing in the local directory."""
        s1 = GitStore(path=tmp_path.joinpath("GitStore1"), remote_url=remote_repo)

        # Clone succeeds without error
        s1.clone()

        # Write an object
        s1.set(objects_and_keys[0][0])

        del s1

        # Create again with existing repo
        s2 = GitStore(path=tmp_path.joinpath("GitStore1"), remote_url=remote_repo)

        # Clone again
        s2.clone()

    def test_iter_keys1(self, caplog, s: Store):
        s.list()
        assert [] == caplog.messages


class TestUnionStore(TestStore):
    @pytest.fixture(scope="class")
    def s(self, request, tmp_path_factory, all_specimens) -> UnionStore:
        result = UnionStore(
            store={
                "A": DictStore(path=tmp_path_factory.mktemp("UnionStoreA")),
                "B": DictStore(path=tmp_path_factory.mktemp("UnionStoreB")),
            },
        )

        # Map maintainer IDs "BAR" and "BAZ" to store "B"; "FOO" explicitly to "A"
        result.maintainer_store.update(FOO="A", BAR="B", BAZ="B")

        result.update_from(all_specimens, errors="log")

        return result

    def test_get_set1(self, s: UnionStore, N_total):
        cl: "common.Codelist" = common.Codelist(id="CL_TEST", version="1.0.0")

        for maintainer_id in "FOO", "BAR", "BAZ", "QUX":
            cl.maintainer = common.Agency(id=maintainer_id)

            s.set(cl)

        assert_le(N_total, len(s.store["A"].list()))
        assert 2 == len(s.store["B"].list())
