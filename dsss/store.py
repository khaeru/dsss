"""Storage of SDMX artefacts.

:class:`.Store` facilitates use of keys derived from the SDMX Information Model and its
class hierarchy. Any artefact handled by :meth:`~.Store.key` can be stored or retrieved,
including:

- Any :class:`~sdmx.model.common.MaintainableArtefact`.
- Any :class:`~sdmx.model.common.BaseDataSet` or
  :class:`~sdmx.model.common.BaseMetadataSet`. This includes the :mod:`sdmx.model.v21`
  and :mod:`sdmx.model.v30` subclasses of Base(Meta)DataSet.

…using standard ‘CRUD’ operations, following the semantics of Python :class:`dict`:

- :meth:`~.Store.set` —create.
- :meth:`~.Store.get` —retrieve.
- :meth:`~.Store.update` —update.
- :meth:`~.Store.delete` —delete.

In general, for :meth:`set` and :meth:`update` operations, it is not necessary to
explicitly give the key; one is computed from the object to be stored, and returned.

Convenience methods are also provided, including :meth:`.assign_version`, :meth:`.list`,
:meth:`.list_versions`, :meth:`.resolve`, :meth:`.update_from`.


Store is abstract with respect to *how* artefacts are stored. Subclasses **may** use
different methods of storage. Concrete subclasses include
:class:`.DictStore`, :class:`.FlatFileStore`, :class:`.StructuredFileStore`,
:class:`.GitStore`, and :class:`.UnionStore`.
"""

import logging
import pickle
import re
from abc import ABC, abstractmethod
from copy import deepcopy
from functools import lru_cache, singledispatch, singledispatchmethod
from hashlib import blake2s
from itertools import chain
from pathlib import Path
from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    Dict,
    Iterable,
    List,
    Literal,
    Mapping,
    MutableMapping,
    Optional,
    Protocol,
    Set,
    Tuple,
    TypeVar,
    Union,
    cast,
)

import lxml.etree
import sdmx
import sdmx.model.version
import sdmx.urn
from sdmx.model import common, v21, v30

if TYPE_CHECKING:
    import git

log = logging.getLogger(__name__)

#: Regular expression matching keys for (Meta)DataSet.
DATA_KEY_PATTERN = re.compile(
    r"(meta|)data-(?P<agency>[^:]+):(?P<id>[^-]+)-(?P<hash>.+)"
)

DataSetClass = (common.BaseDataSet, common.BaseMetadataSet)
AnyMetadataSet = Union[v21.MetadataSet, v30.MetadataSet]


T = TypeVar("T", common.BaseDataSet, common.BaseMetadataSet, covariant=True)


class DataType(Protocol[T]):
    def __hash__(self) -> int: ...


@lru_cache()
def dataset_kind(klass: type) -> Literal["data", "metadata"]:
    """Return a ‘kind’ for a :class:`.BaseDataSet` or :class:`.BaseMetadataSet` type."""
    if common.BaseDataSet in klass.mro():
        return "data"
    elif common.BaseMetadataSet in klass.mro():
        return "metadata"
    else:
        raise TypeError(klass)


@singledispatch
def hashable_metadata(obj) -> Union[Tuple, str]:
    """Recursively generate a hashable collection from `obj`."""
    if obj is None:
        return ""
    raise NotImplementedError(type(obj))  # pragma: no cover


@hashable_metadata.register
def _(obj: v21.MetadataSet):
    return tuple(hashable_metadata(r) for r in obj.report)


@hashable_metadata.register
def _(obj: v21.MetadataReport):
    return tuple(hashable_metadata(mda) for mda in obj.metadata)


@hashable_metadata.register
def _(obj: v21.ReportedAttribute):
    return tuple(
        hashable_metadata(c) for c in chain([getattr(obj, "value", None)], obj.child)
    )


@hashable_metadata.register
def _(obj: v30.MetadataSet):
    log.warning(f"No unique key for {type(obj)}")
    return ""


@hashable_metadata.register
def _(obj: lxml.etree._Element):
    return lxml.etree.tostring(obj)


@hashable_metadata.register
def _(obj: str):
    return obj


def _short_urn(value: str) -> str:
    return sdmx.urn.normalize(sdmx.urn.shorten(value))


def _maintainer_id(
    obj: Union[common.MaintainableArtefact, DataType, str],
) -> str:
    """Return a maintainer for `obj`.

    If `obj` is :class:`.DataSet`, the maintainer of the data flow is used.
    """
    if isinstance(obj, str):
        try:
            return sdmx.urn.match(sdmx.urn.expand(obj))["agency"]
        except ValueError:
            if match := DATA_KEY_PATTERN.fullmatch(obj):
                match.group("agency")

    ma = common.Agency(id="_MISSING")

    if isinstance(obj, common.MaintainableArtefact):
        ma = obj.maintainer or ma
    elif isinstance(obj, DataSetClass):
        ma = cast(
            common.Agency,
            # TODO Remove type exclusions when common.BaseMetaDataSet type hints are
            #      improved
            getattr(obj.described_by, "maintainer", None)  # type: ignore [union-attr]
            or getattr(obj.structured_by, "maintainer", ma),  # type: ignore [union-attr]
        )

    return ma.id


class Store(ABC):
    """Abstract class for key-value storage of SDMX artefacts.

    Subclasses **must** implement :meth:`delete`, :meth:`get`, :meth:`iter_keys`,
    :meth:`set`, and :meth:`update`.
    """

    #: IDs of hooks. Subclasses **may** extend this tuple.
    hook_ids: Tuple[str, ...] = ("before set",)

    #: Mapping from :attr:`hook_ids` to lists of hooks. Hooks are per-instance.
    hook: MutableMapping[str, List[Callable]]

    @abstractmethod
    def __init__(
        self,
        hook: Optional[Mapping[str, Union[Callable, Iterable[Callable]]]] = None,
        **kwargs,
    ) -> None:
        """Initialize the store instance.

        Subclasses **must** call this parent class method to initialize hooks.

        Parameters
        ----------
        hook :
            Hooks for the instance. Mapping from :attr:`hook_ids` to either single
            callables, or iterables of callables.
        """
        self.hook = {id_: [] for id_ in self.hook_ids}

        for key, hooks in (hook or {}).items():
            if key not in self.hook:
                log.warning(f"No hook ID {key!r}; skip")
                continue

            if callable(hooks):
                self.hook[key].append(hooks)
            else:
                self.hook[key].extend(hooks)

    @abstractmethod
    def delete(self, key: str) -> bool:
        """Delete an object given its `key`.

        Raises
        ------
        KeyError
            If the object does not exist.
        """

    @abstractmethod
    def get(self, key: str) -> "sdmx.model.common.AnnotableArtefact":
        """Return an object given its `key`.

        Raises
        ------
        KeyError
            If the object does not exist.
        """

    @abstractmethod
    def iter_keys(self) -> Iterable[str]:
        """Iterate over stored keys.

        The keys are **not** ordered.
        """

    @abstractmethod
    def set(self, obj) -> str:
        """Store `obj` and return its key.

        If `obj` exists, :class:`KeyError` is raised.
        """

    @abstractmethod
    def update(self, obj) -> str:
        """Update `obj` and return its key."""

    # Concrete methods
    def assign_version(self, obj, **kwargs):
        """Assign a version to `obj` subsequent to any existing versions.

        See also
        --------
        sdmx.model.version.increment
        """
        versions = self.list_versions(type(obj), obj.maintainer.id, obj.id)

        if versions:
            next_version = sdmx.model.version.increment(versions[1], **kwargs)
        else:
            next_version = sdmx.model.version.increment("0.0.0", **kwargs)

        obj.version = next_version

    def invoke_hooks(self, kind: str, *args, **kwargs) -> None:
        """Invoke each callable in :attr:`hook` with :attr:`hook_id` `kind`."""
        for hook in self.hook[kind]:
            hook(*args, **kwargs)

    @singledispatchmethod
    def key(self, obj) -> str:
        """Construct a key for `obj`.

        Supported `obj` classes include:

        :class:`~sdmx.model.common.MaintainableArtefact`.
           Example: :py:`"urn:sdmx:org.sdmx.infomodel.codelist.Codelist=FOO:CL(1.0)"`

           The key is the full :attr:`IdentifiableArtefact.urn
           <sdmx.model.common.IdentifiableArtefact.urn>`.

        :class:`~sdmx.model.common.BaseDataSet`, :class:`~sdmx.model.common.BaseMetadataSet`
           Example: :py:`"data-FOO:DSD_ID-adaa503c71ac9574"`

           The key consists of:

           - :py:`"data-"` or :py:`"metadata-"`, based on the class of `obj`;
           - the :attr:`IdentifiableArtefact.id
             <sdmx.model.common.IdentifiableArtefact.id>` of the maintainer of either
             (a) the :class:`Dataflow <sdmx.model.common.BaseDataflow>` that describes
             `obj` or if not defined (b) of the :class:`DataStructure
             <sdmx.model.common.BaseDataStructureDefinition>` that structures `obj`;
           - the ID of the (Meta)Dataflow or (b) (Meta)DataStructure itself; and
           - a hash of the :class:`Observation <sdmx.model.common.BaseObservation>`
             keys.
        """  # noqa: E501
        raise NotImplementedError  # if none of the overloads registered below apply

    @key.register(common.BaseDataSet)
    @key.register(common.BaseMetadataSet)
    def _key_ds(self, obj: DataType):
        # parts0: shown in plain-text in the key
        # Identify the `kind` of `obj`—either "data" or "metadata"
        parts0: List[str] = [dataset_kind(type(obj))]

        # TODO Remove exclusions when common.BaseMetadataSet type hints are improved
        for candidate in obj.described_by, obj.structured_by:  # type: ignore [attr-defined]
            try:
                urn = sdmx.urn.URN(sdmx.urn.make(candidate))
                parts0.append(f"{urn.agency}:{urn.id}")
                break
            except AttributeError:
                continue

        # parts1: hashed to a hexdigest in the key
        parts1: List[Any] = []
        if isinstance(obj, common.BaseDataSet):
            parts1.extend(o.dimension for o in obj.obs)
        elif isinstance(obj, (v21.MetadataSet, v30.MetadataSet)):
            parts1.extend(hashable_metadata(obj))

        hashed_parts = blake2s(pickle.dumps(parts1), digest_size=8)
        return "-".join(parts0 + [hashed_parts.hexdigest()])

    @key.register
    def _key_ma(self, obj: common.MaintainableArtefact):
        if obj.urn:
            result = obj.urn
        else:
            if obj.maintainer is None:
                # TODO Avoid mutating objects; maybe do this on a copy
                obj.maintainer = common.Agency(id="_MISSING")
            result = sdmx.urn.make(obj)
        return sdmx.urn.normalize(result)

    def list(
        self,
        klass: Optional[type] = None,
        maintainer: Optional[str] = None,
        id: Optional[str] = None,
        version: Optional[str] = None,
    ) -> List[str]:
        """List matching keys.

        Only keys that match the given parameters (if any) are returned.

        Parameters
        ----------
        klass : :class:`~sdmx.model.common.AnnotableArtefact`
            Class of artefact.
        maintainer :
            ID of the maintainer of an artefact or its (meta)dataflow.
        id :
            ID of an artefact or its (meta)dataflow.
        version :
            Version of an artefact.
        """
        if issubclass(klass or object, DataSetClass):
            maintainer = maintainer or "[^:]+"
            id = id or "[^-]+"
            pattern = f"{dataset_kind(klass)}-{maintainer}:{id}-.*"
        else:
            placeholder = "@@@"

            if klass is None:
                klass = common.Codelist
                replace_extra = r"codelist\.Codelist"
            else:
                replace_extra = "NotAClass"

            obj = klass(
                id=id or placeholder,
                maintainer=common.Agency(id=maintainer or placeholder),
                version=version or placeholder,
            )

            pattern = (
                re.escape(sdmx.urn.make(obj))
                .replace(placeholder, ".*")
                .replace("Definition", "(Definition)?")
                .replace(replace_extra, ".*")
            )

        return list(filter(re.compile(pattern).fullmatch, self.iter_keys()))

    def list_versions(self, klass: type, maintainer: str, id: str) -> Tuple[str, ...]:
        """Return all versions of a :class:`~sdmx.model.common.MaintainableArtefact`.

        The `klass`, `maintainer`, and `id` arguments are the same as for :meth:`.list`.
        """
        return tuple(
            sorted(
                sdmx.urn.match(k)["version"]
                for k in self.list(klass=klass, maintainer=maintainer, id=id)
            )
        )

    def resolve(self, obj, attr: Optional[str] = None) -> "common.MaintainableArtefact":
        """Resolve an external reference in a named `attr` of `obj`."""
        if attr:
            existing = getattr(obj, attr)
        else:
            existing = obj

        if existing.is_external_reference is False:
            return existing

        if urn := existing.urn:
            urn = sdmx.urn.normalize(urn)
        else:
            urn = self.key(existing)

        resolved = self.get(urn)

        if attr:
            setattr(obj, attr, resolved)

        return cast(common.MaintainableArtefact, resolved)

    @singledispatchmethod
    def update_from(self, obj: "Store", **kwargs) -> None:
        """Update the Store from another `obj`.

        Parameters
        ----------
        obj :
            Any of:

            - :class:`pathlib.Path` of an :file:`.xml` file or directory —the given
              file, or all :file:`.xml` files in the directory and any subdirectories,
              are read and their contents added.
            - another :class:`Store` instance —all contents of the other store are
              added.
            - a :class:`~sdmx.message.DataMessage` —all
              :class:`~sdmx.model.common.BaseDataSet` in the message are read and
              stored.
            - a :class:`~sdmx.message.StructureMessage` —all SDMX structures in the
              message are read and stored.

        Other Parameters
        ----------------
        ignore : optional
            if `obj` is a path, `ignore` is an optional iterable of callables. Each
            of the callables in `ignore` is applied to every file path to be read; if
            the any of them returns :obj:`True`, the file is skipped.

        Raises
        ------
        NotImplementedError
            for any `obj` other than the above.
        """
        if isinstance(obj, Store):
            for key in obj.iter_keys():
                try:
                    self.set(deepcopy(obj.get(key)))
                except Exception as e:
                    action = kwargs.get("errors", "raise")
                    if action == "log":
                        log.info(f"{key} {type(e).__name__}: {e}; skip")
                    else:  # pragma: no cover
                        raise
        else:
            raise NotImplementedError

    @update_from.register
    def _update_from_path(
        self, p: Path, *, ignore: Optional[Iterable[Callable[[Path], bool]]] = None
    ):
        ignore = ignore or []

        if p.is_dir():
            for child in filter(lambda s: not s.name.startswith("."), p.iterdir()):
                self.update_from(child, ignore=ignore)
        elif p.is_file() and p.suffix == ".xml" and not any(i(p) for i in ignore):
            try:
                msg = sdmx.read_sdmx(p)
            except Exception as e:
                log.warning(f"Could not read {p}; {e}")
                log.debug(repr(e))
                return
            self.update_from(msg)

    @update_from.register
    def _update_from_dm(self, msg: sdmx.message.DataMessage):
        for ds in msg.data:
            try:
                self.update(ds)
            except Exception as e:  # pragma: no cover
                log.warning(f"Could not store {type(ds).__name__} {ds}: {e}")
                log.debug(repr(e))

    @update_from.register
    def _update_from_sm(self, msg: sdmx.message.StructureMessage):
        for obj in msg.iter_objects(external_reference=False):
            try:
                self.update(obj)
            except Exception as e:  # pragma: no cover
                log.warning(f"Could not store {type(obj).__name__} {obj}: {e}")
                log.debug(repr(e))


class DictStore(Store):
    _contents: Dict[str, sdmx.model.common.AnnotableArtefact]

    def __init__(self, **kwargs):
        self._contents = dict()
        super().__init__(**kwargs)

    def delete(self, key: str):
        self._contents.pop(key)

    def get(self, key: str):
        return self._contents[key]

    def set(self, obj):
        key = self.key(obj)

        if key in self._contents:
            raise KeyError(key)

        self.invoke_hooks("before set", key, obj)

        self._contents[key] = obj

        return key

    def update(self, obj):
        key = self.key(obj)

        self.invoke_hooks("before set", key, obj)

        self._contents[key] = obj

        return key

    def iter_keys(self):
        return self._contents.keys()


class FileStore(Store):
    """Abstract class for a store using SDMX-ML files in a local directory.

    Each file contains either:

    - a :class:`~sdmx.message.DataMessage` with a single
      :class:`~sdmx.model.common.BaseDataSet`, or
    - a :class:`~sdmx.message.StructureMessage` with a single structure artefact.

    """

    #: Storage location.
    path: Path

    #: Expressions giving file paths to ignore.
    ignore: Set[Callable[[Path], bool]] = set()

    def __init__(self, path: Path, **kwargs) -> None:
        self.path = path
        self.path.mkdir(parents=True, exist_ok=True)
        super().__init__(**kwargs)

    def delete(self, key):
        try:
            self.path_for(None, key).unlink()
        except FileNotFoundError:
            raise KeyError(key)

    def get(self, key: str):
        path = self.path_for(None, key)
        return self.read_message(path)

    @singledispatchmethod
    def set(self, obj):
        raise NotImplementedError

    @singledispatchmethod
    def update(self, obj):
        raise NotImplementedError

    @set.register
    @update.register
    def _(
        self,
        obj: Union[
            common.MaintainableArtefact, common.BaseDataSet, common.BaseMetadataSet
        ],
    ):
        key = self.key(obj)

        path = self.path_for(obj, key)
        self.write_message(obj, path)

        return key

    # New methods for this class

    @abstractmethod
    def path_for(self, obj, key) -> Path:
        """Construct the path to the file to be written."""

    def read_message(
        self, path: Path
    ) -> Union[common.MaintainableArtefact, common.BaseDataSet, common.BaseMetadataSet]:
        """Read a :class:`sdmx.message.Message` from `path` and return its contents."""
        msg = sdmx.read_sdmx(path)

        if isinstance(msg, sdmx.message.StructureMessage):
            for obj in msg.iter_objects(external_reference=False):
                return obj
            # NB This line only reached if an entirely empty StructureMessage is read;
            #    should not occur in practice
            raise ValueError  # pragma: no cover
        elif isinstance(msg, sdmx.message.DataMessage):
            return msg.data[0]
        else:
            raise NotImplementedError

    @singledispatchmethod
    def write_message(self, obj, path: Path) -> sdmx.message.Message:
        """Write `obj` to an SDMX-ML message at `path`."""
        raise NotImplementedError

    @write_message.register
    def _ds(self, obj: common.BaseDataSet, path):
        """Write DataMessage.

        .. todo:: Optionally also write SDMX-CSV with :py:`attributes="gso"`.
        """
        dm = sdmx.message.DataMessage()
        dm.data.append(obj)

        # Update dm.observation_dimension to match the keys of `obj`
        dm.update()

        try:
            with open(path, "wb") as f:
                f.write(sdmx.to_xml(dm, pretty_print=True))
        except Exception:
            # log.error(f"Writing to {path}: {e}")
            path.unlink()
            raise

    @write_message.register
    def _mds(self, obj: common.BaseMetadataSet, path):
        """Write MetadataMessage."""
        mdm = sdmx.message.MetadataMessage()
        mdm.data.append(obj)

        try:
            with open(path, "wb") as f:
                f.write(sdmx.to_xml(mdm, pretty_print=True))
        except Exception:
            # log.error(f"Writing to {path}: {e}")
            path.unlink()
            raise

    @write_message.register
    def _ma(self, obj: common.MaintainableArtefact, path):
        sm = sdmx.message.StructureMessage()
        sm.add(obj)

        try:
            with open(path, "wb") as f:
                f.write(sdmx.to_xml(sm, pretty_print=True))
        except Exception:
            # log.error(f"Writing to {path}: {e}")
            path.unlink()
            raise


class FlatFileStore(FileStore):
    """FileStore as a flat collection of files, with names identical to keys."""

    def iter_keys(self):
        return map(
            lambda p: p.name,
            filter(lambda p: not any(f(p) for f in self.ignore), self.path.iterdir()),
        )

    def path_for(self, obj, key) -> Path:
        return self.path.joinpath(key)


class StructuredFileStore(FileStore):
    """FileStore arranged in directories by maintainer, with more readable names."""

    def path_for(self, obj, key) -> Path:
        if obj is None:
            candidates = list(self.path.rglob(_short_urn(key)))
            if len(candidates) != 1:
                raise KeyError(f"{len(candidates)} matches for {key}: {candidates}")
            return candidates[0]
        else:
            result = self.path.joinpath(_maintainer_id(obj), _short_urn(key))
            result.parent.mkdir(exist_ok=True)
            return result

    def _key_for(self, path: Path) -> str:
        """Inverse of :meth:`path_for`."""
        from sdmx.model import v21, v30

        if DATA_KEY_PATTERN.fullmatch(path.name):
            return path.name
        else:
            # Reassemble the URN given the path name
            for model in v21, v30:
                try:
                    klass = model.get_class(path.name.split("=")[0])
                    return (
                        f"urn:sdmx:org.sdmx.infomodel.{model.PACKAGE[klass.__name__]}."
                        f"{path.name}"
                    )
                except (AttributeError, KeyError):
                    continue
        raise ValueError(path)

    def iter_keys(self):
        # Iterate over top-level directories within `self.path`
        for dir_ in filter(Path.is_dir, self.path.iterdir()):
            # Iterate over files within each directory
            for p in filter(
                lambda p: not any(f(p) for f in self.ignore), dir_.iterdir()
            ):
                try:
                    yield self._key_for(p)
                except Exception:
                    log.info(f"Cannot determine key from file name {p!r}")


class GitStore(StructuredFileStore):
    """A store that uses an underlying Git repository."""

    #: URL of a remote Git repository to mirror.
    remote_url: Optional[str] = None

    #: :class:`.git.Repo` object.
    repo: "git.Repo"

    # Overrides

    ignore = {lambda p: ".git" in p.parts}

    def __init__(
        self,
        path: Path,
        remote_url: Optional[str] = None,
        clone: bool = False,
        **kwargs,
    ) -> None:
        import git

        super().__init__(path=path, **kwargs)
        self.remote_url = remote_url

        # Initialize git Repo object in `path`
        self.repo = git.Repo.init(self.path)

        if clone:  # pragma: no cover
            self.clone()

    def write_message(self, obj, path):
        # Write the file
        super().write_message(obj, path)

        # Add to git, but do not commit
        index = self.repo.index
        index.add(path)

    # New methods for this class

    def clone(self):
        """Clone the repository indicated by :attr:`.remote_url`."""
        import git

        # Ensure there is a remote for the origin
        try:
            self.repo.delete_remote("origin")
        except git.exc.GitCommandError:
            pass

        origin = self.repo.create_remote("origin", self.remote_url)

        # Fetch the remote
        branch_name = "main"
        origin.fetch(f"refs/heads/{branch_name}")
        b = origin.refs[branch_name]

        # Check out the branch
        try:
            head = self.repo.heads[branch_name]
        except IndexError:
            head = self.repo.create_head(branch_name, b)
        head.set_tracking_branch(b).checkout()


class UnionStore(Store):
    """A Store that unites 1 or more underlying Stores."""

    #: Mapping from store IDs to instances of :class:`.Store`.
    store: Mapping[str, Store]

    #: Mapping from maintainer IDs to keys of :attr:`.store`.
    maintainer_store: MutableMapping[str, str]

    #: ID of the default :attr:`store`.
    default: str

    def get_store_id(self, key: str) -> str:
        """Return the ID of the store that should be used for `obj`."""
        maintainer_id = _maintainer_id(key)
        return self.maintainer_store.get(maintainer_id, self.default)

    # Implementations of abstract methods of Store

    def __init__(self, store=Mapping[str, Store], **kwargs):
        super().__init__(**kwargs)

        self.store = dict()
        self.store.update(store)

        self.default = next(iter(self.store.keys()))

        self.maintainer_store = dict()

        log.info(f"Will use default store: {self.default}")

    def delete(self, key):
        return self.store[self.get_store_id(key)].delete(key)

    def get(self, key):
        return self.store[self.get_store_id(key)].get(key)

    def iter_keys(self):
        for store_id, store in self.store.items():
            yield from store.iter_keys()

    def set(self, obj):
        key = self.key(obj)
        return self.store[self.get_store_id(key)].set(obj)

    def update(self, obj):
        key = self.key(obj)
        return self.store[self.get_store_id(key)].update(obj)
