# Modbus Server

A Modbus TCP server that simulates industrial device registers with a web-based monitoring UI.

## Get Started

No programming knowledge required — just Docker.

**Step 1 — Install Docker**

Download and install Docker Desktop for your operating system:
[https://www.docker.com/products/docker-desktop](https://www.docker.com/products/docker-desktop)

Once installed, open it and make sure it is running before continuing.

**Step 2 — Run this command**

Open a terminal (Command Prompt on Windows, Terminal on Mac/Linux) and paste:

```bash
docker run --name EG-modbus-simulator-server -p 5020:5020 -p 8080:8080 $(docker build -q https://github.com/Industrial-Elias-Giannakidis/modbus-simulator-server.git)
```

This will download and start the server automatically. Wait until you see a message that the server is running.

**Step 3 — Open the web interface**

Open your browser and go to:

```
http://localhost:8080
```

**Step 4 — Done**

The Modbus simulator is now running:

- **Web UI:** `http://localhost:8080` — monitor and configure registers
- **Modbus TCP:** `localhost:5020` — connect your Modbus client here

---

## Features

- Modbus TCP server (coils, discrete inputs, holding registers, input registers)
- Web UI for real-time register monitoring and configuration
- Endianness/byte-order conversion support
- Live register editing via web interface

## Running with Python

**Install dependencies:**

```bash
pip install aiohttp pymodbus pytest
```

**Configure ports** (optional — edit `.env`):

```
MODBUS_PORT=5020
API_PORT=8080
```

**Start the server:**

```bash
python index.py
```

- Modbus TCP: `localhost:5020`
- Web UI: `http://localhost:8080`

## Running with Docker

**Single command — build and run directly from GitHub (no clone needed):**

```bash
docker run --name EG-modbus-simulator-server -p 5020:5020 -p 8080:8080 $(docker build -q https://github.com/Industrial-Elias-Giannakidis/modbus-simulator-server.git)
```

- Modbus TCP: `<host>:5020`
- Web UI: `http://<host>:8080`

**Run with custom ports:**

```bash
docker run --name EG-modbus-simulator-server -p 502:502 -p 9090:9090 \
  -e MODBUS_PORT=502 -e API_PORT=9090 \
  $(docker build -q https://github.com/Industrial-Elias-Giannakidis/modbus-simulator-server.git)
```

**Local build** (if you have the repo cloned):

```bash
docker build -t modbus-server .
docker run -p 5020:5020 -p 8080:8080 modbus-server
```

## Web API

| Endpoint           | Method   | Description                         |
| ------------------ | -------- | ----------------------------------- |
| `/`                | GET      | Main dashboard                      |
| `/registers`       | GET      | Register viewer UI                  |
| `/config-editor`   | GET      | Configuration editor UI             |
| `/configs`         | GET/PUT  | Get/set register configurations     |
| `/configs/reset`   | POST     | Reset to default config             |
| `/realvalues`      | GET      | Values before Modbus conversion     |
| `/serverRegisters` | GET      | Values read back from Modbus server |
| `/server-config`   | GET/PUT  | Get/set byte order configuration    |
| `/live`            | GET/POST | Get/toggle live randomization mode  |
| `/restart`         | POST     | Reload config from file             |

## Register Configuration

Registers are defined in `register_configs.json`. Each entry supports:

| Field                             | Description                                                                                      |
| --------------------------------- | ------------------------------------------------------------------------------------------------ |
| `offset`                          | Starting Modbus address                                                                          |
| `memory_area`                     | `coil`, `discrete-input`, `holding-register`, `input-register`                                   |
| `type`                            | `int16`, `uint16`, `int32`, `uint32`, `int64`, `uint64`, `float32`, `float64`, `boolean`, `word` |
| `scale`, `min_value`, `max_value` | Optional scaling (integers only; cannot mix `scale` with `min/max`)                              |
| `bit_offset`, `bit_length`        | For `word` type bit-field extraction                                                             |
