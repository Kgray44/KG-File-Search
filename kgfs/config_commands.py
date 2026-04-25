"""Compatibility module alias for config editing helpers."""

import sys

from kgfs.core import config_commands as _module

sys.modules[__name__] = _module
