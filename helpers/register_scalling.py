from typing import List

from helpers.classes import AddressSnapshot, RegisterConfig, RegisterType


_INT_UINT_TYPES = {
    RegisterType.INT16,
    RegisterType.UINT16,
    RegisterType.INT32,
    RegisterType.UINT32,
    RegisterType.INT64,
    RegisterType.UINT64,
}

_TYPE_RANGES = {
    RegisterType.INT16:  (-32768,        32767),
    RegisterType.UINT16: (0,             65535),
    RegisterType.INT32:  (-(2**31),      2**31 - 1),
    RegisterType.UINT32: (0,             2**32 - 1),
    RegisterType.INT64:  (-(2**63),      2**63 - 1),
    RegisterType.UINT64: (0,             2**64 - 1),
}


class RegisterScalling:
    def __init__(self, configs: List[RegisterConfig]):
        self._config_map = {(c.offset, c.memory_area): c for c in configs}

    def _scale_value(self, value: float, conf: RegisterConfig) -> float:
        t = conf.type

        if t not in _INT_UINT_TYPES:
            return value

        if conf.scale is not None:
            return value * conf.scale

        if t in _INT_UINT_TYPES and conf.min_value is not None:
            type_min, type_max = _TYPE_RANGES[t]
            return conf.min_value + (value - type_min) / (type_max - type_min) * (conf.max_value - conf.min_value)

        return value

    def _unscale_value(self, value: float, conf: RegisterConfig) -> float:
        t = conf.type

        if t not in _INT_UINT_TYPES:
            return value

        if conf.scale is not None:
            return value / conf.scale

        if t in _INT_UINT_TYPES and conf.min_value is not None:
            type_min, type_max = _TYPE_RANGES[t]
            return type_min + (value - conf.min_value) / (conf.max_value - conf.min_value) * (type_max - type_min)

        return value

    def scale(self, snapshots: List[AddressSnapshot]) -> List[AddressSnapshot]:
        result = []
        for s in snapshots:
            conf = self._config_map.get((s.offset, s.memory_area))
            value = self._scale_value(s.value, conf) if conf is not None else s.value
            result.append(AddressSnapshot(s.offset, s.memory_area, value))
        return result

    def unscale(self, snapshots: List[AddressSnapshot]) -> List[AddressSnapshot]:
        result = []
        for s in snapshots:
            conf = self._config_map.get((s.offset, s.memory_area))
            value = self._unscale_value(s.value, conf) if conf is not None else s.value
            result.append(AddressSnapshot(s.offset, s.memory_area, value))
        return result
