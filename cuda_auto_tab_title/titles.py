"""Title extraction and settings, independent of the CudaText runtime."""

import json
import re
from dataclasses import dataclass


MAX_LINE_SIZE = 64 * 1024
MARKDOWN_HEADING = re.compile(r"^#{1,6}(?:\s+|$)")
MARKDOWN_CLOSING = re.compile(r"\s+#+$")
CONTROL_CHARACTERS = re.compile(r"[\x00-\x08\x0e-\x1f\x7f]")


def read_json_object(path):
    try:
        with path.open(encoding="utf-8-sig") as stream:
            value = json.load(stream)
    except (OSError, ValueError, RecursionError):
        return {}
    return value if isinstance(value, dict) else {}


@dataclass(frozen=True)
class Settings:
    enabled: bool = True
    auto_rename: bool = True
    max_title_length: int = 28
    scan_lines: int = 10
    strip_markdown: bool = True
    rename_saved_files: bool = False

    @classmethod
    def load(cls, path):
        raw = read_json_object(path)
        defaults = cls()
        values = {}
        for key in ("enabled", "auto_rename", "strip_markdown"):
            if type(raw.get(key)) is bool:
                values[key] = raw[key]
        for key, limit in (("max_title_length", 4096), ("scan_lines", 1000)):
            value = raw.get(key, getattr(defaults, key))
            if type(value) is int and 1 <= value <= limit:
                values[key] = value
        return cls(**values)


def extract_title(get_line, settings):
    for index in range(settings.scan_lines):
        line = get_line(index, MAX_LINE_SIZE)
        if line is None:
            break
        line = CONTROL_CHARACTERS.sub(" ", line).strip()
        if settings.strip_markdown:
            heading = MARKDOWN_HEADING.match(line)
            if heading:
                line = MARKDOWN_CLOSING.sub("", line[heading.end():])
                if re.fullmatch(r"#+", line):
                    line = ""
        title = " ".join(line.split())
        if len(title) > settings.max_title_length:
            return title[:settings.max_title_length - 1].rstrip() + "…"
        if title:
            return title
    return ""
