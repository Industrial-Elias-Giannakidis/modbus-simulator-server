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
```

**Install dependencies:**
```bash
pip install aiohttp pymodbus pytest
```

## Architecture

This is a Modbus TCP server that simulates industrial device registers with a web-based monitoring UI.

### Data Flow (per 1-second poll cycle)

```
RegisterConfig (JSON) → RegisterFunctionClass (generate values)
    → RegisterScalling.unscale() → RegisterConverter.to_snapshots()
    → ByteConverter.convert() → ModbusServer.update_**()
    → [Modbus TCP clients read via pymodbus]
```

The reverse path (reading back) applies the same transforms in reverse for the web UI display.

### Key Modules

- **[index.py](index.py)** — Entry point. Runs asyncio event loop with aiohttp web server (port 8080) and a 1-second polling task that drives the full data flow pipeline.
- **[modbus_server.py](modbus_server.py)** — Wraps `pymodbus`. Manages 4 memory areas (coils, discrete inputs, holding registers, input registers), each with 100 registers.
- **[helpers/classes.py](helpers/classes.py)** — Core data classes: `RegisterConfig`, `AddressSnapshot`, and enums `MemoryArea`, `RegisterType`, `RegisterFunction`.
- **[helpers/register_function.py](helpers/register_function.py)** — Generates register values using functions: `const`, `sin`, `random`, `const_smooth`, `smooth`, `validated`.
- **[helpers/register_converter.py](helpers/register_converter.py)** — Converts between typed values (int/float/boolean) and raw 16-bit register snapshots. Handles multi-register types (32/64-bit) and bit-field extraction (WORD type).
- **[helpers/register_scalling.py](helpers/register_scalling.py)** — Linear scaling between physical and raw values using `min_value`/`max_value` or a `scale` factor.
- **[helpers/byte_order_converter.py](helpers/byte_order_converter.py)** — Endianness conversions: `big_endian`, `first_word_low`, `first_double_word_low`, `modicon`.
- **[helpers/register_config_validator.py](helpers/register_config_validator.py)** — Validates `RegisterConfig` objects, setting a `valid` flag and collecting error messages.

### Register Configuration

Registers are defined in [register_configs.json](register_configs.json) (active) and [default_register_config.json](default_register_config.json) (reset target). Each entry specifies:
- `offset`: Starting Modbus address
- `memory_area`: `"coil"` | `"discrete-input"` | `"holding-register"` | `"input-register"`
- `type`: `"int16"` | `"uint16"` | `"int32"` | `"uint32"` | `"int64"` | `"uint64"` | `"float32"` | `"float64"` | `"boolean"` | `"word"`
- `function`: `"const"` | `"sin"` | `"random"` | `"const_smooth"` | `"smooth"` | `"validated"`
- `a`, `b`, `c`: Function parameters (min, max, frequency for sine)
- `scale`, `min_value`, `max_value`: Optional scaling
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
