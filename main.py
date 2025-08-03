#!/usr/bin/env python3
"""
Kronoterm MQTT - Main entry point

This script is the main entry point for the Kronoterm MQTT application.
It loads the configuration, initializes the MQTT handler, and runs the publish loop.
"""

import argparse
import asyncio
import logging
import sys

from kronoterm_mqtt.mqtt_handler import KronotermMqttHandler
from kronoterm_mqtt.settings import load_settings

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)

logger = logging.getLogger("kronoterm-mqtt")


async def main():
    """
    Main entry point for the application.
    """
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="Kronoterm MQTT - Publish heat pump data to MQTT")
    parser.add_argument("-c", "--config", help="Path to the configuration file", type=str, default=None)
    parser.add_argument(
        "-v", "--verbose", help="Increase verbosity level (can be used multiple times)", action="count", default=0
    )
    args = parser.parse_args()

    # Load settings
    try:
        settings = load_settings()

        # Override verbosity from command line if specified
        if args.verbose > 0:
            settings.verbosity = args.verbose

        # Set log level based on verbosity
        if settings.verbosity > 0:
            logging.getLogger().setLevel(logging.DEBUG)

        logger.info(f"Loaded configuration with verbosity level {settings.verbosity}")
    except Exception as e:
        logger.error(f"Error loading configuration: {e}")
        sys.exit(1)

    # Initialize MQTT handler
    try:
        with KronotermMqttHandler(settings) as mqtt_handler:
            logger.info("Starting Kronoterm MQTT handler")

            # Run the publish loop
            await mqtt_handler.publish_loop()
    except KeyboardInterrupt:
        logger.info("Received keyboard interrupt, shutting down")
    except Exception as e:
        logger.error(f"Error in main loop: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    # Run the main function
    asyncio.run(main())
