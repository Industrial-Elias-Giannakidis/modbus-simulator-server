import random
from dataclasses import replace

from helpers.classes import AddressSnapshot, MemoryArea, RegisterConfig
from modbus_server import ModbusServer, _DEFAULT_SIZE

def register_configs_to_snapshots(configs: list[RegisterConfig]) -> list[AddressSnapshot]:
    """Convert a list of RegisterConfig to AddressSnapshot using each config's default value."""
    return [
        AddressSnapshot(offset=cfg.offset, memory_area=cfg.memory_area, value=0)
        for cfg in configs
    ]

def snapshot_all(server: ModbusServer) -> list[AddressSnapshot]:
    """Read all addresses from all memory areas and return a flat snapshot list."""
    di_values = server.read_di(0, _DEFAULT_SIZE)
    co_values = server.read_co(0, _DEFAULT_SIZE)
    hr_values = server.read_hr(0, _DEFAULT_SIZE)
    ir_values = server.read_ir(0, _DEFAULT_SIZE)

    entries: list[AddressSnapshot] = []
    for i in range(_DEFAULT_SIZE):
        entries.append(AddressSnapshot(offset=i, memory_area=MemoryArea.DISCRETE_INPUT, value=di_values[i]))
        entries.append(AddressSnapshot(offset=i, memory_area=MemoryArea.COIL, value=co_values[i]))
        entries.append(AddressSnapshot(offset=i, memory_area=MemoryArea.HOLDING_REGISTER, value=hr_values[i]))
        entries.append(AddressSnapshot(offset=i, memory_area=MemoryArea.INPUT_REGISTER, value=ir_values[i]))

    return entries


def randomize_snapshots(snapshots: list[AddressSnapshot], live_mode: bool) -> list[AddressSnapshot]:
    """Return snapshots with randomized values when live_mode is True."""
    if not live_mode:
        return snapshots
    def _random_value(s: AddressSnapshot) -> int:
        if s.memory_area in (MemoryArea.COIL, MemoryArea.DISCRETE_INPUT):
            return random.randint(0, 1)
        return random.randint(0, 0xFFFF)

    return [replace(s, value=_random_value(s)) for s in snapshots]


def apply_snapshots(server: ModbusServer, snapshots: list[AddressSnapshot]) -> None:
    """Write a list of AddressSnapshot entries to the modbus server."""
    for snap in snapshots:
        value = [int(snap.value)]
        if snap.memory_area == MemoryArea.DISCRETE_INPUT:
            server.update_di(snap.offset, value)
        elif snap.memory_area == MemoryArea.COIL:
            server.update_co(snap.offset, value)
        elif snap.memory_area == MemoryArea.HOLDING_REGISTER:
            server.update_hr(snap.offset, value)
        elif snap.memory_area == MemoryArea.INPUT_REGISTER:
            server.update_ir(snap.offset, value)
