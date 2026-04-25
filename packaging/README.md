# KGFS Packaging

Packaging support lives here.

- `pyinstaller/kgfs.spec` is the committed PyInstaller spec for KGFS builds.
- `README-packaging.md` contains the detailed packaging workflow.

Generated package output belongs in `dist-packages/` and is ignored by git.
Do not commit built executables, zip archives, caches, logs, databases, or
user data.
