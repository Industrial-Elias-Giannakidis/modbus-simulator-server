import pytest

from helpers.byte_order_converter import ByteConverter
from helpers.classes import AddressSnapshot, ByterOrderConfig, MemoryArea, RegisterConfig, RegisterType

# Shared instance for static-method tests (register_conf unused by those methods)
converter = ByteConverter(register_conf=[], order_conf=ByterOrderConfig())


class TestReverseBits16:
    def test_lsb_becomes_msb(self):
        assert ByteConverter._reverse_bits_16(0x0001) == 0x8000

    def test_msb_becomes_lsb(self):
        assert ByteConverter._reverse_bits_16(0x8000) == 0x0001

    def test_high_byte_becomes_low_byte(self):
        assert ByteConverter._reverse_bits_16(0xFF00) == 0x00FF

    def test_low_byte_becomes_high_byte(self):
        assert ByteConverter._reverse_bits_16(0x00FF) == 0xFF00

    def test_zero(self):
        assert ByteConverter._reverse_bits_16(0x0000) == 0x0000

    def test_all_ones(self):
        assert ByteConverter._reverse_bits_16(0xFFFF) == 0xFFFF

    def test_complex_bits(serf):
        assert ByteConverter._reverse_bits_16(0x1234) == 0x2C48


class TestSwapBytes:
    def test_swaps_bytes(self):
        assert ByteConverter._swap_bytes(0xABCD) == 0xCDAB

    def test_symmetric(self):
        assert ByteConverter._swap_bytes(ByteConverter._swap_bytes(0x1234)) == 0x1234

    def test_zero(self):
        assert ByteConverter._swap_bytes(0x0000) == 0x0000


class TestModicon:
    def test_single_register_reverses_bits(self):
        assert converter.modicon([0xFF00]) == [0x00FF]

    def test_two_registers(self):
        # reverse_bits(0xFF00) = 0x00FF, reverse_bits(0x00FF) = 0xFF00
        assert converter.modicon([0xFF00, 0x00FF]) == [0x00FF, 0xFF00]

    def test_four_registers(self):
        assert converter.modicon([0xAABC, 0xDEFF, 0xE482, 0x36CD]) == [0x3D55, 0xFF7B, 0x4127, 0xB36C]

    def test_zero_register(self):
        assert converter.modicon([0x0000]) == [0x0000]

    def test_all_ones_register(self):
        assert converter.modicon([0xFFFF]) == [0xFFFF]


class TestFirstWordLow:
    def test_swaps_two_registers(self):
        assert converter.first_word_low([0xABCD, 0xEF01]) == [0xEF01, 0xABCD]

    def test_four_registers(self):
        assert converter.first_word_low([0x0001, 0x0002, 0x0003, 0x0004]) == [0x0004, 0x0003, 0x0002, 0x0001]

    def test_raises_on_odd_length(self):
        with pytest.raises(ValueError):
            converter.first_word_low([0xABCD])

    def test_raises_on_three_registers(self):
        with pytest.raises(ValueError):
            converter.first_word_low([0x0001, 0x0002, 0x0003])

    def test_identity_when_equal_registers(self):
        assert converter.first_word_low([0x1234, 0x1234]) == [0x1234, 0x1234]


class TestFirstDwordLow:
    def test_swaps_two_pairs(self):
        # [0xABCD, 0xEF01, 0x1234, 0x5678] -> [0x1234, 0x5678, 0xABCD, 0xEF01]
        assert converter.first_dword_low([0xABCD, 0xEF01, 0x1234, 0x5678]) == [0x1234, 0x5678, 0xABCD, 0xEF01]

    def test_raises_on_wrong_length_two(self):
        with pytest.raises(ValueError):
            converter.first_dword_low([0x0001, 0x0002])

    def test_raises_on_wrong_length_three(self):
        with pytest.raises(ValueError):
            converter.first_dword_low([0x0001, 0x0002, 0x0003])

    def test_raises_on_wrong_length_five(self):
        with pytest.raises(ValueError):
            converter.first_dword_low([0x0001, 0x0002, 0x0003, 0x0004, 0x0005])

    def test_identity_when_equal_pairs(self):
        assert converter.first_dword_low([0x1234, 0x5678, 0x1234, 0x5678]) == [0x1234, 0x5678, 0x1234, 0x5678]


class TestLittleEndian:
    def test_two_registers(self):
        # [0xABCD, 0xEF01] -> reversed [0xEF01, 0xABCD] -> swap bytes each
        # swap(0xEF01)=0x01EF, swap(0xABCD)=0xCDAB
        assert converter.little_endian([0xABCD, 0xEF01]) == [0x01EF, 0xCDAB]

    def test_single_register(self):
        assert converter.little_endian([0x0102]) == [0x0201]

    def test_four_registers(self):
        # [0x0001, 0x0002, 0x0003, 0x0004] -> reversed [0x0004, 0x0003, 0x0002, 0x0001]
        # swap each: [0x0400, 0x0300, 0x0200, 0x0100]
        assert converter.little_endian([0x0001, 0x0002, 0x0003, 0x0004]) == [0x0400, 0x0300, 0x0200, 0x0100]

    def test_zero(self):
        assert converter.little_endian([0x0000, 0x0000]) == [0x0000, 0x0000]

    def test_all_ones(self):
        assert converter.little_endian([0xFFFF, 0xFFFF]) == [0xFFFF, 0xFFFF]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

HR = MemoryArea.HOLDING_REGISTER
IR = MemoryArea.INPUT_REGISTER


def make_reg(offset, reg_type, length, memory_area=HR):
    return RegisterConfig(offset=offset, memory_area=memory_area, name="t", type=reg_type, length=length)


def make_snap(offset, value, memory_area=HR):
    return AddressSnapshot(offset=offset, memory_area=memory_area, value=value)


def make_conv(register_conf, **order_kwargs):
    return ByteConverter(register_conf=register_conf, order_conf=ByterOrderConfig(**order_kwargs))


def snap_values(snapshots):
    return [s.value for s in sorted(snapshots, key=lambda s: s.offset)]


# ---------------------------------------------------------------------------
# TestConvert
# ---------------------------------------------------------------------------

class TestConvert:
    # --- big_endian (default): values pass through unchanged ---

    def test_int16_big_endian_unchanged(self):
        conf = [make_reg(0, RegisterType.INT16, 1)]
        c = make_conv(conf)
        snaps = [make_snap(0, 0xABCD)]
        result = c.convert(snaps)
        assert snap_values(result) == [0xABCD]

    def test_int32_big_endian_unchanged(self):
        conf = [make_reg(0, RegisterType.INT32, 2)]
        c = make_conv(conf)
        snaps = [make_snap(0, 0x1234), make_snap(1, 0x5678)]
        result = c.convert(snaps)
        assert snap_values(result) == [0x1234, 0x5678]

    def test_int64_big_endian_unchanged(self):
        conf = [make_reg(0, RegisterType.INT64, 4)]
        c = make_conv(conf)
        snaps = [make_snap(i, v) for i, v in enumerate([0xAAAA, 0xBBBB, 0xCCCC, 0xDDDD])]
        result = c.convert(snaps)
        assert snap_values(result) == [0xAAAA, 0xBBBB, 0xCCCC, 0xDDDD]

    def test_float64_big_endian_unchanged(self):
        conf = [make_reg(0, RegisterType.FLOAT64, 4)]
        c = make_conv(conf)
        snaps = [make_snap(i, v) for i, v in enumerate([0x0001, 0x0002, 0x0003, 0x0004])]
        result = c.convert(snaps)
        assert snap_values(result) == [0x0001, 0x0002, 0x0003, 0x0004]

    # --- first_word_low ---

    def test_int32_first_word_low(self):
        # 2 registers: [HIGH, LOW] → [LOW, HIGH]
        conf = [make_reg(0, RegisterType.INT32, 2)]
        c = make_conv(conf, first_word_low=True)
        snaps = [make_snap(0, 0x0001), make_snap(1, 0x0002)]
        result = c.convert(snaps)
        assert snap_values(result) == [0x0002, 0x0001]

    def test_uint32_first_word_low(self):
        conf = [make_reg(0, RegisterType.UINT32, 2)]
        c = make_conv(conf, first_word_low=True)
        snaps = [make_snap(0, 0xABCD), make_snap(1, 0xEF01)]
        result = c.convert(snaps)
        assert snap_values(result) == [0xEF01, 0xABCD]

    def test_int64_first_word_low_reverses_all_four(self):
        # first_word_low on 4 registers fully reverses the list
        conf = [make_reg(0, RegisterType.INT64, 4)]
        c = make_conv(conf, first_word_low=True)
        snaps = [make_snap(i, v) for i, v in enumerate([0xAAAA, 0xBBBB, 0xCCCC, 0xDDDD])]
        result = c.convert(snaps)
        # list(reversed([0xAAAA, 0xBBBB, 0xCCCC, 0xDDDD]))
        assert snap_values(result) == [0xDDDD, 0xCCCC, 0xBBBB, 0xAAAA]

    def test_float32_first_word_low(self):
        conf = [make_reg(0, RegisterType.FLOAT32, 2)]
        c = make_conv(conf, first_word_low=True)
        snaps = [make_snap(0, 0x1111), make_snap(1, 0x2222)]
        result = c.convert(snaps)
        assert snap_values(result) == [0x2222, 0x1111]

    # --- first_dword_low ---

    def test_int64_first_dword_low(self):
        # [A, B, C, D] → [C, D, A, B]
        conf = [make_reg(0, RegisterType.INT64, 4)]
        c = make_conv(conf, first_double_word_low=True)
        snaps = [make_snap(i, v) for i, v in enumerate([0xAAAA, 0xBBBB, 0xCCCC, 0xDDDD])]
        result = c.convert(snaps)
        assert snap_values(result) == [0xCCCC, 0xDDDD, 0xAAAA, 0xBBBB]

    def test_uint64_first_dword_low(self):
        conf = [make_reg(0, RegisterType.UINT64, 4)]
        c = make_conv(conf, first_double_word_low=True)
        snaps = [make_snap(i, v) for i, v in enumerate([0x0001, 0x0002, 0x0003, 0x0004])]
        result = c.convert(snaps)
        assert snap_values(result) == [0x0003, 0x0004, 0x0001, 0x0002]

    def test_first_dword_low_does_not_apply_to_int32(self):
        # first_dword_low requires exactly 4 registers; INT32 has 2 → falls through to big_endian
        conf = [make_reg(0, RegisterType.INT32, 2)]
        c = make_conv(conf, first_double_word_low=True)
        snaps = [make_snap(0, 0x1111), make_snap(1, 0x2222)]
        result = c.convert(snaps)
        # BUG CANDIDATE: no word-swap happens even though user might expect it
        assert snap_values(result) == [0x1111, 0x2222]

    def test_first_dword_low_takes_precedence_over_first_word_low_for_int64(self):
        conf = [make_reg(0, RegisterType.INT64, 4)]
        c = make_conv(conf, first_double_word_low=True, first_word_low=True)
        snaps = [make_snap(i, v) for i, v in enumerate([0xAAAA, 0xBBBB, 0xCCCC, 0xDDDD])]
        result = c.convert(snaps)
        # first_dword_low wins: [C, D, A, B]
        assert snap_values(result) == [0xCCCC, 0xDDDD, 0xAAAA, 0xBBBB]

    # --- little_endian ---

    def test_float32_little_endian(self):
        # [0xABCD, 0xEF01] → reverse → [0xEF01, 0xABCD] → swap bytes each
        # swap(0xEF01)=0x01EF, swap(0xABCD)=0xCDAB
        conf = [make_reg(0, RegisterType.FLOAT32, 2)]
        c = make_conv(conf, big_endian=False)
        snaps = [make_snap(0, 0xABCD), make_snap(1, 0xEF01)]
        result = c.convert(snaps)
        assert snap_values(result) == [0x01EF, 0xCDAB]

    def test_float64_little_endian(self):
        # [0x0001, 0x0002, 0x0003, 0x0004] → reversed + swap_bytes each
        conf = [make_reg(0, RegisterType.FLOAT64, 4)]
        c = make_conv(conf, big_endian=False)
        snaps = [make_snap(i, v) for i, v in enumerate([0x0001, 0x0002, 0x0003, 0x0004])]
        result = c.convert(snaps)
        assert snap_values(result) == [0x0400, 0x0300, 0x0200, 0x0100]

    def test_int32_little_endian(self):
        conf = [make_reg(0, RegisterType.INT32, 2)]
        c = make_conv(conf, big_endian=False)
        snaps = [make_snap(0, 0x0102), make_snap(1, 0x0304)]
        result = c.convert(snaps)
        # reversed: [0x0304, 0x0102] → swap each: [0x0403, 0x0201]
        assert snap_values(result) == [0x0403, 0x0201]

    # --- modicon ---

    def test_int32_modicon(self):
        conf = [make_reg(0, RegisterType.INT32, 2)]
        c = make_conv(conf, modicon=True)
        snaps = [make_snap(0, 0xFF00), make_snap(1, 0x00FF)]
        result = c.convert(snaps)
        assert snap_values(result) == [0x00FF, 0xFF00]

    def test_int64_modicon(self):
        conf = [make_reg(0, RegisterType.INT64, 4)]
        c = make_conv(conf, modicon=True)
        snaps = [make_snap(i, 0xFF00) for i in range(4)]
        result = c.convert(snaps)
        assert snap_values(result) == [0x00FF, 0x00FF, 0x00FF, 0x00FF]

    def test_modicon_takes_precedence_over_all_other_flags(self):
        conf = [make_reg(0, RegisterType.INT32, 2)]
        c = make_conv(conf, modicon=True, first_word_low=True, big_endian=False)
        snaps = [make_snap(0, 0xFF00), make_snap(1, 0xFF00)]
        result = c.convert(snaps)
        # modicon applied, not first_word_low or little_endian
        assert snap_values(result) == [0x00FF, 0x00FF]

    # --- non-numeric types skipped ---

    def test_boolean_type_not_converted(self):
        conf = [make_reg(0, RegisterType.BOOLEAN, 1)]
        c = make_conv(conf, first_word_low=True, big_endian=False)
        snaps = [make_snap(0, 1)]
        result = c.convert(snaps)
        assert snap_values(result) == [1]

    def test_word_type_not_converted(self):
        conf = [make_reg(0, RegisterType.WORD, 1)]
        c = make_conv(conf, big_endian=False)
        snaps = [make_snap(0, 0xABCD)]
        result = c.convert(snaps)
        assert snap_values(result) == [0xABCD]

    def test_length_none_not_converted(self):
        conf = [make_reg(0, RegisterType.INT32, None)]
        c = make_conv(conf, first_word_low=True)
        snaps = [make_snap(0, 0x1111), make_snap(1, 0x2222)]
        result = c.convert(snaps)
        assert snap_values(result) == [0x1111, 0x2222]

    # --- partial / mismatched data ---

    def test_missing_register_skips_conversion(self):
        # Config expects length=2 but only 1 snapshot present
        conf = [make_reg(0, RegisterType.INT32, 2)]
        c = make_conv(conf, first_word_low=True)
        snaps = [make_snap(0, 0xAAAA)]
        result = c.convert(snaps)
        assert snap_values(result) == [0xAAAA]

    def test_snapshot_outside_offset_range_unchanged(self):
        conf = [make_reg(0, RegisterType.INT32, 2)]
        c = make_conv(conf, first_word_low=True)
        snaps = [make_snap(0, 0x1111), make_snap(1, 0x2222), make_snap(5, 0x9999)]
        result = c.convert(snaps)
        values = {s.offset: s.value for s in result}
        assert values[0] == 0x2222  # swapped
        assert values[1] == 0x1111  # swapped
        assert values[5] == 0x9999  # untouched

    # --- memory area isolation ---

    def test_only_matching_memory_area_converted(self):
        hr_conf = make_reg(0, RegisterType.INT32, 2, HR)
        ir_conf = make_reg(0, RegisterType.INT32, 2, IR)
        c = make_conv([hr_conf, ir_conf], first_word_low=True)
        snaps = [
            make_snap(0, 0x0001, HR), make_snap(1, 0x0002, HR),
            make_snap(0, 0x00AA, IR), make_snap(1, 0x00BB, IR),
        ]
        result = c.convert(snaps)
        hr = sorted([s for s in result if s.memory_area == HR], key=lambda s: s.offset)
        ir = sorted([s for s in result if s.memory_area == IR], key=lambda s: s.offset)
        assert [s.value for s in hr] == [0x0002, 0x0001]
        assert [s.value for s in ir] == [0x00BB, 0x00AA]

    def test_wrong_memory_area_snapshots_not_converted(self):
        conf = [make_reg(0, RegisterType.INT32, 2, HR)]
        c = make_conv(conf, first_word_low=True)
        # Snapshots are INPUT_REGISTER, not HOLDING_REGISTER
        snaps = [make_snap(0, 0x1111, IR), make_snap(1, 0x2222, IR)]
        result = c.convert(snaps)
        assert [s.value for s in result] == [0x1111, 0x2222]

    # --- multiple configs in same snapshot list ---

    def test_two_int32_configs_at_different_offsets(self):
        conf = [make_reg(0, RegisterType.INT32, 2), make_reg(10, RegisterType.INT32, 2)]
        c = make_conv(conf, first_word_low=True)
        snaps = [
            make_snap(0, 0xAAAA), make_snap(1, 0xBBBB),
            make_snap(10, 0xCCCC), make_snap(11, 0xDDDD),
        ]
        result = c.convert(snaps)
        values = {s.offset: s.value for s in result}
        assert values[0] == 0xBBBB
        assert values[1] == 0xAAAA
        assert values[10] == 0xDDDD
        assert values[11] == 0xCCCC

    def test_int32_and_int64_coexist(self):
        conf = [make_reg(0, RegisterType.INT32, 2), make_reg(2, RegisterType.INT64, 4)]
        c = make_conv(conf, first_word_low=True)
        snaps = [make_snap(i, i + 1) for i in range(6)]  # values 1..6 at offsets 0..5
        result = c.convert(snaps)
        values = {s.offset: s.value for s in result}
        # INT32 [1,2] → [2,1]
        assert values[0] == 2
        assert values[1] == 1
        # INT64 [3,4,5,6] → reversed [6,5,4,3]
        assert values[2] == 6
        assert values[3] == 5
        assert values[4] == 4
        assert values[5] == 3

    # --- immutability: original snapshots must not be mutated ---

    def test_convert_does_not_mutate_input(self):
        conf = [make_reg(0, RegisterType.INT32, 2)]
        c = make_conv(conf, first_word_low=True)
        snaps = [make_snap(0, 0x1111), make_snap(1, 0x2222)]
        c.convert(snaps)
        assert snaps[0].value == 0x1111
        assert snaps[1].value == 0x2222

    # --- snapshots delivered out-of-offset order ---

    def test_snapshots_out_of_order_sorted_correctly(self):
        conf = [make_reg(0, RegisterType.INT32, 2)]
        c = make_conv(conf, first_word_low=True)
        # Pass high offset first
        snaps = [make_snap(1, 0x2222), make_snap(0, 0x1111)]
        result = c.convert(snaps)
        values = {s.offset: s.value for s in result}
        assert values[0] == 0x2222
        assert values[1] == 0x1111
