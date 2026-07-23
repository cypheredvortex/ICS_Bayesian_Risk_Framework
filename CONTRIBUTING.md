# Contributing to ICS Risk Assessment Framework

## Development Setup

```bash
# Clone and set up
git clone <repository-url>
cd ICS_Bayesian_Risk_Framework
python -m venv venv
source venv/bin/activate  # or venv\Scripts\activate on Windows
pip install -e .
pip install -r requirements-dev.txt
```

## Code Quality

This project uses:
- **Black** for code formatting
- **Ruff** for linting
- **Mypy** for type checking
- **Pytest** for testing

Run all checks before submitting:

```bash
# Format code
black src/ tests/

# Lint
ruff check src/ tests/

# Type check
mypy src/

# Run tests
pytest --cov=src/
```

## Pull Request Process

1. Create a feature branch from `main`
2. Make your changes with clear commit messages
3. Add/update tests as needed
4. Ensure all checks pass
5. Open a pull request with a clear description

## Code Style

- Type hints are required for all function signatures
- Docstrings for all public functions (Google-style)
- Follow SOLID principles
- Keep functions small and focused
- Prefer composition over inheritance

