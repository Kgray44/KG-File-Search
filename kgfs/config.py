"""Compatibility module alias for config models and helpers."""

import sys

from kgfs.core import config as _module

sys.modules[__name__] = _module
