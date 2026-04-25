"""Compatibility module alias for shared dataclasses."""

import sys

from kgfs.core import models as _module

sys.modules[__name__] = _module
