"""Simple FASTA format parser."""

from __future__ import annotations


def parse_fasta(text: str) -> list[tuple[str, str]]:
    """Parse FASTA format text.

    Returns a list of (header, sequence) tuples.  The header does not
    include the leading '>' character.  Sequence lines are concatenated
    and stripped of whitespace.
    """
    records: list[tuple[str, str]] = []
    header: str | None = None
    seq_parts: list[str] = []

    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        if line.startswith(">"):
            # Flush previous record.
            if header is not None:
                records.append((header, "".join(seq_parts)))
            header = line[1:].strip()
            seq_parts = []
        else:
            seq_parts.append(line)

    # Flush last record.
    if header is not None:
        records.append((header, "".join(seq_parts)))

    return records
