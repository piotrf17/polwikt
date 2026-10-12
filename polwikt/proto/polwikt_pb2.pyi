from google.protobuf.internal import containers as _containers
from google.protobuf.internal import enum_type_wrapper as _enum_type_wrapper
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from collections.abc import Iterable as _Iterable, Mapping as _Mapping
from typing import ClassVar as _ClassVar, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class Pos(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    POS_UNSPECIFIED: _ClassVar[Pos]
    POS_NOUN: _ClassVar[Pos]
    POS_PROPER_NOUN: _ClassVar[Pos]
    POS_VERB: _ClassVar[Pos]
    POS_ADJECTIVE: _ClassVar[Pos]
    POS_ADVERB: _ClassVar[Pos]
    POS_PRONOUN: _ClassVar[Pos]
    POS_NUMERAL: _ClassVar[Pos]
    POS_DETERMINER: _ClassVar[Pos]
    POS_PREPOSITION: _ClassVar[Pos]
    POS_CONJUNCTION: _ClassVar[Pos]
    POS_PARTICLE: _ClassVar[Pos]
    POS_INTERJECTION: _ClassVar[Pos]
    POS_PARTICIPLE: _ClassVar[Pos]
    POS_PREFIX: _ClassVar[Pos]
    POS_SUFFIX: _ClassVar[Pos]
    POS_PHRASE: _ClassVar[Pos]
    POS_PREPOSITIONAL_PHRASE: _ClassVar[Pos]
    POS_IDIOM: _ClassVar[Pos]
    POS_PROVERB: _ClassVar[Pos]
    POS_ABBREVIATION: _ClassVar[Pos]
    POS_CONTRACTION: _ClassVar[Pos]
    POS_LETTER: _ClassVar[Pos]

class Case(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    CASE_UNSPECIFIED: _ClassVar[Case]
    CASE_NOMINATIVE: _ClassVar[Case]
    CASE_GENITIVE: _ClassVar[Case]
    CASE_DATIVE: _ClassVar[Case]
    CASE_ACCUSATIVE: _ClassVar[Case]
    CASE_INSTRUMENTAL: _ClassVar[Case]
    CASE_LOCATIVE: _ClassVar[Case]
    CASE_VOCATIVE: _ClassVar[Case]

class Number(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    NUMBER_UNSPECIFIED: _ClassVar[Number]
    NUMBER_SINGULAR: _ClassVar[Number]
    NUMBER_PLURAL: _ClassVar[Number]
    NUMBER_DUAL: _ClassVar[Number]

class Gender(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    GENDER_UNSPECIFIED: _ClassVar[Gender]
    GENDER_MASCULINE: _ClassVar[Gender]
    GENDER_FEMININE: _ClassVar[Gender]
    GENDER_NEUTER: _ClassVar[Gender]
    GENDER_VIRILE: _ClassVar[Gender]
    GENDER_NONVIRILE: _ClassVar[Gender]

class Animacy(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    ANIMACY_UNSPECIFIED: _ClassVar[Animacy]
    ANIMACY_PERSONAL: _ClassVar[Animacy]
    ANIMACY_ANIMATE: _ClassVar[Animacy]
    ANIMACY_INANIMATE: _ClassVar[Animacy]

class Person(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    PERSON_UNSPECIFIED: _ClassVar[Person]
    PERSON_FIRST: _ClassVar[Person]
    PERSON_SECOND: _ClassVar[Person]
    PERSON_THIRD: _ClassVar[Person]

class Tense(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    TENSE_UNSPECIFIED: _ClassVar[Tense]
    TENSE_PRESENT: _ClassVar[Tense]
    TENSE_PAST: _ClassVar[Tense]
    TENSE_FUTURE: _ClassVar[Tense]

class Mood(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    MOOD_UNSPECIFIED: _ClassVar[Mood]
    MOOD_INDICATIVE: _ClassVar[Mood]
    MOOD_IMPERATIVE: _ClassVar[Mood]
    MOOD_CONDITIONAL: _ClassVar[Mood]

class Aspect(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    ASPECT_UNSPECIFIED: _ClassVar[Aspect]
    ASPECT_IMPERFECTIVE: _ClassVar[Aspect]
    ASPECT_PERFECTIVE: _ClassVar[Aspect]
    ASPECT_BIASPECTUAL: _ClassVar[Aspect]

class Degree(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    DEGREE_UNSPECIFIED: _ClassVar[Degree]
    DEGREE_POSITIVE: _ClassVar[Degree]
    DEGREE_COMPARATIVE: _ClassVar[Degree]
    DEGREE_SUPERLATIVE: _ClassVar[Degree]

class VerbForm(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    VERB_FORM_UNSPECIFIED: _ClassVar[VerbForm]
    VERB_FORM_INFINITIVE: _ClassVar[VerbForm]
    VERB_FORM_ACTIVE_ADJECTIVAL_PARTICIPLE: _ClassVar[VerbForm]
    VERB_FORM_PASSIVE_ADJECTIVAL_PARTICIPLE: _ClassVar[VerbForm]
    VERB_FORM_CONTEMPORARY_ADVERBIAL_PARTICIPLE: _ClassVar[VerbForm]
    VERB_FORM_ANTERIOR_ADVERBIAL_PARTICIPLE: _ClassVar[VerbForm]
    VERB_FORM_VERBAL_NOUN: _ClassVar[VerbForm]
    VERB_FORM_IMPERSONAL_PAST: _ClassVar[VerbForm]
POS_UNSPECIFIED: Pos
POS_NOUN: Pos
POS_PROPER_NOUN: Pos
POS_VERB: Pos
POS_ADJECTIVE: Pos
POS_ADVERB: Pos
POS_PRONOUN: Pos
POS_NUMERAL: Pos
POS_DETERMINER: Pos
POS_PREPOSITION: Pos
POS_CONJUNCTION: Pos
POS_PARTICLE: Pos
POS_INTERJECTION: Pos
POS_PARTICIPLE: Pos
POS_PREFIX: Pos
POS_SUFFIX: Pos
POS_PHRASE: Pos
POS_PREPOSITIONAL_PHRASE: Pos
POS_IDIOM: Pos
POS_PROVERB: Pos
POS_ABBREVIATION: Pos
POS_CONTRACTION: Pos
POS_LETTER: Pos
CASE_UNSPECIFIED: Case
CASE_NOMINATIVE: Case
CASE_GENITIVE: Case
CASE_DATIVE: Case
CASE_ACCUSATIVE: Case
CASE_INSTRUMENTAL: Case
CASE_LOCATIVE: Case
CASE_VOCATIVE: Case
NUMBER_UNSPECIFIED: Number
NUMBER_SINGULAR: Number
NUMBER_PLURAL: Number
NUMBER_DUAL: Number
GENDER_UNSPECIFIED: Gender
GENDER_MASCULINE: Gender
GENDER_FEMININE: Gender
GENDER_NEUTER: Gender
GENDER_VIRILE: Gender
GENDER_NONVIRILE: Gender
ANIMACY_UNSPECIFIED: Animacy
ANIMACY_PERSONAL: Animacy
ANIMACY_ANIMATE: Animacy
ANIMACY_INANIMATE: Animacy
PERSON_UNSPECIFIED: Person
PERSON_FIRST: Person
PERSON_SECOND: Person
PERSON_THIRD: Person
TENSE_UNSPECIFIED: Tense
TENSE_PRESENT: Tense
TENSE_PAST: Tense
TENSE_FUTURE: Tense
MOOD_UNSPECIFIED: Mood
MOOD_INDICATIVE: Mood
MOOD_IMPERATIVE: Mood
MOOD_CONDITIONAL: Mood
ASPECT_UNSPECIFIED: Aspect
ASPECT_IMPERFECTIVE: Aspect
ASPECT_PERFECTIVE: Aspect
ASPECT_BIASPECTUAL: Aspect
DEGREE_UNSPECIFIED: Degree
DEGREE_POSITIVE: Degree
DEGREE_COMPARATIVE: Degree
DEGREE_SUPERLATIVE: Degree
VERB_FORM_UNSPECIFIED: VerbForm
VERB_FORM_INFINITIVE: VerbForm
VERB_FORM_ACTIVE_ADJECTIVAL_PARTICIPLE: VerbForm
VERB_FORM_PASSIVE_ADJECTIVAL_PARTICIPLE: VerbForm
VERB_FORM_CONTEMPORARY_ADVERBIAL_PARTICIPLE: VerbForm
VERB_FORM_ANTERIOR_ADVERBIAL_PARTICIPLE: VerbForm
VERB_FORM_VERBAL_NOUN: VerbForm
VERB_FORM_IMPERSONAL_PAST: VerbForm

class GrammaticalTags(_message.Message):
    __slots__ = ("grammatical_case", "number", "gender", "animacy", "person", "tense", "mood", "aspect", "degree", "verb_form")
    GRAMMATICAL_CASE_FIELD_NUMBER: _ClassVar[int]
    NUMBER_FIELD_NUMBER: _ClassVar[int]
    GENDER_FIELD_NUMBER: _ClassVar[int]
    ANIMACY_FIELD_NUMBER: _ClassVar[int]
    PERSON_FIELD_NUMBER: _ClassVar[int]
    TENSE_FIELD_NUMBER: _ClassVar[int]
    MOOD_FIELD_NUMBER: _ClassVar[int]
    ASPECT_FIELD_NUMBER: _ClassVar[int]
    DEGREE_FIELD_NUMBER: _ClassVar[int]
    VERB_FORM_FIELD_NUMBER: _ClassVar[int]
    grammatical_case: Case
    number: Number
    gender: Gender
    animacy: Animacy
    person: Person
    tense: Tense
    mood: Mood
    aspect: Aspect
    degree: Degree
    verb_form: VerbForm
    def __init__(self, grammatical_case: _Optional[_Union[Case, str]] = ..., number: _Optional[_Union[Number, str]] = ..., gender: _Optional[_Union[Gender, str]] = ..., animacy: _Optional[_Union[Animacy, str]] = ..., person: _Optional[_Union[Person, str]] = ..., tense: _Optional[_Union[Tense, str]] = ..., mood: _Optional[_Union[Mood, str]] = ..., aspect: _Optional[_Union[Aspect, str]] = ..., degree: _Optional[_Union[Degree, str]] = ..., verb_form: _Optional[_Union[VerbForm, str]] = ...) -> None: ...

class Form(_message.Message):
    __slots__ = ("form", "tags", "labels", "raw_tags", "table")
    FORM_FIELD_NUMBER: _ClassVar[int]
    TAGS_FIELD_NUMBER: _ClassVar[int]
    LABELS_FIELD_NUMBER: _ClassVar[int]
    RAW_TAGS_FIELD_NUMBER: _ClassVar[int]
    TABLE_FIELD_NUMBER: _ClassVar[int]
    form: str
    tags: GrammaticalTags
    labels: _containers.RepeatedScalarFieldContainer[str]
    raw_tags: _containers.RepeatedScalarFieldContainer[str]
    table: int
    def __init__(self, form: _Optional[str] = ..., tags: _Optional[_Union[GrammaticalTags, _Mapping]] = ..., labels: _Optional[_Iterable[str]] = ..., raw_tags: _Optional[_Iterable[str]] = ..., table: _Optional[int] = ...) -> None: ...

class InflectionTable(_message.Message):
    __slots__ = ("kind", "title", "irregular")
    class Kind(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
        __slots__ = ()
        KIND_UNSPECIFIED: _ClassVar[InflectionTable.Kind]
        KIND_DECLENSION: _ClassVar[InflectionTable.Kind]
        KIND_CONJUGATION: _ClassVar[InflectionTable.Kind]
        KIND_COMPARISON: _ClassVar[InflectionTable.Kind]
        KIND_COMBINED_FORMS: _ClassVar[InflectionTable.Kind]
    KIND_UNSPECIFIED: InflectionTable.Kind
    KIND_DECLENSION: InflectionTable.Kind
    KIND_CONJUGATION: InflectionTable.Kind
    KIND_COMPARISON: InflectionTable.Kind
    KIND_COMBINED_FORMS: InflectionTable.Kind
    KIND_FIELD_NUMBER: _ClassVar[int]
    TITLE_FIELD_NUMBER: _ClassVar[int]
    IRREGULAR_FIELD_NUMBER: _ClassVar[int]
    kind: InflectionTable.Kind
    title: str
    irregular: bool
    def __init__(self, kind: _Optional[_Union[InflectionTable.Kind, str]] = ..., title: _Optional[str] = ..., irregular: _Optional[bool] = ...) -> None: ...

class Sense(_message.Message):
    __slots__ = ("gloss", "labels", "regions", "topics", "keywords", "examples", "relations", "government", "form_of", "subsenses")
    GLOSS_FIELD_NUMBER: _ClassVar[int]
    LABELS_FIELD_NUMBER: _ClassVar[int]
    REGIONS_FIELD_NUMBER: _ClassVar[int]
    TOPICS_FIELD_NUMBER: _ClassVar[int]
    KEYWORDS_FIELD_NUMBER: _ClassVar[int]
    EXAMPLES_FIELD_NUMBER: _ClassVar[int]
    RELATIONS_FIELD_NUMBER: _ClassVar[int]
    GOVERNMENT_FIELD_NUMBER: _ClassVar[int]
    FORM_OF_FIELD_NUMBER: _ClassVar[int]
    SUBSENSES_FIELD_NUMBER: _ClassVar[int]
    gloss: str
    labels: _containers.RepeatedScalarFieldContainer[str]
    regions: _containers.RepeatedScalarFieldContainer[str]
    topics: _containers.RepeatedScalarFieldContainer[str]
    keywords: _containers.RepeatedCompositeFieldContainer[Keyword]
    examples: _containers.RepeatedCompositeFieldContainer[Example]
    relations: _containers.RepeatedCompositeFieldContainer[Relation]
    government: _containers.RepeatedCompositeFieldContainer[Government]
    form_of: FormOf
    subsenses: _containers.RepeatedCompositeFieldContainer[Sense]
    def __init__(self, gloss: _Optional[str] = ..., labels: _Optional[_Iterable[str]] = ..., regions: _Optional[_Iterable[str]] = ..., topics: _Optional[_Iterable[str]] = ..., keywords: _Optional[_Iterable[_Union[Keyword, _Mapping]]] = ..., examples: _Optional[_Iterable[_Union[Example, _Mapping]]] = ..., relations: _Optional[_Iterable[_Union[Relation, _Mapping]]] = ..., government: _Optional[_Iterable[_Union[Government, _Mapping]]] = ..., form_of: _Optional[_Union[FormOf, _Mapping]] = ..., subsenses: _Optional[_Iterable[_Union[Sense, _Mapping]]] = ...) -> None: ...

class Keyword(_message.Message):
    __slots__ = ("text", "taxonomic")
    TEXT_FIELD_NUMBER: _ClassVar[int]
    TAXONOMIC_FIELD_NUMBER: _ClassVar[int]
    text: str
    taxonomic: bool
    def __init__(self, text: _Optional[str] = ..., taxonomic: _Optional[bool] = ...) -> None: ...

class FormOf(_message.Message):
    __slots__ = ("type", "lemma", "tag_sets", "raw_tags")
    class Type(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
        __slots__ = ()
        TYPE_UNSPECIFIED: _ClassVar[FormOf.Type]
        TYPE_INFLECTION: _ClassVar[FormOf.Type]
        TYPE_ALTERNATIVE_FORM: _ClassVar[FormOf.Type]
        TYPE_SYNONYM: _ClassVar[FormOf.Type]
        TYPE_ABBREVIATION: _ClassVar[FormOf.Type]
        TYPE_DERIVATION: _ClassVar[FormOf.Type]
    TYPE_UNSPECIFIED: FormOf.Type
    TYPE_INFLECTION: FormOf.Type
    TYPE_ALTERNATIVE_FORM: FormOf.Type
    TYPE_SYNONYM: FormOf.Type
    TYPE_ABBREVIATION: FormOf.Type
    TYPE_DERIVATION: FormOf.Type
    TYPE_FIELD_NUMBER: _ClassVar[int]
    LEMMA_FIELD_NUMBER: _ClassVar[int]
    TAG_SETS_FIELD_NUMBER: _ClassVar[int]
    RAW_TAGS_FIELD_NUMBER: _ClassVar[int]
    type: FormOf.Type
    lemma: str
    tag_sets: _containers.RepeatedCompositeFieldContainer[GrammaticalTags]
    raw_tags: _containers.RepeatedScalarFieldContainer[str]
    def __init__(self, type: _Optional[_Union[FormOf.Type, str]] = ..., lemma: _Optional[str] = ..., tag_sets: _Optional[_Iterable[_Union[GrammaticalTags, _Mapping]]] = ..., raw_tags: _Optional[_Iterable[str]] = ...) -> None: ...

class Example(_message.Message):
    __slots__ = ("kind", "text", "translation", "literal", "source")
    class Kind(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
        __slots__ = ()
        KIND_UNSPECIFIED: _ClassVar[Example.Kind]
        KIND_EXAMPLE: _ClassVar[Example.Kind]
        KIND_QUOTATION: _ClassVar[Example.Kind]
        KIND_COLLOCATION: _ClassVar[Example.Kind]
    KIND_UNSPECIFIED: Example.Kind
    KIND_EXAMPLE: Example.Kind
    KIND_QUOTATION: Example.Kind
    KIND_COLLOCATION: Example.Kind
    KIND_FIELD_NUMBER: _ClassVar[int]
    TEXT_FIELD_NUMBER: _ClassVar[int]
    TRANSLATION_FIELD_NUMBER: _ClassVar[int]
    LITERAL_FIELD_NUMBER: _ClassVar[int]
    SOURCE_FIELD_NUMBER: _ClassVar[int]
    kind: Example.Kind
    text: str
    translation: str
    literal: str
    source: str
    def __init__(self, kind: _Optional[_Union[Example.Kind, str]] = ..., text: _Optional[str] = ..., translation: _Optional[str] = ..., literal: _Optional[str] = ..., source: _Optional[str] = ...) -> None: ...

class Government(_message.Message):
    __slots__ = ("preposition", "grammatical_case", "description")
    PREPOSITION_FIELD_NUMBER: _ClassVar[int]
    GRAMMATICAL_CASE_FIELD_NUMBER: _ClassVar[int]
    DESCRIPTION_FIELD_NUMBER: _ClassVar[int]
    preposition: str
    grammatical_case: Case
    description: str
    def __init__(self, preposition: _Optional[str] = ..., grammatical_case: _Optional[_Union[Case, str]] = ..., description: _Optional[str] = ...) -> None: ...

class Relation(_message.Message):
    __slots__ = ("type", "term", "gloss", "labels")
    class Type(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
        __slots__ = ()
        TYPE_UNSPECIFIED: _ClassVar[Relation.Type]
        TYPE_SYNONYM: _ClassVar[Relation.Type]
        TYPE_ANTONYM: _ClassVar[Relation.Type]
        TYPE_HYPERNYM: _ClassVar[Relation.Type]
        TYPE_HYPONYM: _ClassVar[Relation.Type]
        TYPE_COORDINATE: _ClassVar[Relation.Type]
        TYPE_MERONYM: _ClassVar[Relation.Type]
        TYPE_HOLONYM: _ClassVar[Relation.Type]
        TYPE_DERIVED: _ClassVar[Relation.Type]
        TYPE_RELATED: _ClassVar[Relation.Type]
        TYPE_ALTERNATIVE_FORM: _ClassVar[Relation.Type]
        TYPE_HOMOPHONE: _ClassVar[Relation.Type]
        TYPE_DIMINUTIVE: _ClassVar[Relation.Type]
        TYPE_AUGMENTATIVE: _ClassVar[Relation.Type]
        TYPE_PERFECTIVE_COUNTERPART: _ClassVar[Relation.Type]
        TYPE_FREQUENTATIVE: _ClassVar[Relation.Type]
        TYPE_FEMININE_EQUIVALENT: _ClassVar[Relation.Type]
        TYPE_MASCULINE_EQUIVALENT: _ClassVar[Relation.Type]
        TYPE_RELATED_ADJECTIVE: _ClassVar[Relation.Type]
        TYPE_RELATED_ADVERB: _ClassVar[Relation.Type]
        TYPE_PARTICIPLE_OF: _ClassVar[Relation.Type]
        TYPE_IMPERFECTIVE_COUNTERPART: _ClassVar[Relation.Type]
    TYPE_UNSPECIFIED: Relation.Type
    TYPE_SYNONYM: Relation.Type
    TYPE_ANTONYM: Relation.Type
    TYPE_HYPERNYM: Relation.Type
    TYPE_HYPONYM: Relation.Type
    TYPE_COORDINATE: Relation.Type
    TYPE_MERONYM: Relation.Type
    TYPE_HOLONYM: Relation.Type
    TYPE_DERIVED: Relation.Type
    TYPE_RELATED: Relation.Type
    TYPE_ALTERNATIVE_FORM: Relation.Type
    TYPE_HOMOPHONE: Relation.Type
    TYPE_DIMINUTIVE: Relation.Type
    TYPE_AUGMENTATIVE: Relation.Type
    TYPE_PERFECTIVE_COUNTERPART: Relation.Type
    TYPE_FREQUENTATIVE: Relation.Type
    TYPE_FEMININE_EQUIVALENT: Relation.Type
    TYPE_MASCULINE_EQUIVALENT: Relation.Type
    TYPE_RELATED_ADJECTIVE: Relation.Type
    TYPE_RELATED_ADVERB: Relation.Type
    TYPE_PARTICIPLE_OF: Relation.Type
    TYPE_IMPERFECTIVE_COUNTERPART: Relation.Type
    TYPE_FIELD_NUMBER: _ClassVar[int]
    TERM_FIELD_NUMBER: _ClassVar[int]
    GLOSS_FIELD_NUMBER: _ClassVar[int]
    LABELS_FIELD_NUMBER: _ClassVar[int]
    type: Relation.Type
    term: str
    gloss: str
    labels: _containers.RepeatedScalarFieldContainer[str]
    def __init__(self, type: _Optional[_Union[Relation.Type, str]] = ..., term: _Optional[str] = ..., gloss: _Optional[str] = ..., labels: _Optional[_Iterable[str]] = ...) -> None: ...

class Pronunciation(_message.Message):
    __slots__ = ("ipa", "labels")
    IPA_FIELD_NUMBER: _ClassVar[int]
    LABELS_FIELD_NUMBER: _ClassVar[int]
    ipa: str
    labels: _containers.RepeatedScalarFieldContainer[str]
    def __init__(self, ipa: _Optional[str] = ..., labels: _Optional[_Iterable[str]] = ...) -> None: ...

class Audio(_message.Message):
    __slots__ = ("file", "label")
    FILE_FIELD_NUMBER: _ClassVar[int]
    LABEL_FIELD_NUMBER: _ClassVar[int]
    file: str
    label: str
    def __init__(self, file: _Optional[str] = ..., label: _Optional[str] = ...) -> None: ...

class NounInfo(_message.Message):
    __slots__ = ("genders", "plurale_tantum", "singulare_tantum", "indeclinable")
    GENDERS_FIELD_NUMBER: _ClassVar[int]
    PLURALE_TANTUM_FIELD_NUMBER: _ClassVar[int]
    SINGULARE_TANTUM_FIELD_NUMBER: _ClassVar[int]
    INDECLINABLE_FIELD_NUMBER: _ClassVar[int]
    genders: _containers.RepeatedCompositeFieldContainer[GenderAnimacy]
    plurale_tantum: bool
    singulare_tantum: bool
    indeclinable: bool
    def __init__(self, genders: _Optional[_Iterable[_Union[GenderAnimacy, _Mapping]]] = ..., plurale_tantum: _Optional[bool] = ..., singulare_tantum: _Optional[bool] = ..., indeclinable: _Optional[bool] = ...) -> None: ...

class GenderAnimacy(_message.Message):
    __slots__ = ("gender", "animacy")
    GENDER_FIELD_NUMBER: _ClassVar[int]
    ANIMACY_FIELD_NUMBER: _ClassVar[int]
    gender: Gender
    animacy: Animacy
    def __init__(self, gender: _Optional[_Union[Gender, str]] = ..., animacy: _Optional[_Union[Animacy, str]] = ...) -> None: ...

class AdjectiveInfo(_message.Message):
    __slots__ = ("not_comparable", "indeclinable")
    NOT_COMPARABLE_FIELD_NUMBER: _ClassVar[int]
    INDECLINABLE_FIELD_NUMBER: _ClassVar[int]
    not_comparable: bool
    indeclinable: bool
    def __init__(self, not_comparable: _Optional[bool] = ..., indeclinable: _Optional[bool] = ...) -> None: ...

class VerbInfo(_message.Message):
    __slots__ = ("aspect",)
    ASPECT_FIELD_NUMBER: _ClassVar[int]
    aspect: Aspect
    def __init__(self, aspect: _Optional[_Union[Aspect, str]] = ...) -> None: ...

class Entry(_message.Message):
    __slots__ = ("pos", "etymology", "senses", "forms", "tables", "pronunciations", "audio", "syllabification", "labels", "relations", "examples", "usage_notes", "topics", "noun", "verb", "adjective")
    POS_FIELD_NUMBER: _ClassVar[int]
    ETYMOLOGY_FIELD_NUMBER: _ClassVar[int]
    SENSES_FIELD_NUMBER: _ClassVar[int]
    FORMS_FIELD_NUMBER: _ClassVar[int]
    TABLES_FIELD_NUMBER: _ClassVar[int]
    PRONUNCIATIONS_FIELD_NUMBER: _ClassVar[int]
    AUDIO_FIELD_NUMBER: _ClassVar[int]
    SYLLABIFICATION_FIELD_NUMBER: _ClassVar[int]
    LABELS_FIELD_NUMBER: _ClassVar[int]
    RELATIONS_FIELD_NUMBER: _ClassVar[int]
    EXAMPLES_FIELD_NUMBER: _ClassVar[int]
    USAGE_NOTES_FIELD_NUMBER: _ClassVar[int]
    TOPICS_FIELD_NUMBER: _ClassVar[int]
    NOUN_FIELD_NUMBER: _ClassVar[int]
    VERB_FIELD_NUMBER: _ClassVar[int]
    ADJECTIVE_FIELD_NUMBER: _ClassVar[int]
    pos: Pos
    etymology: int
    senses: _containers.RepeatedCompositeFieldContainer[Sense]
    forms: _containers.RepeatedCompositeFieldContainer[Form]
    tables: _containers.RepeatedCompositeFieldContainer[InflectionTable]
    pronunciations: _containers.RepeatedCompositeFieldContainer[Pronunciation]
    audio: _containers.RepeatedCompositeFieldContainer[Audio]
    syllabification: str
    labels: _containers.RepeatedScalarFieldContainer[str]
    relations: _containers.RepeatedCompositeFieldContainer[Relation]
    examples: _containers.RepeatedCompositeFieldContainer[Example]
    usage_notes: str
    topics: _containers.RepeatedScalarFieldContainer[str]
    noun: NounInfo
    verb: VerbInfo
    adjective: AdjectiveInfo
    def __init__(self, pos: _Optional[_Union[Pos, str]] = ..., etymology: _Optional[int] = ..., senses: _Optional[_Iterable[_Union[Sense, _Mapping]]] = ..., forms: _Optional[_Iterable[_Union[Form, _Mapping]]] = ..., tables: _Optional[_Iterable[_Union[InflectionTable, _Mapping]]] = ..., pronunciations: _Optional[_Iterable[_Union[Pronunciation, _Mapping]]] = ..., audio: _Optional[_Iterable[_Union[Audio, _Mapping]]] = ..., syllabification: _Optional[str] = ..., labels: _Optional[_Iterable[str]] = ..., relations: _Optional[_Iterable[_Union[Relation, _Mapping]]] = ..., examples: _Optional[_Iterable[_Union[Example, _Mapping]]] = ..., usage_notes: _Optional[str] = ..., topics: _Optional[_Iterable[str]] = ..., noun: _Optional[_Union[NounInfo, _Mapping]] = ..., verb: _Optional[_Union[VerbInfo, _Mapping]] = ..., adjective: _Optional[_Union[AdjectiveInfo, _Mapping]] = ...) -> None: ...

class Etymology(_message.Message):
    __slots__ = ("text",)
    TEXT_FIELD_NUMBER: _ClassVar[int]
    text: str
    def __init__(self, text: _Optional[str] = ...) -> None: ...

class Frequency(_message.Message):
    __slots__ = ("rank", "count", "source")
    RANK_FIELD_NUMBER: _ClassVar[int]
    COUNT_FIELD_NUMBER: _ClassVar[int]
    SOURCE_FIELD_NUMBER: _ClassVar[int]
    rank: int
    count: int
    source: str
    def __init__(self, rank: _Optional[int] = ..., count: _Optional[int] = ..., source: _Optional[str] = ...) -> None: ...

class Word(_message.Message):
    __slots__ = ("lemma", "etymologies", "entries", "frequency")
    LEMMA_FIELD_NUMBER: _ClassVar[int]
    ETYMOLOGIES_FIELD_NUMBER: _ClassVar[int]
    ENTRIES_FIELD_NUMBER: _ClassVar[int]
    FREQUENCY_FIELD_NUMBER: _ClassVar[int]
    lemma: str
    etymologies: _containers.RepeatedCompositeFieldContainer[Etymology]
    entries: _containers.RepeatedCompositeFieldContainer[Entry]
    frequency: Frequency
    def __init__(self, lemma: _Optional[str] = ..., etymologies: _Optional[_Iterable[_Union[Etymology, _Mapping]]] = ..., entries: _Optional[_Iterable[_Union[Entry, _Mapping]]] = ..., frequency: _Optional[_Union[Frequency, _Mapping]] = ...) -> None: ...

class Corpus(_message.Message):
    __slots__ = ("schema_version", "dump_date", "pipeline_version", "word_count", "drop_labels", "license", "attribution")
    SCHEMA_VERSION_FIELD_NUMBER: _ClassVar[int]
    DUMP_DATE_FIELD_NUMBER: _ClassVar[int]
    PIPELINE_VERSION_FIELD_NUMBER: _ClassVar[int]
    WORD_COUNT_FIELD_NUMBER: _ClassVar[int]
    DROP_LABELS_FIELD_NUMBER: _ClassVar[int]
    LICENSE_FIELD_NUMBER: _ClassVar[int]
    ATTRIBUTION_FIELD_NUMBER: _ClassVar[int]
    schema_version: str
    dump_date: str
    pipeline_version: str
    word_count: int
    drop_labels: _containers.RepeatedScalarFieldContainer[str]
    license: str
    attribution: str
    def __init__(self, schema_version: _Optional[str] = ..., dump_date: _Optional[str] = ..., pipeline_version: _Optional[str] = ..., word_count: _Optional[int] = ..., drop_labels: _Optional[_Iterable[str]] = ..., license: _Optional[str] = ..., attribution: _Optional[str] = ...) -> None: ...
