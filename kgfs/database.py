"""Compatibility module alias for database helpers."""

import sys

from kgfs import db as _module

sys.modules[__name__] = _module
