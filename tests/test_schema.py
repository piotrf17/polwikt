"""The schema covers §6's categories and keeps the R7.6 / G5 rules."""

from __future__ import annotations

import filecmp
import subprocess
import sys
from collections.abc import Iterator
from pathlib import Path

import pytest
from google.protobuf.descriptor import Descriptor, EnumDescriptor, FieldDescriptor

from polwikt.proto import polwikt_pb2 as pb

REPO = Path(__file__).resolve().parent.parent
FILE = pb.DESCRIPTOR


def _all_messages() -> Iterator[Descriptor]:
    stack = list(FILE.message_types_by_name.values())
    while stack:
        message = stack.pop()
        yield message
        stack.extend(message.nested_types)


def _all_enums() -> Iterator[EnumDescriptor]:
    yield from FILE.enum_types_by_name.values()
    for message in _all_messages():
        yield from message.enum_types


def _values(enum: EnumDescriptor) -> set[str]:
    prefix = enum.values[0].name.removesuffix("UNSPECIFIED")
    return {v.name.removeprefix(prefix) for v in enum.values[1:]}


def test_every_enum_has_unspecified_zero() -> None:
    for enum in _all_enums():
        zero = enum.values_by_number[0]
        assert zero.name.endswith("_UNSPECIFIED"), enum.full_name


def test_enum_values_share_their_prefix() -> None:
    for enum in _all_enums():
        prefix = enum.values[0].name.removesuffix("UNSPECIFIED")
        for value in enum.values:
            assert value.name.startswith(prefix), (enum.full_name, value.name)


def test_no_map_fields() -> None:
    # R7.6: map entries can't gain fields later and drop article order. (Determinism is
    # not the reason: deterministic=True serialization sorts map entries by key.)
    for message in _all_messages():
        assert not message.GetOptions().map_entry, message.full_name


def test_polish_categories_are_complete() -> None:  # §6, R7.7
    assert _values(pb.Case.DESCRIPTOR) == {
        "NOMINATIVE",
        "GENITIVE",
        "DATIVE",
        "ACCUSATIVE",
        "INSTRUMENTAL",
        "LOCATIVE",
        "VOCATIVE",
    }
    assert {"MASCULINE", "FEMININE", "NEUTER", "VIRILE", "NONVIRILE"} <= _values(
        pb.Gender.DESCRIPTOR
    )
    assert _values(pb.Animacy.DESCRIPTOR) == {"PERSONAL", "ANIMATE", "INANIMATE"}
    assert _values(pb.Aspect.DESCRIPTOR) == {
        "IMPERFECTIVE",
        "PERFECTIVE",
        "BIASPECTUAL",
    }
    assert {"SINGULAR", "PLURAL", "DUAL"} <= _values(pb.Number.DESCRIPTOR)
    assert {"INDICATIVE", "IMPERATIVE", "CONDITIONAL"} <= _values(pb.Mood.DESCRIPTOR)
    assert {"POSITIVE", "COMPARATIVE", "SUPERLATIVE"} <= _values(pb.Degree.DESCRIPTOR)
    # R6.2: every non-finite form the paradigm must carry.
    assert _values(pb.VerbForm.DESCRIPTOR) == {
        "INFINITIVE",
        "ACTIVE_ADJECTIVAL_PARTICIPLE",
        "PASSIVE_ADJECTIVAL_PARTICIPLE",
        "CONTEMPORARY_ADVERBIAL_PARTICIPLE",
        "ANTERIOR_ADVERBIAL_PARTICIPLE",
        "VERBAL_NOUN",
        "IMPERSONAL_PAST",
    }


# R5.3, in the heading spelling en.wiktionary uses.
POS_HEADINGS = """
Noun, Proper noun, Verb, Adjective, Adverb, Pronoun, Numeral, Determiner, Preposition,
Postposition, Conjunction, Particle, Interjection, Prefix, Suffix, Interfix, Infix,
Letter, Symbol, Phrase, Prepositional phrase, Proverb, Idiom, Abbreviation, Initialism,
Acronym, Contraction, Participle, Affix, Circumfix, Combining form, Diacritical mark,
Punctuation mark, Syllable, Romanization"""


def test_pos_covers_every_r5_3_heading() -> None:
    headings = {h.strip() for h in POS_HEADINGS.replace("\n", " ").split(",")}
    expected = {h.upper().replace(" ", "_") for h in headings}
    assert _values(pb.Pos.DESCRIPTOR) == expected


def test_middle_polish_tag_exists_for_re_inclusion() -> None:
    assert "MIDDLE_POLISH" in _values(pb.Tag.DESCRIPTOR)  # R6.6b


def test_grammatical_tags_are_scalar() -> None:
    # One Form per cell-and-case keeps tags scalar and the list pivotable (R7.8).
    for field in pb.GrammaticalTags.DESCRIPTOR.fields:
        assert not field.is_repeated, field.name
        assert field.type == FieldDescriptor.TYPE_ENUM, field.name


HOT_MESSAGES = [
    pb.Form.DESCRIPTOR,
    pb.GrammaticalTags.DESCRIPTOR,
    pb.Sense.DESCRIPTOR,
    pb.LinkSpan.DESCRIPTOR,
    pb.RichText.DESCRIPTOR,
    pb.TemplateCall.DESCRIPTOR,
    pb.NamedArg.DESCRIPTOR,
]


@pytest.mark.parametrize("descriptor", HOT_MESSAGES, ids=lambda d: d.name)
def test_hot_messages_use_one_byte_tags(descriptor: Descriptor) -> None:
    # Field numbers 1-15 encode in one byte; these messages repeat hundreds of times
    # per word, so none of their fields may spill into two-byte tags.
    assert max(f.number for f in descriptor.fields) <= 15


def test_generated_code_is_fresh(tmp_path: Path) -> None:
    # The committed *_pb2 files must be what `make proto` produces from the .proto.
    subprocess.run(
        [
            sys.executable,
            "-m",
            "grpc_tools.protoc",
            f"-I{REPO / 'proto'}",
            f"--python_out={tmp_path}",
            f"--pyi_out={tmp_path}",
            str(REPO / "proto" / "polwikt.proto"),
        ],
        check=True,
    )
    for name in ("polwikt_pb2.py", "polwikt_pb2.pyi"):
        committed = REPO / "polwikt" / "proto" / name
        assert filecmp.cmp(tmp_path / name, committed, shallow=False), (
            f"{name} is stale: run `make proto` and commit"
        )
