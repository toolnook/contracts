# Contributing to LedgerLite

Thanks for your interest in improving LedgerLite! This guide covers the development workflow.

## Getting started

```bash
git clone https://github.com/forgekit/ledgerlite.git
cd ledgerlite
pip install -e ".[dev]"
pytest -v
```

## Development workflow

1. Create a branch for your change:
   ```bash
   git checkout -b fix/your-bug-or-feature
   ```

2. Make your changes. Follow the existing code style.

3. Add or update tests. All new features and bug fixes should include test coverage:
   ```bash
   pytest -v
   ```

4. Write clear, descriptive commit messages:
   ```
   Add multi-currency support to balance calculation
   Fix date parsing for non-ISO formats
   ```

5. Push and open a pull request against `main`.

## Code style

- Use type hints on all public functions.
- Use `Decimal` for all monetary values — never `float`.
- Every public function should have a docstring.
- Keep modules focused — one responsibility per file.
- Prefer dataclasses for data models.

## Testing guidelines

- Test files go in `tests/` and mirror the source structure (e.g. `tests/test_ledger.py` tests `src/ledgerlite/ledger.py`).
- Use pytest fixtures for shared setup (the `ledger` fixture is common).
- Test names should describe behaviour: `"test_add_unbalanced_transaction_raises"` not `"test_1"`.
- Use `tmp_path` for file-based tests — never write to fixed paths.

## Reporting issues

- Use the bug report template for bugs.
- Use the feature request template for new features.
- Include the LedgerLite version, Python version, and a minimal reproduction case.

## Pull request checklist

- [ ] Tests pass (`pytest -v`)
- [ ] Code uses type hints and docstrings
- [ ] No `print()` statements in library code (only in `cli.py`)
- [ ] Commit messages are descriptive
- [ ] Documentation updated if behaviour changes
