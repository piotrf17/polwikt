"""P3 for one page: raw wikitext to a `Word`, or None when nothing survives (R3.9)."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field

from polwikt.config import Config
from polwikt.expand.policy import Policy, canonical_name, default_policy
from polwikt.expand.wtp import PolwiktWtp
from polwikt.extract.sense import indexes
from polwikt.extract.structure import Walk
from polwikt.parse.headings import HeadingMap, heading_map
from polwikt.parse.sections import language_section
from polwikt.parse.tree import iter_templates, template_name
from polwikt.proto import p3_pb2 as p3
from polwikt.proto import polwikt_pb2 as pb


@dataclass(frozen=True)
class Settings:
    """The config P3 needs, so extraction never reads polwikt.toml itself (R10.5)."""

    language: str
    drop_labels: frozenset[str]
    policy: Policy = field(default_factory=default_policy)
    headings: HeadingMap = field(default_factory=heading_map)

    @classmethod
    def from_config(cls, cfg: Config) -> Settings:
        return cls(language=cfg.languages[0], drop_labels=frozenset(cfg.drop_labels))


@dataclass
class PageResult:
    record: p3.PageRecord
    word: pb.Word | None
    stats: Counter[str]
    unhandled: list[str]  # canonical names no policy entry covers, per use (R4.6)
    colabelled: list[str] = field(default_factory=list)  # R6.6c report


def extract_page(
    wtp: PolwiktWtp, title: str, wikitext: str, settings: Settings
) -> pb.Word | None:
    """Expands, parses and walks the Polish section of `title` into one Word."""
    return extract_record(wtp, title, wikitext, settings).word


def extract_record(
    wtp: PolwiktWtp,
    title: str,
    wikitext: str,
    settings: Settings,
    *,
    page_id: int = 0,
    revision_id: int = 0,
) -> PageResult:
    """The Word plus P3's intermediate record (raw calls, unknown sections, R4.2.1)."""
    record = p3.PageRecord(page_id=page_id, revision_id=revision_id, title=title)
    stats: Counter[str] = Counter({"pages": 1})
    section = language_section(wikitext, settings.language)
    if section is None:
        stats["pages.no_language_section"] += 1
        return PageResult(record, None, stats, [])
    index = indexes(wtp, settings.drop_labels)  # before start_page: it uses the sandbox
    wtp.start_page(title)
    tree = wtp.parse(section)
    unhandled = [
        name
        for node in iter_templates(tree)
        if settings.policy.action(name := canonical_name(wtp, template_name(node)))
        is None
    ]
    walk = Walk(
        wtp, settings.policy, settings.headings, settings.drop_labels, index, title
    )
    for node in tree.children:
        if not isinstance(node, str) and node.kind.name == "LEVEL2":
            walk.container(node, [], None)
    stats.update(walk.stats)
    record.unknown_sections.extend(walk.unknown)
    if walk.dropped_any:
        stats["pages.touched_by_drop"] += 1  # R6.6a magnitude check
    if not walk.entries:
        if walk.dropped_any:
            for label in sorted(set(walk.dropped_any)):
                stats[f"dropped.page.{label}"] += 1
        else:
            stats["pages.no_entries"] += 1
        return PageResult(record, None, stats, unhandled, walk.colabelled)

    # Only groups some entry points at survive, renumbered in article order (R5.1).
    used = sorted({draft.group for draft in walk.entries})
    renumber = {old: new for new, old in enumerate(used)}
    word = pb.Word(lemma=title)
    for old in used:
        group = walk.groups[old]
        word.etymologies.append(pb.Etymology(text=group.text))
        record.etymology_calls.append(p3.EtymologyCalls(calls=group.calls))
    for draft in walk.entries:
        draft.entry.etymology = renumber[draft.group]
        for topic in walk.page_topics:  # {{C|pl|…}} at the foot of the page (R6.10)
            if topic not in draft.entry.topics:
                draft.entry.topics.append(topic)
        word.entries.append(draft.entry)
        record.entry_calls.append(draft.calls)
    record.word = word.SerializeToString(deterministic=True)
    stats["pages.with_record"] += 1
    stats["entries"] += len(word.entries)
    return PageResult(record, word, stats, unhandled, walk.colabelled)
