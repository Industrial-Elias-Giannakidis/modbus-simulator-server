"""
Tests for RegisterConfigValidator.

NOTE: The validator uses `_remove` (via vars(config).pop) to strip fields from
the validated config. After removal, the field is absent from the instance dict
(vars(config)) but the dataclass class-level default may still be accessible.
Assertions about stripped fields use `attr not in vars(config)` rather than
`not hasattr(config, attr)` for precise instance-level checks.
"""

import pytest

from helpers.classes import MemoryArea, RegisterConfig, RegisterType
from helpers.register_config_validator import RegisterConfigValidator

validator = RegisterConfigValidator()


# ---------------------------------------------------------------------------
# Factory helpers
# ---------------------------------------------------------------------------

def make_holding(
    offset=0,
    reg_type=RegisterType.INT16,
    **kwargs,
) -> RegisterConfig:
    return RegisterConfig(
        offset=offset,
        memory_area=MemoryArea.HOLDING_REGISTER,
        name="test",
        type=reg_type,
        **kwargs,
    )


def make_input_reg(
    offset=0,
    reg_type=RegisterType.FLOAT32,
    **kwargs,
) -> RegisterConfig:
    return RegisterConfig(
        offset=offset,
        memory_area=MemoryArea.INPUT_REGISTER,
        name="test",
        type=reg_type,
        **kwargs,
    )


def make_coil(offset=0, **kwargs) -> RegisterConfig:
    return RegisterConfig(
        offset=offset,
        memory_area=MemoryArea.COIL,
        name="test",
        type=RegisterType.BOOLEAN,
        **kwargs,
    )


def make_discrete(offset=0, **kwargs) -> RegisterConfig:
    return RegisterConfig(
        offset=offset,
        memory_area=MemoryArea.DISCRETE_INPUT,
        name="test",
        type=RegisterType.BOOLEAN,
        **kwargs,
    )


def make_float32(offset=0, **kwargs) -> RegisterConfig:
    """FLOAT32: max/min/scale stripped, never hits integer scaling logic."""
    return RegisterConfig(
        offset=offset,
        memory_area=MemoryArea.HOLDING_REGISTER,
        name="test",
        type=RegisterType.FLOAT32,
        **kwargs,
    )


def make_float64(offset=0, **kwargs) -> RegisterConfig:
    return RegisterConfig(
        offset=offset,
        memory_area=MemoryArea.HOLDING_REGISTER,
        name="test",
        type=RegisterType.FLOAT64,
        **kwargs,
    )


def make_boolean_holding(offset=0, **kwargs) -> RegisterConfig:
    return RegisterConfig(
        offset=offset,
        memory_area=MemoryArea.HOLDING_REGISTER,
        name="test",
        type=RegisterType.BOOLEAN,
        **kwargs,
    )


def make_int_holding(
    offset=0,
    reg_type=RegisterType.INT16,
    min_value=None,
    max_value=None,
    **kwargs,
) -> RegisterConfig:
    return RegisterConfig(
        offset=offset,
        memory_area=MemoryArea.HOLDING_REGISTER,
        name="test",
        type=reg_type,
        min_value=min_value,
        max_value=max_value,
        **kwargs,
    )


def absent(config: RegisterConfig, attr: str) -> bool:
    """True if attr was stripped from the config's instance dict."""
    return attr not in vars(config)


def present(config: RegisterConfig, attr: str) -> bool:
    return attr in vars(config)


# ---------------------------------------------------------------------------
# Sanity / smoke tests
# ---------------------------------------------------------------------------

class TestSanity:
    def test_float32_holding_const_is_valid(self):
        config = validator.validate(make_float32())
        assert config.valid is True
        assert config.errors == []

    def test_coil_const_is_valid(self):
        config = validator.validate(make_coil())
        assert config.valid is True
        assert config.errors == []

    def test_discrete_input_const_is_valid(self):
        config = validator.validate(make_discrete())
        assert config.valid is True
        assert config.errors == []

    def test_boolean_holding_const_is_valid(self):
        config = validator.validate(make_boolean_holding())
        assert config.valid is True
        assert config.errors == []

    def test_int16_holding_no_scaling_is_valid(self):
        """Integer type without explicit min/max should validate cleanly."""
        config = validator.validate(make_int_holding())
        assert config.valid is True
        assert config.errors == []

    def test_int16_holding_with_min_max_is_valid(self):
        config = validator.validate(make_int_holding(min_value=0.0, max_value=100.0))
        assert config.valid is True

    def test_word_no_bit_fields_is_valid(self):
        """WORD with neither bit_offset nor bit_length should validate cleanly."""
        config = RegisterConfig(
            offset=0, memory_area=MemoryArea.HOLDING_REGISTER,
            name="test",
            type=RegisterType.WORD,
        )
        config = validator.validate(config)
        assert config.valid is True


# ---------------------------------------------------------------------------
# _validate_offset
# ---------------------------------------------------------------------------

class TestValidateOffset:
    def test_zero_offset_is_valid(self):
        config = validator.validate(make_coil(offset=0))
        assert config.valid is True

    def test_positive_offset_is_valid(self):
        config = validator.validate(make_coil(offset=9999))
        assert config.valid is True

    def test_negative_one_is_invalid(self):
        config = validator.validate(make_coil(offset=-1))
        assert config.valid is False
        assert any("offset" in e for e in config.errors)

    def test_large_negative_offset_is_invalid(self):
        config = validator.validate(make_coil(offset=-32768))
        assert config.valid is False
        assert any("-32768" in e for e in config.errors)

    def test_error_message_contains_actual_value(self):
        config = validator.validate(make_coil(offset=-7))
        assert any("-7" in e for e in config.errors)

    def test_offset_1_is_valid(self):
        config = validator.validate(make_coil(offset=1))
        assert config.valid is True

    def test_offset_65535_is_valid(self):
        config = validator.validate(make_float32(offset=65535))
        assert config.valid is True


# ---------------------------------------------------------------------------
# _validate_length
# ---------------------------------------------------------------------------

class TestValidateLength:
    @pytest.mark.parametrize("reg_type, expected_length", [
        (RegisterType.INT16,   1),
        (RegisterType.UINT16,  1),
        (RegisterType.BOOLEAN, 1),
        (RegisterType.INT32,   2),
        (RegisterType.UINT32,  2),
        (RegisterType.FLOAT32, 2),
        (RegisterType.INT64,   4),
        (RegisterType.UINT64,  4),
        (RegisterType.FLOAT64, 4),
    ])
    def test_length_set_correctly(self, reg_type, expected_length):
        config = validator.validate(make_int_holding(reg_type=reg_type))
        assert config.length == expected_length

    def test_word_type_length_is_1(self):
        config = RegisterConfig(
            offset=0, memory_area=MemoryArea.HOLDING_REGISTER,
            name="test",
            type=RegisterType.WORD,
            bit_offset=0, bit_length=8,
        )
        config = validator.validate(config)
        assert config.length == 1

    def test_none_type_is_invalid(self):
        config = RegisterConfig(
            offset=0, memory_area=MemoryArea.HOLDING_REGISTER,
            name="test",
            type=None,
        )
        config = validator.validate(config)
        assert config.valid is False
        assert any("register type is not valid" in e for e in config.errors)
        assert any("None" in e for e in config.errors)

    def test_coil_strips_length_after_setting_it(self):
        """_validate_length sets length, then _validate_boolean_addresses removes it."""
        config = validator.validate(make_coil())
        assert absent(config, "length")

    def test_float64_length_is_4(self):
        config = validator.validate(make_float64())
        assert config.length == 4


# ---------------------------------------------------------------------------
# _validate_bit_offset
# ---------------------------------------------------------------------------

class TestValidateBitOffset:
    def test_word_no_bit_fields_is_valid(self):
        config = RegisterConfig(
            offset=0, memory_area=MemoryArea.HOLDING_REGISTER,
            name="test",
            type=RegisterType.WORD,
        )
        config = validator.validate(config)
        assert config.valid is True

    def test_word_valid_bit_offset_and_length(self):
        config = RegisterConfig(
            offset=0, memory_area=MemoryArea.HOLDING_REGISTER,
            name="test",
            type=RegisterType.WORD, bit_offset=0, bit_length=8,
        )
        config = validator.validate(config)
        assert config.valid is True

    def test_word_bit_offset_8_length_8_exact_boundary(self):
        config = RegisterConfig(
            offset=0, memory_area=MemoryArea.HOLDING_REGISTER,
            name="test",
            type=RegisterType.WORD, bit_offset=8, bit_length=8,
        )
        config = validator.validate(config)
        assert config.valid is True

    def test_word_bit_offset_0_length_16_full_word(self):
        config = RegisterConfig(
            offset=0, memory_area=MemoryArea.HOLDING_REGISTER,
            name="test",
            type=RegisterType.WORD, bit_offset=0, bit_length=16,
        )
        config = validator.validate(config)
        assert config.valid is True

    def test_word_overflow_bit_offset_plus_length_exceeds_16(self):
        config = RegisterConfig(
            offset=0, memory_area=MemoryArea.HOLDING_REGISTER,
            name="test",
            type=RegisterType.WORD, bit_offset=10, bit_length=8,
        )
        config = validator.validate(config)
        assert config.valid is False
        assert any("overflow" in e for e in config.errors)

    def test_word_negative_bit_offset_is_invalid(self):
        config = RegisterConfig(
            offset=0, memory_area=MemoryArea.HOLDING_REGISTER,
            name="test",
            type=RegisterType.WORD, bit_offset=-1, bit_length=8,
        )
        config = validator.validate(config)
        assert config.valid is False
        assert any("overflow" in e for e in config.errors)

    def test_word_bit_offset_17_is_invalid(self):
        config = RegisterConfig(
            offset=0, memory_area=MemoryArea.HOLDING_REGISTER,
            name="test",
            type=RegisterType.WORD, bit_offset=17, bit_length=1,
        )
        config = validator.validate(config)
        assert config.valid is False

    def test_word_only_bit_length_provided_defaults_bit_offset_to_0(self):
        """When bit_length provided but bit_offset absent, bit_offset defaults to 0."""
        config = RegisterConfig(
            offset=0, memory_area=MemoryArea.HOLDING_REGISTER,
            name="test",
            type=RegisterType.WORD, bit_length=4,
        )
        config = validator.validate(config)
        assert config.valid is True
        assert config.bit_offset == 0
        assert config.bit_length == 4

    def test_word_only_bit_offset_provided_defaults_bit_length(self):
        """When bit_offset provided but bit_length absent, bit_length defaults to 16-bit_offset."""
        config = RegisterConfig(
            offset=0, memory_area=MemoryArea.HOLDING_REGISTER,
            name="test",
            type=RegisterType.WORD, bit_offset=4,
        )
        config = validator.validate(config)
        assert config.valid is True
        assert config.bit_offset == 4
        assert config.bit_length == 12  # 16 - 4

    def test_non_word_type_strips_bit_offset_and_bit_length(self):
        config = RegisterConfig(
            offset=0, memory_area=MemoryArea.HOLDING_REGISTER,
            name="test",
            type=RegisterType.FLOAT32,
            bit_offset=4, bit_length=8,
        )
        config = validator.validate(config)
        assert absent(config, "bit_offset")
        assert absent(config, "bit_length")

    def test_int32_type_strips_bit_fields(self):
        config = RegisterConfig(
            offset=0, memory_area=MemoryArea.HOLDING_REGISTER,
            name="test",
            type=RegisterType.INT32,
            bit_offset=2, bit_length=6,
            min_value=0.0, max_value=100.0,
        )
        config = validator.validate(config)
        assert absent(config, "bit_offset")
        assert absent(config, "bit_length")

    def test_float64_type_strips_bit_fields(self):
        config = RegisterConfig(
            offset=0, memory_area=MemoryArea.HOLDING_REGISTER,
            name="test",
            type=RegisterType.FLOAT64,
            bit_offset=0, bit_length=8,
        )
        config = validator.validate(config)
        assert absent(config, "bit_offset")
        assert absent(config, "bit_length")


# ---------------------------------------------------------------------------
# _validate_scalling
# ---------------------------------------------------------------------------

class TestValidateScalling:
    def test_int_no_scaling_is_valid(self):
        config = validator.validate(make_int_holding())
        assert config.valid is True

    def test_coil_strips_max_min_scale(self):
        config = RegisterConfig(
            offset=0, memory_area=MemoryArea.COIL,
            name="test",
            type=RegisterType.BOOLEAN,
            max_value=100.0, min_value=0.0, scale=2.0,
        )
        config = validator.validate(config)
        assert absent(config, "max_value")
        assert absent(config, "min_value")
        assert absent(config, "scale")

    def test_discrete_input_strips_max_min_scale(self):
        config = RegisterConfig(
            offset=0, memory_area=MemoryArea.DISCRETE_INPUT,
            name="test",
            type=RegisterType.BOOLEAN,
            max_value=50.0, min_value=10.0, scale=0.5,
        )
        config = validator.validate(config)
        assert absent(config, "max_value")
        assert absent(config, "min_value")
        assert absent(config, "scale")

    def test_float32_strips_max_min_scale(self):
        config = RegisterConfig(
            offset=0, memory_area=MemoryArea.HOLDING_REGISTER,
            name="test",
            type=RegisterType.FLOAT32,
            max_value=99.9, min_value=0.1, scale=1.5,
        )
        config = validator.validate(config)
        assert absent(config, "max_value")
        assert absent(config, "min_value")
        assert absent(config, "scale")

    def test_float64_strips_max_min_scale(self):
        config = RegisterConfig(
            offset=0, memory_area=MemoryArea.HOLDING_REGISTER,
            name="test",
            type=RegisterType.FLOAT64,
            max_value=1000.0, min_value=-1000.0,
        )
        config = validator.validate(config)
        assert absent(config, "max_value")
        assert absent(config, "min_value")

    def test_boolean_holding_strips_max_min_scale(self):
        config = make_boolean_holding(max_value=1.0, min_value=0.0, scale=0.1)
        config = validator.validate(config)
        assert absent(config, "max_value")
        assert absent(config, "min_value")
        assert absent(config, "scale")

    def test_word_strips_max_min_scale(self):
        config = RegisterConfig(
            offset=0, memory_area=MemoryArea.HOLDING_REGISTER,
            name="test",
            type=RegisterType.WORD,
            max_value=255.0, min_value=0.0,
            bit_offset=0, bit_length=8,
        )
        config = validator.validate(config)
        assert absent(config, "max_value")
        assert absent(config, "min_value")

    def test_int32_valid_min_max(self):
        config = make_int_holding(reg_type=RegisterType.INT32, min_value=0.0, max_value=1000.0)
        config = validator.validate(config)
        assert config.valid is True
        assert config.errors == []

    def test_uint32_valid_min_max(self):
        config = make_int_holding(reg_type=RegisterType.UINT32, min_value=0.0, max_value=65535.0)
        config = validator.validate(config)
        assert config.valid is True

    def test_int64_valid_min_max(self):
        config = make_int_holding(reg_type=RegisterType.INT64, min_value=-1e12, max_value=1e12)
        config = validator.validate(config)
        assert config.valid is True

    def test_max_without_min_is_invalid(self):
        config = make_int_holding(max_value=100.0)  # min_value=None
        config = validator.validate(config)
        assert config.valid is False
        assert any("max_value" in e and "min_value" in e for e in config.errors)

    def test_min_without_max_is_invalid(self):
        config = make_int_holding(min_value=0.0)  # max_value=None
        config = validator.validate(config)
        assert config.valid is False
        assert any("min_value" in e and "max_value" in e for e in config.errors)

    def test_max_less_than_min_is_invalid(self):
        config = make_int_holding(min_value=100.0, max_value=10.0)
        config = validator.validate(config)
        assert config.valid is False
        assert any("max_value" in e and "min_value" in e for e in config.errors)

    def test_equal_min_max_is_valid(self):
        config = make_int_holding(min_value=50.0, max_value=50.0)
        config = validator.validate(config)
        assert config.valid is True

    def test_scale_alone_is_valid_for_int_type(self):
        config = make_int_holding(scale=0.01)
        config = validator.validate(config)
        assert config.valid is True

    def test_scale_and_min_max_together_is_invalid(self):
        config = make_int_holding(min_value=0.0, max_value=100.0, scale=2.0)
        config = validator.validate(config)
        assert config.valid is False
        assert any("scale" in e for e in config.errors)

    def test_scale_and_only_max_is_invalid(self):
        """scale + max_value (no min) triggers two errors: max-without-min and scale+minmax."""
        config = make_int_holding(max_value=100.0, scale=1.5)
        config = validator.validate(config)
        assert config.valid is False

    def test_negative_min_and_positive_max_is_valid(self):
        config = make_int_holding(reg_type=RegisterType.INT16, min_value=-32768.0, max_value=32767.0)
        config = validator.validate(config)
        assert config.valid is True

    def test_uint16_no_scaling_is_valid(self):
        config = make_int_holding(reg_type=RegisterType.UINT16)
        config = validator.validate(config)
        assert config.valid is True


# ---------------------------------------------------------------------------
# _validate_memory_area
# ---------------------------------------------------------------------------

class TestValidateMemoryArea:
    def test_all_valid_memory_areas(self):
        for area in MemoryArea:
            if area in (MemoryArea.COIL, MemoryArea.DISCRETE_INPUT):
                config = RegisterConfig(
                    offset=0, memory_area=area,
                    name="test",
                    type=RegisterType.BOOLEAN,
                )
            else:
                config = RegisterConfig(
                    offset=0, memory_area=area,
                    name="test",
                    type=RegisterType.FLOAT32,
                )
            config = validator.validate(config)
            assert config.valid is True, f"Expected {area} to be valid, errors: {config.errors}"

    def test_invalid_memory_area_string_is_invalid(self):
        config = RegisterConfig(
            offset=0,
            memory_area="invalid-area",  # type: ignore
            name="test",
            type=RegisterType.FLOAT32,
        )
        config = validator.validate(config)
        assert config.valid is False
        assert any("memory_area" in e for e in config.errors)

    def test_error_message_contains_bad_area_value(self):
        config = RegisterConfig(
            offset=0,
            memory_area="mystery-zone",  # type: ignore
            name="test",
            type=RegisterType.FLOAT32,
        )
        config = validator.validate(config)
        assert any("mystery-zone" in e for e in config.errors)


# ---------------------------------------------------------------------------
# _validate_boolean_addresses
# ---------------------------------------------------------------------------

class TestValidateBooleanAddresses:
    def test_coil_strips_register_specific_fields(self):
        config = RegisterConfig(
            offset=0, memory_area=MemoryArea.COIL,
            name="test",
            type=RegisterType.BOOLEAN,
            big_endian=True, modicon=False,
            first_word_low=True, first_double_word_low=True,
        )
        config = validator.validate(config)
        assert absent(config, "type")
        assert absent(config, "length")
        assert absent(config, "big_endian")
        assert absent(config, "modicon")
        assert absent(config, "first_word_low")
        assert absent(config, "first_double_word_low")
        assert absent(config, "bit_offset")
        assert absent(config, "bit_length")

    def test_discrete_input_strips_register_specific_fields(self):
        config = RegisterConfig(
            offset=0, memory_area=MemoryArea.DISCRETE_INPUT,
            name="test",
            type=RegisterType.BOOLEAN,
        )
        config = validator.validate(config)
        assert absent(config, "type")
        assert absent(config, "length")
        assert absent(config, "big_endian")

    def test_holding_register_keeps_all_fields(self):
        config = make_float32()
        config = validator.validate(config)
        assert present(config, "type")
        assert present(config, "length")
        assert present(config, "big_endian")
        assert present(config, "first_word_low")
        assert present(config, "modicon")

    def test_input_register_keeps_all_fields(self):
        config = make_input_reg()
        config = validator.validate(config)
        assert present(config, "type")
        assert present(config, "length")

    def test_coil_strips_max_min_and_scale(self):
        config = make_coil(max_value=5.0, min_value=0.0, scale=1.0)
        config = validator.validate(config)
        assert absent(config, "max_value")
        assert absent(config, "min_value")
        assert absent(config, "scale")


# ---------------------------------------------------------------------------
# _validate_default
# ---------------------------------------------------------------------------

class TestValidateDefault:
    def test_coil_default_0_is_valid(self):
        config = make_coil(default=0)
        config = validator.validate(config)
        assert config.valid is True

    def test_coil_default_1_is_valid(self):
        config = make_coil(default=1)
        config = validator.validate(config)
        assert config.valid is True

    def test_coil_default_2_is_invalid(self):
        config = make_coil(default=2)
        config = validator.validate(config)
        assert config.valid is False
        assert any("non-binary" in e for e in config.errors)

    def test_coil_default_minus_1_is_invalid(self):
        config = make_coil(default=-1)
        config = validator.validate(config)
        assert config.valid is False
        assert any("non-binary" in e for e in config.errors)

    def test_coil_default_100_is_invalid(self):
        config = make_coil(default=100)
        config = validator.validate(config)
        assert config.valid is False
        assert any("non-binary" in e for e in config.errors)

    def test_discrete_input_default_0_is_valid(self):
        config = make_discrete(default=0)
        config = validator.validate(config)
        assert config.valid is True

    def test_discrete_input_default_1_is_valid(self):
        config = make_discrete(default=1)
        config = validator.validate(config)
        assert config.valid is True

    def test_discrete_input_default_5_is_invalid(self):
        config = make_discrete(default=5)
        config = validator.validate(config)
        assert config.valid is False
        assert any("non-binary" in e for e in config.errors)

    @pytest.mark.parametrize("val", [-9999, 0, 1, 255, 32767, 99999])
    def test_holding_register_any_default_is_valid(self, val):
        config = make_float32(default=val)
        config = validator.validate(config)
        assert config.valid is True, f"Expected default={val} to be valid"

    def test_error_message_contains_bad_value(self):
        config = make_coil(default=99)
        config = validator.validate(config)
        assert any("99" in e for e in config.errors)

    def test_error_message_contains_memory_area(self):
        config = make_coil(default=5)
        config = validator.validate(config)
        # In Python 3.12+ str(MemoryArea.COIL) may render as "MemoryArea.COIL"
        assert any("COIL" in e.upper() or "coil" in e for e in config.errors)


# ---------------------------------------------------------------------------
# validate_all
# ---------------------------------------------------------------------------

class TestValidateAll:
    def test_empty_list_returns_empty(self):
        assert validator.validate_all([]) == []

    def test_all_valid_configs(self):
        configs = [make_float32(offset=i) for i in range(10)]
        results = validator.validate_all(configs)
        assert len(results) == 10
        assert all(r.valid for r in results)

    def test_mixed_valid_and_invalid(self):
        configs = [
            make_coil(offset=0),
            make_coil(offset=-1),
            make_float32(offset=5),
            make_coil(default=3),
        ]
        results = validator.validate_all(configs)
        assert results[0].valid is True
        assert results[1].valid is False
        assert results[2].valid is True
        assert results[3].valid is False

    def test_all_invalid_configs(self):
        configs = [make_coil(offset=-i) for i in range(1, 6)]
        results = validator.validate_all(configs)
        assert all(not r.valid for r in results)

    def test_result_list_length_matches_input(self):
        configs = [make_coil(offset=i) for i in range(7)]
        results = validator.validate_all(configs)
        assert len(results) == 7


# ---------------------------------------------------------------------------
# validate_or_raise
# ---------------------------------------------------------------------------

class TestValidateOrRaise:
    def test_raises_for_invalid_config(self):
        config = make_coil(offset=-1)
        config = validator.validate(config)
        with pytest.raises(ValueError):
            validator.validate_or_raise(config)

    def test_does_not_raise_for_valid_config(self):
        config = validator.validate(make_coil())
        validator.validate_or_raise(config)  # must not raise

    def test_error_message_contains_memory_area(self):
        config = make_coil(offset=-3)
        config = validator.validate(config)
        with pytest.raises(ValueError, match="(?i)coil"):  # case-insensitive: "coil" or "COIL"
            validator.validate_or_raise(config)

    def test_error_message_contains_offset(self):
        config = make_coil(offset=-3)
        config = validator.validate(config)
        with pytest.raises(ValueError, match="-3"):
            validator.validate_or_raise(config)

    def test_error_message_lists_all_errors(self):
        config = make_coil(offset=-1, default=5)
        config = validator.validate(config)
        with pytest.raises(ValueError) as exc_info:
            validator.validate_or_raise(config)
        msg = str(exc_info.value)
        assert "offset" in msg
        assert "non-binary" in msg


# ---------------------------------------------------------------------------
# is_valid
# ---------------------------------------------------------------------------

class TestIsValid:
    def test_returns_true_for_valid_config(self):
        config = validator.validate(make_coil())
        assert validator.is_valid(config) is True

    def test_returns_false_for_invalid_config(self):
        config = validator.validate(make_coil(offset=-1))
        assert validator.is_valid(config) is False


# ---------------------------------------------------------------------------
# Re-validation resets state
# ---------------------------------------------------------------------------

class TestRevalidation:
    def test_fixing_offset_makes_fresh_config_valid(self):
        """Each validation call should reset errors and valid flag."""
        config1 = make_coil(offset=-1)
        config1 = validator.validate(config1)
        assert config1.valid is False

        # Fresh config with fixed offset
        config2 = make_coil(offset=10)
        config2 = validator.validate(config2)
        assert config2.valid is True
        assert config2.errors == []

    def test_errors_reset_on_fresh_validation(self):
        """validate() resets errors to [] before each run."""
        config1 = make_float32(offset=-1)
        validator.validate(config1)
        assert len(config1.errors) == 1  # offset error

        config1.offset = 0
        validator.validate(config1)
        assert config1.errors == []  # errors cleared, now valid

    def test_valid_flag_resets_for_non_stripping_config(self):
        """For float32 (no stripping), re-validation after fix works correctly."""
        config = make_float32(offset=-1)
        validator.validate(config)
        assert config.valid is False

        config.offset = 0
        validator.validate(config)
        assert config.valid is True

    def test_errors_cleared_on_each_validate_call(self):
        """Each validate() call starts with a clean slate."""
        config = make_float32(offset=-5)
        validator.validate(config)
        assert len(config.errors) == 1

        # Validate again without fixing: still exactly 1 error (not cumulative)
        validator.validate(config)
        assert len(config.errors) == 1


# ---------------------------------------------------------------------------
# Multiple simultaneous errors
# ---------------------------------------------------------------------------

class TestMultipleErrors:
    def test_offset_and_default_both_invalid(self):
        config = make_coil(offset=-5, default=9)
        config = validator.validate(config)
        assert config.valid is False
        assert len(config.errors) >= 2
        assert any("offset" in e for e in config.errors)
        assert any("non-binary" in e for e in config.errors)

    def test_negative_offset_plus_bad_default(self):
        config = RegisterConfig(
            offset=-10, memory_area=MemoryArea.COIL,
            name="test",
            type=RegisterType.BOOLEAN, default=7,
        )
        config = validator.validate(config)
        assert config.valid is False
        assert any("offset" in e for e in config.errors)
        assert any("non-binary" in e for e in config.errors)

    def test_scale_and_max_without_min_has_two_errors(self):
        """max_value (no min) + scale alongside max: two separate errors."""
        config = make_int_holding(max_value=100.0, scale=1.5)
        config = validator.validate(config)
        assert config.valid is False
        assert len(config.errors) >= 2


# ---------------------------------------------------------------------------
# Complex combined scenarios
# ---------------------------------------------------------------------------

class TestComplexScenarios:
    def test_uint32_holding_with_min_max(self):
        config = RegisterConfig(
            offset=4, memory_area=MemoryArea.HOLDING_REGISTER,
            name="sensor_value",
            type=RegisterType.UINT32,
            min_value=0.0, max_value=65535.0,
        )
        config = validator.validate(config)
        assert config.valid is True
        assert config.length == 2

    def test_word_register_with_bit_field_extraction(self):
        config = RegisterConfig(
            offset=3, memory_area=MemoryArea.HOLDING_REGISTER,
            name="status_flags",
            type=RegisterType.WORD,
            bit_offset=4, bit_length=4,
        )
        config = validator.validate(config)
        assert config.valid is True
        assert config.length == 1
        assert config.bit_offset == 4
        assert config.bit_length == 4

    def test_large_validated_register_set_all_valid(self):
        configs = [
            RegisterConfig(offset=0,  memory_area=MemoryArea.HOLDING_REGISTER, name="v0", type=RegisterType.FLOAT32),
            RegisterConfig(offset=2,  memory_area=MemoryArea.HOLDING_REGISTER, name="v1", type=RegisterType.FLOAT64),
            RegisterConfig(offset=6,  memory_area=MemoryArea.HOLDING_REGISTER, name="v2", type=RegisterType.FLOAT32),
            RegisterConfig(offset=8,  memory_area=MemoryArea.COIL,             name="v3", type=RegisterType.BOOLEAN),
            RegisterConfig(offset=9,  memory_area=MemoryArea.COIL,             name="v4", type=RegisterType.BOOLEAN),
            RegisterConfig(offset=10, memory_area=MemoryArea.DISCRETE_INPUT,   name="v5", type=RegisterType.BOOLEAN),
            RegisterConfig(offset=11, memory_area=MemoryArea.HOLDING_REGISTER, name="v6", type=RegisterType.INT16, min_value=0.0, max_value=100.0),
            RegisterConfig(offset=12, memory_area=MemoryArea.HOLDING_REGISTER, name="v7", type=RegisterType.INT32, min_value=0.0, max_value=999.0),
            RegisterConfig(offset=14, memory_area=MemoryArea.HOLDING_REGISTER, name="v8", type=RegisterType.WORD, bit_offset=0, bit_length=8),
            RegisterConfig(offset=15, memory_area=MemoryArea.HOLDING_REGISTER, name="v9", type=RegisterType.UINT64),
        ]
        results = validator.validate_all(configs)
        for i, r in enumerate(results):
            assert r.valid is True, f"Config {i} ({r.name!r}) expected valid, errors: {r.errors}"

    def test_float32_strips_scaling(self):
        config = RegisterConfig(
            offset=0, memory_area=MemoryArea.HOLDING_REGISTER,
            name="smooth_val",
            type=RegisterType.FLOAT32,
            max_value=100.0, min_value=0.0,
        )
        config = validator.validate(config)
        assert config.valid is True
        assert absent(config, "max_value")
        assert absent(config, "min_value")

    def test_validate_or_raise_on_complex_invalid(self):
        config = RegisterConfig(
            offset=-1, memory_area=MemoryArea.HOLDING_REGISTER,
            name="bad",
            type=RegisterType.FLOAT32,
        )
        config = validator.validate(config)
        with pytest.raises(ValueError) as exc_info:
            validator.validate_or_raise(config)
        msg = str(exc_info.value)
        # Python 3.12+ renders enum as "MemoryArea.HOLDING_REGISTER"; older as "holding-register"
        assert "HOLDING_REGISTER" in msg.upper() or "holding-register" in msg
        assert "-1" in msg

    def test_int16_with_scale_valid(self):
        config = make_int_holding(reg_type=RegisterType.INT16, scale=0.1)
        config = validator.validate(config)
        assert config.valid is True

    def test_uint64_no_scaling_valid(self):
        config = RegisterConfig(
            offset=0, memory_area=MemoryArea.HOLDING_REGISTER,
            name="test",
            type=RegisterType.UINT64,
        )
        config = validator.validate(config)
        assert config.valid is True
        assert config.length == 4
