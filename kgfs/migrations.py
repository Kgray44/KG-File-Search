"""Compatibility module alias for database migrations."""

import sys

from kgfs.db import migrations as _module

sys.modules[__name__] = _module
