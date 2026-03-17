# Contributing to Multi-Industry AI Assistant

Thank you for your interest in contributing! This guide will help you get started.

## How to Contribute

1. **Fork** the repository
2. **Create a branch** for your feature or fix (`git checkout -b feature/my-feature`)
3. **Make your changes** and ensure they follow the project conventions
4. **Test** your changes thoroughly
5. **Commit** with a clear, descriptive message
6. **Push** to your fork and open a **Pull Request**

## Development Setup

```bash
# Clone your fork
git clone https://github.com/<your-username>/multi-industry-ai-assistant.git
cd multi-industry-ai-assistant

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # Linux/macOS
# .venv\Scripts\activate   # Windows

# Install dependencies
pip install -r requirements.txt
pip install -r requirements-dev.txt  # if available

# Run tests
pytest
```

## Code Standards

- **Formatting**: Use `black` for code formatting and `isort` for import sorting
- **Linting**: Run `flake8` or `ruff` before submitting changes
- **Type Hints**: Use type annotations for all function signatures
- **Docstrings**: Follow Google-style docstrings for all public functions and classes

```bash
# Format code
black .
isort .

# Lint
flake8 .
# or
ruff check .

# Type checking
mypy src/
```

## Pull Request Guidelines

- Keep PRs focused on a single change
- Update documentation if needed
- Include tests for new functionality
- Ensure all tests pass before submitting
- Describe what your PR does and why

## Reporting Issues

- Use GitHub Issues to report bugs or request features
- Include steps to reproduce any bugs
- For security vulnerabilities, see [SECURITY.md](SECURITY.md)

## Code of Conduct

Be respectful, inclusive, and constructive in all interactions.
