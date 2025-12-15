# HasAPI PyPI Upload Guide

This guide explains how to build and upload the HasAPI framework to PyPI.

## Prerequisites

1. **Python Environment**: Ensure you have Python 3.10+ installed
2. **Virtual Environment**: Activate your virtual environment
3. **PyPI Account**: Create accounts on both [PyPI](https://pypi.org) and [Test PyPI](https://test.pypi.org)
4. **API Tokens**: Generate API tokens for both PyPI and Test PyPI

## Setup

### 1. Install Build Tools

```bash
pip install build twine
```

### 2. Configure PyPI Credentials

Create a `.pypirc` file in your home directory:

```ini
[distutils]
index-servers =
    pypi
    testpypi

[pypi]
username = __token__
password = pypi-your-api-token-here

[testpypi]
repository = https://test.pypi.org/legacy/
username = __token__
password = pypi-your-test-api-token-here
```

## Build Process

### 1. Update Version

Before building, update the version in two places:

**pyproject.toml:**
```toml
version = "0.1.2"  # Increment version
```

**hasapi/__init__.py:**
```python
__version__ = "0.1.2"  # Match the version above
```

### 2. Clean Previous Builds

```bash
rm -rf dist/ build/ *.egg-info
```

### 3. Build the Package

```bash
python -m build
```

This creates:
- `dist/hasapi-X.X.X.tar.gz` (source distribution)
- `dist/hasapi-X.X.X-py3-none-any.whl` (wheel distribution)

### 4. Verify the Build

```bash
python -m twine check dist/*
```

Should output: `PASSED` for all files.

## Upload Process

### Option 1: Test PyPI First (Recommended)

Upload to Test PyPI to verify everything works:

```bash
python -m twine upload --repository testpypi dist/*
```

Test the installation:
```bash
pip install --index-url https://test.pypi.org/simple/ hasapi
```

### Option 2: Production PyPI

Once tested, upload to production PyPI:

```bash
python -m twine upload dist/*
```

## Package Configuration

### Current Configuration

The package is configured with:

- **Name**: `hasapi`
- **Dependencies**: Core web framework dependencies + PyJWT
- **Optional Dependencies**: AI, PyTorch, ONNX, Vector DB, and benchmark extras
- **Excluded**: `examples/` and `tests/` folders (via MANIFEST.in)
- **License**: MIT
- **Python**: Requires 3.10+

### Project URLs

- **Homepage**: https://github.com/Haslab-dev/HasAPI
- **Documentation**: https://github.com/Haslab-dev/HasAPI#readme
- **Repository**: https://github.com/Haslab-dev/HasAPI
- **Issues**: https://github.com/Haslab-dev/HasAPI/issues

## Installation Options

Users can install with:

```bash
# Core framework only
pip install hasapi

# With AI support (OpenAI, Anthropic)
pip install hasapi[ai]

# With PyTorch support
pip install hasapi[pytorch]

# With ONNX support
pip install hasapi[onnx]

# With vector database support
pip install hasapi[vector]

# With all features
pip install hasapi[all]
```

## Version Management

### Semantic Versioning

Follow semantic versioning (MAJOR.MINOR.PATCH):

- **MAJOR**: Breaking changes
- **MINOR**: New features, backward compatible
- **PATCH**: Bug fixes, backward compatible

### Release Checklist

Before each release:

1. [ ] Update version in `pyproject.toml`
2. [ ] Update version in `hasapi/__init__.py`
3. [ ] Update CHANGELOG.md (if exists)
4. [ ] Test locally
5. [ ] Clean build artifacts
6. [ ] Build package
7. [ ] Check package with twine
8. [ ] Upload to Test PyPI
9. [ ] Test installation from Test PyPI
10. [ ] Upload to production PyPI
11. [ ] Create GitHub release tag
12. [ ] Update documentation

## Troubleshooting

### Common Issues

1. **Version Already Exists**: You cannot upload the same version twice. Increment the version number.

2. **Authentication Failed**: Check your API tokens in `.pypirc` or use `--username __token__ --password your-token`

3. **Package Validation Failed**: Run `twine check dist/*` to see validation errors.

4. **Missing Dependencies**: Ensure all required dependencies are listed in `pyproject.toml`

### File Exclusion

The `MANIFEST.in` file controls what gets included:

```
include README.md
include LICENSE
recursive-exclude examples *
recursive-exclude tests *
recursive-exclude __pycache__ *
recursive-exclude *.pyc *
```

## Automation

Consider setting up GitHub Actions for automated publishing:

```yaml
# .github/workflows/publish.yml
name: Publish to PyPI

on:
  release:
    types: [published]

jobs:
  publish:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v3
    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.10'
    - name: Install dependencies
      run: |
        pip install build twine
    - name: Build package
      run: python -m build
    - name: Publish to PyPI
      env:
        TWINE_USERNAME: __token__
        TWINE_PASSWORD: ${{ secrets.PYPI_API_TOKEN }}
      run: twine upload dist/*
```

## Support

For issues with the upload process:
- Check [PyPI Help](https://pypi.org/help/)
- Review [Python Packaging Guide](https://packaging.python.org/)
- Open an issue in the repository

---

**Last Updated**: December 2024
**Package Version**: 0.1.1
**PyPI URL**: https://pypi.org/project/hasapi/