from typing import List

from helpers.classes import ByterOrderConfig, RegisterConfig, AddressSnapshot, RegisterType

_NUMERIC_TYPES = {
    RegisterType.INT16, RegisterType.UINT16,
    RegisterType.INT32, RegisterType.UINT32,
    RegisterType.INT64, RegisterType.UINT64,
    RegisterType.FLOAT32, RegisterType.FLOAT64,
}


class ByteConverter:
    def __init__(self, register_conf: List[RegisterConfig], order_conf: ByterOrderConfig):
        self.register_conf = register_conf
        self.order_conf = order_conf

    @staticmethod
    def _swap_bytes(word: int) -> int:
        """Swap the two bytes of a 16-bit word."""
        return ((word & 0xFF) << 8) | ((word >> 8) & 0xFF)

    @staticmethod
    def _reverse_bits_16(word: int) -> int:
        """Reverse all 16 bits of a word."""
        result = 0
        for _ in range(16):
            result = (result << 1) | (word & 1)
            word >>= 1
        return result

    def modicon(self, registers: List[int]) -> List[int]:
        """Each register's bits are read in reverse order.
        Returns a list of the same length as the input."""
        return [self._reverse_bits_16(reg & 0xFFFF) for reg in registers]

    def first_word_low(self, registers: List[int]) -> List[int]:
        """Word-swapped order: first register is the least significant word.
        Requires an even number of registers.
        For 2 registers: CD AB -> AB CD (registers[0]=low, registers[1]=high)."""
        if len(registers) % 2 != 0:
            raise ValueError("first_word_low requires an even number of registers")
        return list(reversed(registers))

    def first_dword_low(self, registers: List[int]) -> List[int]:
        """DWord-swapped order: requires exactly 4 registers.
        AB CD EF GH -> EF GH AB CD (registers[0:2]=low DWord, registers[2:4]=high DWord)."""
        if len(registers) != 4:
            raise ValueError("first_dword_low requires exactly 4 registers")
        return registers[2:4] + registers[0:2]

    def little_endian(self, registers: List[int]) -> List[int]:
        """Fully little-endian byte order: bytes are completely reversed.
        For 2 registers: DCBA byte order (first register = low word with swapped bytes)."""
        return [self._swap_bytes(reg) for reg in reversed(registers)]

    def get_order_conf(self) -> ByterOrderConfig:
        return ByterOrderConfig(
            big_endian=self.order_conf.big_endian,
            first_word_low=self.order_conf.first_word_low,
            first_double_word_low=self.order_conf.first_double_word_low,
            modicon=self.order_conf.modicon,
        )

    def set_order_conf(self, order_conf: ByterOrderConfig) -> None:
        self.order_conf = order_conf

    def update_order_conf(
        self,
        big_endian: bool = True,
        first_word_low: bool = False,
        first_double_word_low: bool = False,
        modicon: bool = False,
    ) -> None:
        self.order_conf = ByterOrderConfig(
            big_endian=big_endian,
            first_word_low=first_word_low,
            first_double_word_low=first_double_word_low,
            modicon=modicon,
        )

    def convert(self, snapshots: List[AddressSnapshot]) -> List[AddressSnapshot]:
        """Apply byte-order conversions from order_conf to int/uint/float registers.
        Register groups are determined by register_conf (offset + length).
        Returns a new list of the same length with converted values."""
        result = [AddressSnapshot(s.offset, s.memory_area, s.value) for s in snapshots]

        for conf in self.register_conf:
            if conf.length is None or conf.type not in _NUMERIC_TYPES:
                continue

            indices = sorted(
                [
                    i for i, s in enumerate(result)
                    if s.memory_area == conf.memory_area
                    and conf.offset <= s.offset < conf.offset + conf.length
                ],
                key=lambda i: result[i].offset,
            )

            if len(indices) != conf.length:
                continue

            values = [result[i].value for i in indices]

            if self.order_conf.modicon:
                converted = self.modicon(values)
            elif self.order_conf.first_double_word_low and len(values) == 4:
                converted = self.first_dword_low(values)
            elif self.order_conf.first_word_low and len(values) >= 2 and len(values) % 2 == 0:
                converted = self.first_word_low(values)
            elif not self.order_conf.big_endian:
                converted = self.little_endian(values)
            else:
                converted = values

            for i, val in zip(indices, converted):
                result[i].value = val

        return result
