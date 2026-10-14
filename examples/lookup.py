"""Look Polish words up in a polwikt corpus: the consumer example from the README.

    uv run python examples/lookup.py data/corpus kotów mamy

An app reads the shards with nothing but `zstandard`, `protobuf` and the module
`protoc --python_out=. polwikt.proto` generates from the schema in the release: each
shard is zstd, and the decompressed stream is `Word` messages, each prefixed by its
length as a varint (R7.2). The corpus ships no lookup index (R7.3), so this builds the
one a dictionary needs: every lemma and every inflected spelling (the entry's Forms,
which include the folded form-of pages, R3.13b) -> the entries it belongs to.
"""

from __future__ import annotations

import sys
from collections import defaultdict
from collections.abc import Iterator
from pathlib import Path

import zstandard

from polwikt.proto import polwikt_pb2 as pb  # outside this repo: the protoc output


def read_words(corpus: Path) -> Iterator[pb.Word]:
    """Every Word in the corpus, in shard order."""
    for shard in sorted(corpus.glob("words-*.pb.zst")):
        with shard.open("rb") as f:
            reader = zstandard.ZstdDecompressor().stream_reader(
                f, read_across_frames=True
            )
            data = reader.read()
        pos = 0
        while pos < len(data):
            size, shift = 0, 0
            while True:  # the varint length prefix
                byte = data[pos]
                pos += 1
                size |= (byte & 0x7F) << shift
                shift += 7
                if byte < 0x80:
                    break
            yield pb.Word.FromString(data[pos : pos + size])
            pos += size


def describe(tags: pb.GrammaticalTags) -> str:
    """The Form's enums as words: CASE_GENITIVE, NUMBER_PLURAL -> "genitive plural"."""
    words = []
    for field, value in tags.ListFields():
        values = field.enum_type.values_by_number
        prefix = values[0].name.removesuffix("UNSPECIFIED")  # "VERB_FORM_"
        word = values[value].name.removeprefix(prefix).replace("_", " ").lower()
        words.append(f"{word} person" if field.name == "person" else word)
    return " ".join(words)


def build_index(words: Iterator[pb.Word]) -> dict[str, list[tuple[str, str, str]]]:
    """Spelling -> (lemma, part of speech, what the spelling is), lemmas first."""
    index: dict[str, list[tuple[str, str, str]]] = defaultdict(list)
    for word in words:
        for entry in word.entries:
            pos = pb.Pos.Name(entry.pos).removeprefix("POS_").lower()
            hits = [(word.lemma, "lemma")]
            hits += [(form.form, describe(form.tags)) for form in entry.forms]
            for spelling, what in hits:
                hit = (word.lemma, pos, what)
                if hit not in index[spelling]:
                    index[spelling].append(hit)
    return index


def main(corpus: Path, queries: list[str]) -> None:
    index = build_index(read_words(corpus))
    for query in queries:
        for lemma, pos, what in index.get(query, []):
            print(f"{query}: {what} of {lemma} ({pos})")
        if query not in index:
            print(f"{query}: not found")


if __name__ == "__main__":
    main(Path(sys.argv[1]), sys.argv[2:])
