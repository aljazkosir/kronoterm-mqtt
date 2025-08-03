import logging
from typing import Dict, List, Optional, Tuple

from pymodbus.client import ModbusTcpClient
from pymodbus.exceptions import ModbusIOException
from pymodbus.pdu import ExceptionResponse
from pymodbus.pdu.register_message import ReadHoldingRegistersResponse, WriteSingleRegisterResponse

from .settings import HeatPump, ModbusSettings

logger = logging.getLogger(__name__)


class KronotermModbusClient:
    """
    Client for communicating with Kronoterm heat pump via Modbus TCP.
    """

    def __init__(self, settings: ModbusSettings, slave_id: int = 20):
        """
        Initialize the Modbus client.

        Args:
            settings: Modbus connection settings
            slave_id: Modbus slave ID (default: 20 for Kronoterm heat pumps)
        """
        self.settings = settings
        self.slave_id = slave_id
        self.client = None

    def connect(self) -> bool:
        """
        Connect to the Modbus TCP server.

        Returns:
            True if connection was successful, False otherwise

        Raises:
            ValueError: If host or port is not set in the settings
        """
        # Check if host and port are set
        if self.settings.host is None:
            raise ValueError("Modbus host is not set. Please set MODBUS_HOST in your environment variables.")

        if self.settings.port is None:
            raise ValueError("Modbus port is not set. Please set MODBUS_PORT in your environment variables.")

        self.client = ModbusTcpClient(host=self.settings.host, port=self.settings.port, timeout=self.settings.timeout)

        connected = self.client.connect()
        if connected:
            logger.info(f"Connected to Modbus TCP server at {self.settings.host}:{self.settings.port}")
        else:
            logger.error(f"Failed to connect to Modbus TCP server at {self.settings.host}:{self.settings.port}")

        return connected

    def disconnect(self):
        """
        Disconnect from the Modbus TCP server.
        """
        if self.client:
            self.client.close()
            logger.info("Disconnected from Modbus TCP server")

    def read_holding_registers(self, address: int, count: int) -> Optional[List[int]]:
        """
        Read holding registers from the heat pump.

        Args:
            address: Starting register address
            count: Number of registers to read

        Returns:
            List of register values, or None if an error occurred
        """
        if not self.client:
            logger.error("Modbus client not connected")
            return None

        response = self.client.read_holding_registers(address=address, count=count, device_id=self.slave_id)

        if isinstance(response, (ExceptionResponse, ModbusIOException)):
            logger.error(f"Error reading registers: {response}")
            return None

        assert isinstance(response, ReadHoldingRegistersResponse), f"Unexpected response type: {type(response)}"

        # Convert values to signed integers
        return [value - (value >> 15 << 16) for value in response.registers]

    def write_register(self, address: int, value: int) -> bool:
        """
        Write a value to a register.

        Args:
            address: Register address
            value: Value to write

        Returns:
            True if write was successful, False otherwise
        """
        if not self.client:
            logger.error("Modbus client not connected")
            return False

        response = self.client.write_register(address=address, value=value, slave=self.slave_id)

        if isinstance(response, (ExceptionResponse, ModbusIOException)):
            logger.error(f"Error writing register: {response}")
            return False

        assert isinstance(response, WriteSingleRegisterResponse), f"Unexpected response type: {type(response)}"
        return True

    def read_register_blocks(self, address_ranges: List[Tuple[int, int]]) -> Dict[int, int]:
        """
        Read multiple blocks of registers.

        Args:
            address_ranges: List of (start_address, end_address) tuples

        Returns:
            Dictionary mapping register addresses to values
        """
        registers = {}

        for address_start, address_end in address_ranges:
            count = address_end - address_start + 1
            values = self.read_holding_registers(address_start, count)

            if values:
                for i, value in enumerate(values):
                    registers[address_start + i] = value

        return registers


def get_modbus_client(heat_pump: HeatPump, verbosity: int = 0) -> KronotermModbusClient:
    """
    Create and connect a Modbus client for the heat pump.

    Args:
        heat_pump: Heat pump configuration
        verbosity: Verbosity level

    Returns:
        Connected Modbus client
    """
    client = KronotermModbusClient(settings=heat_pump.modbus, slave_id=heat_pump.modbus.slave_id)

    if verbosity > 0:
        logger.info(f"Connecting to Modbus TCP server at {heat_pump.modbus.host}:{heat_pump.modbus.port}")

    connected = client.connect()

    if not connected:
        raise ConnectionError(
            f"Failed to connect to Modbus TCP server at {heat_pump.modbus.host}:{heat_pump.modbus.port}"
        )

    return client
