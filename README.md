# Signs

Manages the signs for The Flip museum. Some signs are static text rendered to PDF; others merge data to generate many printable pages.

It starts as a CLI app and will gain a web interface later. See [`docs/Architecture.md`](docs/Architecture.md).

## Setup

Requires [mise](https://mise.jdx.dev/), which installs Python and [uv](https://docs.astral.sh/uv/), plus these system packages:

```bash
sudo apt install inkscape scribus xvfb fontconfig
```

The integration tests also need `poppler-utils`.

Scribus must be 1.6.x. Then:

```bash
mise run bootstrap
uv run signs --help
```

## Rendering a sign

```bash
uv run signs render tests/fixtures/staff-only.svg
uv run signs render tests/fixtures/donation-box.sla -o sign.pdf
```

If a template has a missing font or image, or cut-off text in a Scribus file, `signs render` lists the problems and writes no PDF. See the known limits in [`docs/Architecture.md`](docs/Architecture.md).

## Checking machine signs

Set `FLIPFIX_API_KEY` to a [FlipFix API key](https://github.com/The-Flip/flipfix/blob/main/docs/API.md#obtaining-a-key), under `[env]` in `mise.local.toml`, which git ignores.

Then, from the repo root, list the floor machines that aren't ready for a sign:

```bash
uv run signs check-machines
```

It exits 1 if it finds any. `--data` reads a different CSV.

## Fonts

Open fonts are included. Fonts that can't be redistributed, such as Arial, must never be committed, because this repo is public. Put your licensed copies in `~/.local/share/signs/fonts`, or set `SIGNS_LICENSED_FONT_DIR` to another directory.

Run `mise tasks` to list the development commands.
