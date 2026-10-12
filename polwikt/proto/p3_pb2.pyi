from google.protobuf.internal import containers as _containers
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from collections.abc import Iterable as _Iterable, Mapping as _Mapping
from typing import ClassVar as _ClassVar, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class TemplateArg(_message.Message):
    __slots__ = ("key", "value")
    KEY_FIELD_NUMBER: _ClassVar[int]
    VALUE_FIELD_NUMBER: _ClassVar[int]
    key: str
    value: str
    def __init__(self, key: _Optional[str] = ..., value: _Optional[str] = ...) -> None: ...

class TemplateCall(_message.Message):
    __slots__ = ("name", "written_name", "args")
    NAME_FIELD_NUMBER: _ClassVar[int]
    WRITTEN_NAME_FIELD_NUMBER: _ClassVar[int]
    ARGS_FIELD_NUMBER: _ClassVar[int]
    name: str
    written_name: str
    args: _containers.RepeatedCompositeFieldContainer[TemplateArg]
    def __init__(self, name: _Optional[str] = ..., written_name: _Optional[str] = ..., args: _Optional[_Iterable[_Union[TemplateArg, _Mapping]]] = ...) -> None: ...

class EntryCalls(_message.Message):
    __slots__ = ("headword", "inflection")
    HEADWORD_FIELD_NUMBER: _ClassVar[int]
    INFLECTION_FIELD_NUMBER: _ClassVar[int]
    headword: _containers.RepeatedCompositeFieldContainer[TemplateCall]
    inflection: _containers.RepeatedCompositeFieldContainer[TemplateCall]
    def __init__(self, headword: _Optional[_Iterable[_Union[TemplateCall, _Mapping]]] = ..., inflection: _Optional[_Iterable[_Union[TemplateCall, _Mapping]]] = ...) -> None: ...

class EtymologyCalls(_message.Message):
    __slots__ = ("calls",)
    CALLS_FIELD_NUMBER: _ClassVar[int]
    calls: _containers.RepeatedCompositeFieldContainer[TemplateCall]
    def __init__(self, calls: _Optional[_Iterable[_Union[TemplateCall, _Mapping]]] = ...) -> None: ...

class UnknownSection(_message.Message):
    __slots__ = ("heading", "wikitext")
    HEADING_FIELD_NUMBER: _ClassVar[int]
    WIKITEXT_FIELD_NUMBER: _ClassVar[int]
    heading: str
    wikitext: str
    def __init__(self, heading: _Optional[str] = ..., wikitext: _Optional[str] = ...) -> None: ...

class PageRecord(_message.Message):
    __slots__ = ("page_id", "revision_id", "title", "word", "entry_calls", "etymology_calls", "unknown_sections")
    PAGE_ID_FIELD_NUMBER: _ClassVar[int]
    REVISION_ID_FIELD_NUMBER: _ClassVar[int]
    TITLE_FIELD_NUMBER: _ClassVar[int]
    WORD_FIELD_NUMBER: _ClassVar[int]
    ENTRY_CALLS_FIELD_NUMBER: _ClassVar[int]
    ETYMOLOGY_CALLS_FIELD_NUMBER: _ClassVar[int]
    UNKNOWN_SECTIONS_FIELD_NUMBER: _ClassVar[int]
    page_id: int
    revision_id: int
    title: str
    word: bytes
    entry_calls: _containers.RepeatedCompositeFieldContainer[EntryCalls]
    etymology_calls: _containers.RepeatedCompositeFieldContainer[EtymologyCalls]
    unknown_sections: _containers.RepeatedCompositeFieldContainer[UnknownSection]
    def __init__(self, page_id: _Optional[int] = ..., revision_id: _Optional[int] = ..., title: _Optional[str] = ..., word: _Optional[bytes] = ..., entry_calls: _Optional[_Iterable[_Union[EntryCalls, _Mapping]]] = ..., etymology_calls: _Optional[_Iterable[_Union[EtymologyCalls, _Mapping]]] = ..., unknown_sections: _Optional[_Iterable[_Union[UnknownSection, _Mapping]]] = ...) -> None: ...
