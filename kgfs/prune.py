"""Compatibility module alias for prune helpers."""

import sys

from kgfs.indexing import prune as _module

sys.modules[__name__] = _module
