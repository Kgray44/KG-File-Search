"""Compatibility module alias for platform helpers."""

import sys

from kgfs.core import platform_utils as _module

sys.modules[__name__] = _module
