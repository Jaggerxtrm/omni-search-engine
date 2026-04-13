class VaultctlError(Exception):
    """Base error for vaultctl."""


class ConfigError(VaultctlError):
    """Configuration is invalid."""


class NotFoundError(VaultctlError):
    """Requested entity was not found."""
