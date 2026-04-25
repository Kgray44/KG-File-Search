"""Compatibility module alias for path helpers."""

import sys

from kgfs.core import path_utils as _module

sys.modules[__name__] = _module
