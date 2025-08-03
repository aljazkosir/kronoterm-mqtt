import dataclasses
import logging
import os
import tomllib
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv
from ha_services.mqtt4homeassistant.data_classes import MqttSettings

logger = logging.getLogger(__name__)


@dataclasses.dataclass
class ModbusSettings:
    """
    Settings for the Modbus TCP connection to the heat pump.
    """

    host: Optional[str] = None
    port: Optional[int] = None
    timeout: float = 5
    slave_id: int = 20  # Default Modbus slave ID for Kronoterm heat pumps


@dataclasses.dataclass
class HeatPump:
    """
    Configuration for the heat pump.
    """

    definitions_name: str = "kronoterm"
    device_name: str = "Heat Pump"  # Appearing in MQTT as Device
    model: str = "Adapt"  # Just for MQTT device Model info
    modbus: dataclasses = dataclasses.field(default_factory=ModbusSettings)

    def get_definitions(self, verbosity: int) -> dict:
        """
        Load the definitions from the TOML file.
        """
        # Look for definitions in several locations
        possible_paths = [
            Path(f"/app/definitions/{self.definitions_name}.toml"),  # Docker container path
            Path(f"./definitions/{self.definitions_name}.toml"),  # Current directory
            Path(__file__).parent.parent / "definitions" / f"{self.definitions_name}.toml",  # Package directory
        ]

        for definition_file_path in possible_paths:
            if definition_file_path.exists():
                content = definition_file_path.read_text(encoding="UTF-8")
                definitions = tomllib.loads(content)

                if verbosity > 1:
                    from rich.pretty import pprint

                    pprint(definitions)

                return definitions

        raise FileNotFoundError(
            f"Could not find definitions file {self.definitions_name}.toml in any of the expected locations"
        )


@dataclasses.dataclass
class Settings:
    """
    Main settings class for kronoterm-mqtt.

    This class contains all the configuration options for the application.
    """

    # Information about the MQTT server
    mqtt: dataclasses = dataclasses.field(default_factory=MqttSettings)

    # Heat pump configuration
    heat_pump: dataclasses = dataclasses.field(default_factory=HeatPump)

    # Polling interval in seconds
    polling_interval: int = 10

    # Verbosity level (0-3)
    verbosity: int = 0

    def __post_init__(self):
        """
        Set default values that aren't handled by default_factory and apply environment variables
        """
        # Set MQTT defaults
        self.mqtt.main_uid = "kronoterm"

        # Apply MQTT settings from environment variables
        if mqtt_host := os.environ.get("MQTT_HOST"):
            self.mqtt.host = mqtt_host

        if mqtt_port := os.environ.get("MQTT_PORT"):
            self.mqtt.port = int(mqtt_port)

        if mqtt_username := os.environ.get("MQTT_USERNAME"):
            self.mqtt.user_name = mqtt_username

        if mqtt_password := os.environ.get("MQTT_PASSWORD"):
            self.mqtt.password = mqtt_password

        if mqtt_main_uid := os.environ.get("MQTT_MAIN_UID"):
            self.mqtt.main_uid = mqtt_main_uid

        # Apply Heat Pump settings from environment variables
        if heat_pump_definitions_name := os.environ.get("HEAT_PUMP_DEFINITIONS_NAME"):
            self.heat_pump.definitions_name = heat_pump_definitions_name

        if heat_pump_device_name := os.environ.get("HEAT_PUMP_DEVICE_NAME"):
            self.heat_pump.device_name = heat_pump_device_name

        if heat_pump_model := os.environ.get("HEAT_PUMP_MODEL"):
            self.heat_pump.model = heat_pump_model

        # Apply Modbus settings from environment variables
        if modbus_host := os.environ.get("MODBUS_HOST"):
            self.heat_pump.modbus.host = modbus_host

        if modbus_port := os.environ.get("MODBUS_PORT"):
            self.heat_pump.modbus.port = int(modbus_port)

        if modbus_timeout := os.environ.get("MODBUS_TIMEOUT"):
            self.heat_pump.modbus.timeout = float(modbus_timeout)

        if modbus_slave_id := os.environ.get("MODBUS_SLAVE_ID"):
            self.heat_pump.modbus.slave_id = int(modbus_slave_id)


def load_settings() -> Settings:
    """
    Load settings from environment variables.

    Returns:
        Settings object with the loaded configuration.
    """
    # Load environment variables from .env file if it exists
    dotenv_paths = [
        Path(".env"),  # Current directory
        Path(__file__).parent.parent / ".env",  # Project root directory
    ]

    for dotenv_path in dotenv_paths:
        if dotenv_path.exists():
            load_dotenv(dotenv_path=dotenv_path)
            logger.info(f"Loaded environment variables from {dotenv_path}")
            break

    return Settings()
