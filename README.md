# Signs

Manages the signs for The Flip museum. Some signs are static text rendered to PDF; others merge data to generate many printable pages.

It starts as a CLI app and will gain a web interface later. See [`docs/Architecture.md`](docs/Architecture.md).

## Setup

Requires [mise](https://mise.jdx.dev/), which installs Python and [uv](https://docs.astral.sh/uv/).

```bash
mise run bootstrap
uv run signs --help
```

Run `mise tasks` to list the development commands.
