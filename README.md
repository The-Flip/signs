# Signs

Manages the signs for The Flip museum. Some signs are static text rendered to PDF; others merge data to generate many printable pages.

It starts as a CLI app and will gain a web interface later. See [`docs/Architecture.md`](docs/Architecture.md).

## Setup

Requires [mise](https://mise.jdx.dev/), which installs Python and [uv](https://docs.astral.sh/uv/), plus these system packages:

```bash
sudo apt install inkscape scribus xvfb fontconfig poppler-utils
```

Scribus must be 1.6.x. Then:

```bash
mise run bootstrap
uv run signs --help
```

## Rendering a sign

```bash
uv run signs render staff-only.svg
uv run signs render general-sign-template.sla -o sign.pdf
```

If a template has a missing font, cut-off text, or a missing image, `signs render` lists the problems and writes no PDF.

## Fonts

Open fonts are included. Fonts that can't be redistributed, such as Arial, must never be committed, because this repo is public. Put your licensed copies in `~/.local/share/signs/fonts`, or set `SIGNS_LICENSED_FONT_DIR` to another directory.

Run `mise tasks` to list the development commands.
