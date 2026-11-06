# Architecture

Signs manages the printed signs for The Flip museum.

`signs render` turns a template into a PDF. Merging data is still to come, so parts of this doc record the intended shape; update it as the code lands.

## Kinds of Sign

- **Static signs**: fixed text rendered to a PDF.
- **Merged signs**: a layout combined with a data source to generate many printable pages.

Both should go through the same rendering path. A static sign is the simple case, not a separate system.

## Rendering

Templates are Inkscape SVG and Scribus SLA files, and those apps do the rendering: no other renderer reproduces their layouts reliably. `render()` in `render.py` picks an exporter by file suffix, and writes to `dest` only once everything has passed.

Headless export has no safety net, so we check templates ourselves. A failed check raises `TemplateCheckError` and produces no PDF.

| Check          | SVG                                                | SLA                                                  |
| -------------- | -------------------------------------------------- | ---------------------------------------------------- |
| Missing fonts  | `fc-match` on the families that text actually uses | Fonts that `getFontNames()` gains on opening the doc |
| Cut-off text   | Not checked                                        | Visible text missing from the frame                  |
| Missing images | Linked files that don't exist                      | Linked files that don't exist                        |

Things that aren't obvious:

- **Both apps silently substitute missing fonts** and still report success.
- **Don't trust Scribus's font reporting.** After a document opens, `getFontNames()` and `getFont()` report missing fonts as present. Only the list from before opening is accurate.
- **Don't compare template fonts with the PDF's fonts for SLA files.** Templates declare DejaVu Sans as a default, and DejaVu is also what Scribus substitutes, so a substituted PDF would pass. The integration tests use `pdffonts` to prove the real checks work.
- **`textOverflows()` isn't enough.** It also fires for blank trailing paragraphs, which lose nothing on the sign.
- **Scribus's Preflight Verifier isn't reachable in 1.6.x.** A newer `exportDocumentCheck` command will expose it, so recheck when upgrading Scribus. It doesn't cover substituted fonts, so the font check stays either way.

`scribus_scripts/` runs inside Scribus's own Python, so it can only use the standard library and `scribus`, and it reports back through a JSON file. It has its own directory because Python puts a script's directory on `sys.path`, and nothing there may shadow `scribus`.

Fonts we can redistribute are bundled in `src/signs/fonts/` and added through a temporary fontconfig file, so rendering doesn't depend on what's installed. Keep every weight of a family: a sign can use any of them, and the checks work at family level.

Known limits:

- No cut-off text check for SVG flowed text, so those signs need a visual look.
- No check for characters a font lacks, or for a missing weight of an available SVG font family.
- The cut-off text check assumes frames aren't linked. No current template links frames.
- SVG fonts set in `<style>` blocks aren't seen, and SVG text with no font set uses Inkscape's default. No current template does the former.
- SLA checks skip master pages. No current template has images there.

All external programs run through `run_tool` in `tools.py`, which handles timeouts and interrupts by killing the whole process group.

## Interfaces

The app starts as a CLI and will gain a web interface. To make that cheap:

- Keep sign logic in library modules under `src/signs/`.
- Keep `cli.py` thin: parse arguments, call library code, report results.
- Don't let library code print, prompt, or exit. Return values and raise exceptions, so a web view can call the same code.
