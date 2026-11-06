# Testing

Tests use [pytest](https://docs.pytest.org/) and live in `tests/`.

```bash
mise run test                       # Run the suite, without integration tests
mise run test tests/test_cli.py     # Run one file, class, or function
mise run test-all                   # Run everything, including integration tests
```

Integration tests are marked `integration` and drive the real Inkscape and Scribus, so they need the system packages in the README. The pre-push hook runs them.

## Patterns

- Name tests for the behavior they verify, e.g. `test_version_flag_prints_installed_version`.
- Test CLI commands through Typer's `CliRunner`, and keep detailed behavior tests against the library code.
- Prefer real inputs and real output over mocks. Write generated files to pytest's `tmp_path`.
- Don't mock without a clear reason, such as a slow or unavailable external service. FlipFix is the one service we fake: pass `httpx.MockTransport` to `fetch_machines`, and replace `cli.fetch_machines` in CLI tests.
- Keep rendering fixtures in `tests/fixtures/` as real templates, and build failure cases by editing a copy in `tmp_path`.
- When testing that a check does NOT fire, confirm the test fails with the check's logic removed. Otherwise it may not reach the code at all.
