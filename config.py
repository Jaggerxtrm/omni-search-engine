"""
Configuration Management

Loads and validates configuration from YAML file with environment variable substitution.
Provides typed access to all configuration settings.
"""

import os
import re
from pathlib import Path
from typing import Optional, Dict, Any
import yaml


class ConfigError(Exception):
    """Raised when configuration is invalid or missing required fields."""
    pass


class Config:
    """
    Configuration manager for Obsidian Semantic Search.

    Loads settings from YAML file with support for:
    - Environment variable substitution: ${VAR_NAME}
    - Path expansion: ~/ to absolute paths
    - Required field validation
    - Nested configuration access
    """

    def __init__(self, config_path: Optional[str] = None):
        """
        Initialize configuration from YAML file.

        Args:
            config_path: Path to config.yaml. Defaults to:
                         1. CONFIG_PATH environment variable
                         2. ./config.yaml
                         3. /data/config.yaml (container default)

        Raises:
            ConfigError: If config file not found or invalid
        """
        # Determine config path
        if config_path is None:
            config_path = os.getenv('CONFIG_PATH')
        if config_path is None:
            # Try local first, then container default
            if Path('./config.yaml').exists():
                config_path = './config.yaml'
            elif Path('/data/config.yaml').exists():
                config_path = '/data/config.yaml'
            else:
                raise ConfigError(
                    "Config file not found. Please set CONFIG_PATH or create config.yaml"
                )

        self.config_path = Path(config_path)
        if not self.config_path.exists():
            raise ConfigError(f"Config file not found: {self.config_path}")

        # Load and parse YAML
        with open(self.config_path, 'r') as f:
            raw_config = yaml.safe_load(f)

        if not isinstance(raw_config, dict):
            raise ConfigError(f"Invalid config file: {self.config_path}")

        # Substitute environment variables
        self._config = self._substitute_env_vars(raw_config)

        # Validate required fields
        self._validate()

    def _substitute_env_vars(self, obj: Any) -> Any:
        """
        Recursively substitute ${VAR_NAME} with environment variables.

        Args:
            obj: Configuration object (dict, list, str, or other)

        Returns:
            Object with environment variables substituted
        """
        if isinstance(obj, dict):
            return {k: self._substitute_env_vars(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [self._substitute_env_vars(item) for item in obj]
        elif isinstance(obj, str):
            # Find all ${VAR_NAME} patterns
            pattern = r'\$\{([^}]+)\}'
            matches = re.findall(pattern, obj)

            for var_name in matches:
                env_value = os.getenv(var_name)
                if env_value is None:
                    raise ConfigError(
                        f"Environment variable not set: {var_name} "
                        f"(required in config: {obj})"
                    )
                obj = obj.replace(f'${{{var_name}}}', env_value)

            return obj
        else:
            return obj

    def _validate(self):
        """Validate required configuration fields."""
        required_fields = [
            ('obsidian_vault_path', str),
            ('openai_api_key', str),
        ]

        for field_name, field_type in required_fields:
            if field_name not in self._config:
                raise ConfigError(f"Missing required field: {field_name}")

            value = self._config[field_name]
            if not isinstance(value, field_type):
                raise ConfigError(
                    f"Invalid type for {field_name}: "
                    f"expected {field_type.__name__}, got {type(value).__name__}"
                )

            # Additional validation for paths and keys
            if field_name == 'obsidian_vault_path':
                vault_path = Path(value).expanduser()
                if not vault_path.exists():
                    raise ConfigError(
                        f"Obsidian vault not found: {value} "
                        f"(expanded: {vault_path})"
                    )

            if field_name == 'openai_api_key':
                if not value.startswith('sk-'):
                    raise ConfigError(
                        f"Invalid OpenAI API key format: should start with 'sk-'"
                    )

    @property
    def vault_path(self) -> Path:
        """Get Obsidian vault path (expanded and absolute)."""
        return Path(self._config['obsidian_vault_path']).expanduser().resolve()

    @property
    def openai_api_key(self) -> str:
        """Get OpenAI API key."""
        return self._config['openai_api_key']

    @property
    def chromadb_path(self) -> Path:
        """Get ChromaDB storage path (expanded and absolute)."""
        default_path = '~/.config/obsidian-semantic-search/chromadb'
        path_str = self._config.get('chromadb_path', default_path)
        return Path(path_str).expanduser().resolve()

    @property
    def target_chunk_size(self) -> int:
        """Get target chunk size in tokens."""
        return self._config.get('chunking', {}).get('target_chunk_size', 800)

    @property
    def max_chunk_size(self) -> int:
        """Get maximum chunk size in tokens."""
        return self._config.get('chunking', {}).get('max_chunk_size', 1500)

    @property
    def min_chunk_size(self) -> int:
        """Get minimum chunk size in tokens."""
        return self._config.get('chunking', {}).get('min_chunk_size', 100)

    @property
    def embedding_model(self) -> str:
        """Get OpenAI embedding model name."""
        return self._config.get('embedding', {}).get('model', 'text-embedding-3-small')

    @property
    def embedding_batch_size(self) -> int:
        """Get embedding batch size for API calls."""
        return self._config.get('embedding', {}).get('batch_size', 100)

    @property
    def default_n_results(self) -> int:
        """Get default number of search results to return."""
        return self._config.get('search', {}).get('default_n_results', 5)

    @property
    def similarity_threshold(self) -> float:
        """Get similarity threshold for link suggestions."""
        return self._config.get('search', {}).get('similarity_threshold', 0.7)

    @property
    def debounce_seconds(self) -> float:
        """Get debounce seconds for file watcher."""
        env_val = os.getenv('DEBOUNCE_SECONDS')
        if env_val:
            try:
                return float(env_val)
            except ValueError:
                pass
        return self._config.get('watcher', {}).get('debounce_seconds', 30.0)

    def get(self, key: str, default: Any = None) -> Any:
        """
        Get configuration value by key (supports dot notation).

        Args:
            key: Configuration key (e.g., 'chunking.target_chunk_size')
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

    def __repr__(self) -> str:
        """String representation of config (masks API key)."""
        masked_config = self._config.copy()
        if 'openai_api_key' in masked_config:
            key = masked_config['openai_api_key']
            masked_config['openai_api_key'] = f"{key[:7]}...{key[-4:]}" if len(key) > 11 else "***"

        return f"Config(path={self.config_path}, settings={masked_config})"


def load_config(config_path: Optional[str] = None) -> Config:
    """
    Load configuration from file.

    Args:
        config_path: Optional path to config file

    Returns:
        Config object

    Raises:
        ConfigError: If config is invalid
    """
    return Config(config_path)
