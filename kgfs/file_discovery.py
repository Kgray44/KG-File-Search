"""Compatibility module alias for indexing discovery."""

import sys

from kgfs.indexing import discovery as _module

sys.modules[__name__] = _module
