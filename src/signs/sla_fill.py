"""Fill a Scribus template's placeholders with one machine's sign content.

Text in an SLA file is a flat list of runs. `breakline` ends a line and `para` or `trail`
ends a paragraph. Filling works a line at a time, because a line can be repeated or
dropped depending on the data.
"""

import re
from collections.abc import Mapping
from copy import deepcopy
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

from defusedxml import DefusedXmlException, ElementTree

from signs.problems import RenderError

if TYPE_CHECKING:
    from xml.etree.ElementTree import Element

type Line = list[Element]

PLACEHOLDER = re.compile(r"%([^%\s]+)%")
INFO_COLUMN = re.compile(r"Info(\d+)")
PARAGRAPH_BREAK = re.compile(r"\n\s*\n")
INLINE_MARKDOWN = re.compile(r"(\*{1,3})((?:\\[*\\]|[^*\\])+)\1|((?:\\[*\\]|[^*\\])+)")
ESCAPED_CHARACTER = re.compile(r"\\([*\\])")
MAIN_TEXT = "MainText"
RICH_TEXT = f"%{MAIN_TEXT}%"
REPEATED_PLACEHOLDERS = {"Heading", "Info"}
PARAGRAPH_ENDS = {"para", "trail"}
FONT_WEIGHTS = {"ExtraLight", "Light", "Regular", "Medium", "SemiBold", "Bold"}


@dataclass(frozen=True)
class Run:
    """Text that shares one style."""

    text: str
    bold: bool = False
    italic: bool = False


@dataclass
class Paragraph:
    lines: list[Line]
    end: Element | None


def parse_markdown(text: str) -> list[list[Run]]:
    """Split the sign's limited markdown into paragraphs of styled runs."""
    unified = text.replace("\r\n", "\n").replace("\r", "\n").strip()
    return [parse_paragraph(paragraph) for paragraph in PARAGRAPH_BREAK.split(unified)]


def parse_paragraph(text: str) -> list[Run]:
    if "\n" in text:
        raise RenderError(f"Main text needs a blank line between paragraphs: {text[:40]}")
    runs = []
    position = 0
    while position < len(text):
        found = INLINE_MARKDOWN.match(text, position)
        if found is None:
            raise RenderError(f"Unmatched markup in main text: {text[position : position + 40]}")
        marks, styled, plain = found.groups()
        content = ESCAPED_CHARACTER.sub(r"\1", styled or plain)
        stars = len(marks or "")  # One is italic, two is bold, three is both
        runs.append(Run(content, bold=stars >= 2, italic=stars in (1, 3)))
        position = found.end()
    return runs


def styled_font(font: str, run: Run) -> str:
    """Return the real font for a run, such as `Bai Jamjuree SemiBold Italic`."""
    if not run.bold and not run.italic:
        return font
    family, _, weight = font.rpartition(" ")
    if not family or weight not in FONT_WEIGHTS:
        raise RenderError(f"Can't work out styles for {font or RICH_TEXT}")
    if run.bold:
        weight = "Bold"
    if run.italic:
        weight = "Italic" if weight == "Regular" else f"{weight} Italic"
    return f"{family} {weight}"


def split_story(story: Element) -> list[Paragraph]:
    paragraphs = []
    lines: list[Line] = [[]]
    for child in story:
        if child.tag == "breakline":
            lines.append([])
        elif child.tag in PARAGRAPH_ENDS:
            paragraphs.append(Paragraph(lines, child))
            lines = [[]]
        elif child.tag != "DefaultStyle":
            lines[-1].append(child)
    if any(lines):
        paragraphs.append(Paragraph(lines, None))
    return paragraphs


def line_text(line: Line) -> list[str]:
    return [item.get("CH", "") for item in line if item.tag == "ITEXT"]


def line_placeholders(line: Line, content: Mapping[str, str]) -> list[str]:
    """Return a line's placeholder names, refusing any that can't be filled."""
    texts = line_text(line)
    names = PLACEHOLDER.findall("".join(texts))
    if names != [name for text in texts for name in PLACEHOLDER.findall(text)]:
        raise RenderError(f"Template splits a placeholder across styles: {''.join(texts)}")
    for name in names:
        if name not in content and name not in REPEATED_PLACEHOLDERS:
            raise RenderError(f"Template uses %{name}%, which isn't in the machine data")
    return names


def fill_text(text: str, values: Mapping[str, str]) -> str:
    """Fill a run's placeholders. A blank value mustn't leave its spacing behind."""
    filled = PLACEHOLDER.sub(lambda found: values[found[1]].strip(), text)
    has_blank = any(not values[name].strip() for name in PLACEHOLDER.findall(text))
    return filled.strip() if has_blank else filled


def filled_line(line: Line, values: Mapping[str, str]) -> Line:
    filled = deepcopy(line)
    for item in filled:
        text = item.get("CH", "")
        if PLACEHOLDER.search(text):
            item.set("CH", fill_text(text, values))
    return filled


def heading_pairs(content: Mapping[str, str]) -> list[dict[str, str]]:
    """Return each heading with its info, in number order, skipping pairs with no info."""
    numbers = sorted(int(found[1]) for found in map(INFO_COLUMN.fullmatch, content) if found)
    pairs = []
    for number in numbers:
        info = content[f"Info{number}"]
        heading = content.get(f"Heading{number}", "")
        if info.strip() and not heading.strip():
            raise RenderError(f"Info{number} has no heading")
        if info.strip():
            pairs.append({"Heading": heading, "Info": info})
    return pairs


def fill_line(line: Line, names: list[str], content: Mapping[str, str]) -> list[Line]:
    """Return the lines to print for a template line: none, one or several."""
    if not names:
        return [line]
    if REPEATED_PLACEHOLDERS.intersection(names):
        return [filled_line(line, {**content, **pair}) for pair in heading_pairs(content)]
    if not any(content[name].strip() for name in names):
        return []
    return [filled_line(line, content)]


def paragraph_break(end: Element | None) -> Element:
    if end is None:
        raise RenderError(f"Template needs a paragraph break after {RICH_TEXT}")
    separator = deepcopy(end)
    separator.tag = "para"
    return separator


def rich_text_items(item: Element, end: Element | None, text: str) -> Line:
    """Turn the rich text placeholder into runs, with paragraph breaks between them."""
    items: Line = []
    paragraphs = parse_markdown(text)
    for index, runs in enumerate(paragraphs):
        if index:
            items.append(paragraph_break(end))
        for run in runs:
            styled = deepcopy(item)
            styled.set("CH", run.text)
            if run.bold or run.italic:
                styled.set("FONT", styled_font(item.get("FONT", ""), run))
            items.append(styled)
    return items


def fill_rich_line(line: Line, end: Element | None, content: Mapping[str, str]) -> Line:
    if len(line) != 1 or line[0].get("CH") != RICH_TEXT:
        raise RenderError(f"Template must have {RICH_TEXT} alone on its line")
    return rich_text_items(line[0], end, content[MAIN_TEXT])


def fill_paragraph(
    paragraph: Paragraph, separator: Element | None, content: Mapping[str, str]
) -> Line:
    filled_lines: list[Line] = []
    for line in paragraph.lines:
        names = line_placeholders(line, content)
        if MAIN_TEXT in names:
            filled_lines.append(fill_rich_line(line, paragraph.end, content))
        else:
            filled_lines.extend(fill_line(line, names, content))
    items: Line = []
    for index, line in enumerate(filled_lines):
        if index:
            if separator is None:
                raise RenderError("Template needs a line break to repeat a line")
            items.append(deepcopy(separator))
        items.extend(line)
    if paragraph.end is not None:
        items.append(paragraph.end)
    return items


def fill_story(story: Element, content: Mapping[str, str]) -> None:
    separator = story.find("breakline")
    kept = [child for child in story if child.tag == "DefaultStyle"]
    filled = [
        item
        for paragraph in split_story(story)
        for item in fill_paragraph(paragraph, separator, content)
    ]
    del story[:]
    story.extend([*kept, *filled])


def absolute_image_links(root: Element, template: Path) -> None:
    """Rewrite image links, because the filled copy lives somewhere else."""
    for item in root.iter("PAGEOBJECT"):
        image = item.get("PFILE")
        if image:
            item.set("PFILE", str((template.parent / image).resolve()))


def fill_template(template: Path, content: Mapping[str, str], dest: Path) -> None:
    """Write a copy of a template filled in for one machine."""
    try:
        root = ElementTree.fromstring(template.read_bytes())
    except (ElementTree.ParseError, DefusedXmlException, OSError) as error:
        raise RenderError(f"Can't read template {template}: {error}") from error
    if not any(RICH_TEXT in item.get("CH", "") for item in root.iter("ITEXT")):
        raise RenderError(f"Template {template} has no {RICH_TEXT}")
    for story in root.iter("StoryText"):
        fill_story(story, content)
    absolute_image_links(root, template)
    try:
        dest.write_text(ElementTree.tostring(root, encoding="unicode"), encoding="utf-8")
    except OSError as error:
        raise RenderError(f"Could not write {dest}: {error}") from error
