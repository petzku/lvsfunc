from typing import Any

countby: Any

class groupby:
    @classmethod
    def __init__(self, *args, **kwargs) -> None: ...
    def __iter__(self) -> Any: ...
    def __next__(self) -> Any: ...
    def __reduce__(self) -> Any: ...
    def __setstate__(self, state) -> Any: ...

class map:
    @classmethod
    def __init__(self, *args, **kwargs) -> None: ...
    def __iter__(self) -> Any: ...
    def __next__(self) -> Any: ...
    def __reduce__(self) -> Any: ...

class partitionby:
    @classmethod
    def __init__(self, *args, **kwargs) -> None: ...
    def __iter__(self) -> Any: ...
    def __next__(self) -> Any: ...
    def __reduce__(self) -> Any: ...
    def __setstate__(self, state) -> Any: ...