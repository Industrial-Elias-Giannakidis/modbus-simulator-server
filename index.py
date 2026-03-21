import asyncio
import dataclasses
import json
import logging
from pathlib import Path

from aiohttp import web

from helpers.byte_order_converter import ByteConverter
from helpers.classes import AddressSnapshot, ByterOrderConfig, MemoryArea, RegisterConfig
from helpers.register_config_validator import RegisterConfigValidator
from helpers.register_converter import RegisterConverter
from helpers.register_scalling import RegisterScalling
from helpers.snapshot import apply_snapshots, randomize_snapshots, register_configs_to_snapshots, snapshot_all
from modbus_server import ModbusServer, create_modbus_server

logger = logging.getLogger("main")

def _load_env(path: str = ".env") -> dict[str, str]:
    env: dict[str, str] = {}
    try:
        for line in Path(path).read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, _, value = line.partition("=")
                env[key.strip()] = value.strip()
    except FileNotFoundError:
        pass
    return env

_env = _load_env()
MODBUS_PORT = int(_env.get("MODBUS_PORT", 5020))
MODBUS_HOST = "0.0.0.0"
API_PORT = int(_env.get("API_PORT", 8080))

_REGISTER_CONFIG_FIELDS = {f.name for f in dataclasses.fields(RegisterConfig)}

def _to_register_config(entry: dict) -> RegisterConfig:
    return RegisterConfig(**{k: v for k, v in entry.items() if k in _REGISTER_CONFIG_FIELDS})

_raw = json.loads(Path("register_configs.json").read_text(encoding="utf-8"))
config_list = [_to_register_config(entry) for entry in _raw]
_configs_json = json.dumps(_raw)
validator = RegisterConfigValidator()

validated_config_list = validator.validate_all(config_list)

invalid_config_list = [c for c in validated_config_list if not c.valid]
valid_config_list = [c for c in validated_config_list if c.valid]

_SERVER_CONFIG_PATH = Path("server_config.json")

def _load_server_config() -> ByterOrderConfig:
    try:
        data = json.loads(_SERVER_CONFIG_PATH.read_text(encoding="utf-8"))
        return ByterOrderConfig(
            big_endian=bool(data.get("big_endian", True)),
            first_word_low=bool(data.get("first_word_low", False)),
            first_double_word_low=bool(data.get("first_double_word_low", False)),
            modicon=bool(data.get("modicon", False)),
        )
    except FileNotFoundError:
        return ByterOrderConfig()

_byte_order_config: ByterOrderConfig = _load_server_config()

registerScalling = RegisterScalling(valid_config_list)
registerConverter = RegisterConverter(valid_config_list)
byteOrderConverter = ByteConverter(valid_config_list, _byte_order_config)

snapshot = register_configs_to_snapshots(valid_config_list)

_WRITABLE_AREAS = {MemoryArea.HOLDING_REGISTER, MemoryArea.COIL}

def _build_writable_set(configs: list[RegisterConfig]) -> set:
    """Return (offset, memory_area) pairs for all configured writable (HR/coil) addresses."""
    result = set()
    for c in configs:
        if c.memory_area in _WRITABLE_AREAS:
            for i in range(c.length or 1):
                result.add((c.offset + i, c.memory_area))
    return result

_all_writable_set = _build_writable_set(valid_config_list)
_live_mode: bool = False

_real_values: list[AddressSnapshot] = []
_server_values: list[AddressSnapshot] = []

_server: ModbusServer | None = None


def _rebuild_pipeline(new_validated: list[RegisterConfig]) -> None:
    """Rebuild all pipeline objects from a validated config list and immediately
    refresh _server_values / _real_values from the current Modbus server state,
    preserving existing register values while reflecting added/removed configs."""
    global registerScalling, registerConverter, byteOrderConverter, snapshot
    global valid_config_list, invalid_config_list, _all_writable_set
    global _real_values, _server_values

    new_valid = [c for c in new_validated if c.valid]
    new_invalid = [c for c in new_validated if not c.valid]

    valid_config_list = new_valid
    invalid_config_list = new_invalid

    registerScalling = RegisterScalling(new_valid)
    registerConverter = RegisterConverter(new_valid)
    byteOrderConverter = ByteConverter(new_valid, _byte_order_config)
    _all_writable_set = _build_writable_set(new_valid)

    if _server is not None:
        raw = snapshot_all(_server)
        _server_values = raw
        s = byteOrderConverter.convert(snapshots=raw)
        s = registerConverter.to_registers(snapshots=s)
        s = registerScalling.scale(snapshots=s)
        _real_values = s
        snapshot = s
    else:
        snapshot = register_configs_to_snapshots(new_valid)


def _snapshots_to_json(snapshots: list[AddressSnapshot]) -> web.Response:
    data = [
        {"offset": s.offset, "memory_area": s.memory_area, "value": s.value}
        for s in snapshots
    ]
    return web.Response(text=json.dumps(data), content_type="application/json")


async def handle_real_values(_request: web.Request) -> web.Response:
    return _snapshots_to_json(_real_values)


async def handle_server_registers(_request: web.Request) -> web.Response:
    return _snapshots_to_json(_server_values)


async def handle_configs(_request: web.Request) -> web.Response:
    return web.Response(text=_configs_json, content_type="application/json")


async def handle_ui(_request: web.Request) -> web.FileResponse:
    return web.FileResponse(Path("static/index.html"))


async def handle_server_registers_ui(_request: web.Request) -> web.FileResponse:
    return web.FileResponse(Path("static/server_registers.html"))


async def handle_configs_ui(_request: web.Request) -> web.FileResponse:
    return web.FileResponse(Path("static/configs.html"))


async def handle_logo(_request: web.Request) -> web.FileResponse:
    return web.FileResponse(Path("docs/logo.png"))


async def handle_footer(_request: web.Request) -> web.FileResponse:
    return web.FileResponse(Path("static/footer.html"))


async def handle_footer_css(_request: web.Request) -> web.FileResponse:
    return web.FileResponse(Path("static/footer.css"))


async def handle_server_config_get(_request: web.Request) -> web.Response:
    return web.Response(text=json.dumps(dataclasses.asdict(_byte_order_config)), content_type="application/json")


async def handle_server_config_update(request: web.Request) -> web.Response:
    global _byte_order_config, byteOrderConverter, _server_values
    try:
        data = await request.json()
        new_bo = ByterOrderConfig(
            big_endian=bool(data.get("big_endian", True)),
            first_word_low=bool(data.get("first_word_low", False)),
            first_double_word_low=bool(data.get("first_double_word_low", False)),
            modicon=bool(data.get("modicon", False)),
        )
        _SERVER_CONFIG_PATH.write_text(json.dumps(dataclasses.asdict(new_bo), indent=2), encoding="utf-8")
        _byte_order_config = new_bo
        byteOrderConverter = ByteConverter(valid_config_list, _byte_order_config)
        registers = []
        if _real_values:
            s = registerScalling.unscale(snapshots=_real_values)
            s = registerConverter.to_snapshots(snapshots=s)
            s = byteOrderConverter.convert(snapshots=s)
            _server_values = s
            registers = [{"offset": snap.offset, "memory_area": snap.memory_area, "value": snap.value} for snap in s]
        return web.Response(text=json.dumps({**dataclasses.asdict(new_bo), "registers": registers}), content_type="application/json")
    except Exception as e:
        return web.Response(status=400, text=json.dumps({"error": str(e)}), content_type="application/json")


async def handle_configs_reset(_request: web.Request) -> web.Response:
    global _configs_json
    try:
        default_text = Path("default_register_config.json").read_text(encoding="utf-8")
        data = json.loads(default_text)
        text = json.dumps(data, indent=2, ensure_ascii=False)
        Path("register_configs.json").write_text(text, encoding="utf-8")
        _configs_json = json.dumps(data)

        new_config_list = [_to_register_config(entry) for entry in data]
        _rebuild_pipeline(validator.validate_all(new_config_list))

        return web.Response(text=json.dumps(data), content_type="application/json")
    except Exception as e:
        return web.Response(
            status=400,
            text=json.dumps({"error": str(e)}),
            content_type="application/json",
        )


async def handle_configs_update(request: web.Request) -> web.Response:
    global _configs_json
    try:
        data = await request.json()
        text = json.dumps(data, indent=2, ensure_ascii=False)
        Path("register_configs.json").write_text(text, encoding="utf-8")
        _configs_json = json.dumps(data)

        new_config_list = [_to_register_config(entry) for entry in data]
        _rebuild_pipeline(validator.validate_all(new_config_list))

        return web.Response(text='{"ok":true}', content_type="application/json")
    except Exception as e:
        return web.Response(
            status=400,
            text=json.dumps({"error": str(e)}),
            content_type="application/json",
        )


async def handle_restart(_request: web.Request) -> web.Response:
    global _configs_json
    try:
        raw = json.loads(Path("register_configs.json").read_text(encoding="utf-8"))
        _configs_json = json.dumps(raw)

        new_config_list = [_to_register_config(entry) for entry in raw]
        _rebuild_pipeline(validator.validate_all(new_config_list))

        return web.Response(text='{"ok":true}', content_type="application/json")
    except Exception as e:
        return web.Response(status=400, text=json.dumps({"error": str(e)}), content_type="application/json")


async def handle_live_get(_request: web.Request) -> web.Response:
    return web.Response(text=json.dumps({"live": _live_mode}), content_type="application/json")


async def handle_live_toggle(_request: web.Request) -> web.Response:
    global _live_mode
    _live_mode = not _live_mode
    return web.Response(text=json.dumps({"live": _live_mode}), content_type="application/json")


async def poll_loop(server: ModbusServer):
    """Every second, snapshot all memory areas."""
    global _real_values, _server_values, snapshot
    while True:
        # Server is truth — read and convert to real values
        snapshot = snapshot_all(server)
        if _live_mode:
            snapshot = randomize_snapshots(snapshot, live_mode=_live_mode)
            apply_snapshots(server, snapshots=snapshot)
        _server_values = snapshot
        snapshot = byteOrderConverter.convert(snapshots=snapshot)
        snapshot = registerConverter.to_registers(snapshots=snapshot)
        snapshot = registerScalling.scale(snapshots=snapshot)
        _real_values = snapshot

        await asyncio.sleep(1)

async def main():
    global _server
    server = create_modbus_server(host=MODBUS_HOST, port=MODBUS_PORT)
    _server = server
    try:
        asyncio.create_task(poll_loop(server))

        app = web.Application()
        app.router.add_get("/", handle_ui)
        app.router.add_get("/registers", handle_server_registers_ui)
        app.router.add_get("/config-editor", handle_configs_ui)
        app.router.add_get("/configs", handle_configs)
        app.router.add_put("/configs", handle_configs_update)
        app.router.add_post("/configs/reset", handle_configs_reset)
        app.router.add_get("/server-config", handle_server_config_get)
        app.router.add_put("/server-config", handle_server_config_update)
        app.router.add_get("/realvalues", handle_real_values)
        app.router.add_get("/serverRegisters", handle_server_registers)
        app.router.add_post("/restart", handle_restart)
        app.router.add_get("/live", handle_live_get)
        app.router.add_post("/live", handle_live_toggle)
        app.router.add_get("/logo.png", handle_logo)
        app.router.add_get("/footer.html", handle_footer)
        app.router.add_get("/footer.css", handle_footer_css)
        runner = web.AppRunner(app)
        await runner.setup()
        site = web.TCPSite(runner, "0.0.0.0", API_PORT)
        await site.start()
        logger.info("Web API listening on port %d", API_PORT)

        await server.start()
    except Exception as e:
        logger.error("Failed to start Modbus server: %s", e)
        raise


if __name__ == "__main__":
    asyncio.run(main())
