# Kronoterm MQTT (fully vibe coded :D)

A Docker-based application that connects to Kronoterm heat pumps via Modbus TCP and publishes data to MQTT for Home Assistant integration.

## Overview

Kronoterm MQTT reads data from Kronoterm heat pumps connected via Modbus TCP interface and publishes it to an MQTT broker. Home Assistant can then discover and display the sensor readings automatically.

## Features

- Connects to Kronoterm heat pumps via Modbus TCP
- Publishes sensor data to MQTT for Home Assistant integration
- Supports Home Assistant MQTT discovery
- Configurable via environment variables in a .env file
- Packaged as a Docker container for easy deployment

## Requirements

- Docker and Docker Compose
- Kronoterm heat pump with Modbus TCP interface
- MQTT broker (e.g., Mosquitto)
- Home Assistant with MQTT integration

## Installation

### Using Docker Compose

1. Clone this repository:
   ```bash
   git clone https://github.com/yourusername/kronoterm-mqtt.git
   cd kronoterm-mqtt
   ```

2. Create a `.env` file from the example:
   ```bash
   cp .env.example .env
   ```

3. Configure the application by editing the `.env` file with your specific settings

4. Build and start the container:
   ```bash
   docker-compose up -d
   ```

### Manual Installation

1. Clone this repository:
   ```bash
   git clone https://github.com/yourusername/kronoterm-mqtt.git
   cd kronoterm-mqtt
   ```

2. Install Poetry (if not already installed):
   ```bash
   curl -sSL https://install.python-poetry.org | python3 -
   ```

3. Install dependencies using Poetry:
   ```bash
   poetry install
   ```

4. Create a `.env` file from the example:
   ```bash
   cp .env.example .env
   ```

5. Configure the application by editing the `.env` file with your specific settings

6. Run the application:
   ```bash
   poetry run python main.py
   ```

   Or activate the Poetry virtual environment and run:
   ```bash
   poetry shell
   python main.py
   ```

## Configuration

The application is configured using environment variables defined in a `.env` file.

### Environment Variables

Environment variables are set in a `.env` file in the project root. This file is:
1. Automatically loaded by Docker Compose using the `env_file` directive when running the container
2. Loaded by the application directly when running manually

The `.env` file approach simplifies configuration management by keeping all settings in one place and works consistently in both Docker and non-Docker environments.

The following environment variables are available:

### MQTT Settings
- `MQTT_HOST`: MQTT broker host
- `MQTT_PORT`: MQTT broker port
- `MQTT_USERNAME`: MQTT username
- `MQTT_PASSWORD`: MQTT password
- `MQTT_CLIENT_ID`: MQTT client ID
- `MQTT_MAIN_UID`: Main device UID for Home Assistant

### Heat Pump Settings
- `HEAT_PUMP_DEFINITIONS_NAME`: Name of the definitions file (without .toml extension)
- `HEAT_PUMP_DEVICE_NAME`: Device name in Home Assistant
- `HEAT_PUMP_MODEL`: Heat pump model

### Modbus Settings
- `MODBUS_HOST`: Modbus TCP host
- `MODBUS_PORT`: Modbus TCP port
- `MODBUS_TIMEOUT`: Modbus timeout in seconds
- `MODBUS_SLAVE_ID`: Modbus slave ID

### General Settings
- `POLLING_INTERVAL`: Polling interval in seconds
- `VERBOSITY`: Verbosity level (0-3)

An example `.env` file is provided as `.env.example` in the repository. You can copy this file to `.env` and modify it with your specific settings.

## Home Assistant Integration

1. Install the MQTT integration in Home Assistant if you haven't already.
2. Start the Kronoterm MQTT application.
3. The heat pump should appear in Home Assistant under Settings -> Devices & Services -> MQTT.

## Customizing Sensors

The sensors, binary sensors, and enum sensors are defined in the `definitions/kronoterm.toml` file. You can customize this file to add, remove, or modify sensors.

To disable a sensor, change `[[sensor]]` to `[[sensor_disabled]]` in the definition file.

## Troubleshooting

- **Connection Issues**: Ensure that the Modbus TCP host and port are correct and that the heat pump is accessible from the Docker container.
- **MQTT Issues**: Verify that the MQTT broker is running and accessible, and that the credentials are correct.
- **Sensor Issues**: Check the logs for any errors related to reading or publishing sensor data.

To increase verbosity for debugging, set the `VERBOSITY` environment variable to a higher value (1-3) in the `.env` file or use the `--verbose` command-line option.

## License

This project is licensed under the GPL-3.0 License - see the LICENSE file for details.

## Acknowledgements

- [kronoterm2mqtt](https://github.com/kosl/kronoterm2mqtt) - The original project that this is based on
- [ha-services](https://github.com/jedie/ha-services) - Home Assistant MQTT services
- [pymodbus](https://github.com/pymodbus-dev/pymodbus) - Modbus protocol implementation
