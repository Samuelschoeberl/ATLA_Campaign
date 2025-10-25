"""Migrated config_common shim."""
CONFIG = {}

def get(key, default=None):
    return CONFIG.get(key, default)
