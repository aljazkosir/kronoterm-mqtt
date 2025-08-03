import asyncio
import itertools
import logging
from decimal import Decimal
from typing import Any, Dict, List, Optional, Tuple

from ha_services.mqtt4homeassistant.components.binary_sensor import BinarySensor
from ha_services.mqtt4homeassistant.components.select import Select
from ha_services.mqtt4homeassistant.components.sensor import Sensor
from ha_services.mqtt4homeassistant.components.switch import Switch
from ha_services.mqtt4homeassistant.device import MqttDevice
from ha_services.mqtt4homeassistant.mqtt import get_connected_client
from ha_services.mqtt4homeassistant.utilities.string_utils import slugify
from paho.mqtt.client import Client

from .constants import DEFAULT_DEVICE_MANUFACTURER, REVERSED_DOMESTIC_WATER_OPTIONS
from .modbus import KronotermModbusClient, get_modbus_client
from .settings import Settings

logger = logging.getLogger(__name__)


class KronotermMqttHandler:
    """
    Handler for communicating with Kronoterm heat pump via Modbus and publishing data to MQTT.
    """

    def __init__(self, settings: Settings):
        """
        Initialize the MQTT handler.

        Args:
            settings: Application settings
        """
        self.settings = settings
        self.verbosity = settings.verbosity
        self.heat_pump = settings.heat_pump
        self.device_name = self.heat_pump.device_name

        # Initialize MQTT client
        self.mqtt_client = get_connected_client(settings=settings.mqtt, verbosity=self.verbosity)
        self.mqtt_client.loop_start()

        # Initialize Modbus client
        self.modbus_client: Optional[KronotermModbusClient] = None

        # Initialize device and components
        self.main_device: Optional[MqttDevice] = None
        self.sensors: Dict[int, Tuple[Sensor, Decimal]] = {}
        self.binary_sensors: Dict[int, Tuple[BinarySensor, Optional[int]]] = {}
        self.enum_sensors: Dict[int, Tuple[Sensor, Dict[str, List[Any]]]] = {}
        self.address_ranges: List[Tuple[int, int]] = []
        self.registers: Dict[int, int] = {}

        # Initialize switches and selects
        self.dhw_circulation_switch: Optional[Switch] = None
        self.additional_source_switch: Optional[Switch] = None
        self.domestic_water_operation: Optional[Select] = None

    def __enter__(self):
        """
        Enter the context manager.
        """
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """
        Exit the context manager, cleaning up resources.
        """
        logger.info("Closing MQTT and Modbus clients")

        if self.modbus_client:
            self.modbus_client.disconnect()

        if self.mqtt_client:
            self.mqtt_client.loop_stop()
            self.mqtt_client.disconnect()

    async def init_device(self):
        """
        Initialize the device and components from definitions.
        """
        # Create main device
        self.main_device = MqttDevice(
            name=self.heat_pump.device_name,
            uid=self.settings.mqtt.main_uid,
            manufacturer=DEFAULT_DEVICE_MANUFACTURER,
            model=self.heat_pump.model,
            sw_version="1.0.0",  # TODO: Get version from package
            config_throttle_sec=self.settings.mqtt.publish_config_throttle_seconds,
        )

        # Load definitions
        definitions = self.heat_pump.get_definitions(self.verbosity)

        # Create sensors
        parameters = definitions["sensor"]
        for parameter in parameters:
            if self.verbosity > 1:
                logger.info(f"Creating sensor {parameter}")

            address = parameter["register"] - 1  # KRONOTERM MA_numbering is one-based in documentation!
            scale = parameter["scale"]
            precision = len(str(scale)[str(scale).rfind(".") + 1 :]) if scale < 1 else 0

            self.sensors[address] = (
                Sensor(
                    device=self.main_device,
                    name=parameter["name"],
                    uid=slugify(parameter["name"], "_").lower(),
                    device_class=parameter["device_class"],
                    state_class=parameter["state_class"] if len(parameter["state_class"]) else None,
                    unit_of_measurement=parameter["unit_of_measurement"]
                    if len(parameter["unit_of_measurement"])
                    else None,
                    suggested_display_precision=precision,
                ),
                Decimal(str(parameter["scale"])),
            )

        # Create binary sensors
        binary_sensor_definitions = definitions["binary_sensor"]
        for parameter in binary_sensor_definitions:
            address = parameter["register"] - 1  # KRONOTERM MA_numbering is one-based in documentation!

            self.binary_sensors[address] = (
                BinarySensor(
                    device=self.main_device,
                    name=parameter["name"],
                    uid=slugify(parameter["name"], "_").lower(),
                    device_class=parameter["device_class"] if len(parameter["device_class"]) else None,
                ),
                parameter.get("bit"),
            )

        # Create enum sensors
        enum_sensor_definitions = definitions["enum_sensor"]
        for parameter in enum_sensor_definitions:
            address = parameter["register"] - 1  # KRONOTERM MA_numbering is one-based in documentation!

            self.enum_sensors[address] = (
                Sensor(
                    device=self.main_device,
                    name=parameter["name"],
                    uid=slugify(parameter["name"], "_").lower(),
                    device_class="enum",
                    state_class=None,
                ),
                *parameter["options"],
            )

        # Create switches
        self.dhw_circulation_switch = Switch(
            device=self.main_device,
            name="Circulation of sanitary water",
            uid="dhw_circulation_switch",
            callback=self.dhw_circulation_callback,
        )

        self.additional_source_switch = Switch(
            device=self.main_device,
            name="Additional Source",
            uid="additional_source_switch",
            callback=self.additional_source_callback,
        )

        # Create selects
        self.domestic_water_operation = Select(
            device=self.main_device,
            name="Domestic water operation",
            uid="domestic_water_operation",
            default_option="ON",
            options=("OFF", "ON", "SCHEDULED"),
            callback=self.domestic_water_operation_callback,
        )

        # Compute address ranges for efficient Modbus reading
        addresses = sorted(
            list(self.sensors.keys())
            + list(self.binary_sensors.keys())
            + list(self.enum_sensors.keys())
            + [2327, 2014, 2025]
        )
        self.address_ranges = list(self.ranges(addresses))

        if self.verbosity > 0:
            logger.info(f"Address ranges: {self.address_ranges}")

    def dhw_circulation_callback(self, *, client: Client, component: Switch, old_state: str, new_state: str):
        """
        Callback for DHW circulation switch state change.
        """
        logger.info(f"{component.name} state changed: {old_state!r} -> {new_state!r}")

        value = 1 if new_state == "ON" else 0
        success = self.modbus_client.write_register(address=2327, value=value)

        if success:
            component.set_state(new_state)
            component.publish_state(client)
        else:
            logger.error(f"Failed to write register for {component.name}")

    def additional_source_callback(self, *, client: Client, component: Switch, old_state: str, new_state: str):
        """
        Callback for additional source switch state change.
        """
        logger.info(f"{component.name} state changed: {old_state!r} -> {new_state!r}")

        value = 1 if new_state == "ON" else 0
        success = self.modbus_client.write_register(address=2014, value=value)

        if success:
            component.set_state(new_state)
            component.publish_state(client)
        else:
            logger.error(f"Failed to write register for {component.name}")

    def domestic_water_operation_callback(self, *, client: Client, component: Select, old_state: str, new_state: str):
        """
        Callback for domestic water operation select state change.
        """
        from .constants import DOMESTIC_WATER_OPTIONS

        logger.info(f"{component.name} state changed: {old_state!r} -> {new_state!r}")

        value = DOMESTIC_WATER_OPTIONS[new_state]
        success = self.modbus_client.write_register(address=2025, value=value)

        if success:
            component.set_state(new_state)
            component.publish_state(client)
        else:
            logger.error(f"Failed to write register for {component.name}")

    def ranges(self, addresses: List[int]) -> List[Tuple[int, int]]:
        """
        Prepare intervals of modbus addresses for fetching register groups.
        See https://stackoverflow.com/questions/4628333
        """
        for _, b in itertools.groupby(enumerate(addresses), lambda pair: pair[1] - pair[0]):
            b = list(b)
            yield b[0][1], b[-1][1]

    async def publish_loop(self):
        """
        Main loop for reading data from the heat pump and publishing to MQTT.
        """
        # Initialize device if not already initialized
        if self.main_device is None:
            await self.init_device()

        # Create and connect Modbus client
        self.modbus_client = get_modbus_client(self.heat_pump, self.verbosity)

        # Define switches and selects for updating
        switches = {
            2327: self.dhw_circulation_switch,
            2014: self.additional_source_switch,
        }

        selects = {
            2025: self.domestic_water_operation,
        }

        logger.info("Kronoterm to MQTT publish loop started...")

        while True:
            try:
                # Read register blocks
                self.registers = self.modbus_client.read_register_blocks(self.address_ranges)

                # Update and publish sensor values
                for address, (sensor, scale) in self.sensors.items():
                    if address in self.registers:
                        value = self.registers[address]
                        value = float(scale) * value
                        sensor.set_state(value)
                        sensor.publish(self.mqtt_client)

                # Update and publish binary sensor values
                for address, (sensor, bit) in self.binary_sensors.items():
                    if address in self.registers:
                        value = self.registers[address]
                        if bit is not None:
                            value &= 1 << bit
                        sensor.set_state(sensor.ON if value else sensor.OFF)
                        sensor.publish(self.mqtt_client)

                # Update and publish enum sensor values
                for address, (sensor, options) in self.enum_sensors.items():
                    if address in self.registers:
                        value = self.registers[address]
                        for index, key in enumerate(options["keys"]):  # noqa
                            if value == key:
                                break
                        sensor.set_state(options["values"][index])  # noqa
                        sensor.publish(self.mqtt_client)

                # Update and publish switch states
                for address, switch in switches.items():
                    if address in self.registers:
                        switch.set_state(switch.ON if self.registers[address] else switch.OFF)
                        switch.publish(self.mqtt_client)

                # Update and publish select states
                for address, select in selects.items():
                    if address in self.registers:
                        select.set_state(REVERSED_DOMESTIC_WATER_OPTIONS[self.registers[address]])
                        select.publish(self.mqtt_client)

                # Wait for next iteration
                if self.verbosity > 0:
                    logger.info(f"Waiting {self.settings.polling_interval} seconds for next iteration...")

                await asyncio.sleep(self.settings.polling_interval)

            except Exception as e:
                logger.error(f"Error in publish loop: {e}", exc_info=True)
                logger.info(f"Retrying in {self.settings.polling_interval} seconds...")
                await asyncio.sleep(self.settings.polling_interval)
