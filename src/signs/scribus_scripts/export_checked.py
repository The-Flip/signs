"""Check a Scribus document and export it to PDF if it passes.

This runs inside Scribus's own Python, not the signs environment, so it can only use the
standard library and the `scribus` module. Results go to a JSON report for the parent
process. The report is written last, so a missing report means this script failed.

Usage: export_checked.py SOURCE DEST REPORT
"""

import json
import os
import sys

import scribus

IMAGE_FRAME = 2
TEXT_FRAME = 4
GROUP = 12
SNIPPET_LENGTH = 40


def problem(kind: str, message: str) -> dict[str, str]:
    return {"kind": kind, "message": message}


def hidden_text(frame: str) -> str:
    """Return the text a frame can't show.

    `textOverflows()` alone isn't enough: it also fires for blank trailing paragraphs,
    which lose nothing on the printed sign.
    """
    if not scribus.textOverflows(frame):
        return ""
    scribus.layoutText(frame)
    visible_length = len(scribus.getFrameText(frame))
    return str(scribus.getAllText(frame))[visible_length:].strip()


def overflow_problem(page: int, frame: str) -> dict[str, str] | None:
    hidden = hidden_text(frame)
    if not hidden:
        return None
    snippet = hidden if len(hidden) <= SNIPPET_LENGTH else f"{hidden[:SNIPPET_LENGTH]}..."
    return problem("overflow", f'Page {page}: {len(hidden)} characters cut off: "{snippet}"')


def image_problem(page: int, frame: str, source: str) -> dict[str, str] | None:
    image = scribus.getImageFile(frame)
    if not image or os.path.isfile(os.path.join(os.path.dirname(source), image)):
        return None
    return problem("image", f"Page {page}: image not found: {image}")


def frame_problem(page: int, frame: str, frame_type: int, source: str) -> dict[str, str] | None:
    if frame_type == TEXT_FRAME:
        return overflow_problem(page, frame)
    if frame_type == IMAGE_FRAME:
        return image_problem(page, frame, source)
    if frame_type == GROUP:
        # `getPageItems()` doesn't list the frames in a group, so they can't be checked
        return problem("group", f"Page {page}: ungroup {frame} so its frames can be checked")
    return None


def collect_problems(source: str, fonts_before_open: set[str]) -> list[dict[str, str]]:
    """Check the open document. When Scribus ships `exportDocumentCheck`, use it here.

    Opening a document adds its missing fonts to `getFontNames()`, so anything new since
    before the open is really missing. `getFont()` can't help: it reports the requested
    font, not the substitute.
    """
    problems = [
        problem("font", f"Font not available: {font}")
        for font in sorted(set(scribus.getFontNames()) - fonts_before_open)
    ]
    for page in range(1, scribus.pageCount() + 1):
        scribus.gotoPage(page)
        for name, frame_type, _ in scribus.getPageItems():
            found = frame_problem(page, name, frame_type, source)
            if found:
                problems.append(found)
    return problems


def export_pdf(dest: str) -> None:
    pdf = scribus.PDFfile()
    pdf.file = dest
    pdf.save()


def main() -> None:
    source, dest, report = sys.argv[1:4]
    fonts_before_open = set(scribus.getFontNames())
    scribus.openDoc(source)
    problems = collect_problems(source, fonts_before_open)
    if not problems:
        export_pdf(dest)
    scribus.closeDoc()
    unfinished_report = f"{report}.tmp"
    with open(unfinished_report, "w") as out:
        json.dump(problems, out)
    os.replace(unfinished_report, report)


main()
