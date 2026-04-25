"""Optional OCR preprocessing hooks.

The first OCR pass intentionally keeps preprocessing minimal so the base app
does not require image-processing dependencies. Pillow can be added through the
optional OCR extra later without changing the public OCR backend interface.
"""
