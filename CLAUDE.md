# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

**Run the server:**
```bash
python index.py
```
- Modbus TCP server on `localhost:5020` (configured via `.env`)
- Web UI on `http://localhost:8080`

**Run tests:**
```bash
pytest helpers/test_byte_order_converter.py
pytest helpers/test_register_config_validator.py

# Run a single test
pytest helpers/test_register_config_validator.py::TestValidateOffset::test_negative_offset
```

**Install dependencies:**
```bash
pip install aiohttp pymodbus pytest
```

## Architecture

This is a Modbus TCP server that simulates industrial device registers with a web-based monitoring UI.

### Data Flow (per 1-second poll cycle)

```
RegisterConfig (JSON) → RegisterScalling.unscale() → RegisterConverter.to_snapshots()
    → ByteConverter.convert() → ModbusServer.update_**()
    → [Modbus TCP clients read via pymodbus]
```

The reverse path (reading back) applies the same transforms in reverse for the web UI display.

### Key Modules

- **[index.py](index.py)** — Entry point. Runs asyncio event loop with aiohttp web server (port 8080) and a 1-second polling task that drives the full data flow pipeline. Holds all global state (`valid_config_list`, `_real_values`, `_server_values`, etc.). `_rebuild_pipeline()` is called on any config change.
- **[modbus_server.py](modbus_server.py)** — Wraps `pymodbus`. Manages 4 memory areas (coils, discrete inputs, holding registers, input registers), each with 300 registers.
- **[helpers/classes.py](helpers/classes.py)** — Core data classes: `RegisterConfig`, `AddressSnapshot`, and enums `MemoryArea`, `RegisterType`.
- **[helpers/register_converter.py](helpers/register_converter.py)** — Converts between typed values (int/float/boolean) and raw 16-bit register snapshots. Handles multi-register types (32/64-bit) and bit-field extraction (WORD type). Multiple configs targeting the same offset (bit-fields) are merged with bitwise OR in `to_snapshots()`.
- **[helpers/register_scalling.py](helpers/register_scalling.py)** — Linear scaling between physical and raw values using `min_value`/`max_value` or a `scale` factor. Floats are never scaled.
- **[helpers/byte_order_converter.py](helpers/byte_order_converter.py)** — Endianness conversions: `big_endian`, `first_word_low`, `first_double_word_low`, `modicon`. Conversion precedence (in order): `modicon → first_dword_low → first_word_low → little_endian → big_endian`. Applied only to numeric types.
- **[helpers/snapshot.py](helpers/snapshot.py)** — Reads all 4 memory areas from the Modbus server (`snapshot_all()`), converts configs to initial snapshots, and writes snapshots back (`apply_snapshots()`).
- **[helpers/register_config_validator.py](helpers/register_config_validator.py)** — Validates `RegisterConfig` objects in-place, setting a `valid` flag and collecting error messages. Coils and discrete-inputs always have `type` coerced to `BOOLEAN` with scaling and bit-fields stripped.

### Register Configuration

Registers are defined in [register_configs.json](register_configs.json) (active) and [default_register_config.json](default_register_config.json) (reset target). [server_config.json](server_config.json) holds the byte-order flags (`big_endian`, `first_word_low`, `first_double_word_low`, `modicon`) and is updated at runtime via the API. Each register entry specifies:
- `offset`: Starting Modbus address
- `memory_area`: `"coil"` | `"discrete-input"` | `"holding-register"` | `"input-register"`
- `type`: `"int16"` | `"uint16"` | `"int32"` | `"uint32"` | `"int64"` | `"uint64"` | `"float32"` | `"float64"` | `"boolean"` | `"word"`
- `scale`, `min_value`, `max_value`: Optional scaling (integers only; cannot mix `scale` with `min/max`)
- `bit_offset`, `bit_length`: For WORD type bit-field extraction

### Web API Endpoints

| Endpoint | Method | Description |
|---|---|---|
| `/` | GET | Main dashboard |
| `/registers` | GET | Register viewer UI |
| `/config-editor` | GET | Configuration editor UI |
| `/configs` | GET/PUT | Get/set register configurations |
| `/configs/reset` | POST | Reset to default config |
| `/realvalues` | GET | Values before Modbus conversion |
| `/serverRegisters` | GET | Values read back from Modbus server |
