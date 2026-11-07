# Architecture

Signs manages the printed signs for The Flip museum.

`signs render` turns a template into a PDF, and `signs render-machines` merges machine data into a template to print many signs.

## Kinds of Sign

- **Static signs**: fixed text rendered to a PDF.
- **Merged signs**: a layout combined with a data source to generate many printable pages.

Both should go through the same rendering path. A static sign is the simple case, not a separate system.

## Rendering

Templates are Inkscape SVG and Scribus SLA files, and those apps do the rendering: no other renderer reproduces their layouts reliably. `render()` in `render.py` picks an exporter by file suffix, and moves the PDF to `dest` in one step only once everything has passed. The output must be a `.pdf`, so a mistyped `-o` can't replace a template.

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

Rendering sees fonts from three places, through a temporary fontconfig file:

- **Bundled:** open fonts in `src/signs/fonts/`, one folder per family with its license. Keep every weight: a sign can use any of them, and the checks work at family level.
- **Licensed:** fonts we can use but not redistribute, such as Arial. The repo is public, so these live outside it, in `~/.local/share/signs/fonts` or wherever `SIGNS_LICENSED_FONT_DIR` points. A server deployment needs them supplied the same way.
- **System:** whatever the machine has installed.

Known limits:

- No cut-off text check for SVG flowed text, so those signs need a visual look.
- No check for characters a font lacks, or for a missing weight of an available SVG font family.
- The cut-off text check assumes frames aren't linked. No current template links frames.
- SVG fonts set in `<style>` blocks aren't seen, and SVG text with no font set uses Inkscape's default. No current template does the former.
- SLA checks skip master pages. No current template has images there.
- SLA templates with grouped frames are refused, because Scribus doesn't list the frames inside a group, so they can't be checked.
- An empty SLA image frame passes, because it may be a deliberate placeholder.

All external programs run through `run_tool` in `tools.py`, which handles timeouts and interrupts by killing the whole process group.

## Templates

Templates aren't kept in this repo, apart from test fixtures. They live outside it for now and will eventually become data rather than checked-in files.

## Machine Data

Each physical machine gets its own sign, so two machines of the same model need two signs. Rows are joined on FlipFix's `asset_id`, and two machines of one model each have their own row.

- **FlipFix** says which machines exist and where they are. A machine is on the floor when its location is `Museum` or `Coin-op`. Read it through `GET /api/v1/machines/`, with the key in `FLIPFIX_API_KEY` in `mise.local.toml`. That file is git-ignored; never commit the key.
- **`data/machines.csv`** holds what the sign says, including for machines that are off the floor now. It's a stopgap until the app has a data store, and it's now the source of truth: it was copied once from the Google Sheet, so edit the CSV rather than the sheet.

`signs check-machines` compares the two. A floor machine is incomplete if it has no row, no `MainText`, or placeholder `MainText` in square brackets. It also reports machines at a location it doesn't recognize, so a renamed location can't hide a machine, and rows whose `asset_id` FlipFix doesn't know, since those are probably typos. It lists everything it finds and exits 1 if there's anything to list.

`signs render-machines` prints signs into one PDF using one template, so a run covers either a single changed sign or a whole batch. With no asset ids it prints everything ready on the floor. A named machine prints wherever it is, so a sign can be ready before the machine comes back. Machines that need another template get their own run with `--template`.

Each sign is filled in and goes through `render()` separately, so every check applies and a failure names the machine. A sign that fails is left out and listed, and the rest still print. Machines without finished content are listed too. Either way the PDF is written and the command exits 1. A rendered sign must be exactly one page, so one bad sign can't shift the rest of a print run.

Filling a template (`sla_fill.py`):

- The `%Heading%` line repeats for each `HeadingN` with a non-blank `InfoN`.
- A line whose placeholders are all blank is dropped.
- `%MainText%` must be alone on its line, so it always gets its markup turned into fonts.
- A template placeholder that isn't a CSV column stops the sign, as does a template with no `%MainText%`, an `InfoN` with no heading, or `MainText` markup that doesn't parse. Raw markup can't reach a printed sign.
- Bold and italic in `MainText` become the matching font in the family, such as `Bai Jamjuree SemiBold Italic`. The template's font must be named `Family Weight`, and the font checks catch a family without that face.

`MainText` is markdown limited to `*italic*`, `**bold**`, `***bold italic***` and blank lines between paragraphs, with `\` escaping a literal `*` or `\`. Other columns are plain text. A blank `Produced`, or a blank `Info` with its `Heading`, drops that line from the sign.

## Interfaces

The app starts as a CLI and will gain a web interface. To make that cheap:

- Keep sign logic in library modules under `src/signs/`.
- Keep `cli.py` thin: parse arguments, call library code, report results.
- Don't let library code print, prompt, or exit. Return values and raise exceptions, so a web view can call the same code.
