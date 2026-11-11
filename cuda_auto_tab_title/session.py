"""Persist title ownership alongside CudaText's native session."""

import hashlib
import json
import os
import tempfile
from dataclasses import asdict, dataclass
from pathlib import Path

from .titles import read_json_object


INACTIVE_LIMIT = 4096


def title_hash(observed_title):
    return hashlib.sha256(observed_title.encode("utf-8", "surrogatepass")).hexdigest()


@dataclass(frozen=True)
class TitleRecord:
    digest: str
    stars: int
    manual: bool

    @classmethod
    def from_title(cls, title, manual):
        # PROP_TAB_TITLE omits leading asterisks, including literal ones.
        observed = title.lstrip("*")
        return cls(title_hash(observed), len(title) - len(observed), manual)

    def matches(self, observed_title):
        return isinstance(observed_title, str) and self.digest == title_hash(observed_title)


def load_records(path):
    records = {}
    for tab_id, value in read_json_object(path).items():
        if not tab_id.isascii() or not tab_id.isdecimal() or not isinstance(value, dict):
            continue
        digest, stars, manual = value.get("digest"), value.get("stars"), value.get("manual")
        if (isinstance(digest, str) and len(digest) == 64
                and type(stars) is int and 0 <= stars <= 65536
                and type(manual) is bool):
            records[tab_id] = TitleRecord(digest, stars, manual)
    return records


def save_records(path, live_ids, owned):
    previous = load_records(path)
    # Keep a bounded cache for other sessions and explicit session backups.
    inactive = [key for key in previous if key not in live_ids][-INACTIVE_LIMIT:]
    records = {key: previous[key] for key in inactive}
    records.update(owned)
    if list(records.items()) == list(previous.items()):
        return
    temp_path = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", dir=path.parent,
            prefix=path.stem + "-", suffix=".tmp", delete=False,
        ) as stream:
            temp_path = Path(stream.name)
            json.dump({key: asdict(value) for key, value in records.items()}, stream)
            stream.write("\n")
        os.replace(temp_path, path)
    finally:
        if temp_path is not None:
            temp_path.unlink(missing_ok=True)
