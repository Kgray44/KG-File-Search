"""Compatibility module alias for snippet helpers."""

import sys

from kgfs.search import snippets as _module

sys.modules[__name__] = _module
