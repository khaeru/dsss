"""Local data storage."""

import logging
import pickle
import re
from abc import ABC, abstractmethod
from functools import singledispatchmethod
from hashlib import blake2s
from itertools import chain
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple, Union

import packaging.version
import sdmx
import sdmx.urn
from sdmx.model import common

log = logging.getLogger(__name__)


def increment_version(
    existing: str, major=None, minor=None, micro=None, dev=None
) -> str:
    v = packaging.version.parse(existing)

    if major is minor is micro is dev is None:
        micro = dev = True

    return ".".join(
        [
            f"{v.major + int(major or 0)}",
            f"{v.minor + int(minor or 0)}",
            f"{v.micro + int(micro or 0)}",
        ]
    ) + (f"dev{int(v.dev or 0) + int(dev or 0)}" if (dev or v.dev is not None) else "")


def _maintainer_id(
    obj: Union[common.MaintainableArtefact, common.BaseDataSet],
) -> str:
    """Return a maintainer for `obj`.

    If `obj` is :class:`.DataSet`, the maintainer of the data flow is used.
    """
    if isinstance(obj, common.MaintainableArtefact):
        result = obj.maintainer
    elif obj.described_by:
        result = obj.described_by.maintainer
    elif obj.structured_by:
        result = obj.structured_by.maintainer
    else:
        result = common.Agency(id="NONE")
    return result.id if result else "NONE"


_SHORT_URN_EXPR = re.compile(r"(urn:sdmx:org\.sdmx\.infomodel\.[^\.]+\.)?(?P<short>.*)")


def _short_urn(value: str) -> str:
    m = _SHORT_URN_EXPR.match(value)
    assert m
    return m.group("short")


class Store(ABC):
    """Base class for key-value storage of SDMX artefacts.

    :class:`.Store` facilitates use of keys derived from the SDMX Information Model and
    class hierarchy. Currently the following can be stored and retrieved:

    1. :class:`.MaintainableArtefact` → the complete :attr:`.IdentifiableArtefact.urn`.
    2. :class:`.BaseDataSet` → the :attr`~.IdentifiableArtefact.urn` of the
       :class:`.BaseDataFlow` and a hash of the :class:`.Observation` keys.

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

    - :meth:`list ` —list keys for objects matching the given criteria.
    - :meth:`update_from` —update multiple objects from a message, file containing a
      message, or directory containing files.

    """

    @abstractmethod
    def __init__(self, **kwargs) -> None: ...

    # CRUD methods

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
    def set(self, obj) -> str:
        """Store `obj` and return its key."""

    @abstractmethod
    def update(self, obj) -> str:
        """Update `obj` and return its key."""

    @singledispatchmethod
    def key(self, obj) -> str:
        """Construct the key for `obj`."""
        raise NotImplementedError

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
            return obj.urn
        else:
            if obj.maintainer is None:
                obj.maintainer = common.Agency(id="UNKNOWN")
            return sdmx.urn.make(obj)

    @abstractmethod
    def iter_keys(self) -> Iterable[str]:
        """Iterate over stored keys."""

    def list(
        self,
        klass: Optional[type] = None,
        maintainer: Optional[str] = None,
        id: Optional[str] = None,
        version: Optional[str] = None,
    ):
        """List keys for :class:`MaintainableArtefacts` matching certain attributes."""
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
        """Return all stored versions of the :class:`.MaintainableArtefact`."""
        return tuple(
            sorted(
                sdmx.urn.match(k)["version"]
                for k in self.list(klass=klass, maintainer=maintainer, id=id)
            )
        )

    def assign_version(self, obj, **kwargs):
        """Assign a version to `obj` subsequent to any existing versions."""
        versions = self.list_versions(type(obj), obj.maintainer.id, obj.id)

        if versions:
            next_version = increment_version(versions[1], **kwargs)
        else:
            next_version = increment_version("0.0.0", **kwargs)

        obj.version = next_version

    @singledispatchmethod
    def update_from(self, obj, **kwargs):
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
        for name, cls_ in msg.iter_collections():
            for id_, obj in msg.objects(cls_).items():
                if obj.is_external_reference:
                    continue
                try:
                    self.set(obj)
                except Exception as e:
                    log.warning(f"Could not store {type(obj).__name__} {obj}: {e}")
                    log.debug(repr(e))


class DictStore(Store):
    _contents: Dict[str, sdmx.model.common.AnnotableArtefact]

    def __init__(self):
        self._contents = dict()

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

    - a :class:`.DataMessage` with a single :class:`.BaseDataSet`, or
    - a :class:`.StructureMessage` with a single structure artefact.

    """

    #: Storage location.
    path: Path

    def __init__(self, path: Path) -> None:
        self.path = path
        self.path.mkdir(parents=True, exist_ok=True)

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

    @abstractmethod
    def path_for(self, obj, key) -> Path:
        """Construct the path to the file to be written."""

    def read_message(
        self, path: Path
    ) -> Union[common.MaintainableArtefact, common.BaseDataSet]:
        msg = sdmx.read_sdmx(path)

        if isinstance(msg, sdmx.message.StructureMessage):
            result = next(
                chain(*[msg.objects(cls).values() for _, cls in msg.iter_collections()])
            )
            return result
        elif isinstance(msg, sdmx.message.DataMessage):
            return msg.data[0]
        else:
            raise NotImplementedError

    @singledispatchmethod
    def write_message(self, obj, path: Path) -> sdmx.message.Message:
        """Encapsulate `obj` in a message."""
        raise NotImplementedError

    @write_message.register
    def _ds(self, obj: common.BaseDataSet, path):
        dm = sdmx.message.DataMessage()
        dm.data.append(obj)

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
            assert 1 == len(candidates)
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
                yield self._key_for(p)


class GitStore(StructuredFileStore):
    """Not implemented."""
