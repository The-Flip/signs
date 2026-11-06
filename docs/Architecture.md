# Architecture

Signs manages the printed signs for The Flip museum.

Only the CLI skeleton exists so far. This doc records the intended shape; update it as the code lands.

## Kinds of Sign

- **Static signs**: fixed text rendered to a PDF.
- **Merged signs**: a layout combined with a data source to generate many printable pages.

Both should go through the same rendering path. A static sign is the simple case, not a separate system.

## Interfaces

The app starts as a CLI and will gain a web interface. To make that cheap:

- Keep sign logic in library modules under `src/signs/`.
- Keep `cli.py` thin: parse arguments, call library code, report results.
- Don't let library code print, prompt, or exit. Return values and raise exceptions, so a web view can call the same code.
