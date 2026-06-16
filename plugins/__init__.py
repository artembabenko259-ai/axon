"""AXON plugin package — drop Python files in `.axon/plugins/`."""

from plugins.loader import AxonPlugin, discover_plugins, list_plugin_commands

__all__ = ["AxonPlugin", "discover_plugins", "list_plugin_commands"]
