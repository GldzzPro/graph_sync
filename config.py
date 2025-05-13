import os
import yaml
from typing import List
from pydantic import BaseModel, Field, validator
from dotenv import load_dotenv
from models import Instance


class AppConfig(BaseModel):
    """Application configuration for Odoo JSON-RPC instances."""
    instances: List[Instance] = Field(..., description="List of Odoo instance configurations")
    log_level: str = Field("INFO", description="Logging level")

    @validator('instances')
    def validate_instances(cls, v):
        if not v:
            raise ValueError('At least one Odoo instance must be configured')
        return v

    @validator('log_level')
    def validate_log_level(cls, v):
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if v not in valid_levels:
            raise ValueError(f'Log level must be one of {valid_levels}')
        return v


class Config:
    """Configuration manager for the application."""

    def __init__(self, config_path: str = None):
        # Load environment variables from .env file
        load_dotenv()

        # Determine config file path
        self.config_path = config_path or os.getenv("CONFIG_PATH", "config.yml")
        # Load and validate the application configuration
        self.app_config = self._load_config()

    def _load_config(self) -> AppConfig:
        """Load configuration from YAML file and/or environment variables."""
        try:
            # Load from YAML if present
            config_data = {}
            if os.path.exists(self.config_path):
                with open(self.config_path, 'r') as f:
                    config_data = yaml.safe_load(f) or {}

            # Ensure instances key exists
            instances_data = config_data.get('instances', [])

            # Override via environment variables for Docker container instances
            docker_instances = os.getenv("DOCKER_INSTANCES")
            if docker_instances:
                # Format: "name1:url1,name2:url2"
                for instance_str in docker_instances.split(','):
                    if ':' in instance_str:
                        name, url = instance_str.split(':', 1)
                        instances_data.append({
                            'name': name.strip(),
                            'url': url.strip()
                        })

            config_data['instances'] = instances_data
            config_data['log_level'] = os.getenv("LOG_LEVEL", config_data.get('log_level', 'INFO'))

            # Validate and return
            return AppConfig(**config_data)
        except Exception as e:
            raise ValueError(f"Failed to load configuration: {e}")

    @property
    def instances(self) -> List[Instance]:
        """Get the list of Odoo instances."""
        return self.app_config.instances

    @property
    def log_level(self) -> str:
        """Get the log level."""
        return self.app_config.log_level
