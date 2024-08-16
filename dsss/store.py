"""Storage of SDMX artefacts."""

import logging
import pickle
import re
import subprocess
from abc import ABC, abstractmethod
from functools import singledispatchmethod
from hashlib import blake2s
from pathlib import Path
from typing import Callable, Dict, Iterable, List, Mapping, Optional, Tuple, Union, cast

import sdmx
import sdmx.model.version
import sdmx.urn
from sdmx.model import common

log = logging.getLogger(__name__)


def _short_urn(value: str) -> str:
    return sdmx.urn.normalize(sdmx.urn.shorten(value))


def _maintainer_id(
    obj: Union[common.MaintainableArtefact, common.BaseDataSet, str],
) -> str:
    """Return a maintainer for `obj`.

    If `obj` is :class:`.DataSet`, the maintainer of the data flow is used.
    """
    if isinstance(obj, str):
        return sdmx.urn.match(sdmx.urn.expand(obj))["agency"]
    if isinstance(obj, common.MaintainableArtefact):
        result = obj.maintainer
    elif obj.described_by:
        result = obj.described_by.maintainer
    elif obj.structured_by:
        result = obj.structured_by.maintainer
    else:
        result = common.Agency(id="NONE")
    return result.id if result else "NONE"


class Store(ABC):
    """Base class for key-value storage of SDMX artefacts.

    :class:`.Store` facilitates use of keys derived from the SDMX Information Model and
    class hierarchy. Currently the following can be stored and retrieved:

    1. Value type: :class:`~sdmx.model.common.MaintainableArtefact`.

       Key: The full :attr:`IdentifiableArtefact.urn
       <sdmx.model.common.IdentifiableArtefact.urn>`.

       Example: :py:`"urn:sdmx:org.sdmx.infomodel.codelist.Codelist=FOO:CL(1.0)"`.

    2. Value type: :class:`~sdmx.model.common.BaseDataSet`.

       Key: The :attr:`IdentifiableArtefact.id
       <sdmx.model.common.IdentifiableArtefact.id>` of the
       :class:`~sdmx.model.common.BaseDataStructureDefinition` (associated via the
       :attr:`BaseDataSet.structured_by <sdmx.model.common.BaseDataSet.structured_by>`
       attribute) and a hash of the :class:`~sdmx.model.common.BaseObservation` keys,
       joined with a hyphen.

       Example: :py:`"DataSet-DSD_ID-adaa503c71ac9574"`.

       This includes the :mod:`sdmx.model.v21` and :mod:`sdmx.model.v30` subclasses of
       BaseDataSet, BaseDataflow, and BaseObservation.

    Store is abstract with respect to *how* artefacts are stored; subclasses may use
    different methods of local or remote storage.

    Store implements the standard ‘CRUD’ operations, following the semantics of Python
    :class:`dict`:

    - :meth:`set` —create.
    - :meth:`get` —retrieve.
    - :meth:`update` —update.
    - :meth:`delete` —delete.

    In general, for :meth:`set` and :meth:`update` operations, it is not necessary to
    explicitly give the key; one is computed from the object to be stored, and returned.

    The following convenience methods are also provided:

    - :meth:`list` —list keys for objects matching the given criteria.
    - :meth:`update_from` —update multiple objects from a message, file containing a
      message, or directory containing files.
    """

    hook_ids: Tuple[str, ...] = ("pre-write",)

    #: Hooks are per-instance.
    hook: Mapping[str, List[Callable]]

    # Methods that must be implemented by concrete subclasses

    @abstractmethod
    def __init__(
        self,
        hook: Optional[Mapping[str, Union[Callable, Iterable[Callable]]]] = None,
        **kwargs,
    ) -> None:
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
        -------
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

        If `obj` exists, it is overwritten unconditionally.
        """

    @abstractmethod
    def update(self, obj) -> str:
        """Update `obj` and return its key."""

    # Concrete methods
    def assign_version(self, obj, **kwargs):
        """Assign a version to `obj` subsequent to any existing versions.

        See also
        --------
        increment_version
        """
        versions = self.list_versions(type(obj), obj.maintainer.id, obj.id)

        if versions:
            next_version = sdmx.model.version.increment(versions[1], **kwargs)
        else:
            next_version = sdmx.model.version.increment("0.0.0", **kwargs)

        obj.version = next_version

    @singledispatchmethod
    def key(self, obj) -> str:
        """Construct a key for `obj`."""
        raise NotImplementedError  # if none of the overloads registered below apply

    @key.register
    def _key_ds(self, obj: common.BaseDataSet):
        assert obj.structured_by
        parts0: List[str] = [type(obj).__name__, obj.structured_by.id]
        parts1 = [o.dimension for o in obj.obs]

        hashed_parts = blake2s(pickle.dumps(parts1), digest_size=8)
        return "-".join(parts0 + [hashed_parts.hexdigest()])

    @key.register
    def _key_ma(self, obj: common.MaintainableArtefact):
        if obj.urn:
            result = obj.urn
        else:
            if obj.maintainer is None:
                obj.maintainer = common.Agency(id="UNKNOWN")
            result = sdmx.urn.make(obj)
        return sdmx.urn.normalize(result)

    def list(
        self,
        klass: Optional[type] = None,
        maintainer: Optional[str] = None,
        id: Optional[str] = None,
        version: Optional[str] = None,
    ):
        """List keys for :class:`~sdmx.model.common.MaintainableArtefact`.

        Only keys that match the given `klass`, `maintainer`, `id` and/or `version` are
        returned.
        """
        if klass is common.BaseDataSet:
            assert id
            pattern = f".*DataSet-{id}-.*"
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

        urn_re = re.compile(pattern)

        return list(filter(urn_re.fullmatch, self.iter_keys()))

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

    def resolve(self, obj, attr: str) -> "common.MaintainableArtefact":
        """Resolve an external reference in a named `attr` of `obj`."""
        existing = getattr(obj, attr)
        if not existing.is_external_reference:
            return existing
        new_attr = self.get(existing.urn)
        setattr(obj, attr, new_attr)
        return cast(common.MaintainableArtefact, new_attr)

    @singledispatchmethod
    def update_from(self, obj, **kwargs):
        """Update the Store from another `obj`.

        `obj` may be a:

        - :class:`~sdmx.message.DataMessage` —all
          :class:`~sdmx.model.common.BaseDataSet` in the message are read and stored.
        - :class:`~sdmx.message.StructureMessage` —all SDMX structures in the message
          are read and stored.
        - :class:`pathlib.Path` of an :file:`.xml` file or directory. The given file,
          or all :file:`.xml` files in the directory, are read, and their contents
          added.
        """
        raise NotImplementedError

    @update_from.register
    def _update_from_path(self, p: Path):
        if p.is_dir():
            for child in filter(lambda s: not s.name.startswith("."), p.iterdir()):
                self.update_from(child)
        elif p.is_file() and p.suffix == ".xml":
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
                self.set(ds)
            except Exception as e:
                log.warning(f"Could not store {type(ds).__name__} {ds}: {e}")
                log.debug(repr(e))

    @update_from.register
    def _update_from_sm(self, msg: sdmx.message.StructureMessage):
        for obj in msg.iter_objects(external_reference=False):
            try:
                self.set(obj)
            except Exception as e:
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

    @singledispatchmethod
    def set(self, obj):
        raise NotImplementedError

    @singledispatchmethod
    def update(self, obj):
        raise NotImplementedError

    @set.register
    @update.register
    def _(self, obj: Union[common.MaintainableArtefact, common.BaseDataSet]):
        key = self.key(obj)

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

    def __init__(self, path: Path, **kwargs) -> None:
        self.path = path
        self.path.mkdir(parents=True, exist_ok=True)
        super().__init__(**kwargs)

    def delete(self, key):
        path = self.path_for(None, key)
        path.unlink()

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
    def _(self, obj: Union[common.MaintainableArtefact, common.BaseDataSet]):
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
    ) -> Union[common.MaintainableArtefact, common.BaseDataSet]:
        """Read a :class:`sdmx.message.Message` from `path` and return its contents."""
        msg = sdmx.read_sdmx(path)

        if isinstance(msg, sdmx.message.StructureMessage):
            for obj in msg.iter_objects(external_reference=False):
                return obj
            raise ValueError
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
        dm = sdmx.message.DataMessage()
        dm.data.append(obj)

        # Update dm.observation_dimension to match the keys of `obj`
        dm.update()

        with open(path, "wb") as f:
            f.write(sdmx.to_xml(dm, pretty_print=True))

    @write_message.register
    def _ma(self, obj: common.MaintainableArtefact, path):
        sm = sdmx.message.StructureMessage()
        sm.add(obj)

        with open(path, "wb") as f:
            f.write(sdmx.to_xml(sm, pretty_print=True))


class FlatFileStore(FileStore):
    """FileStore as a flat collection of files, with names identical to keys."""

    def iter_keys(self):
        return [p.name for p in self.path.iterdir()]

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
        """Inverse of path_for."""
        from sdmx.model.v21 import PACKAGE, get_class

        if "DataSet-" in path.name:
            return path.name
        else:
            # Reassemble the URN given the path name
            klass = get_class(path.name.split("=")[0])
            assert klass
            return f"urn:sdmx:org.sdmx.infomodel.{PACKAGE[klass.__name__]}.{path.name}"

    def iter_keys(self):
        for maintainer in filter(Path.is_dir, self.path.iterdir()):
            for p in maintainer.iterdir():
                try:
                    yield self._key_for(p)
                except Exception:
                    log.info(f"Cannot determine key from file name {p!r}")


class GitStore(StructuredFileStore):
    """Not implemented."""
