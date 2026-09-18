"""
Stage 2 of the pipeline: splitting documents into chunks.

⚠️ THIS IS THE FILE YOU CHANGE IN MILESTONE 3.

`split_documents` below is deliberately plain. It cuts every document into
fixed-size pieces with a fixed overlap and pays no attention to where sentences
or paragraphs end. It works, and it is not good.

On a corpus of short posts it may not cut anything at all: `campus_life` comes
out as 88 documents and 88 chunks, because almost nothing in it reaches 800
characters. That is the baseline, not a bug — Milestone 3 is where you decide
whether one post should stay one chunk.

Your job in Milestone 3 is to replace the *body* of `split_documents` with a
strategy that fits the documents you actually read in Milestone 1. Keep the
name and the shape of what it returns — the rest of the pipeline calls it, and
your README has to name the function that produced your chunks.

If you get stuck for 30 minutes, `fallback_split` is the original. Switch back
to it, write down what you saw, and move on. That's a real observation about
your pipeline, not giving up.
"""

import re
from dataclasses import dataclass

import config
from ingest import Document

# A markdown "## Section" line. The city guides put every topic under one of
# these, so they're the natural seam to cut on.
SECTION_HEADING = re.compile(r"^##\s+.+$", re.M)

# A "# Title" line at the very top of a document, e.g. "# Halden Bay".
DOC_TITLE = re.compile(r"\A#\s+(.+)$", re.M)


@dataclass
class Chunk:
    """One piece of one document."""

    text: str
    source: str        # which file it came from
    index: int         # which chunk within that file, starting at 0
    produced_by: str   # the function that made it — cite this in your README

    @property
    def label(self) -> str:
        return f"{self.source}#{self.index}"


def fallback_split(
    documents: list[Document],
    chunk_size: int | None = None,
    overlap: int | None = None,
) -> list[Chunk]:
    """
    The starter's original chunker. Fixed-size character windows with overlap.

    Keep this function. Milestone 3's stop rule points back at it, and having
    something to compare your own strategy against is useful in week 2.
    """
    chunk_size = chunk_size or config.CHUNK_SIZE
    overlap = overlap or config.CHUNK_OVERLAP

    if overlap >= chunk_size:
        raise ValueError("overlap has to be smaller than chunk_size")

    chunks: list[Chunk] = []
    for doc in documents:
        start = 0
        index = 0
        while start < len(doc.text):
            piece = doc.text[start : start + chunk_size].strip()
            if piece:
                chunks.append(
                    Chunk(
                        text=piece,
                        source=doc.source,
                        index=index,
                        produced_by="chunker.py::fallback_split",
                    )
                )
                index += 1
            start += chunk_size - overlap

    return chunks


def _pack_paragraphs(text: str, limit: int) -> list[str]:
    """
    Split text that's too long on paragraph breaks, greedily filling up to
    `limit`. A single paragraph over the limit falls back to character windows,
    because at that point there's no seam left to cut on.
    """
    pieces: list[str] = []
    current = ""

    for para in re.split(r"\n\s*\n", text):
        para = para.strip()
        if not para:
            continue

        if len(para) > limit:
            if current:
                pieces.append(current)
                current = ""
            step = limit - config.CHUNK_OVERLAP
            for start in range(0, len(para), step):
                window = para[start : start + limit].strip()
                if window:
                    pieces.append(window)
            continue

        candidate = f"{current}\n\n{para}" if current else para
        if len(candidate) <= limit:
            current = candidate
        else:
            pieces.append(current)
            current = para

    if current:
        pieces.append(current)

    return pieces


def split_documents(documents: list[Document]) -> list[Chunk]:
    """
    Split each guide on its "## Section" headings, one chunk per section.

    Two things this does that the fallback doesn't:

    1. It cuts on section boundaries instead of a character count, so a chunk
       is a whole topic — "Getting there", "Eat and drink" — rather than 800
       characters ending mid-word.

    2. It prefixes every chunk with the document's title. The guides repeat an
       identical "Practical notes" block, so without the title those chunks are
       near-identical text embedded eight different ways, and retrieval can't
       tell which town's notes it found. The title makes each one distinct.

    CHUNK_SIZE is a ceiling here, not a target. Most sections in city_guides
    land between 200 and 500 characters and are emitted whole; the rare long
    one gets packed on paragraph breaks by `_pack_paragraphs`.
    """
    limit = config.CHUNK_SIZE
    chunks: list[Chunk] = []

    for doc in documents:
        title_match = DOC_TITLE.search(doc.text)
        title = title_match.group(1).strip() if title_match else doc.source

        headings = list(SECTION_HEADING.finditer(doc.text))

        # Everything before the first "##" — the title and the intro paragraph.
        # It already carries the title, so it isn't prefixed again.
        starts = [h.start() for h in headings]
        segments: list[str] = []

        # The cross-cutting guides (walking, eating, seasons, transport) go
        # straight from "# Title" into the first "##" with no intro paragraph.
        # That leaves a preamble that is nothing but the title — 23 characters
        # of no content, which would still get embedded and retrieved. Drop it.
        preamble = (doc.text[: starts[0]] if starts else doc.text).strip()
        if preamble and preamble != (title_match.group(0).strip() if title_match else None):
            segments.append(preamble)

        for i, start in enumerate(starts):
            end = starts[i + 1] if i + 1 < len(starts) else len(doc.text)
            section = doc.text[start:end].strip()
            if section:
                segments.append(f"# {title}\n\n{section}")

        index = 0
        for segment in segments:
            for piece in _pack_paragraphs(segment, limit) or [segment]:
                chunks.append(
                    Chunk(
                        text=piece,
                        source=doc.source,
                        index=index,
                        produced_by="chunker.py::split_documents",
                    )
                )
                index += 1

    return chunks


def describe(chunks: list[Chunk]) -> str:
    """A one-line summary, printed after indexing."""
    if not chunks:
        return "0 chunks"
    lengths = [len(c.text) for c in chunks]
    return (
        f"{len(chunks)} chunks, "
        f"{sum(lengths) // len(lengths)} characters on average "
        f"(shortest {min(lengths)}, longest {max(lengths)}), "
        f"produced by {chunks[0].produced_by}"
    )


if __name__ == "__main__":
    from ingest import load_documents

    chunks = split_documents(load_documents())
    print(describe(chunks))
