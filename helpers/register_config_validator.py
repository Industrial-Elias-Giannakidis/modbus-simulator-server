from typing import List

from helpers.classes import MemoryArea, RegisterConfig, RegisterType

# Minimum register count (16-bit words) required for each type.
_TYPE_LENGTH = {
    RegisterType.INT16: 1,
    RegisterType.UINT16: 1,
    RegisterType.WORD: 1,
    RegisterType.BOOLEAN: 1,
    RegisterType.INT32: 2,
    RegisterType.UINT32: 2,
    RegisterType.FLOAT32: 2,
    RegisterType.INT64: 4,
    RegisterType.UINT64: 4,
    RegisterType.FLOAT64: 4,
}

class RegisterConfigValidator:
    def validate(self, config: RegisterConfig) -> RegisterConfig:
        config.errors = []
        config.valid = True

        config = self._validate_offset(config)
        config = self._validate_length(config)
        config = self._validate_bit_offset(config)
        config = self._validate_scalling(config)
        config = self._validate_memory_area(config)
        config = self._validate_boolean_addresses(config)

        return config

    def validate_all(self, configs: List[RegisterConfig]) -> List[RegisterConfig]:
        return [self.validate(config) for config in configs]

    def is_valid(self, config: RegisterConfig) -> bool:
        return config.valid

    def validate_or_raise(self, config: RegisterConfig) -> None:
        if not self.is_valid(config):
            raise ValueError(
                f"Invalid RegisterConfig at memory area {config.memory_area} and at offset {config.offset}:\n"
                + "\n".join(f"  - {e}" for e in config.errors)
            )

    # -- helpers -------------------------------------------------------------

    def _remove(self, config: RegisterConfig, *attrs: str) -> None:
        for attr in attrs:
            vars(config).pop(attr, None)

    # -- individual checks --------------------------------------------------

    def _validate_offset(self, config: RegisterConfig) -> RegisterConfig:
        if config.offset < 0:
            config.errors.append(f"offset must be >= 0, got {config.offset}")
            config.valid = False
        return config

    def _validate_length(self, config: RegisterConfig) -> RegisterConfig:
        length = _TYPE_LENGTH.get(config.type)
        if length is None:
            config.errors.append(f"register type is not valid, got {config.type}")
            config.valid = False
        else:
            config.length = length
        return config

    def _validate_bit_offset(self, config: RegisterConfig) -> RegisterConfig:
        if config.type == RegisterType.WORD:

            if config.bit_offset is None and config.bit_length is None:
                return config

            if config.bit_offset is None:
                config.bit_offset = 0

            if config.bit_length is None:
                config.bit_length = 16 - config.bit_offset

            if config.bit_offset < 0 or config.bit_offset + config.bit_length > 16:
                config.errors.append("register word has overflow bit offset and length")
                config.valid = False

            return config
        else:
            self._remove(config, "bit_offset", "bit_length")
            return config

    def _validate_scalling(self, config: RegisterConfig) -> RegisterConfig:
        if config.memory_area == MemoryArea.COIL or config.memory_area == MemoryArea.DISCRETE_INPUT:
            self._remove(config, "max_value", "min_value", "scale")
            return config

        if config.type in (RegisterType.FLOAT32, RegisterType.FLOAT64, RegisterType.BOOLEAN, RegisterType.WORD):
            self._remove(config, "max_value", "min_value", "scale")
            return config

        has_max = config.max_value is not None
        has_min = config.min_value is not None
        has_scale = config.scale is not None

        if has_max and not has_min:
            config.errors.append("register cannot be scaled with max_value but without min_value")
            config.valid = False

        if not has_max and has_min:
            config.errors.append("register cannot be scaled with min_value but without max_value")
            config.valid = False

        if has_max and has_min:
            if config.max_value < config.min_value:
                config.errors.append("max_value cannot be less than min_value")
                config.valid = False

        if has_scale and (has_min or has_max):
            config.errors.append("cannot use both scale and min/max value scaling at the same time")
            config.valid = False

        return config

    def _validate_memory_area(self, config: RegisterConfig) -> RegisterConfig:
        try:
            MemoryArea(config.memory_area)
        except ValueError:
            config.errors.append(f"no valid memory_area, got {config.memory_area}")
            config.valid = False

        return config

    def _validate_boolean_addresses(self, config: RegisterConfig) -> RegisterConfig:
        if config.memory_area == MemoryArea.COIL or config.memory_area == MemoryArea.DISCRETE_INPUT:
            self._remove(
                config,
                "length", "bit_offset", "bit_length",
                "max_value", "min_value", "scale",
                "first_word_low", "first_double_word_low",
                "big_endian", "modicon",
            )
            config.type = RegisterType.BOOLEAN
        return config


