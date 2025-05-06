import os
import yaml
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field, validator
from dotenv import load_dotenv
from models import Instance


class Neo4jConfig(BaseModel):
    """Neo4j database configuration."""
    uri: str
    username: str
    password: str
    
    @validator('uri')
    def validate_uri(cls, v):
        if not v.startswith('bolt://') and not v.startswith('neo4j://') and not v.startswith('neo4j+s://'):
            raise ValueError('Neo4j URI must start with bolt://, neo4j://, or neo4j+s://')
        return v


class AppConfig(BaseModel):
    """Application configuration."""
    instances: List[Instance]
    neo4j: Neo4jConfig
    log_level: str = "INFO"
    
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
    
    def __init__(self):
        # Load environment variables from .env file
        load_dotenv()
        
        # Load configuration from YAML file or environment variables
        self.app_config = self._load_config()
    
    def _load_config(self) -> AppConfig:
        """Load configuration from YAML file and/or environment variables."""
        try:
            # First try to load from YAML file
            config_data = {}
            config_path = os.getenv("CONFIG_PATH", "config.yaml")
            
            if os.path.exists(config_path):
                with open(config_path, "r") as f:
                    config_data = yaml.safe_load(f) or {}
            
            # Initialize with empty structures if not present
            if "instances" not in config_data:
                config_data["instances"] = []
            if "neo4j" not in config_data:
                config_data["neo4j"] = {}
            
            # Override with environment variables
            
            # Neo4j configuration
            neo4j_uri = os.getenv("NEO4J_URI")
            neo4j_user = os.getenv("NEO4J_USERNAME")
            neo4j_pass = os.getenv("NEO4J_PASSWORD")
            
            if neo4j_uri:
                config_data["neo4j"]["uri"] = neo4j_uri
            if neo4j_user:
                config_data["neo4j"]["username"] = neo4j_user
            if neo4j_pass:
                config_data["neo4j"]["password"] = neo4j_pass
            
            # Odoo instance configuration from environment
            odoo_url = os.getenv("ODOO_URL")
            odoo_db = os.getenv("ODOO_DB")
            odoo_user = os.getenv("ODOO_USERNAME")
            odoo_pass = os.getenv("ODOO_PASSWORD")
            odoo_api_key = os.getenv("ODOO_API_KEY")
            
            if odoo_url:
                # Add or update the first instance
                if not config_data["instances"]:
                    config_data["instances"].append({})
                
                config_data["instances"][0]["name"] = "odoo"
                config_data["instances"][0]["url"] = odoo_url
                
                if odoo_db:
                    config_data["instances"][0]["db_name"] = odoo_db
                if odoo_user:
                    config_data["instances"][0]["username"] = odoo_user
                if odoo_pass:
                    config_data["instances"][0]["password"] = odoo_pass
                if odoo_api_key:
                    config_data["instances"][0]["api_key"] = odoo_api_key
            
            # Log level
            log_level = os.getenv("LOG_LEVEL")
            if log_level:
                config_data["log_level"] = log_level
            
            # Validate and create the config object
            return AppConfig(**config_data)
        except Exception as e:
            raise ValueError(f"Failed to load configuration: {str(e)}")
    
    @property
    def instances(self) -> List[Instance]:
        """Get the list of Odoo instances."""
        return self.app_config.instances
    
    @property
    def neo4j(self) -> Neo4jConfig:
        """Get the Neo4j configuration."""
        return self.app_config.neo4j
    
    @property
    def log_level(self) -> str:
        """Get the log level."""
        return self.app_config.log_level