import pytest

from server_state.byte_order_converter import ByteConverter

# ByteConverter.__init__ requires order_conf but the conversion methods don't use it
converter = ByteConverter(order_conf=[])


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
