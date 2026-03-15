import logging

from pymodbus.datastore import (
    ModbusSequentialDataBlock,
    ModbusDeviceContext,
    ModbusServerContext,
)
from pymodbus.server import StartAsyncTcpServer

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)

_SLAVE_ID = 0x00
_FC_CO = 1  # Coils
_FC_DI = 2  # Discrete Inputs
_FC_HR = 3  # Holding Registers
_FC_IR = 4  # Input Registers
_DEFAULT_SIZE = 300


class ModbusServer:
    def __init__(self, host: str = "0.0.0.0", port: int = 5020):
        self._port = port
        self._host = host
        self._logger = logging.getLogger("ModbusServer")
        self._tcp_server = None

        store = ModbusDeviceContext(
            di=ModbusSequentialDataBlock(1, [0] * _DEFAULT_SIZE),
            co=ModbusSequentialDataBlock(1, [0] * _DEFAULT_SIZE),
            hr=ModbusSequentialDataBlock(1, [0] * _DEFAULT_SIZE),
            ir=ModbusSequentialDataBlock(1, [0] * _DEFAULT_SIZE),
        )
        self._context = ModbusServerContext(devices=store, single=True)

        self._logger.info("Modbus server configured on %s:%d", self._host, self._port)
        self._logger.info(
            "Memory areas initialized: DI[0-%d], CO[0-%d], HR[0-%d], IR[0-%d] (all zeros)",
            _DEFAULT_SIZE - 1,
            _DEFAULT_SIZE - 1,
            _DEFAULT_SIZE - 1,
            _DEFAULT_SIZE - 1,
        )

    async def start(self):
        """Start the async TCP server. Blocks until the server is stopped."""
        self._logger.info(
            "Starting Modbus TCP server on %s:%d ...", self._host, self._port
        )
        self._tcp_server = await StartAsyncTcpServer(
            context=self._context,
            address=(self._host, self._port),
        )
        return self._tcp_server

    def server(self):
        """Return the underlying TCP server instance (available after start())."""
        return self._tcp_server

    # ------------------------------------------------------------------
    # Write helpers
    # ------------------------------------------------------------------

    def update_di(self, address: int, values: list[int]):
        """Write values to Discrete Inputs starting at address."""
        self._context[_SLAVE_ID].setValues(_FC_DI, address, values)
        self._logger.debug("DI[%d] <- %s", address, values)

    def update_co(self, address: int, values: list[int]):
        """Write values to Coils starting at address."""
        self._context[_SLAVE_ID].setValues(_FC_CO, address, values)
        self._logger.debug("CO[%d] <- %s", address, values)

    def update_hr(self, address: int, values: list[int]):
        """Write values to Holding Registers starting at address."""
        self._context[_SLAVE_ID].setValues(_FC_HR, address, values)
        self._logger.debug("HR[%d] <- %s", address, values)

    def update_ir(self, address: int, values: list[int]):
        """Write values to Input Registers starting at address."""
        self._context[_SLAVE_ID].setValues(_FC_IR, address, values)
        self._logger.debug("IR[%d] <- %s", address, values)

    # ------------------------------------------------------------------
    # Read helpers
    # ------------------------------------------------------------------

    def read_di(self, address: int, count: int = 1) -> list[int]:
        """Read count Discrete Input values starting at address."""
        return self._context[_SLAVE_ID].getValues(_FC_DI, address, count)

    def read_co(self, address: int, count: int = 1) -> list[int]:
        """Read count Coil values starting at address."""
        return self._context[_SLAVE_ID].getValues(_FC_CO, address, count)

    def read_hr(self, address: int, count: int = 1) -> list[int]:
        """Read count Holding Register values starting at address."""
        return self._context[_SLAVE_ID].getValues(_FC_HR, address, count)

    def read_ir(self, address: int, count: int = 1) -> list[int]:
        """Read count Input Register values starting at address."""
        return self._context[_SLAVE_ID].getValues(_FC_IR, address, count)


def create_modbus_server(host: str = "0.0.0.0", port: int = 5020) -> ModbusServer:
    """Factory function — returns a configured ModbusServer instance."""
    return ModbusServer(host=host, port=port)
