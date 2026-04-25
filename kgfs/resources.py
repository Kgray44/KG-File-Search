"""Compatibility module alias for resource helpers."""

import sys

from kgfs.core import resources as _module

sys.modules[__name__] = _module
