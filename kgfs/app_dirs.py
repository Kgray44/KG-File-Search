"""Compatibility module alias for app directory helpers."""

import sys

from kgfs.core import app_dirs as _module

sys.modules[__name__] = _module
