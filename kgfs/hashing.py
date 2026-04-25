"""Compatibility module alias for hashing helpers."""

import sys

from kgfs.indexing import hashing as _module

sys.modules[__name__] = _module
