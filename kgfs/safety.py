"""Compatibility module alias for risky-root safety helpers."""

import sys

from kgfs.core import safety as _module

sys.modules[__name__] = _module
