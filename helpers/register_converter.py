import struct
from typing import List, Union

from helpers.classes import AddressSnapshot, RegisterConfig, RegisterType


class RegisterConverter:
    def __init__(self, configs: List[RegisterConfig]):
        self.configs = configs

    def _to_register(
        self, snapshots: List[AddressSnapshot], conf: RegisterConfig
    ) -> Union[int, float, bool]:
        """Convert register(s) from snapshots to the typed value defined by conf."""
        if conf.type == RegisterType.BOOLEAN:
            match = next(
                (s for s in snapshots if s.memory_area == conf.memory_area and s.offset == conf.offset),
                None,
            )
            if match is None:
                raise ValueError(
                    f"No snapshot found at offset {conf.offset} ({conf.memory_area}) for BOOLEAN config"
                )
            return bool(match.value)

        matching = sorted(
            [
                s for s in snapshots
                if s.memory_area == conf.memory_area
                and conf.offset <= s.offset < conf.offset + conf.length
            ],
            key=lambda s: s.offset,
        )

        if len(matching) != conf.length:
            raise ValueError(
                f"Expected {conf.length} register(s) at offset {conf.offset}, found {len(matching)}"
            )

        values = [s.value & 0xFFFF for s in matching]

        if conf.type == RegisterType.BOOLEAN:
            return bool((values[0] >> (conf.bit_offset or 0)) & 1)

        if conf.type == RegisterType.WORD:
            if (conf.bit_length or 0) > 0:
                extracted = (values[0] >> (conf.bit_offset or 0)) & ((1 << conf.bit_length) - 1)
                return bool(extracted) if conf.bit_length == 1 else extracted
            return values[0]

        if conf.type == RegisterType.UINT16:
            return values[0]

        if conf.type == RegisterType.INT16:
            return struct.unpack(">h", struct.pack(">H", values[0]))[0]

        if conf.type == RegisterType.UINT32:
            return (values[0] << 16) | values[1]

        if conf.type == RegisterType.INT32:
            raw = (values[0] << 16) | values[1]
            return struct.unpack(">i", struct.pack(">I", raw))[0]

        if conf.type == RegisterType.UINT64:
            raw = 0
            for v in values:
                raw = (raw << 16) | v
            return raw

        if conf.type == RegisterType.INT64:
            raw = 0
            for v in values:
                raw = (raw << 16) | v
            return struct.unpack(">q", struct.pack(">Q", raw))[0]

        if conf.type == RegisterType.FLOAT32:
            return struct.unpack(">f", struct.pack(">HH", values[0], values[1]))[0]

        if conf.type == RegisterType.FLOAT64:
            return struct.unpack(
                ">d", struct.pack(">HHHH", values[0], values[1], values[2], values[3])
            )[0]

        raise ValueError(f"Unsupported register type: {conf.type}")

    def _to_snapshots(
        self, conf: RegisterConfig, value: Union[int, float, bool]
    ) -> List[AddressSnapshot]:
        """Convert a typed value back to a list of AddressSnapshot using conf."""
        if conf.type == RegisterType.BOOLEAN:
            raw = (1 << (conf.bit_offset or 0)) if value else 0
            return [AddressSnapshot(conf.offset, conf.memory_area, raw)]

        if conf.type == RegisterType.WORD:
            if (conf.bit_length or 0) > 0:
                v = int(bool(value)) if conf.bit_length == 1 else int(value)
                positioned = (v & ((1 << conf.bit_length) - 1)) << conf.bit_offset
                return [AddressSnapshot(conf.offset, conf.memory_area, positioned)]
            return [AddressSnapshot(conf.offset, conf.memory_area, int(value) & 0xFFFF)]

        if conf.type == RegisterType.UINT16:
            return [AddressSnapshot(conf.offset, conf.memory_area, int(value) & 0xFFFF)]

        if conf.type == RegisterType.INT16:
            raw = struct.unpack(">H", struct.pack(">h", int(value)))[0]
            return [AddressSnapshot(conf.offset, conf.memory_area, raw)]

        if conf.type == RegisterType.UINT32:
            v = int(value)
            words = [(v >> 16) & 0xFFFF, v & 0xFFFF]
            return [AddressSnapshot(conf.offset + i, conf.memory_area, w) for i, w in enumerate(words)]

        if conf.type == RegisterType.INT32:
            raw = struct.unpack(">I", struct.pack(">i", int(value)))[0]
            words = [(raw >> 16) & 0xFFFF, raw & 0xFFFF]
            return [AddressSnapshot(conf.offset + i, conf.memory_area, w) for i, w in enumerate(words)]

        if conf.type == RegisterType.UINT64:
            v = int(value)
            words = [(v >> (48 - 16 * i)) & 0xFFFF for i in range(4)]
            return [AddressSnapshot(conf.offset + i, conf.memory_area, w) for i, w in enumerate(words)]

        if conf.type == RegisterType.INT64:
            raw = struct.unpack(">Q", struct.pack(">q", int(value)))[0]
            words = [(raw >> (48 - 16 * i)) & 0xFFFF for i in range(4)]
            return [AddressSnapshot(conf.offset + i, conf.memory_area, w) for i, w in enumerate(words)]

        if conf.type == RegisterType.FLOAT32:
            words = struct.unpack(">HH", struct.pack(">f", value))
            return [AddressSnapshot(conf.offset + i, conf.memory_area, w) for i, w in enumerate(words)]

        if conf.type == RegisterType.FLOAT64:
            words = struct.unpack(">HHHH", struct.pack(">d", value))
            return [AddressSnapshot(conf.offset + i, conf.memory_area, w) for i, w in enumerate(words)]

        raise ValueError(f"Unsupported register type: {conf.type}")

    def to_registers(self, snapshots: List[AddressSnapshot]) -> List[AddressSnapshot]:
        """Convert raw register snapshots to one typed-value snapshot per config."""
        result = []
        for conf in self.configs:
            value = self._to_register(snapshots, conf)
            result.append(AddressSnapshot(conf.offset, conf.memory_area, value))
        return result

    def to_snapshots(self, snapshots: List[AddressSnapshot]) -> List[AddressSnapshot]:
        """Convert typed-value snapshots (one per config) back to raw register snapshots.

        When multiple configs share the same register offset (e.g. bit-field sub-values
        packed into one WORD), their individual bit contributions are OR-ed together into
        a single merged snapshot.
        """
        merged: dict = {}
        for conf, snap in zip(self.configs, snapshots):
            for s in self._to_snapshots(conf, snap.value):
                key = (s.offset, s.memory_area)
                if key in merged:
                    merged[key] = AddressSnapshot(s.offset, s.memory_area, merged[key].value | s.value)
                else:
                    merged[key] = s
        return list(merged.values())
