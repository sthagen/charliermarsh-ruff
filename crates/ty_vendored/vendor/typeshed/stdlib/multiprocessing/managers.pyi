import queue
import sys
import threading
from _typeshed import SupportsKeysAndGetItem, SupportsRichComparison, SupportsRichComparisonT
from collections.abc import (
    Callable,
    Iterable,
    Iterator,
    Mapping,
    MutableMapping,
    MutableSequence,
    MutableSet,
    Sequence,
    Set as AbstractSet,
)
from types import GenericAlias, TracebackType
from typing import Any, AnyStr, ClassVar, Generic, SupportsIndex, TypeVar, overload
from typing_extensions import Self, TypeAlias

from . import pool
from .connection import Connection, _Address
from .context import BaseContext
from .shared_memory import _SLT, ShareableList as _ShareableList, SharedMemory as _SharedMemory
from .util import Finalize as _Finalize

__all__ = ["BaseManager", "SyncManager", "BaseProxy", "Token", "SharedMemoryManager"]

_T = TypeVar("_T")
_KT = TypeVar("_KT")
_VT = TypeVar("_VT")
_S = TypeVar("_S")

class Namespace:
    def __init__(self, **kwds: Any) -> None: ...
    def __getattr__(self, name: str, /) -> Any: ...
    def __setattr__(self, name: str, value: Any, /) -> None: ...

_Namespace: TypeAlias = Namespace

class Token:
    """
    Type to uniquely identify a shared object
    """

    typeid: str | bytes | None
    address: _Address | None
    id: str | bytes | int | None
    def __init__(self, typeid: bytes | str | None, address: _Address | None, id: str | bytes | int | None) -> None: ...
    def __getstate__(self) -> tuple[str | bytes | None, tuple[str | bytes, int], str | bytes | int | None]: ...
    def __setstate__(self, state: tuple[str | bytes | None, tuple[str | bytes, int], str | bytes | int | None]) -> None: ...

class BaseProxy:
    """
    A base for proxies of shared objects
    """

    _address_to_local: dict[_Address, Any]
    _mutex: Any
    def __init__(
        self,
        token: Any,
        serializer: str,
        manager: Any = None,
        authkey: AnyStr | None = None,
        exposed: Any = None,
        incref: bool = True,
        manager_owned: bool = False,
    ) -> None: ...
    def __deepcopy__(self, memo: Any | None) -> Any: ...
    def _callmethod(self, methodname: str, args: tuple[Any, ...] = (), kwds: dict[Any, Any] = {}) -> None:
        """
        Try to call a method of the referent and return a copy of the result
        """

    def _getvalue(self) -> Any:
        """
        Get a copy of the value of the referent
        """

    def __reduce__(self) -> tuple[Any, tuple[Any, Any, str, dict[Any, Any]]]: ...

class ValueProxy(BaseProxy, Generic[_T]):
    def get(self) -> _T: ...
    def set(self, value: _T) -> None: ...
    value: _T
    def __class_getitem__(cls, item: Any, /) -> GenericAlias:
        """Represent a PEP 585 generic type

        E.g. for t = list[int], t.__origin__ is list and t.__args__ is (int,).
        """

if sys.version_info >= (3, 13):
    class _BaseDictProxy(BaseProxy, MutableMapping[_KT, _VT]):
        __builtins__: ClassVar[dict[str, Any]]
        def __len__(self) -> int: ...
        def __getitem__(self, key: _KT, /) -> _VT: ...
        def __setitem__(self, key: _KT, value: _VT, /) -> None: ...
        def __delitem__(self, key: _KT, /) -> None: ...
        def __iter__(self) -> Iterator[_KT]: ...
        def copy(self) -> dict[_KT, _VT]: ...
        @overload  # type: ignore[override]
        def get(self, key: _KT, /) -> _VT | None: ...
        @overload
        def get(self, key: _KT, default: _VT, /) -> _VT: ...
        @overload
        def get(self, key: _KT, default: _T, /) -> _VT | _T: ...
        @overload
        def pop(self, key: _KT, /) -> _VT: ...
        @overload
        def pop(self, key: _KT, default: _VT, /) -> _VT: ...
        @overload
        def pop(self, key: _KT, default: _T, /) -> _VT | _T: ...
        def keys(self) -> list[_KT]: ...  # type: ignore[override]
        def items(self) -> list[tuple[_KT, _VT]]: ...  # type: ignore[override]
        def values(self) -> list[_VT]: ...  # type: ignore[override]

    class DictProxy(_BaseDictProxy[_KT, _VT]):
        def __class_getitem__(cls, args: Any, /) -> GenericAlias:
            """Represent a PEP 585 generic type

            E.g. for t = list[int], t.__origin__ is list and t.__args__ is (int,).
            """

else:
    class DictProxy(BaseProxy, MutableMapping[_KT, _VT]):
        __builtins__: ClassVar[dict[str, Any]]
        def __len__(self) -> int: ...
        def __getitem__(self, key: _KT, /) -> _VT: ...
        def __setitem__(self, key: _KT, value: _VT, /) -> None: ...
        def __delitem__(self, key: _KT, /) -> None: ...
        def __iter__(self) -> Iterator[_KT]: ...
        def copy(self) -> dict[_KT, _VT]: ...
        @overload  # type: ignore[override]
        def get(self, key: _KT, /) -> _VT | None: ...
        @overload
        def get(self, key: _KT, default: _VT, /) -> _VT: ...
        @overload
        def get(self, key: _KT, default: _T, /) -> _VT | _T: ...
        @overload
        def pop(self, key: _KT, /) -> _VT: ...
        @overload
        def pop(self, key: _KT, default: _VT, /) -> _VT: ...
        @overload
        def pop(self, key: _KT, default: _T, /) -> _VT | _T: ...
        def keys(self) -> list[_KT]: ...  # type: ignore[override]
        def items(self) -> list[tuple[_KT, _VT]]: ...  # type: ignore[override]
        def values(self) -> list[_VT]: ...  # type: ignore[override]

if sys.version_info >= (3, 14):
    class _BaseSetProxy(BaseProxy, MutableSet[_T]):
        __builtins__: ClassVar[dict[str, Any]]
        # Copied from builtins.set
        def add(self, element: _T, /) -> None: ...
        def copy(self) -> set[_T]: ...
        def clear(self) -> None: ...
        def difference(self, *s: Iterable[Any]) -> set[_T]: ...
        def difference_update(self, *s: Iterable[Any]) -> None: ...
        def discard(self, element: _T, /) -> None: ...
        def intersection(self, *s: Iterable[Any]) -> set[_T]: ...
        def intersection_update(self, *s: Iterable[Any]) -> None: ...
        def isdisjoint(self, s: Iterable[Any], /) -> bool: ...
        def issubset(self, s: Iterable[Any], /) -> bool: ...
        def issuperset(self, s: Iterable[Any], /) -> bool: ...
        def pop(self) -> _T: ...
        def remove(self, element: _T, /) -> None: ...
        def symmetric_difference(self, s: Iterable[_T], /) -> set[_T]: ...
        def symmetric_difference_update(self, s: Iterable[_T], /) -> None: ...
        def union(self, *s: Iterable[_S]) -> set[_T | _S]: ...
        def update(self, *s: Iterable[_T]) -> None: ...
        def __len__(self) -> int: ...
        def __contains__(self, o: object, /) -> bool: ...
        def __iter__(self) -> Iterator[_T]: ...
        def __and__(self, value: AbstractSet[object], /) -> set[_T]: ...
        def __iand__(self, value: AbstractSet[object], /) -> Self: ...
        def __or__(self, value: AbstractSet[_S], /) -> set[_T | _S]: ...
        def __ior__(self, value: AbstractSet[_T], /) -> Self: ...  # type: ignore[override,misc]
        def __sub__(self, value: AbstractSet[_T | None], /) -> set[_T]: ...
        def __isub__(self, value: AbstractSet[object], /) -> Self: ...
        def __xor__(self, value: AbstractSet[_S], /) -> set[_T | _S]: ...
        def __ixor__(self, value: AbstractSet[_T], /) -> Self: ...  # type: ignore[override,misc]
        def __le__(self, value: AbstractSet[object], /) -> bool: ...
        def __lt__(self, value: AbstractSet[object], /) -> bool: ...
        def __ge__(self, value: AbstractSet[object], /) -> bool: ...
        def __gt__(self, value: AbstractSet[object], /) -> bool: ...
        def __eq__(self, value: object, /) -> bool: ...
        def __rand__(self, value: AbstractSet[object], /) -> set[_T]: ...
        def __ror__(self, value: AbstractSet[_S], /) -> set[_T | _S]: ...  # type: ignore[misc]
        def __rsub__(self, value: AbstractSet[_T], /) -> set[_T]: ...
        def __rxor__(self, value: AbstractSet[_S], /) -> set[_T | _S]: ...  # type: ignore[misc]
        def __class_getitem__(cls, item: Any, /) -> GenericAlias: ...

    class SetProxy(_BaseSetProxy[_T]): ...

class BaseListProxy(BaseProxy, MutableSequence[_T]):
    __builtins__: ClassVar[dict[str, Any]]
    def __len__(self) -> int: ...
    def __add__(self, x: list[_T], /) -> list[_T]: ...
    def __delitem__(self, i: SupportsIndex | slice, /) -> None: ...
    @overload
    def __getitem__(self, i: SupportsIndex, /) -> _T: ...
    @overload
    def __getitem__(self, s: slice, /) -> list[_T]: ...
    @overload
    def __setitem__(self, i: SupportsIndex, o: _T, /) -> None: ...
    @overload
    def __setitem__(self, s: slice, o: Iterable[_T], /) -> None: ...
    def __mul__(self, n: SupportsIndex, /) -> list[_T]: ...
    def __rmul__(self, n: SupportsIndex, /) -> list[_T]: ...
    def __imul__(self, value: SupportsIndex, /) -> Self: ...
    def __reversed__(self) -> Iterator[_T]: ...
    def append(self, object: _T, /) -> None: ...
    def extend(self, iterable: Iterable[_T], /) -> None: ...
    def pop(self, index: SupportsIndex = ..., /) -> _T: ...
    def index(self, value: _T, start: SupportsIndex = ..., stop: SupportsIndex = ..., /) -> int: ...
    def count(self, value: _T, /) -> int: ...
    def insert(self, index: SupportsIndex, object: _T, /) -> None: ...
    def remove(self, value: _T, /) -> None: ...
    # Use BaseListProxy[SupportsRichComparisonT] for the first overload rather than [SupportsRichComparison]
    # to work around invariance
    @overload
    def sort(self: BaseListProxy[SupportsRichComparisonT], *, key: None = None, reverse: bool = ...) -> None: ...
    @overload
    def sort(self, *, key: Callable[[_T], SupportsRichComparison], reverse: bool = ...) -> None: ...

class ListProxy(BaseListProxy[_T]):
    def __iadd__(self, value: Iterable[_T], /) -> Self: ...  # type: ignore[override]
    def __imul__(self, value: SupportsIndex, /) -> Self: ...  # type: ignore[override]
    if sys.version_info >= (3, 13):
        def __class_getitem__(cls, args: Any, /) -> Any:
            """Represent a PEP 585 generic type

            E.g. for t = list[int], t.__origin__ is list and t.__args__ is (int,).
            """

# Send is (kind, result)
# Receive is (id, methodname, args, kwds)
_ServerConnection: TypeAlias = Connection[tuple[str, Any], tuple[str, str, Iterable[Any], Mapping[str, Any]]]

# Returned by BaseManager.get_server()
class Server:
    """
    Server class which runs in a process controlled by a manager object
    """

    address: _Address | None
    id_to_obj: dict[str, tuple[Any, set[str], dict[str, str]]]
    fallback_mapping: dict[str, Callable[[_ServerConnection, str, Any], Any]]
    public: list[str]
    # Registry values are (callable, exposed, method_to_typeid, proxytype)
    def __init__(
        self,
        registry: dict[str, tuple[Callable[..., Any], Iterable[str], dict[str, str], Any]],
        address: _Address | None,
        authkey: bytes,
        serializer: str,
    ) -> None: ...
    def serve_forever(self) -> None:
        """
        Run the server forever
        """

    def accepter(self) -> None: ...
    if sys.version_info >= (3, 10):
        def handle_request(self, conn: _ServerConnection) -> None:
            """
            Handle a new connection
            """
    else:
        def handle_request(self, c: _ServerConnection) -> None:
            """
            Handle a new connection
            """

    def serve_client(self, conn: _ServerConnection) -> None:
        """
        Handle requests from the proxies in a particular process/thread
        """

    def fallback_getvalue(self, conn: _ServerConnection, ident: str, obj: _T) -> _T: ...
    def fallback_str(self, conn: _ServerConnection, ident: str, obj: Any) -> str: ...
    def fallback_repr(self, conn: _ServerConnection, ident: str, obj: Any) -> str: ...
    def dummy(self, c: _ServerConnection) -> None: ...
    def debug_info(self, c: _ServerConnection) -> str:
        """
        Return some info --- useful to spot problems with refcounting
        """

    def number_of_objects(self, c: _ServerConnection) -> int:
        """
        Number of shared objects
        """

    def shutdown(self, c: _ServerConnection) -> None:
        """
        Shutdown this process
        """

    def create(self, c: _ServerConnection, typeid: str, /, *args: Any, **kwds: Any) -> tuple[str, tuple[str, ...]]:
        """
        Create a new shared object and return its id
        """

    def get_methods(self, c: _ServerConnection, token: Token) -> set[str]:
        """
        Return the methods of the shared object indicated by token
        """

    def accept_connection(self, c: _ServerConnection, name: str) -> None:
        """
        Spawn a new thread to serve this connection
        """

    def incref(self, c: _ServerConnection, ident: str) -> None: ...
    def decref(self, c: _ServerConnection, ident: str) -> None: ...

class BaseManager:
    """
    Base class for managers
    """

    if sys.version_info >= (3, 11):
        def __init__(
            self,
            address: _Address | None = None,
            authkey: bytes | None = None,
            serializer: str = "pickle",
            ctx: BaseContext | None = None,
            *,
            shutdown_timeout: float = 1.0,
        ) -> None: ...
    else:
        def __init__(
            self,
            address: _Address | None = None,
            authkey: bytes | None = None,
            serializer: str = "pickle",
            ctx: BaseContext | None = None,
        ) -> None: ...

    def get_server(self) -> Server:
        """
        Return server object with serve_forever() method and address attribute
        """

    def connect(self) -> None:
        """
        Connect manager object to the server process
        """

    def start(self, initializer: Callable[..., object] | None = None, initargs: Iterable[Any] = ()) -> None:
        """
        Spawn a server process for this manager object
        """
    shutdown: _Finalize  # only available after start() was called
    def join(self, timeout: float | None = None) -> None:  # undocumented
        """
        Join the manager process (if it has been spawned)
        """

    @property
    def address(self) -> _Address | None: ...
    @classmethod
    def register(
        cls,
        typeid: str,
        callable: Callable[..., object] | None = None,
        proxytype: Any = None,
        exposed: Sequence[str] | None = None,
        method_to_typeid: Mapping[str, str] | None = None,
        create_method: bool = True,
    ) -> None:
        """
        Register a typeid with the manager type
        """

    def __enter__(self) -> Self: ...
    def __exit__(
        self, exc_type: type[BaseException] | None, exc_val: BaseException | None, exc_tb: TracebackType | None
    ) -> None: ...

class SyncManager(BaseManager):
    """
    Subclass of `BaseManager` which supports a number of shared object types.

    The types registered are those intended for the synchronization
    of threads, plus `dict`, `list` and `Namespace`.

    The `multiprocessing.Manager()` function creates started instances of
    this class.
    """

    def Barrier(
        self, parties: int, action: Callable[[], None] | None = None, timeout: float | None = None
    ) -> threading.Barrier: ...
    def BoundedSemaphore(self, value: int = 1) -> threading.BoundedSemaphore: ...
    def Condition(self, lock: threading.Lock | threading._RLock | None = None) -> threading.Condition: ...
    def Event(self) -> threading.Event: ...
    def Lock(self) -> threading.Lock: ...
    def Namespace(self) -> _Namespace: ...
    def Pool(
        self,
        processes: int | None = None,
        initializer: Callable[..., object] | None = None,
        initargs: Iterable[Any] = (),
        maxtasksperchild: int | None = None,
        context: Any | None = None,
    ) -> pool.Pool: ...
    def Queue(self, maxsize: int = ...) -> queue.Queue[Any]: ...
    def JoinableQueue(self, maxsize: int = ...) -> queue.Queue[Any]: ...
    def RLock(self) -> threading.RLock: ...
    def Semaphore(self, value: int = 1) -> threading.Semaphore: ...
    def Array(self, typecode: Any, sequence: Sequence[_T]) -> Sequence[_T]: ...
    def Value(self, typecode: Any, value: _T) -> ValueProxy[_T]: ...
    # Overloads are copied from builtins.dict.__init__
    @overload
    def dict(self) -> DictProxy[Any, Any]: ...
    @overload
    def dict(self, **kwargs: _VT) -> DictProxy[str, _VT]: ...
    @overload
    def dict(self, map: SupportsKeysAndGetItem[_KT, _VT], /) -> DictProxy[_KT, _VT]: ...
    @overload
    def dict(self, map: SupportsKeysAndGetItem[str, _VT], /, **kwargs: _VT) -> DictProxy[str, _VT]: ...
    @overload
    def dict(self, iterable: Iterable[tuple[_KT, _VT]], /) -> DictProxy[_KT, _VT]: ...
    @overload
    def dict(self, iterable: Iterable[tuple[str, _VT]], /, **kwargs: _VT) -> DictProxy[str, _VT]: ...
    @overload
    def dict(self, iterable: Iterable[list[str]], /) -> DictProxy[str, str]: ...
    @overload
    def dict(self, iterable: Iterable[list[bytes]], /) -> DictProxy[bytes, bytes]: ...
    @overload
    def list(self, sequence: Sequence[_T], /) -> ListProxy[_T]: ...
    @overload
    def list(self) -> ListProxy[Any]: ...
    if sys.version_info >= (3, 14):
        @overload
        def set(self, iterable: Iterable[_T], /) -> SetProxy[_T]: ...
        @overload
        def set(self) -> SetProxy[Any]: ...

class RemoteError(Exception): ...

class SharedMemoryServer(Server):
    def track_segment(self, c: _ServerConnection, segment_name: str) -> None:
        """Adds the supplied shared memory block name to Server's tracker."""

    def release_segment(self, c: _ServerConnection, segment_name: str) -> None:
        """Calls unlink() on the shared memory block with the supplied name
        and removes it from the tracker instance inside the Server.
        """

    def list_segments(self, c: _ServerConnection) -> list[str]:
        """Returns a list of names of shared memory blocks that the Server
        is currently tracking.
        """

class SharedMemoryManager(BaseManager):
    """Like SyncManager but uses SharedMemoryServer instead of Server.

    It provides methods for creating and returning SharedMemory instances
    and for creating a list-like object (ShareableList) backed by shared
    memory.  It also provides methods that create and return Proxy Objects
    that support synchronization across processes (i.e. multi-process-safe
    locks and semaphores).
    """

    def get_server(self) -> SharedMemoryServer:
        """Better than monkeypatching for now; merge into Server ultimately"""

    def SharedMemory(self, size: int) -> _SharedMemory:
        """Returns a new SharedMemory instance with the specified size in
        bytes, to be tracked by the manager.
        """

    def ShareableList(self, sequence: Iterable[_SLT] | None) -> _ShareableList[_SLT]:
        """Returns a new ShareableList instance populated with the values
        from the input sequence, to be tracked by the manager.
        """

    def __del__(self) -> None: ...
