from google.protobuf.internal import containers as _containers
from google.protobuf.internal import enum_type_wrapper as _enum_type_wrapper
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from collections.abc import Iterable as _Iterable, Mapping as _Mapping
from typing import ClassVar as _ClassVar, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class ComicJobStatus(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    COMIC_JOB_UNKNOWN: _ClassVar[ComicJobStatus]
    COMIC_JOB_QUEUED: _ClassVar[ComicJobStatus]
    COMIC_JOB_RUNNING: _ClassVar[ComicJobStatus]
    COMIC_JOB_COMPLETED: _ClassVar[ComicJobStatus]
    COMIC_JOB_FAILED: _ClassVar[ComicJobStatus]
    COMIC_JOB_CANCELLED: _ClassVar[ComicJobStatus]
COMIC_JOB_UNKNOWN: ComicJobStatus
COMIC_JOB_QUEUED: ComicJobStatus
COMIC_JOB_RUNNING: ComicJobStatus
COMIC_JOB_COMPLETED: ComicJobStatus
COMIC_JOB_FAILED: ComicJobStatus
COMIC_JOB_CANCELLED: ComicJobStatus

class StartComicGenerationRequest(_message.Message):
    __slots__ = ("job_id", "user_id", "summary", "style", "num_panels", "request_id")
    JOB_ID_FIELD_NUMBER: _ClassVar[int]
    USER_ID_FIELD_NUMBER: _ClassVar[int]
    SUMMARY_FIELD_NUMBER: _ClassVar[int]
    STYLE_FIELD_NUMBER: _ClassVar[int]
    NUM_PANELS_FIELD_NUMBER: _ClassVar[int]
    REQUEST_ID_FIELD_NUMBER: _ClassVar[int]
    job_id: str
    user_id: str
    summary: str
    style: str
    num_panels: int
    request_id: str
    def __init__(self, job_id: _Optional[str] = ..., user_id: _Optional[str] = ..., summary: _Optional[str] = ..., style: _Optional[str] = ..., num_panels: _Optional[int] = ..., request_id: _Optional[str] = ...) -> None: ...

class StartComicGenerationResponse(_message.Message):
    __slots__ = ("job_id", "status")
    JOB_ID_FIELD_NUMBER: _ClassVar[int]
    STATUS_FIELD_NUMBER: _ClassVar[int]
    job_id: str
    status: ComicJobStatus
    def __init__(self, job_id: _Optional[str] = ..., status: _Optional[_Union[ComicJobStatus, str]] = ...) -> None: ...

class PanelResult(_message.Message):
    __slots__ = ("index", "caption_vi", "image_url", "prompt_en", "seed", "status", "error_message", "speaker", "panel_type", "speaker_position")
    INDEX_FIELD_NUMBER: _ClassVar[int]
    CAPTION_VI_FIELD_NUMBER: _ClassVar[int]
    IMAGE_URL_FIELD_NUMBER: _ClassVar[int]
    PROMPT_EN_FIELD_NUMBER: _ClassVar[int]
    SEED_FIELD_NUMBER: _ClassVar[int]
    STATUS_FIELD_NUMBER: _ClassVar[int]
    ERROR_MESSAGE_FIELD_NUMBER: _ClassVar[int]
    SPEAKER_FIELD_NUMBER: _ClassVar[int]
    PANEL_TYPE_FIELD_NUMBER: _ClassVar[int]
    SPEAKER_POSITION_FIELD_NUMBER: _ClassVar[int]
    index: int
    caption_vi: str
    image_url: str
    prompt_en: str
    seed: int
    status: str
    error_message: str
    speaker: str
    panel_type: str
    speaker_position: str
    def __init__(self, index: _Optional[int] = ..., caption_vi: _Optional[str] = ..., image_url: _Optional[str] = ..., prompt_en: _Optional[str] = ..., seed: _Optional[int] = ..., status: _Optional[str] = ..., error_message: _Optional[str] = ..., speaker: _Optional[str] = ..., panel_type: _Optional[str] = ..., speaker_position: _Optional[str] = ...) -> None: ...

class GetComicJobStatusRequest(_message.Message):
    __slots__ = ("job_id",)
    JOB_ID_FIELD_NUMBER: _ClassVar[int]
    job_id: str
    def __init__(self, job_id: _Optional[str] = ...) -> None: ...

class GetComicJobStatusResponse(_message.Message):
    __slots__ = ("job_id", "status", "progress_current", "progress_total", "page_image_url", "panels", "error_message", "current_step")
    JOB_ID_FIELD_NUMBER: _ClassVar[int]
    STATUS_FIELD_NUMBER: _ClassVar[int]
    PROGRESS_CURRENT_FIELD_NUMBER: _ClassVar[int]
    PROGRESS_TOTAL_FIELD_NUMBER: _ClassVar[int]
    PAGE_IMAGE_URL_FIELD_NUMBER: _ClassVar[int]
    PANELS_FIELD_NUMBER: _ClassVar[int]
    ERROR_MESSAGE_FIELD_NUMBER: _ClassVar[int]
    CURRENT_STEP_FIELD_NUMBER: _ClassVar[int]
    job_id: str
    status: ComicJobStatus
    progress_current: int
    progress_total: int
    page_image_url: str
    panels: _containers.RepeatedCompositeFieldContainer[PanelResult]
    error_message: str
    current_step: str
    def __init__(self, job_id: _Optional[str] = ..., status: _Optional[_Union[ComicJobStatus, str]] = ..., progress_current: _Optional[int] = ..., progress_total: _Optional[int] = ..., page_image_url: _Optional[str] = ..., panels: _Optional[_Iterable[_Union[PanelResult, _Mapping]]] = ..., error_message: _Optional[str] = ..., current_step: _Optional[str] = ...) -> None: ...

class CancelComicJobRequest(_message.Message):
    __slots__ = ("job_id",)
    JOB_ID_FIELD_NUMBER: _ClassVar[int]
    job_id: str
    def __init__(self, job_id: _Optional[str] = ...) -> None: ...

class CancelComicJobResponse(_message.Message):
    __slots__ = ("job_id", "status")
    JOB_ID_FIELD_NUMBER: _ClassVar[int]
    STATUS_FIELD_NUMBER: _ClassVar[int]
    job_id: str
    status: ComicJobStatus
    def __init__(self, job_id: _Optional[str] = ..., status: _Optional[_Union[ComicJobStatus, str]] = ...) -> None: ...

class CheckHealthRequest(_message.Message):
    __slots__ = ()
    def __init__(self) -> None: ...

class CheckHealthResponse(_message.Message):
    __slots__ = ("is_alive", "dependencies")
    class DependenciesEntry(_message.Message):
        __slots__ = ("key", "value")
        KEY_FIELD_NUMBER: _ClassVar[int]
        VALUE_FIELD_NUMBER: _ClassVar[int]
        key: str
        value: str
        def __init__(self, key: _Optional[str] = ..., value: _Optional[str] = ...) -> None: ...
    IS_ALIVE_FIELD_NUMBER: _ClassVar[int]
    DEPENDENCIES_FIELD_NUMBER: _ClassVar[int]
    is_alive: bool
    dependencies: _containers.ScalarMap[str, str]
    def __init__(self, is_alive: _Optional[bool] = ..., dependencies: _Optional[_Mapping[str, str]] = ...) -> None: ...
