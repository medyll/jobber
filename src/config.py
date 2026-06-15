"""
Jobber Configuration Module

Centralized configuration management for Jobber.
Loads settings from config.yaml and provides easy access.
"""

import os
import yaml
from typing import Dict, Any, Optional

class Config:
    """Configuration manager for Jobber."""
    
    def __init__(self, config_path: Optional[str] = None):
        """Initialize configuration from YAML file.
        
        Args:
            config_path: Path to config file. Defaults to 'config.yaml' in project root.
        """
        self.config_path = config_path or self._find_config_path()
        self._config = self._load_config()
    
    def _find_config_path(self) -> str:
        """Find the configuration file path."""
        # Look in current directory first
        if os.path.exists('config.yaml'):
            return 'config.yaml'
        
        # Look in project root (one level up from src/)
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        config_in_root = os.path.join(project_root, 'config.yaml')
        if os.path.exists(config_in_root):
            return config_in_root
        
        raise FileNotFoundError(
            "Configuration file 'config.yaml' not found. "
            "Please create one or run install.ps1 to generate a default configuration."
        )
    
    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from YAML file."""
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
            return config or {}
        except Exception as e:
            raise RuntimeError(f"Failed to load configuration from {self.config_path}: {e}")
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get configuration value by key with dot notation.
        
        Args:
            key: Dot-notated key (e.g., 'ollama.enabled')
            default: Default value if key not found
            
        Returns:
            Configuration value or default
        """
        keys = key.split('.')
        value = self._config
        
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default
        
        return value
    
    def get_ollama_config(self) -> Dict[str, Any]:
        """Get Ollama configuration."""
        return self.get('ollama', {})
    
    def get_playwright_config(self) -> Dict[str, Any]:
        """Get Playwright configuration."""
        return self.get('playwright', {})
    
    def get_logging_config(self) -> Dict[str, Any]:
        """Get logging configuration."""
        return self.get('logging', {})
    
    def get_paths(self) -> Dict[str, Any]:
        """Get paths configuration."""
        return self.get('paths', {})
    
    def get_mcp_server_config(self) -> Dict[str, Any]:
        """Get MCP server configuration."""
        return self.get('mcp_server', {})
    
    def reload(self) -> None:
        """Reload configuration from file."""
        self._config = self._load_config()

# Global config instance
config = Config()


def get_config() -> Config:
    """Get the global configuration instance."""
    return config
