from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional, Union

class MemoryArea(str, Enum):
    DISCRETE_INPUT = "discrete-input"
    HOLDING_REGISTER = "holding-register"
    COIL = "coil"
    INPUT_REGISTER = "input-register"

class RegisterType(str, Enum):
    INT16 = "int16"
    UINT16 = "uint16"
    INT32 = "int32"
    UINT32 = "uint32"
    INT64 = "int64"
    UINT64 = "uint64"
    FLOAT32 = "float32"
    FLOAT64 = "float64"
    BOOLEAN = "boolean"
    WORD = "word"

@dataclass
class AddressSnapshot:
    offset: int
    memory_area: MemoryArea
    value: Union[int, float, bool]

@dataclass
class RegisterConfig:
    offset: int
    memory_area: MemoryArea
    name: str
    type: Optional[RegisterType] = None
    description: str = ""
    length: Optional[int] = None
    bit_offset: Optional[int] = None
    bit_length: Optional[int] = None
    max_value: Optional[float] = None
    min_value: Optional[float] = None
    scale: Optional[float] = None
    errors: List[str] = field(default_factory=list)

@dataclass
class ByterOrderConfig:
    first_word_low: bool = False
    first_double_word_low: bool = False
    big_endian: bool = True
    modicon: bool = False