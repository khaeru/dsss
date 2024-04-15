from typing import List, Tuple

import pytest
import sdmx
from sdmx.model import common, v21

from dsss.store import DictStore, FlatFileStore, Store, StructuredFileStore


@pytest.fixture
def objects_and_keys() -> List[Tuple[common.AnnotableArtefact, str]]:
    """A collection of storable objects for testing."""
    result: List[Tuple[common.AnnotableArtefact, str]] = []

    a = common.Agency(id="FOO")
    o1: "common.Codelist" = common.Codelist(id="CL", version="1.0", maintainer=a)

    result.append((o1, "urn:sdmx:org.sdmx.infomodel.codelist.Codelist=FOO:CL(1.0)"))

    dfd = v21.DataflowDefinition(id="DFD", maintainer=a)
    dsd = v21.DataStructureDefinition(id="DSD", maintainer=a)
    o2 = v21.DataSet(described_by=dfd, structured_by=dsd)

    result.append((o2, "DataSet-FOO-adaa503c71ac9574"))

    return result


class TestStore:
    @pytest.fixture(
        scope="class",
        params=[(DictStore, None), (FlatFileStore, True), (StructuredFileStore, True)],
        ids=["DictStore", "FlatFileStore", "StructureFileStore"],
    )
    def s(self, request, tmp_path_factory) -> Store:
        klass, with_tmp_dir = request.param
        args = []
        if with_tmp_dir:
            args.append(tmp_path_factory.mktemp(klass.__name__))
        return klass(*args)

    def test_key(self, specimen, s) -> None:
        with specimen("ECB_EXR/1/M.USD.EUR.SP00.A.xml") as f:
            msg = sdmx.read_sdmx(f)

        k = s.key(msg.data[0])

        # Key contains the ID of the maintainer of the DFD or DSD
        assert "GenericDataSet-ECB-d8f6df84c6fd4880" == k

    def test_set_get(
        self, s, objects_and_keys: List[Tuple[common.AnnotableArtefact, str]]
    ) -> None:
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
            assert result.compare(obj, strict=strict)

    @pytest.fixture(scope="class")
    def all_specimens(self, s, specimen) -> Store:
        for path, *_ in specimen.specimens:
            s.update_from(path)
        return s

    def test_iter_keys(self, all_specimens) -> None:
        assert 896 == len(list(all_specimens.iter_keys()))

    def test_list(self, all_specimens) -> None:
        # klass= only
        assert 88 == len(all_specimens.list(common.Codelist))

        # klass= and maintainer=
        assert 15 == len(all_specimens.list(common.Codelist, maintainer="SDMX"))

        # klass= and id=
        assert 5 == len(all_specimens.list(common.Codelist, id="CL_UNIT_MULT"))

    def test_list_versions(self, all_specimens) -> None:
        result = all_specimens.list_versions(
            common.Codelist, maintainer="SDMX", id="CL_UNIT_MULT"
        )

        assert ("1.0", "1.1") == result

    def test_assign_version(self, all_specimens) -> None:
        obj: "common.Codelist" = common.Codelist(
            id="CL_UNIT_MULT", maintainer=common.Agency(id="SDMX")
        )

        assert obj.version is None

        all_specimens.assign_version(obj)

        # Next version after 1.1.0 is 1.1.1dev1
        assert "1.1.1dev1" == obj.version
