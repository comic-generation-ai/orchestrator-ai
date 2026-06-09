from google.protobuf.internal import containers as _containers
from google.protobuf.internal import enum_type_wrapper as _enum_type_wrapper
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from collections.abc import Iterable as _Iterable, Mapping as _Mapping
from typing import ClassVar as _ClassVar, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class ImageGenerationStatus(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    PENDING: _ClassVar[ImageGenerationStatus]
    PROCESSING: _ClassVar[ImageGenerationStatus]
    SUCCESS: _ClassVar[ImageGenerationStatus]
    FAILED: _ClassVar[ImageGenerationStatus]
PENDING: ImageGenerationStatus
PROCESSING: ImageGenerationStatus
SUCCESS: ImageGenerationStatus
FAILED: ImageGenerationStatus

class GenerateImageRequest(_message.Message):
    __slots__ = ("reference_image_url", "prompt", "width", "height", "seed", "num_inference_steps", "caption_text", "speech_bubbles")
    REFERENCE_IMAGE_URL_FIELD_NUMBER: _ClassVar[int]
    PROMPT_FIELD_NUMBER: _ClassVar[int]
    WIDTH_FIELD_NUMBER: _ClassVar[int]
    HEIGHT_FIELD_NUMBER: _ClassVar[int]
    SEED_FIELD_NUMBER: _ClassVar[int]
    NUM_INFERENCE_STEPS_FIELD_NUMBER: _ClassVar[int]
    CAPTION_TEXT_FIELD_NUMBER: _ClassVar[int]
    SPEECH_BUBBLES_FIELD_NUMBER: _ClassVar[int]
    reference_image_url: str
    prompt: str
    width: int
    height: int
    seed: int
    num_inference_steps: int
    caption_text: str
    speech_bubbles: _containers.RepeatedCompositeFieldContainer[SpeechBuble]
    def __init__(self, reference_image_url: _Optional[str] = ..., prompt: _Optional[str] = ..., width: _Optional[int] = ..., height: _Optional[int] = ..., seed: _Optional[int] = ..., num_inference_steps: _Optional[int] = ..., caption_text: _Optional[str] = ..., speech_bubbles: _Optional[_Iterable[_Union[SpeechBuble, _Mapping]]] = ...) -> None: ...

class GenerateImageResponse(_message.Message):
    __slots__ = ("task_id", "status")
    TASK_ID_FIELD_NUMBER: _ClassVar[int]
    STATUS_FIELD_NUMBER: _ClassVar[int]
    task_id: str
    status: ImageGenerationStatus
    def __init__(self, task_id: _Optional[str] = ..., status: _Optional[_Union[ImageGenerationStatus, str]] = ...) -> None: ...

class TaskStatusRequest(_message.Message):
    __slots__ = ("task_id",)
    TASK_ID_FIELD_NUMBER: _ClassVar[int]
    task_id: str
    def __init__(self, task_id: _Optional[str] = ...) -> None: ...

class TaskStatusResponse(_message.Message):
    __slots__ = ("task_id", "status", "minio_url", "error_message")
    TASK_ID_FIELD_NUMBER: _ClassVar[int]
    STATUS_FIELD_NUMBER: _ClassVar[int]
    MINIO_URL_FIELD_NUMBER: _ClassVar[int]
    ERROR_MESSAGE_FIELD_NUMBER: _ClassVar[int]
    task_id: str
    status: ImageGenerationStatus
    minio_url: str
    error_message: str
    def __init__(self, task_id: _Optional[str] = ..., status: _Optional[_Union[ImageGenerationStatus, str]] = ..., minio_url: _Optional[str] = ..., error_message: _Optional[str] = ...) -> None: ...

class CancelRequest(_message.Message):
    __slots__ = ("task_id",)
    TASK_ID_FIELD_NUMBER: _ClassVar[int]
    task_id: str
    def __init__(self, task_id: _Optional[str] = ...) -> None: ...

class CancelResponse(_message.Message):
    __slots__ = ("task_id", "status")
    TASK_ID_FIELD_NUMBER: _ClassVar[int]
    STATUS_FIELD_NUMBER: _ClassVar[int]
    task_id: str
    status: ImageGenerationStatus
    def __init__(self, task_id: _Optional[str] = ..., status: _Optional[_Union[ImageGenerationStatus, str]] = ...) -> None: ...

class CheckHealthRequest(_message.Message):
    __slots__ = ()
    def __init__(self) -> None: ...

class CheckHealthResponse(_message.Message):
    __slots__ = ("is_alive", "versions")
    class VersionsEntry(_message.Message):
        __slots__ = ("key", "value")
        KEY_FIELD_NUMBER: _ClassVar[int]
        VALUE_FIELD_NUMBER: _ClassVar[int]
        key: str
        value: str
        def __init__(self, key: _Optional[str] = ..., value: _Optional[str] = ...) -> None: ...
    IS_ALIVE_FIELD_NUMBER: _ClassVar[int]
    VERSIONS_FIELD_NUMBER: _ClassVar[int]
    is_alive: bool
    versions: _containers.ScalarMap[str, str]
    def __init__(self, is_alive: _Optional[bool] = ..., versions: _Optional[_Mapping[str, str]] = ...) -> None: ...

class CheckGpuHealthRequest(_message.Message):
    __slots__ = ()
    def __init__(self) -> None: ...

class CheckGpuHealthResponse(_message.Message):
    __slots__ = ("is_healthy", "gpu_name", "gpu_memory_usage", "gpu_memory_free", "gpu_memory_total", "gpu_memory_used")
    IS_HEALTHY_FIELD_NUMBER: _ClassVar[int]
    GPU_NAME_FIELD_NUMBER: _ClassVar[int]
    GPU_MEMORY_USAGE_FIELD_NUMBER: _ClassVar[int]
    GPU_MEMORY_FREE_FIELD_NUMBER: _ClassVar[int]
    GPU_MEMORY_TOTAL_FIELD_NUMBER: _ClassVar[int]
    GPU_MEMORY_USED_FIELD_NUMBER: _ClassVar[int]
    is_healthy: bool
    gpu_name: str
    gpu_memory_usage: str
    gpu_memory_free: str
    gpu_memory_total: str
    gpu_memory_used: str
    def __init__(self, is_healthy: _Optional[bool] = ..., gpu_name: _Optional[str] = ..., gpu_memory_usage: _Optional[str] = ..., gpu_memory_free: _Optional[str] = ..., gpu_memory_total: _Optional[str] = ..., gpu_memory_used: _Optional[str] = ...) -> None: ...

class ClearGpuCacheRequest(_message.Message):
    __slots__ = ()
    def __init__(self) -> None: ...

class ClearGpuCacheResponse(_message.Message):
    __slots__ = ("is_cleared",)
    IS_CLEARED_FIELD_NUMBER: _ClassVar[int]
    is_cleared: bool
    def __init__(self, is_cleared: _Optional[bool] = ...) -> None: ...

class SpeechBuble(_message.Message):
    __slots__ = ("text", "bubble_type", "x_pos", "y_pos")
    TEXT_FIELD_NUMBER: _ClassVar[int]
    BUBBLE_TYPE_FIELD_NUMBER: _ClassVar[int]
    X_POS_FIELD_NUMBER: _ClassVar[int]
    Y_POS_FIELD_NUMBER: _ClassVar[int]
    text: str
    bubble_type: str
    x_pos: float
    y_pos: float
    def __init__(self, text: _Optional[str] = ..., bubble_type: _Optional[str] = ..., x_pos: _Optional[float] = ..., y_pos: _Optional[float] = ...) -> None: ...

class CheckCpuHealthRequest(_message.Message):
    __slots__ = ()
    def __init__(self) -> None: ...

class CheckCpuHealthResponse(_message.Message):
    __slots__ = ("is_healthy", "cpu_name", "cpu_memory_usage", "cpu_memory_free", "cpu_memory_total", "cpu_memory_used")
    IS_HEALTHY_FIELD_NUMBER: _ClassVar[int]
    CPU_NAME_FIELD_NUMBER: _ClassVar[int]
    CPU_MEMORY_USAGE_FIELD_NUMBER: _ClassVar[int]
    CPU_MEMORY_FREE_FIELD_NUMBER: _ClassVar[int]
    CPU_MEMORY_TOTAL_FIELD_NUMBER: _ClassVar[int]
    CPU_MEMORY_USED_FIELD_NUMBER: _ClassVar[int]
    is_healthy: bool
    cpu_name: str
    cpu_memory_usage: str
    cpu_memory_free: str
    cpu_memory_total: str
    cpu_memory_used: str
    def __init__(self, is_healthy: _Optional[bool] = ..., cpu_name: _Optional[str] = ..., cpu_memory_usage: _Optional[str] = ..., cpu_memory_free: _Optional[str] = ..., cpu_memory_total: _Optional[str] = ..., cpu_memory_used: _Optional[str] = ...) -> None: ...
