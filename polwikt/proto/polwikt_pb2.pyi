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
    POS_POSTPOSITION: _ClassVar[Pos]
    POS_CONJUNCTION: _ClassVar[Pos]
    POS_PARTICLE: _ClassVar[Pos]
    POS_INTERJECTION: _ClassVar[Pos]
    POS_PARTICIPLE: _ClassVar[Pos]
    POS_PHRASE: _ClassVar[Pos]
    POS_PREPOSITIONAL_PHRASE: _ClassVar[Pos]
    POS_PROVERB: _ClassVar[Pos]
    POS_IDIOM: _ClassVar[Pos]
    POS_PREFIX: _ClassVar[Pos]
    POS_SUFFIX: _ClassVar[Pos]
    POS_INTERFIX: _ClassVar[Pos]
    POS_INFIX: _ClassVar[Pos]
    POS_CIRCUMFIX: _ClassVar[Pos]
    POS_AFFIX: _ClassVar[Pos]
    POS_COMBINING_FORM: _ClassVar[Pos]
    POS_ABBREVIATION: _ClassVar[Pos]
    POS_INITIALISM: _ClassVar[Pos]
    POS_ACRONYM: _ClassVar[Pos]
    POS_CONTRACTION: _ClassVar[Pos]
    POS_LETTER: _ClassVar[Pos]
    POS_SYMBOL: _ClassVar[Pos]
    POS_DIACRITICAL_MARK: _ClassVar[Pos]
    POS_PUNCTUATION_MARK: _ClassVar[Pos]
    POS_SYLLABLE: _ClassVar[Pos]
    POS_ROMANIZATION: _ClassVar[Pos]

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
    TENSE_PLUPERFECT: _ClassVar[Tense]

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

class Voice(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    VOICE_UNSPECIFIED: _ClassVar[Voice]
    VOICE_ACTIVE: _ClassVar[Voice]
    VOICE_PASSIVE: _ClassVar[Voice]

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

class Tag(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    TAG_UNSPECIFIED: _ClassVar[Tag]
    TAG_COLLOQUIAL: _ClassVar[Tag]
    TAG_INFORMAL: _ClassVar[Tag]
    TAG_FORMAL: _ClassVar[Tag]
    TAG_LITERARY: _ClassVar[Tag]
    TAG_POETIC: _ClassVar[Tag]
    TAG_SLANG: _ClassVar[Tag]
    TAG_VULGAR: _ClassVar[Tag]
    TAG_OFFENSIVE: _ClassVar[Tag]
    TAG_DEROGATORY: _ClassVar[Tag]
    TAG_HUMOROUS: _ClassVar[Tag]
    TAG_IRONIC: _ClassVar[Tag]
    TAG_EUPHEMISTIC: _ClassVar[Tag]
    TAG_ARCHAIC: _ClassVar[Tag]
    TAG_DATED: _ClassVar[Tag]
    TAG_OBSOLETE: _ClassVar[Tag]
    TAG_HISTORICAL: _ClassVar[Tag]
    TAG_RARE: _ClassVar[Tag]
    TAG_NEOLOGISM: _ClassVar[Tag]
    TAG_MIDDLE_POLISH: _ClassVar[Tag]
    TAG_NONSTANDARD: _ClassVar[Tag]
    TAG_PROSCRIBED: _ClassVar[Tag]
    TAG_DIALECTAL: _ClassVar[Tag]
    TAG_REGIONAL: _ClassVar[Tag]
    TAG_FIGURATIVE: _ClassVar[Tag]
    TAG_LITERAL: _ClassVar[Tag]
    TAG_TRANSITIVE: _ClassVar[Tag]
    TAG_INTRANSITIVE: _ClassVar[Tag]
    TAG_REFLEXIVE: _ClassVar[Tag]
    TAG_IMPERSONAL: _ClassVar[Tag]
    TAG_AUXILIARY: _ClassVar[Tag]
    TAG_DEFECTIVE: _ClassVar[Tag]
    TAG_INDECLINABLE: _ClassVar[Tag]
    TAG_PLURALE_TANTUM: _ClassVar[Tag]
    TAG_SINGULARE_TANTUM: _ClassVar[Tag]
    TAG_COLLECTIVE: _ClassVar[Tag]
    TAG_DIMINUTIVE: _ClassVar[Tag]
    TAG_AUGMENTATIVE: _ClassVar[Tag]
    TAG_ABBREVIATION: _ClassVar[Tag]
    TAG_ONOMATOPOEIC: _ClassVar[Tag]
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
POS_POSTPOSITION: Pos
POS_CONJUNCTION: Pos
POS_PARTICLE: Pos
POS_INTERJECTION: Pos
POS_PARTICIPLE: Pos
POS_PHRASE: Pos
POS_PREPOSITIONAL_PHRASE: Pos
POS_PROVERB: Pos
POS_IDIOM: Pos
POS_PREFIX: Pos
POS_SUFFIX: Pos
POS_INTERFIX: Pos
POS_INFIX: Pos
POS_CIRCUMFIX: Pos
POS_AFFIX: Pos
POS_COMBINING_FORM: Pos
POS_ABBREVIATION: Pos
POS_INITIALISM: Pos
POS_ACRONYM: Pos
POS_CONTRACTION: Pos
POS_LETTER: Pos
POS_SYMBOL: Pos
POS_DIACRITICAL_MARK: Pos
POS_PUNCTUATION_MARK: Pos
POS_SYLLABLE: Pos
POS_ROMANIZATION: Pos
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
TENSE_PLUPERFECT: Tense
MOOD_UNSPECIFIED: Mood
MOOD_INDICATIVE: Mood
MOOD_IMPERATIVE: Mood
MOOD_CONDITIONAL: Mood
ASPECT_UNSPECIFIED: Aspect
ASPECT_IMPERFECTIVE: Aspect
ASPECT_PERFECTIVE: Aspect
ASPECT_BIASPECTUAL: Aspect
VOICE_UNSPECIFIED: Voice
VOICE_ACTIVE: Voice
VOICE_PASSIVE: Voice
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
TAG_UNSPECIFIED: Tag
TAG_COLLOQUIAL: Tag
TAG_INFORMAL: Tag
TAG_FORMAL: Tag
TAG_LITERARY: Tag
TAG_POETIC: Tag
TAG_SLANG: Tag
TAG_VULGAR: Tag
TAG_OFFENSIVE: Tag
TAG_DEROGATORY: Tag
TAG_HUMOROUS: Tag
TAG_IRONIC: Tag
TAG_EUPHEMISTIC: Tag
TAG_ARCHAIC: Tag
TAG_DATED: Tag
TAG_OBSOLETE: Tag
TAG_HISTORICAL: Tag
TAG_RARE: Tag
TAG_NEOLOGISM: Tag
TAG_MIDDLE_POLISH: Tag
TAG_NONSTANDARD: Tag
TAG_PROSCRIBED: Tag
TAG_DIALECTAL: Tag
TAG_REGIONAL: Tag
TAG_FIGURATIVE: Tag
TAG_LITERAL: Tag
TAG_TRANSITIVE: Tag
TAG_INTRANSITIVE: Tag
TAG_REFLEXIVE: Tag
TAG_IMPERSONAL: Tag
TAG_AUXILIARY: Tag
TAG_DEFECTIVE: Tag
TAG_INDECLINABLE: Tag
TAG_PLURALE_TANTUM: Tag
TAG_SINGULARE_TANTUM: Tag
TAG_COLLECTIVE: Tag
TAG_DIMINUTIVE: Tag
TAG_AUGMENTATIVE: Tag
TAG_ABBREVIATION: Tag
TAG_ONOMATOPOEIC: Tag

class GrammaticalTags(_message.Message):
    __slots__ = ("grammatical_case", "number", "gender", "animacy", "person", "tense", "mood", "aspect", "voice", "degree", "verb_form")
    GRAMMATICAL_CASE_FIELD_NUMBER: _ClassVar[int]
    NUMBER_FIELD_NUMBER: _ClassVar[int]
    GENDER_FIELD_NUMBER: _ClassVar[int]
    ANIMACY_FIELD_NUMBER: _ClassVar[int]
    PERSON_FIELD_NUMBER: _ClassVar[int]
    TENSE_FIELD_NUMBER: _ClassVar[int]
    MOOD_FIELD_NUMBER: _ClassVar[int]
    ASPECT_FIELD_NUMBER: _ClassVar[int]
    VOICE_FIELD_NUMBER: _ClassVar[int]
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
    voice: Voice
    degree: Degree
    verb_form: VerbForm
    def __init__(self, grammatical_case: _Optional[_Union[Case, str]] = ..., number: _Optional[_Union[Number, str]] = ..., gender: _Optional[_Union[Gender, str]] = ..., animacy: _Optional[_Union[Animacy, str]] = ..., person: _Optional[_Union[Person, str]] = ..., tense: _Optional[_Union[Tense, str]] = ..., mood: _Optional[_Union[Mood, str]] = ..., aspect: _Optional[_Union[Aspect, str]] = ..., voice: _Optional[_Union[Voice, str]] = ..., degree: _Optional[_Union[Degree, str]] = ..., verb_form: _Optional[_Union[VerbForm, str]] = ...) -> None: ...

class TemplateCall(_message.Message):
    __slots__ = ("name", "positional", "named")
    NAME_FIELD_NUMBER: _ClassVar[int]
    POSITIONAL_FIELD_NUMBER: _ClassVar[int]
    NAMED_FIELD_NUMBER: _ClassVar[int]
    name: str
    positional: _containers.RepeatedScalarFieldContainer[str]
    named: _containers.RepeatedCompositeFieldContainer[NamedArg]
    def __init__(self, name: _Optional[str] = ..., positional: _Optional[_Iterable[str]] = ..., named: _Optional[_Iterable[_Union[NamedArg, _Mapping]]] = ...) -> None: ...

class NamedArg(_message.Message):
    __slots__ = ("name", "value")
    NAME_FIELD_NUMBER: _ClassVar[int]
    VALUE_FIELD_NUMBER: _ClassVar[int]
    name: str
    value: str
    def __init__(self, name: _Optional[str] = ..., value: _Optional[str] = ...) -> None: ...

class RichText(_message.Message):
    __slots__ = ("text", "links", "wikitext")
    TEXT_FIELD_NUMBER: _ClassVar[int]
    LINKS_FIELD_NUMBER: _ClassVar[int]
    WIKITEXT_FIELD_NUMBER: _ClassVar[int]
    text: str
    links: _containers.RepeatedCompositeFieldContainer[LinkSpan]
    wikitext: str
    def __init__(self, text: _Optional[str] = ..., links: _Optional[_Iterable[_Union[LinkSpan, _Mapping]]] = ..., wikitext: _Optional[str] = ...) -> None: ...

class LinkSpan(_message.Message):
    __slots__ = ("start", "end", "target", "anchor", "lang_code")
    START_FIELD_NUMBER: _ClassVar[int]
    END_FIELD_NUMBER: _ClassVar[int]
    TARGET_FIELD_NUMBER: _ClassVar[int]
    ANCHOR_FIELD_NUMBER: _ClassVar[int]
    LANG_CODE_FIELD_NUMBER: _ClassVar[int]
    start: int
    end: int
    target: str
    anchor: str
    lang_code: str
    def __init__(self, start: _Optional[int] = ..., end: _Optional[int] = ..., target: _Optional[str] = ..., anchor: _Optional[str] = ..., lang_code: _Optional[str] = ...) -> None: ...

class EntryRef(_message.Message):
    __slots__ = ("title", "etymology_index", "entry_index")
    TITLE_FIELD_NUMBER: _ClassVar[int]
    ETYMOLOGY_INDEX_FIELD_NUMBER: _ClassVar[int]
    ENTRY_INDEX_FIELD_NUMBER: _ClassVar[int]
    title: str
    etymology_index: int
    entry_index: int
    def __init__(self, title: _Optional[str] = ..., etymology_index: _Optional[int] = ..., entry_index: _Optional[int] = ...) -> None: ...

class RawSection(_message.Message):
    __slots__ = ("heading", "wikitext")
    HEADING_FIELD_NUMBER: _ClassVar[int]
    WIKITEXT_FIELD_NUMBER: _ClassVar[int]
    heading: str
    wikitext: str
    def __init__(self, heading: _Optional[str] = ..., wikitext: _Optional[str] = ...) -> None: ...

class Example(_message.Message):
    __slots__ = ("kind", "text", "translation", "literal", "citation", "tags", "raw_tags", "template")
    class Kind(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
        __slots__ = ()
        KIND_UNSPECIFIED: _ClassVar[Example.Kind]
        KIND_USAGE_EXAMPLE: _ClassVar[Example.Kind]
        KIND_QUOTATION: _ClassVar[Example.Kind]
        KIND_COLLOCATION: _ClassVar[Example.Kind]
    KIND_UNSPECIFIED: Example.Kind
    KIND_USAGE_EXAMPLE: Example.Kind
    KIND_QUOTATION: Example.Kind
    KIND_COLLOCATION: Example.Kind
    KIND_FIELD_NUMBER: _ClassVar[int]
    TEXT_FIELD_NUMBER: _ClassVar[int]
    TRANSLATION_FIELD_NUMBER: _ClassVar[int]
    LITERAL_FIELD_NUMBER: _ClassVar[int]
    CITATION_FIELD_NUMBER: _ClassVar[int]
    TAGS_FIELD_NUMBER: _ClassVar[int]
    RAW_TAGS_FIELD_NUMBER: _ClassVar[int]
    TEMPLATE_FIELD_NUMBER: _ClassVar[int]
    kind: Example.Kind
    text: RichText
    translation: RichText
    literal: str
    citation: Citation
    tags: _containers.RepeatedScalarFieldContainer[Tag]
    raw_tags: _containers.RepeatedScalarFieldContainer[str]
    template: TemplateCall
    def __init__(self, kind: _Optional[_Union[Example.Kind, str]] = ..., text: _Optional[_Union[RichText, _Mapping]] = ..., translation: _Optional[_Union[RichText, _Mapping]] = ..., literal: _Optional[str] = ..., citation: _Optional[_Union[Citation, _Mapping]] = ..., tags: _Optional[_Iterable[_Union[Tag, str]]] = ..., raw_tags: _Optional[_Iterable[str]] = ..., template: _Optional[_Union[TemplateCall, _Mapping]] = ...) -> None: ...

class Citation(_message.Message):
    __slots__ = ("author", "title", "year", "publisher", "page", "url", "raw")
    AUTHOR_FIELD_NUMBER: _ClassVar[int]
    TITLE_FIELD_NUMBER: _ClassVar[int]
    YEAR_FIELD_NUMBER: _ClassVar[int]
    PUBLISHER_FIELD_NUMBER: _ClassVar[int]
    PAGE_FIELD_NUMBER: _ClassVar[int]
    URL_FIELD_NUMBER: _ClassVar[int]
    RAW_FIELD_NUMBER: _ClassVar[int]
    author: str
    title: str
    year: str
    publisher: str
    page: str
    url: str
    raw: str
    def __init__(self, author: _Optional[str] = ..., title: _Optional[str] = ..., year: _Optional[str] = ..., publisher: _Optional[str] = ..., page: _Optional[str] = ..., url: _Optional[str] = ..., raw: _Optional[str] = ...) -> None: ...

class Pronunciation(_message.Message):
    __slots__ = ("ipa", "syllabification", "rhyme", "audio_file", "audio_label", "homophones", "tags", "raw_tags", "template")
    IPA_FIELD_NUMBER: _ClassVar[int]
    SYLLABIFICATION_FIELD_NUMBER: _ClassVar[int]
    RHYME_FIELD_NUMBER: _ClassVar[int]
    AUDIO_FILE_FIELD_NUMBER: _ClassVar[int]
    AUDIO_LABEL_FIELD_NUMBER: _ClassVar[int]
    HOMOPHONES_FIELD_NUMBER: _ClassVar[int]
    TAGS_FIELD_NUMBER: _ClassVar[int]
    RAW_TAGS_FIELD_NUMBER: _ClassVar[int]
    TEMPLATE_FIELD_NUMBER: _ClassVar[int]
    ipa: str
    syllabification: str
    rhyme: str
    audio_file: str
    audio_label: str
    homophones: _containers.RepeatedScalarFieldContainer[str]
    tags: _containers.RepeatedScalarFieldContainer[Tag]
    raw_tags: _containers.RepeatedScalarFieldContainer[str]
    template: TemplateCall
    def __init__(self, ipa: _Optional[str] = ..., syllabification: _Optional[str] = ..., rhyme: _Optional[str] = ..., audio_file: _Optional[str] = ..., audio_label: _Optional[str] = ..., homophones: _Optional[_Iterable[str]] = ..., tags: _Optional[_Iterable[_Union[Tag, str]]] = ..., raw_tags: _Optional[_Iterable[str]] = ..., template: _Optional[_Union[TemplateCall, _Mapping]] = ...) -> None: ...

class Government(_message.Message):
    __slots__ = ("preposition", "grammatical_case", "slot_gloss", "raw")
    PREPOSITION_FIELD_NUMBER: _ClassVar[int]
    GRAMMATICAL_CASE_FIELD_NUMBER: _ClassVar[int]
    SLOT_GLOSS_FIELD_NUMBER: _ClassVar[int]
    RAW_FIELD_NUMBER: _ClassVar[int]
    preposition: str
    grammatical_case: Case
    slot_gloss: str
    raw: str
    def __init__(self, preposition: _Optional[str] = ..., grammatical_case: _Optional[_Union[Case, str]] = ..., slot_gloss: _Optional[str] = ..., raw: _Optional[str] = ...) -> None: ...

class Relation(_message.Message):
    __slots__ = ("type", "term", "gloss", "sense_id", "tags", "raw_tags", "target", "inferred", "template")
    class Type(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
        __slots__ = ()
        TYPE_UNSPECIFIED: _ClassVar[Relation.Type]
        TYPE_SYNONYM: _ClassVar[Relation.Type]
        TYPE_ANTONYM: _ClassVar[Relation.Type]
        TYPE_HYPERNYM: _ClassVar[Relation.Type]
        TYPE_HYPONYM: _ClassVar[Relation.Type]
        TYPE_MERONYM: _ClassVar[Relation.Type]
        TYPE_HOLONYM: _ClassVar[Relation.Type]
        TYPE_COORDINATE: _ClassVar[Relation.Type]
        TYPE_TROPONYM: _ClassVar[Relation.Type]
        TYPE_DERIVED: _ClassVar[Relation.Type]
        TYPE_RELATED: _ClassVar[Relation.Type]
        TYPE_ALTERNATIVE_FORM: _ClassVar[Relation.Type]
        TYPE_SEE_ALSO: _ClassVar[Relation.Type]
        TYPE_DIMINUTIVE: _ClassVar[Relation.Type]
        TYPE_AUGMENTATIVE: _ClassVar[Relation.Type]
        TYPE_ASPECT_PARTNER: _ClassVar[Relation.Type]
        TYPE_FREQUENTATIVE: _ClassVar[Relation.Type]
        TYPE_COMPARATIVE: _ClassVar[Relation.Type]
        TYPE_SUPERLATIVE: _ClassVar[Relation.Type]
        TYPE_RELATED_ADJECTIVE: _ClassVar[Relation.Type]
        TYPE_RELATED_ADVERB: _ClassVar[Relation.Type]
        TYPE_FEMININE_EQUIVALENT: _ClassVar[Relation.Type]
        TYPE_MASCULINE_EQUIVALENT: _ClassVar[Relation.Type]
    TYPE_UNSPECIFIED: Relation.Type
    TYPE_SYNONYM: Relation.Type
    TYPE_ANTONYM: Relation.Type
    TYPE_HYPERNYM: Relation.Type
    TYPE_HYPONYM: Relation.Type
    TYPE_MERONYM: Relation.Type
    TYPE_HOLONYM: Relation.Type
    TYPE_COORDINATE: Relation.Type
    TYPE_TROPONYM: Relation.Type
    TYPE_DERIVED: Relation.Type
    TYPE_RELATED: Relation.Type
    TYPE_ALTERNATIVE_FORM: Relation.Type
    TYPE_SEE_ALSO: Relation.Type
    TYPE_DIMINUTIVE: Relation.Type
    TYPE_AUGMENTATIVE: Relation.Type
    TYPE_ASPECT_PARTNER: Relation.Type
    TYPE_FREQUENTATIVE: Relation.Type
    TYPE_COMPARATIVE: Relation.Type
    TYPE_SUPERLATIVE: Relation.Type
    TYPE_RELATED_ADJECTIVE: Relation.Type
    TYPE_RELATED_ADVERB: Relation.Type
    TYPE_FEMININE_EQUIVALENT: Relation.Type
    TYPE_MASCULINE_EQUIVALENT: Relation.Type
    TYPE_FIELD_NUMBER: _ClassVar[int]
    TERM_FIELD_NUMBER: _ClassVar[int]
    GLOSS_FIELD_NUMBER: _ClassVar[int]
    SENSE_ID_FIELD_NUMBER: _ClassVar[int]
    TAGS_FIELD_NUMBER: _ClassVar[int]
    RAW_TAGS_FIELD_NUMBER: _ClassVar[int]
    TARGET_FIELD_NUMBER: _ClassVar[int]
    INFERRED_FIELD_NUMBER: _ClassVar[int]
    TEMPLATE_FIELD_NUMBER: _ClassVar[int]
    type: Relation.Type
    term: str
    gloss: str
    sense_id: str
    tags: _containers.RepeatedScalarFieldContainer[Tag]
    raw_tags: _containers.RepeatedScalarFieldContainer[str]
    target: EntryRef
    inferred: bool
    template: TemplateCall
    def __init__(self, type: _Optional[_Union[Relation.Type, str]] = ..., term: _Optional[str] = ..., gloss: _Optional[str] = ..., sense_id: _Optional[str] = ..., tags: _Optional[_Iterable[_Union[Tag, str]]] = ..., raw_tags: _Optional[_Iterable[str]] = ..., target: _Optional[_Union[EntryRef, _Mapping]] = ..., inferred: _Optional[bool] = ..., template: _Optional[_Union[TemplateCall, _Mapping]] = ...) -> None: ...

class Descendant(_message.Message):
    __slots__ = ("type", "lang_code", "term", "gloss", "raw_tags", "children")
    class Type(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
        __slots__ = ()
        TYPE_UNSPECIFIED: _ClassVar[Descendant.Type]
        TYPE_INHERITED: _ClassVar[Descendant.Type]
        TYPE_BORROWED: _ClassVar[Descendant.Type]
        TYPE_LEARNED_BORROWING: _ClassVar[Descendant.Type]
        TYPE_CALQUE: _ClassVar[Descendant.Type]
        TYPE_SEMANTIC_LOAN: _ClassVar[Descendant.Type]
    TYPE_UNSPECIFIED: Descendant.Type
    TYPE_INHERITED: Descendant.Type
    TYPE_BORROWED: Descendant.Type
    TYPE_LEARNED_BORROWING: Descendant.Type
    TYPE_CALQUE: Descendant.Type
    TYPE_SEMANTIC_LOAN: Descendant.Type
    TYPE_FIELD_NUMBER: _ClassVar[int]
    LANG_CODE_FIELD_NUMBER: _ClassVar[int]
    TERM_FIELD_NUMBER: _ClassVar[int]
    GLOSS_FIELD_NUMBER: _ClassVar[int]
    RAW_TAGS_FIELD_NUMBER: _ClassVar[int]
    CHILDREN_FIELD_NUMBER: _ClassVar[int]
    type: Descendant.Type
    lang_code: str
    term: str
    gloss: str
    raw_tags: _containers.RepeatedScalarFieldContainer[str]
    children: _containers.RepeatedCompositeFieldContainer[Descendant]
    def __init__(self, type: _Optional[_Union[Descendant.Type, str]] = ..., lang_code: _Optional[str] = ..., term: _Optional[str] = ..., gloss: _Optional[str] = ..., raw_tags: _Optional[_Iterable[str]] = ..., children: _Optional[_Iterable[_Union[Descendant, _Mapping]]] = ...) -> None: ...

class EtymologyLink(_message.Message):
    __slots__ = ("type", "lang_code", "term", "gloss", "roman", "template")
    class Type(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
        __slots__ = ()
        TYPE_UNSPECIFIED: _ClassVar[EtymologyLink.Type]
        TYPE_INHERITED: _ClassVar[EtymologyLink.Type]
        TYPE_BORROWED: _ClassVar[EtymologyLink.Type]
        TYPE_LEARNED_BORROWING: _ClassVar[EtymologyLink.Type]
        TYPE_SEMI_LEARNED_BORROWING: _ClassVar[EtymologyLink.Type]
        TYPE_DERIVED: _ClassVar[EtymologyLink.Type]
        TYPE_CALQUE: _ClassVar[EtymologyLink.Type]
        TYPE_SEMANTIC_LOAN: _ClassVar[EtymologyLink.Type]
        TYPE_COGNATE: _ClassVar[EtymologyLink.Type]
        TYPE_AFFIX: _ClassVar[EtymologyLink.Type]
        TYPE_COMPOUND: _ClassVar[EtymologyLink.Type]
        TYPE_BACKFORMATION: _ClassVar[EtymologyLink.Type]
        TYPE_CLIPPING: _ClassVar[EtymologyLink.Type]
        TYPE_ONOMATOPOEIC: _ClassVar[EtymologyLink.Type]
        TYPE_UNKNOWN_ORIGIN: _ClassVar[EtymologyLink.Type]
    TYPE_UNSPECIFIED: EtymologyLink.Type
    TYPE_INHERITED: EtymologyLink.Type
    TYPE_BORROWED: EtymologyLink.Type
    TYPE_LEARNED_BORROWING: EtymologyLink.Type
    TYPE_SEMI_LEARNED_BORROWING: EtymologyLink.Type
    TYPE_DERIVED: EtymologyLink.Type
    TYPE_CALQUE: EtymologyLink.Type
    TYPE_SEMANTIC_LOAN: EtymologyLink.Type
    TYPE_COGNATE: EtymologyLink.Type
    TYPE_AFFIX: EtymologyLink.Type
    TYPE_COMPOUND: EtymologyLink.Type
    TYPE_BACKFORMATION: EtymologyLink.Type
    TYPE_CLIPPING: EtymologyLink.Type
    TYPE_ONOMATOPOEIC: EtymologyLink.Type
    TYPE_UNKNOWN_ORIGIN: EtymologyLink.Type
    TYPE_FIELD_NUMBER: _ClassVar[int]
    LANG_CODE_FIELD_NUMBER: _ClassVar[int]
    TERM_FIELD_NUMBER: _ClassVar[int]
    GLOSS_FIELD_NUMBER: _ClassVar[int]
    ROMAN_FIELD_NUMBER: _ClassVar[int]
    TEMPLATE_FIELD_NUMBER: _ClassVar[int]
    type: EtymologyLink.Type
    lang_code: str
    term: str
    gloss: str
    roman: str
    template: TemplateCall
    def __init__(self, type: _Optional[_Union[EtymologyLink.Type, str]] = ..., lang_code: _Optional[str] = ..., term: _Optional[str] = ..., gloss: _Optional[str] = ..., roman: _Optional[str] = ..., template: _Optional[_Union[TemplateCall, _Mapping]] = ...) -> None: ...

class Reference(_message.Message):
    __slots__ = ("text", "group", "template")
    TEXT_FIELD_NUMBER: _ClassVar[int]
    GROUP_FIELD_NUMBER: _ClassVar[int]
    TEMPLATE_FIELD_NUMBER: _ClassVar[int]
    text: RichText
    group: str
    template: TemplateCall
    def __init__(self, text: _Optional[_Union[RichText, _Mapping]] = ..., group: _Optional[str] = ..., template: _Optional[_Union[TemplateCall, _Mapping]] = ...) -> None: ...

class FormOf(_message.Message):
    __slots__ = ("type", "lemma", "target", "tag_sets", "raw_tags", "template")
    class Type(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
        __slots__ = ()
        TYPE_UNSPECIFIED: _ClassVar[FormOf.Type]
        TYPE_INFLECTION: _ClassVar[FormOf.Type]
        TYPE_PARTICIPLE: _ClassVar[FormOf.Type]
        TYPE_ALTERNATIVE_FORM: _ClassVar[FormOf.Type]
        TYPE_ABBREVIATION: _ClassVar[FormOf.Type]
        TYPE_MISSPELLING: _ClassVar[FormOf.Type]
    TYPE_UNSPECIFIED: FormOf.Type
    TYPE_INFLECTION: FormOf.Type
    TYPE_PARTICIPLE: FormOf.Type
    TYPE_ALTERNATIVE_FORM: FormOf.Type
    TYPE_ABBREVIATION: FormOf.Type
    TYPE_MISSPELLING: FormOf.Type
    TYPE_FIELD_NUMBER: _ClassVar[int]
    LEMMA_FIELD_NUMBER: _ClassVar[int]
    TARGET_FIELD_NUMBER: _ClassVar[int]
    TAG_SETS_FIELD_NUMBER: _ClassVar[int]
    RAW_TAGS_FIELD_NUMBER: _ClassVar[int]
    TEMPLATE_FIELD_NUMBER: _ClassVar[int]
    type: FormOf.Type
    lemma: str
    target: EntryRef
    tag_sets: _containers.RepeatedCompositeFieldContainer[GrammaticalTags]
    raw_tags: _containers.RepeatedScalarFieldContainer[str]
    template: TemplateCall
    def __init__(self, type: _Optional[_Union[FormOf.Type, str]] = ..., lemma: _Optional[str] = ..., target: _Optional[_Union[EntryRef, _Mapping]] = ..., tag_sets: _Optional[_Iterable[_Union[GrammaticalTags, _Mapping]]] = ..., raw_tags: _Optional[_Iterable[str]] = ..., template: _Optional[_Union[TemplateCall, _Mapping]] = ...) -> None: ...

class Sense(_message.Message):
    __slots__ = ("gloss", "tags", "raw_tags", "examples", "relations", "government", "form_of", "sense_id", "subsenses", "topics", "categories", "templates")
    GLOSS_FIELD_NUMBER: _ClassVar[int]
    TAGS_FIELD_NUMBER: _ClassVar[int]
    RAW_TAGS_FIELD_NUMBER: _ClassVar[int]
    EXAMPLES_FIELD_NUMBER: _ClassVar[int]
    RELATIONS_FIELD_NUMBER: _ClassVar[int]
    GOVERNMENT_FIELD_NUMBER: _ClassVar[int]
    FORM_OF_FIELD_NUMBER: _ClassVar[int]
    SENSE_ID_FIELD_NUMBER: _ClassVar[int]
    SUBSENSES_FIELD_NUMBER: _ClassVar[int]
    TOPICS_FIELD_NUMBER: _ClassVar[int]
    CATEGORIES_FIELD_NUMBER: _ClassVar[int]
    TEMPLATES_FIELD_NUMBER: _ClassVar[int]
    gloss: RichText
    tags: _containers.RepeatedScalarFieldContainer[Tag]
    raw_tags: _containers.RepeatedScalarFieldContainer[str]
    examples: _containers.RepeatedCompositeFieldContainer[Example]
    relations: _containers.RepeatedCompositeFieldContainer[Relation]
    government: _containers.RepeatedCompositeFieldContainer[Government]
    form_of: FormOf
    sense_id: str
    subsenses: _containers.RepeatedCompositeFieldContainer[Sense]
    topics: _containers.RepeatedScalarFieldContainer[str]
    categories: _containers.RepeatedScalarFieldContainer[str]
    templates: _containers.RepeatedCompositeFieldContainer[TemplateCall]
    def __init__(self, gloss: _Optional[_Union[RichText, _Mapping]] = ..., tags: _Optional[_Iterable[_Union[Tag, str]]] = ..., raw_tags: _Optional[_Iterable[str]] = ..., examples: _Optional[_Iterable[_Union[Example, _Mapping]]] = ..., relations: _Optional[_Iterable[_Union[Relation, _Mapping]]] = ..., government: _Optional[_Iterable[_Union[Government, _Mapping]]] = ..., form_of: _Optional[_Union[FormOf, _Mapping]] = ..., sense_id: _Optional[str] = ..., subsenses: _Optional[_Iterable[_Union[Sense, _Mapping]]] = ..., topics: _Optional[_Iterable[str]] = ..., categories: _Optional[_Iterable[str]] = ..., templates: _Optional[_Iterable[_Union[TemplateCall, _Mapping]]] = ...) -> None: ...

class Form(_message.Message):
    __slots__ = ("form", "tags", "raw_tags", "source", "usage_tags", "has_own_page", "pronunciations", "record")
    class Source(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
        __slots__ = ()
        SOURCE_UNSPECIFIED: _ClassVar[Form.Source]
        SOURCE_DECLENSION_TABLE: _ClassVar[Form.Source]
        SOURCE_CONJUGATION_TABLE: _ClassVar[Form.Source]
        SOURCE_HEADWORD: _ClassVar[Form.Source]
        SOURCE_FORM_PAGE: _ClassVar[Form.Source]
    SOURCE_UNSPECIFIED: Form.Source
    SOURCE_DECLENSION_TABLE: Form.Source
    SOURCE_CONJUGATION_TABLE: Form.Source
    SOURCE_HEADWORD: Form.Source
    SOURCE_FORM_PAGE: Form.Source
    FORM_FIELD_NUMBER: _ClassVar[int]
    TAGS_FIELD_NUMBER: _ClassVar[int]
    RAW_TAGS_FIELD_NUMBER: _ClassVar[int]
    SOURCE_FIELD_NUMBER: _ClassVar[int]
    USAGE_TAGS_FIELD_NUMBER: _ClassVar[int]
    HAS_OWN_PAGE_FIELD_NUMBER: _ClassVar[int]
    PRONUNCIATIONS_FIELD_NUMBER: _ClassVar[int]
    RECORD_FIELD_NUMBER: _ClassVar[int]
    form: str
    tags: GrammaticalTags
    raw_tags: _containers.RepeatedScalarFieldContainer[str]
    source: Form.Source
    usage_tags: _containers.RepeatedScalarFieldContainer[Tag]
    has_own_page: bool
    pronunciations: _containers.RepeatedCompositeFieldContainer[Pronunciation]
    record: EntryRef
    def __init__(self, form: _Optional[str] = ..., tags: _Optional[_Union[GrammaticalTags, _Mapping]] = ..., raw_tags: _Optional[_Iterable[str]] = ..., source: _Optional[_Union[Form.Source, str]] = ..., usage_tags: _Optional[_Iterable[_Union[Tag, str]]] = ..., has_own_page: _Optional[bool] = ..., pronunciations: _Optional[_Iterable[_Union[Pronunciation, _Mapping]]] = ..., record: _Optional[_Union[EntryRef, _Mapping]] = ...) -> None: ...

class NounInfo(_message.Message):
    __slots__ = ("genders", "indeclinable", "plurale_tantum", "singulare_tantum")
    GENDERS_FIELD_NUMBER: _ClassVar[int]
    INDECLINABLE_FIELD_NUMBER: _ClassVar[int]
    PLURALE_TANTUM_FIELD_NUMBER: _ClassVar[int]
    SINGULARE_TANTUM_FIELD_NUMBER: _ClassVar[int]
    genders: _containers.RepeatedCompositeFieldContainer[GenderAnimacy]
    indeclinable: bool
    plurale_tantum: bool
    singulare_tantum: bool
    def __init__(self, genders: _Optional[_Iterable[_Union[GenderAnimacy, _Mapping]]] = ..., indeclinable: _Optional[bool] = ..., plurale_tantum: _Optional[bool] = ..., singulare_tantum: _Optional[bool] = ...) -> None: ...

class GenderAnimacy(_message.Message):
    __slots__ = ("gender", "animacy")
    GENDER_FIELD_NUMBER: _ClassVar[int]
    ANIMACY_FIELD_NUMBER: _ClassVar[int]
    gender: Gender
    animacy: Animacy
    def __init__(self, gender: _Optional[_Union[Gender, str]] = ..., animacy: _Optional[_Union[Animacy, str]] = ...) -> None: ...

class VerbInfo(_message.Message):
    __slots__ = ("aspect", "reflexive", "impersonal", "defective")
    ASPECT_FIELD_NUMBER: _ClassVar[int]
    REFLEXIVE_FIELD_NUMBER: _ClassVar[int]
    IMPERSONAL_FIELD_NUMBER: _ClassVar[int]
    DEFECTIVE_FIELD_NUMBER: _ClassVar[int]
    aspect: Aspect
    reflexive: bool
    impersonal: bool
    defective: bool
    def __init__(self, aspect: _Optional[_Union[Aspect, str]] = ..., reflexive: _Optional[bool] = ..., impersonal: _Optional[bool] = ..., defective: _Optional[bool] = ...) -> None: ...

class AdjectiveInfo(_message.Message):
    __slots__ = ("comparability",)
    class Comparability(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
        __slots__ = ()
        COMPARABILITY_UNSPECIFIED: _ClassVar[AdjectiveInfo.Comparability]
        COMPARABILITY_COMPARABLE: _ClassVar[AdjectiveInfo.Comparability]
        COMPARABILITY_NOT_COMPARABLE: _ClassVar[AdjectiveInfo.Comparability]
    COMPARABILITY_UNSPECIFIED: AdjectiveInfo.Comparability
    COMPARABILITY_COMPARABLE: AdjectiveInfo.Comparability
    COMPARABILITY_NOT_COMPARABLE: AdjectiveInfo.Comparability
    COMPARABILITY_FIELD_NUMBER: _ClassVar[int]
    comparability: AdjectiveInfo.Comparability
    def __init__(self, comparability: _Optional[_Union[AdjectiveInfo.Comparability, str]] = ...) -> None: ...

class PosEntry(_message.Message):
    __slots__ = ("pos", "heading", "headword", "head_templates", "tags", "raw_tags", "senses", "forms", "inflection_templates", "relations", "examples", "descendants", "pronunciations", "usage_notes", "references", "categories", "other_sections", "noun", "verb", "adjective")
    POS_FIELD_NUMBER: _ClassVar[int]
    HEADING_FIELD_NUMBER: _ClassVar[int]
    HEADWORD_FIELD_NUMBER: _ClassVar[int]
    HEAD_TEMPLATES_FIELD_NUMBER: _ClassVar[int]
    TAGS_FIELD_NUMBER: _ClassVar[int]
    RAW_TAGS_FIELD_NUMBER: _ClassVar[int]
    SENSES_FIELD_NUMBER: _ClassVar[int]
    FORMS_FIELD_NUMBER: _ClassVar[int]
    INFLECTION_TEMPLATES_FIELD_NUMBER: _ClassVar[int]
    RELATIONS_FIELD_NUMBER: _ClassVar[int]
    EXAMPLES_FIELD_NUMBER: _ClassVar[int]
    DESCENDANTS_FIELD_NUMBER: _ClassVar[int]
    PRONUNCIATIONS_FIELD_NUMBER: _ClassVar[int]
    USAGE_NOTES_FIELD_NUMBER: _ClassVar[int]
    REFERENCES_FIELD_NUMBER: _ClassVar[int]
    CATEGORIES_FIELD_NUMBER: _ClassVar[int]
    OTHER_SECTIONS_FIELD_NUMBER: _ClassVar[int]
    NOUN_FIELD_NUMBER: _ClassVar[int]
    VERB_FIELD_NUMBER: _ClassVar[int]
    ADJECTIVE_FIELD_NUMBER: _ClassVar[int]
    pos: Pos
    heading: str
    headword: str
    head_templates: _containers.RepeatedCompositeFieldContainer[TemplateCall]
    tags: _containers.RepeatedScalarFieldContainer[Tag]
    raw_tags: _containers.RepeatedScalarFieldContainer[str]
    senses: _containers.RepeatedCompositeFieldContainer[Sense]
    forms: _containers.RepeatedCompositeFieldContainer[Form]
    inflection_templates: _containers.RepeatedCompositeFieldContainer[TemplateCall]
    relations: _containers.RepeatedCompositeFieldContainer[Relation]
    examples: _containers.RepeatedCompositeFieldContainer[Example]
    descendants: _containers.RepeatedCompositeFieldContainer[Descendant]
    pronunciations: _containers.RepeatedCompositeFieldContainer[Pronunciation]
    usage_notes: RichText
    references: _containers.RepeatedCompositeFieldContainer[Reference]
    categories: _containers.RepeatedScalarFieldContainer[str]
    other_sections: _containers.RepeatedCompositeFieldContainer[RawSection]
    noun: NounInfo
    verb: VerbInfo
    adjective: AdjectiveInfo
    def __init__(self, pos: _Optional[_Union[Pos, str]] = ..., heading: _Optional[str] = ..., headword: _Optional[str] = ..., head_templates: _Optional[_Iterable[_Union[TemplateCall, _Mapping]]] = ..., tags: _Optional[_Iterable[_Union[Tag, str]]] = ..., raw_tags: _Optional[_Iterable[str]] = ..., senses: _Optional[_Iterable[_Union[Sense, _Mapping]]] = ..., forms: _Optional[_Iterable[_Union[Form, _Mapping]]] = ..., inflection_templates: _Optional[_Iterable[_Union[TemplateCall, _Mapping]]] = ..., relations: _Optional[_Iterable[_Union[Relation, _Mapping]]] = ..., examples: _Optional[_Iterable[_Union[Example, _Mapping]]] = ..., descendants: _Optional[_Iterable[_Union[Descendant, _Mapping]]] = ..., pronunciations: _Optional[_Iterable[_Union[Pronunciation, _Mapping]]] = ..., usage_notes: _Optional[_Union[RichText, _Mapping]] = ..., references: _Optional[_Iterable[_Union[Reference, _Mapping]]] = ..., categories: _Optional[_Iterable[str]] = ..., other_sections: _Optional[_Iterable[_Union[RawSection, _Mapping]]] = ..., noun: _Optional[_Union[NounInfo, _Mapping]] = ..., verb: _Optional[_Union[VerbInfo, _Mapping]] = ..., adjective: _Optional[_Union[AdjectiveInfo, _Mapping]] = ...) -> None: ...

class EtymologyGroup(_message.Message):
    __slots__ = ("number", "etymology", "links", "etymology_templates", "pronunciations", "entries", "relations", "categories", "other_sections")
    NUMBER_FIELD_NUMBER: _ClassVar[int]
    ETYMOLOGY_FIELD_NUMBER: _ClassVar[int]
    LINKS_FIELD_NUMBER: _ClassVar[int]
    ETYMOLOGY_TEMPLATES_FIELD_NUMBER: _ClassVar[int]
    PRONUNCIATIONS_FIELD_NUMBER: _ClassVar[int]
    ENTRIES_FIELD_NUMBER: _ClassVar[int]
    RELATIONS_FIELD_NUMBER: _ClassVar[int]
    CATEGORIES_FIELD_NUMBER: _ClassVar[int]
    OTHER_SECTIONS_FIELD_NUMBER: _ClassVar[int]
    number: int
    etymology: RichText
    links: _containers.RepeatedCompositeFieldContainer[EtymologyLink]
    etymology_templates: _containers.RepeatedCompositeFieldContainer[TemplateCall]
    pronunciations: _containers.RepeatedCompositeFieldContainer[Pronunciation]
    entries: _containers.RepeatedCompositeFieldContainer[PosEntry]
    relations: _containers.RepeatedCompositeFieldContainer[Relation]
    categories: _containers.RepeatedScalarFieldContainer[str]
    other_sections: _containers.RepeatedCompositeFieldContainer[RawSection]
    def __init__(self, number: _Optional[int] = ..., etymology: _Optional[_Union[RichText, _Mapping]] = ..., links: _Optional[_Iterable[_Union[EtymologyLink, _Mapping]]] = ..., etymology_templates: _Optional[_Iterable[_Union[TemplateCall, _Mapping]]] = ..., pronunciations: _Optional[_Iterable[_Union[Pronunciation, _Mapping]]] = ..., entries: _Optional[_Iterable[_Union[PosEntry, _Mapping]]] = ..., relations: _Optional[_Iterable[_Union[Relation, _Mapping]]] = ..., categories: _Optional[_Iterable[str]] = ..., other_sections: _Optional[_Iterable[_Union[RawSection, _Mapping]]] = ...) -> None: ...

class Word(_message.Message):
    __slots__ = ("title", "page_id", "revision_id", "lang_code", "etymologies", "pronunciations", "relations", "trivia", "references", "further_reading", "anagrams", "categories", "other_sections")
    TITLE_FIELD_NUMBER: _ClassVar[int]
    PAGE_ID_FIELD_NUMBER: _ClassVar[int]
    REVISION_ID_FIELD_NUMBER: _ClassVar[int]
    LANG_CODE_FIELD_NUMBER: _ClassVar[int]
    ETYMOLOGIES_FIELD_NUMBER: _ClassVar[int]
    PRONUNCIATIONS_FIELD_NUMBER: _ClassVar[int]
    RELATIONS_FIELD_NUMBER: _ClassVar[int]
    TRIVIA_FIELD_NUMBER: _ClassVar[int]
    REFERENCES_FIELD_NUMBER: _ClassVar[int]
    FURTHER_READING_FIELD_NUMBER: _ClassVar[int]
    ANAGRAMS_FIELD_NUMBER: _ClassVar[int]
    CATEGORIES_FIELD_NUMBER: _ClassVar[int]
    OTHER_SECTIONS_FIELD_NUMBER: _ClassVar[int]
    title: str
    page_id: int
    revision_id: int
    lang_code: str
    etymologies: _containers.RepeatedCompositeFieldContainer[EtymologyGroup]
    pronunciations: _containers.RepeatedCompositeFieldContainer[Pronunciation]
    relations: _containers.RepeatedCompositeFieldContainer[Relation]
    trivia: RichText
    references: _containers.RepeatedCompositeFieldContainer[Reference]
    further_reading: _containers.RepeatedCompositeFieldContainer[Reference]
    anagrams: _containers.RepeatedScalarFieldContainer[str]
    categories: _containers.RepeatedScalarFieldContainer[str]
    other_sections: _containers.RepeatedCompositeFieldContainer[RawSection]
    def __init__(self, title: _Optional[str] = ..., page_id: _Optional[int] = ..., revision_id: _Optional[int] = ..., lang_code: _Optional[str] = ..., etymologies: _Optional[_Iterable[_Union[EtymologyGroup, _Mapping]]] = ..., pronunciations: _Optional[_Iterable[_Union[Pronunciation, _Mapping]]] = ..., relations: _Optional[_Iterable[_Union[Relation, _Mapping]]] = ..., trivia: _Optional[_Union[RichText, _Mapping]] = ..., references: _Optional[_Iterable[_Union[Reference, _Mapping]]] = ..., further_reading: _Optional[_Iterable[_Union[Reference, _Mapping]]] = ..., anagrams: _Optional[_Iterable[str]] = ..., categories: _Optional[_Iterable[str]] = ..., other_sections: _Optional[_Iterable[_Union[RawSection, _Mapping]]] = ...) -> None: ...

class Corpus(_message.Message):
    __slots__ = ("schema_version", "dump_date", "dump_sha1", "dump_pinned", "pipeline_git_revision", "generated_at", "languages", "drop_labels", "word_count", "shard_count", "license", "attribution")
    SCHEMA_VERSION_FIELD_NUMBER: _ClassVar[int]
    DUMP_DATE_FIELD_NUMBER: _ClassVar[int]
    DUMP_SHA1_FIELD_NUMBER: _ClassVar[int]
    DUMP_PINNED_FIELD_NUMBER: _ClassVar[int]
    PIPELINE_GIT_REVISION_FIELD_NUMBER: _ClassVar[int]
    GENERATED_AT_FIELD_NUMBER: _ClassVar[int]
    LANGUAGES_FIELD_NUMBER: _ClassVar[int]
    DROP_LABELS_FIELD_NUMBER: _ClassVar[int]
    WORD_COUNT_FIELD_NUMBER: _ClassVar[int]
    SHARD_COUNT_FIELD_NUMBER: _ClassVar[int]
    LICENSE_FIELD_NUMBER: _ClassVar[int]
    ATTRIBUTION_FIELD_NUMBER: _ClassVar[int]
    schema_version: str
    dump_date: str
    dump_sha1: str
    dump_pinned: bool
    pipeline_git_revision: str
    generated_at: str
    languages: _containers.RepeatedScalarFieldContainer[str]
    drop_labels: _containers.RepeatedScalarFieldContainer[str]
    word_count: int
    shard_count: int
    license: str
    attribution: str
    def __init__(self, schema_version: _Optional[str] = ..., dump_date: _Optional[str] = ..., dump_sha1: _Optional[str] = ..., dump_pinned: _Optional[bool] = ..., pipeline_git_revision: _Optional[str] = ..., generated_at: _Optional[str] = ..., languages: _Optional[_Iterable[str]] = ..., drop_labels: _Optional[_Iterable[str]] = ..., word_count: _Optional[int] = ..., shard_count: _Optional[int] = ..., license: _Optional[str] = ..., attribution: _Optional[str] = ...) -> None: ...
