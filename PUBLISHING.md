# Publishing

1. Bump `__version__` in `src/mista/_version.py` and add a CHANGELOG entry.
2. Run the checks and build:

   ```bash
   .venv/bin/pytest && .venv/bin/mypy
   rm -rf dist && .venv/bin/python -m build
   .venv/bin/twine check dist/*
   ```

3. Upload to PyPI (needs a PyPI API token for the `mista` project; the first upload creates it
   if the name is free):

   ```bash
   .venv/bin/twine upload dist/*
   ```

4. Tag the release:

   ```bash
   git tag v0.1.0 && git push origin v0.1.0
   ```
