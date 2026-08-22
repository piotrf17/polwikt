"""The schema covers the Polish grammatical categories of REQUIREMENTS.md section 6.

These are guard-rail tests: R7.6 forbids renumbering fields, so a category that is
missing here is expensive to add later. They assert coverage, not behaviour.
"""

from __future__ import annotations

from polwikt.proto import Aspect, Case, Degree, Gender, Number, Tag, Word
from polwikt.proto.polwikt_pb2 import DESCRIPTOR


def _names(enum_name: str) -> set[str]:
    return {v.name for v in DESCRIPTOR.enum_types_by_name[enum_name].values}


def test_seven_cases() -> None:
    """Seven cases; the vocative is a real one, not an afterthought (R6.1)."""
    cases = _names("Case") - {"CASE_UNSPECIFIED"}
    assert len(cases) == 7
    assert Case.CASE_VOCATIVE in Case.values()


def test_gender_covers_the_virile_split() -> None:
    """Plural agreement splits virile / nonvirile, orthogonally to animacy (R6.1)."""
    assert {Gender.GENDER_VIRILE, Gender.GENDER_NONVIRILE} <= set(Gender.values())
    assert len(_names("Animacy")) - 1 == 3  # personal, animate, inanimate


def test_number_includes_dual() -> None:
    """Middle Polish duals survive in oczy/ręce/uszy."""
    assert Number.NUMBER_DUAL in Number.values()


def test_verb_categories() -> None:
    """R6.2: aspect, the four participles, the verbal noun and the -no/-to past."""
    assert Aspect.ASPECT_BIASPECTUAL in Aspect.values()
    non_finite = _names("NonFinite") - {"NON_FINITE_UNSPECIFIED"}
    assert non_finite == {
        "NON_FINITE_INFINITIVE",
        "NON_FINITE_ACTIVE_ADJECTIVAL_PARTICIPLE",
        "NON_FINITE_PASSIVE_ADJECTIVAL_PARTICIPLE",
        "NON_FINITE_CONTEMPORARY_ADVERBIAL_PARTICIPLE",
        "NON_FINITE_ANTERIOR_ADVERBIAL_PARTICIPLE",
        "NON_FINITE_VERBAL_NOUN",
        "NON_FINITE_IMPERSONAL_PAST",
    }
    assert len(_names("Person")) - 1 == 3
    assert len(_names("Mood")) - 1 == 3  # indicative, imperative, conditional
    assert len(_names("Tense")) - 1 == 3


def test_degree_and_pos_coverage() -> None:
    assert Degree.DEGREE_SUPERLATIVE in Degree.values()
    pos = _names("Pos")
    for expected in (
        "POS_NOUN",
        "POS_VERB",
        "POS_NUMERAL",
        "POS_PROVERB",
        "POS_PREFIX",
    ):
        assert expected in pos
    assert len(pos) - 1 >= 31  # R5.3 lists 31 headings


def test_middle_polish_is_representable() -> None:
    """R6.6a drops it, but the tag exists so the decision stays auditable."""
    assert Tag.TAG_MIDDLE_POLISH in Tag.values()


def test_every_enum_has_an_unspecified_zero() -> None:
    for enum in DESCRIPTOR.enum_types_by_name.values():
        assert enum.values[0].number == 0
        assert enum.values[0].name.endswith("UNSPECIFIED"), enum.name


def test_no_map_fields_anywhere() -> None:
    """Map ordering is unspecified, which would break byte-identical output (G5)."""
    for message in DESCRIPTOR.message_types_by_name.values():
        for field in message.fields:
            assert not (
                field.message_type is not None
                and field.message_type.GetOptions().map_entry
            ), f"{message.name}.{field.name} is a map"


def test_hot_fields_are_cheap_to_encode() -> None:
    """Field numbers <= 15 use a one-byte tag; keep the repeated hot paths there."""
    for name in ("title", "etymology_groups", "pronunciations"):
        assert Word.DESCRIPTOR.fields_by_name[name].number <= 15
