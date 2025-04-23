import os
import yaml
from typing import List, Dict, Any, Optional
from pydantic import BaseModel
from dotenv import load_dotenv
from models import Instance


class Neo4jConfig(BaseModel):
    """Neo4j database configuration."""
    uri: str
    username: str
    password: str


class AppConfig(BaseModel):
    """Application configuration."""
    instances: List[Instance]
    neo4j: Neo4jConfig
    log_level: str = "INFO"


class Config:
    """Configuration manager for the application."""
    
    def __init__(self):
        # Load environment variables from .env file
        load_dotenv()
        
        # Load configuration from YAML file
        config_path = os.getenv("CONFIG_PATH", "config.yaml")
        self.app_config = self._load_config(config_path)
    
    def _load_config(self, config_path: str) -> AppConfig:
        """Load configuration from YAML file."""
        try:
            with open(config_path, "r") as f:
                config_data = yaml.safe_load(f)
            
            # Override with environment variables if provided
            neo4j_uri = os.getenv("NEO4J_URI")
            neo4j_user = os.getenv("NEO4J_USERNAME")
            neo4j_pass = os.getenv("NEO4J_PASSWORD")
            
            if neo4j_uri:
                config_data["neo4j"]["uri"] = neo4j_uri
            if neo4j_user:
                config_data["neo4j"]["username"] = neo4j_user
            if neo4j_pass:
                config_data["neo4j"]["password"] = neo4j_pass
                
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