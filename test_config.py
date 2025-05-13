import os
import pytest
import yaml
import logging

from config import Config, AppConfig
from models import Instance

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

CONFIG_PATH = os.getenv('CONFIG_PATH', 'config.yaml')


def test_config_loads_from_file_and_env():
    logger.info(f"Using config file at: {CONFIG_PATH}")
    print(f"Loading configuration from {CONFIG_PATH}")

    # Ensure CONFIG_PATH exists
    assert os.path.exists(CONFIG_PATH), f"Config file not found: {CONFIG_PATH}"
    print("Config file found.")
    logger.debug("Config file exists check passed.")

    # Load config
    cfg = Config(config_path=CONFIG_PATH)
    print("Config object instantiated.")
    logger.debug("Config instantiation successful: %s", cfg)

    # Validate AppConfig
    assert isinstance(cfg.app_config, AppConfig), "app_config is not an AppConfig instance"
    print("app_config is a valid AppConfig instance.")
    logger.debug("AppConfig type check passed.")

    # Validate log_level
    log_level = cfg.log_level
    print(f"Log level loaded: {log_level}")
    logger.debug("Loaded log level: %s", log_level)
    assert log_level in ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"], "Invalid log level"

    # Validate instances
    instances = cfg.instances
    print(f"Number of instances loaded: {len(instances)}")
    logger.debug("Instances loaded: %s", instances)
    assert len(instances) > 0, "No Odoo instances configured"

    # Check each instance has required attributes
    for inst in instances:
        print(f"Checking instance: {inst.name}")
        logger.debug("Validating instance: %s", inst)
        assert isinstance(inst.name, str) and inst.name, "Instance name missing"
        assert isinstance(inst.url, str) and inst.url.startswith('http'), "Invalid URL"
        assert isinstance(inst.db_name, str) and inst.db_name, "DB name missing"
        assert isinstance(inst.username, str) and inst.username, "Username missing"
        assert isinstance(inst.password, str) and inst.password, "Password missing"
        print(f"Instance {inst.name} validation passed.")
        logger.info("Instance %s validated successfully.", inst.name)

print(test_config_loads_from_file_and_env())