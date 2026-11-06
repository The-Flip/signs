# Testing

Tests use [pytest](https://docs.pytest.org/) and live in `tests/`.

```bash
mise run test                       # Run the suite
mise run test tests/test_cli.py     # Run one file, class, or function
```

## Patterns

- Name tests for the behavior they verify, e.g. `test_version_flag_prints_installed_version`.
- Test CLI commands through Typer's `CliRunner`, and keep detailed behavior tests against the library code.
- Prefer real inputs and real output over mocks. Write generated files to pytest's `tmp_path`.
- Don't mock without a clear reason, such as a slow or unavailable external service.
