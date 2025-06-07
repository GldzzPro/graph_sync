import os
import yaml
from typing import List
import logging
from models import Instance

logger = logging.getLogger(__name__)

class Config:
    """Configuration manager for the application."""

    def __init__(self, config_path: str = None):
        # Determine config file path
        self.config_path = config_path or os.getenv("CONFIG_PATH", "config.yaml")
        self.instances = []
        self.log_level = os.getenv("LOG_LEVEL", "INFO")
        
        # Load configuration
        self._load_config()

    def _load_config(self) -> None:
        """Load configuration from YAML file and/or environment variables."""
        try:
            # Initialize empty instances list
            instances_data = []
            
            # First, try to load from environment variables (Docker priority)
            docker_instances = os.getenv("DOCKER_INSTANCES")
            if docker_instances:
                logger.info(f"Loading instances from DOCKER_INSTANCES environment variable")
                # Format: "name1:url1,name2:url2"
                for instance_str in docker_instances.split(','):
                    if ':' in instance_str:
                        name, url = instance_str.split(':', 1)
                        instances_data.append({
                            'name': name.strip(),
                            'url': url.strip()
                        })
                logger.info(f"Loaded {len(instances_data)} instances from environment")
            
            # If no environment instances, load from YAML file
            elif os.path.exists(self.config_path):
                try:
                    logger.info(f"Loading configuration from {self.config_path}")
                    with open(self.config_path, 'r') as f:
                        config_data = yaml.safe_load(f) or {}
                        
                    # Get instances from config file
                    instances_data = config_data.get('instances', [])
                    logger.info(f"Loaded {len(instances_data)} instances from config file")
                    
                    # Get log level from config file if not set via env var
                    if not os.getenv("LOG_LEVEL"):
                        self.log_level = config_data.get('log_level', 'INFO')
                        
                except Exception as e:
                    logger.warning(f"Failed to load config from {self.config_path}: {e}")
            else:
                logger.warning(f"Config file {self.config_path} not found")

            # Convert to Instance objects
            self.instances = [Instance(**instance) for instance in instances_data]
            
            # Validate instances
            if not self.instances:
                logger.warning("No instances configured. Please check your configuration.")
                logger.info("Available configuration methods:")
                logger.info("1. Set DOCKER_INSTANCES environment variable (format: name1:url1,name2:url2)")
                logger.info(f"2. Create config file at {self.config_path}")
            else:
                logger.info(f"Successfully configured {len(self.instances)} instances:")
                for instance in self.instances:
                    logger.info(f"  - {instance.name}: {instance.url}")
                
            # Validate log level
            valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
            if self.log_level not in valid_levels:
                logger.warning(f"Invalid log level: {self.log_level}. Using INFO instead.")
                self.log_level = "INFO"
                
        except Exception as e:
            logger.error(f"Failed to load configuration: {e}")
            # Ensure instances is at least an empty list
            self.instances = []