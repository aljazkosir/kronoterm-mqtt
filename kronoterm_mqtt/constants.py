"""
Constants used throughout the kronoterm-mqtt project.
"""

# Default Modbus slave ID for Kronoterm heat pumps
MODBUS_SLAVE_ID = 20

# Device information
DEFAULT_DEVICE_MANUFACTURER = "Kronoterm"

# Domestic water operation options
DOMESTIC_WATER_OPTIONS = {
    "OFF": 0,
    "ON": 1,
    "AUTO": 2,
}

# Reversed domestic water options for lookup by value
REVERSED_DOMESTIC_WATER_OPTIONS = {v: k for k, v in DOMESTIC_WATER_OPTIONS.items()}
