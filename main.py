#!/usr/bin/env python3
"""Two-Sentence Horror entry writer (stdlib only).

Writes the ENTRY text to /output/entry.txt (the path the grader reads)
and to entry.txt next to this file, then reads both files back and fails
hard if either differs byte-for-byte from ENTRY.
"""

import hashlib
import os
import re
import sys

ENTRY = (
    "Every birthday since I was seven, my mother has left me a voicemail, "
    "and this year I finally played them all back in order, from the first "
    "to the last. "
    "In the last one she apologizes for the birthdays she will miss, then "
    "adds, in a voice I have never heard, that I should stop "
    "listening \u2014 because the woman in all the other messages was never her."
)

OUTPUT_PATH = "/output/entry.txt"

# Common abbreviations whose period must never appear inside the entry;
# the gate counts exactly two sentence terminators, so any other period
# (abbreviation, ellipsis, decimal) would break the count.
ABBREVIATIONS = (
    "mr.", "mrs.", "ms.", "dr.", "st.", "jr.", "sr.", "vs.", "etc.",
    "e.g.", "i.e.", "u.s.", "a.m.", "p.m.",
)

TERMINATORS = ".!?"


def validate_entry(text):
    """Check text against every competition gate before anything is written.

    Gates enforced here (mirroring the sealed scorer): text must be a
    non-empty str of 1-400 characters, with no leading/trailing
    whitespace, exactly two sentence terminators, each one ending a
    sentence (followed by a space and a capital, or by end of text),
    no doubled terminators, and no abbreviation period that could
    inflate the terminator count. Any failure aborts with a message
    naming the gate that failed, so a bad entry never reaches disk.
    """
    if not isinstance(text, str):
        raise SystemExit("FAIL: validate_entry: ENTRY is not str (got %s)"
                         % type(text).__name__)
    data = text.encode("utf-8")  # raises on non-UTF-8-encodable text
    if not (1 <= len(text) <= 400):
        raise SystemExit(
            "FAIL: validate_entry: ENTRY is %d chars, gate requires 1-400"
            % len(text))
    if not text.strip():
        raise SystemExit("FAIL: validate_entry: ENTRY is only whitespace")
    lowered = text.lower()
    for abbr in ABBREVIATIONS:
        # Match the abbreviation as a whole word, not as a substring of
        # another word ("last." must not trip the "st." check).
        if re.search(r"(?<![a-z])" + re.escape(abbr), lowered):
            raise SystemExit(
                "FAIL: validate_entry: ENTRY contains abbreviation %r, "
                "which would add a spurious sentence terminator" % abbr)
    if ".." in text or "!!" in text or "??" in text or ".!" in text:
        raise SystemExit(
            "FAIL: validate_entry: ENTRY contains a doubled terminator")
    count = sum(1 for ch in text if ch in TERMINATORS)
    if count != 2:
        raise SystemExit(
            "FAIL: validate_entry: ENTRY has %d sentence terminators, "
            "gate requires exactly 2" % count
        )
    # Each terminator must end a sentence: followed by a space and a
    # capital letter, or by the end of the text.
    for i, ch in enumerate(text):
        if ch in TERMINATORS:
            rest = text[i + 1:]
            if rest and not (rest[0] == " " and len(rest) > 1
                             and rest[1].isupper()):
                raise SystemExit(
                    "FAIL: validate_entry: terminator at position %d is "
                    "not a sentence end (must be followed by a space and "
                    "a capital, or by end of text)" % i
                )
    if text != text.strip():
        raise SystemExit(
            "FAIL: validate_entry: ENTRY has leading/trailing whitespace")
    return len(data)


def write_and_verify(path, text):
    """Write text to path atomically, then read it back and fail hard
    unless the bytes on disk are identical (and match the sha256)."""
    data = text.encode("utf-8")
    expected = hashlib.sha256(data).hexdigest()
    parent = os.path.dirname(path)
    if parent:
        os.makedirs(parent, exist_ok=True)
    tmp_path = "%s.tmp.%d" % (path, os.getpid())
    try:
        with open(tmp_path, "wb") as f:
            f.write(data)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp_path, path)
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)
    with open(path, "rb") as f:
        back = f.read()
    if back != data:
        raise SystemExit("FAIL: read-back mismatch for %s" % path)
    if hashlib.sha256(back).hexdigest() != expected:
        raise SystemExit("FAIL: sha256 mismatch for %s" % path)
    return len(data), expected


def main():
    """Validate the entry, write it to both destinations, verify they agree."""
    validate_entry(ENTRY)
    local_path = os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "entry.txt"
    )
    destinations = (OUTPUT_PATH, local_path)
    results = [write_and_verify(path, ENTRY) for path in destinations]
    if len({result for result in results}) != 1:
        raise SystemExit(
            "FAIL: %s and %s disagree (sizes/digests differ)"
            % destinations)
    n, digest = results[0]
    for path in destinations:
        print("wrote %d bytes to %s" % (n, path))
    print("sha256: %s" % digest)
    print("chars: %d, sentences: 2" % len(ENTRY))
    return 0


if __name__ == "__main__":
    sys.exit(main())
