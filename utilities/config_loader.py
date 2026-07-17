"""
config_loader.py
----------------
Loads the YAML configuration files and makes them easy to use in code.

Simple idea:
  * settings.yaml           -> global settings (server, paths, email, logging)
  * <layer>.yaml            -> table details for one ETL layer

Everything is cached so the files are read only once per run.
"""

import os
import yaml

# folder that contains this file's parent project  ->  .../config
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_CONFIG_DIR = os.path.join(_PROJECT_ROOT, "config")

# map a layer name to its YAML file
_LAYER_FILES = {
    "SourceToPreStaging": "source_to_prestaging.yaml",
    "PreStagingToStaging": "prestaging_to_staging.yaml",
    "StagingToDWH": "staging_to_dwh.yaml",
}

_cache = {}


def _read_yaml(file_name):
    path = os.path.join(_CONFIG_DIR, file_name)
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def get_settings():
    """Return the global settings.yaml content (cached)."""
    if "settings" not in _cache:
        _cache["settings"] = _read_yaml("settings.yaml")
    return _cache["settings"]


def get_layer_config(layer_name):
    """Return the config for one layer, e.g. 'SourceToPreStaging' (cached)."""
    if layer_name not in _LAYER_FILES:
        raise ValueError(f"Unknown layer '{layer_name}'. "
                         f"Valid layers: {list(_LAYER_FILES)}")
    if layer_name not in _cache:
        _cache[layer_name] = _read_yaml(_LAYER_FILES[layer_name])
    return _cache[layer_name]


def get_table_config(layer_name, table_name):
    """Return the config block for a single table inside a layer."""
    layer = get_layer_config(layer_name)
    tables = layer.get("tables", {})
    if table_name not in tables:
        raise ValueError(f"Table '{table_name}' not found in layer '{layer_name}'.")
    return tables[table_name]


def resolve_database(logical_name):
    """Turn a logical db name ('source') into the real db ('Bank_Source')."""
    return get_settings()["databases"][logical_name]


def abs_path(*relative_parts):
    """Build an absolute path under the project root."""
    return os.path.join(_PROJECT_ROOT, *relative_parts)
