# Contributing to VXLAN Calculator

Thank you for your interest in contributing to VXLAN Calculator!

## Development Setup

1. **Clone the repository**

   ```bash
   git clone https://github.com/ashimov/vxlan-calculator.git
   cd vxlan-calculator
   ```

2. **Create a virtual environment**

   ```bash
   python -m venv .venv
   source .venv/bin/activate  # Linux/macOS
   # or
   .venv\Scripts\activate     # Windows
   ```

3. **Install dependencies**

   ```bash
   pip install -e ".[dev]"
   ```

4. **Install pre-commit hooks** (optional but recommended)

   ```bash
   pre-commit install
   ```

## Code Quality

This project uses modern Python tooling:

- **Ruff** - Linting and formatting
- **Mypy** - Static type checking
- **Pytest** - Testing

### Running checks

```bash
# Linting
ruff check src/

# Formatting
ruff format src/

# Type checking
mypy src/

# Tests
pytest
```

## Pull Request Process

1. **Create a feature branch**

   ```bash
   git checkout -b feature/your-feature-name
   ```

2. **Make your changes**
   - Follow the existing code style
   - Add type hints to all functions
   - Update documentation if needed

3. **Run all checks**

   ```bash
   ruff check src/ && ruff format --check src/ && mypy src/ && pytest
   ```

4. **Commit your changes**

   ```bash
   git commit -m "feat: add your feature description"
   ```

   Follow [Conventional Commits](https://www.conventionalcommits.org/):
   - `feat:` - New feature
   - `fix:` - Bug fix
   - `docs:` - Documentation only
   - `refactor:` - Code refactoring
   - `test:` - Adding tests
   - `chore:` - Maintenance

5. **Push and create PR**

   ```bash
   git push origin feature/your-feature-name
   ```

## Adding New Vendor Configs

To add support for a new vendor in the EVPN calculator:

1. Add the vendor to `Vendor` enum in `src/evpn_ninja/calculators/evpn.py`
2. Create a config generator function `_generate_<vendor>_config()`
3. Add the generator to the `config_generators` dictionary
4. Update tests

## Questions?

Feel free to open an issue for any questions or suggestions.
