"""Compatibility module alias for indexing filters."""

import sys

from kgfs.indexing import filters as _module

sys.modules[__name__] = _module
