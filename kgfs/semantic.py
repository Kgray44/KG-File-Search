"""Compatibility module alias for local semantic helpers."""

import sys

from kgfs.search import semantic as _module

sys.modules[__name__] = _module
