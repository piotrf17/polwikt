"""Pronunciation sections and word frequency (R6.5, R6.13).

A Pronunciation section is read from its expansion: {{pl-pr}} renders every
transcription, recording, syllabification and homophone list as its own line, and the
dialect variants it derives from the respelling only exist there. Each line kind is
identified by a marker in `data/pronunciation.toml`; a line of no known kind is counted
(`pronunciation.line.unknown`).

Labels: a dialect line's labels precede its "IPA:" marker and apply to every
transcription on it; a qualifier after the marker (`<a:colloquial>` on one respelling)
precedes the transcription it qualifies. Anything carrying a `drop_labels` label (the
`mp=` Middle Polish line, R6.6a) is dropped and counted by kind. Dialects transcribed
identically share one Pronunciation, labelled with each of them.
"""

from __future__ import annotations

import logging
import re
import tomllib
from collections import Counter
from dataclasses import dataclass, field
from functools import cache
from importlib import resources
from typing import Any

from wikitextprocessor import WikiNode

from polwikt.expand.run import expand_text
from polwikt.expand.wtp import PolwiktWtp
from polwikt.parse.text import drop_boxes, plain_text
from polwikt.proto import polwikt_pb2 as pb

log = logging.getLogger(__name__)

_IPA = re.compile(r'<span class="IPA[^"]*">([/\[][^<]*[/\]])</span>')
_LABEL = re.compile(r'<span class="ib-content[^"]*">(.*?)</span>')
# A label with its bracket spans: "(colloquial)" after an audio caption.
_BRACKETED = re.compile(
    r'<span class="ib-brac[^"]*">\(</span>.*?<span class="ib-brac[^"]*">\)</span>'
)
_GROUP_HEADER = re.compile(
    r"^[*#:]*\s*\(.*\):$"
)  # "(Greater Poland):" above its dialects
_AUDIO_FILE = re.compile(r'class="audiofile">\[\[\s*File:([^|\]]+)')
_CAPTION = re.compile(r"<td>(.*?)</td>")
_MENTION = re.compile(r'<i class="[^"]*\bmention\b[^"]*"[^>]*>(.*?)</i>')
_TERM = re.compile(r'<span class="Latn[^"]*"[^>]*>(.*?)</span>')
_NEXT_TERM = re.compile(r',\s*(?=<span class="Latn)')
_QUOTES = "“”"  # “robić”


@dataclass(frozen=True)
class Config:
    ipa: str
    audio: str
    syllabification: str
    homophones: str
    ignored: tuple[str, ...]
    caption: re.Pattern[str]
    frequency: dict[str, str]


@cache
def config() -> Config:
    path = resources.files("polwikt.data").joinpath("pronunciation.toml")
    data: dict[str, Any] = tomllib.loads(path.read_text("utf-8"))
    lines = data["lines"]
    return Config(
        ipa=lines["ipa"],
        audio=lines["audio"],
        syllabification=lines["syllabification"],
        homophones=lines["homophones"],
        ignored=tuple(lines["ignored"]),
        caption=re.compile(lines["audio_caption"]),
        frequency=dict(data["frequency"]),
    )


@dataclass
class Sounds:
    """What one Pronunciation section gives every entry it applies to."""

    pronunciations: list[pb.Pronunciation] = field(default_factory=list)
    audio: list[pb.Audio] = field(default_factory=list)
    syllabification: list[str] = field(default_factory=list)
    homophones: list[pb.Relation] = field(default_factory=list)


def sounds(
    wtp: PolwiktWtp,
    section: WikiNode,
    title: str,
    drop_labels: frozenset[str],
    stats: Counter[str],
) -> Sounds:
    """{{pl-pr}} / {{IPA}} / {{audio}} lines of an expanded Pronunciation section."""
    cfg = config()
    body = "".join(
        wtp.node_to_wikitext(c)
        for c in section.children
        if not (isinstance(c, WikiNode) and str(c.kind.name).startswith("LEVEL"))
    )
    out = Sounds()
    reader = _Reader(title, drop_labels, stats, out)
    for line in drop_boxes(expand_text(wtp, body).text).splitlines():
        if cfg.ipa in line:
            reader.ipa(line, cfg.ipa)
        elif cfg.audio in line:
            reader.audio(line)
        elif cfg.syllabification in line:
            _extend_unique(out.syllabification, _terms(line))
        elif cfg.homophones in line:
            reader.homophones(line)
        elif not any(m in line for m in cfg.ignored):
            text = plain_text(line)
            if text and not _GROUP_HEADER.match(text):
                stats["pronunciation.line.unknown"] += 1
                log.warning("%s: unknown pronunciation line: %.200s", title, text)
    return out


@dataclass
class _Reader:
    title: str
    drop: frozenset[str]
    stats: Counter[str]
    out: Sounds

    def _dropped(self, kind: str, labels: list[str]) -> bool:
        hit = sorted(self.drop.intersection(labels))
        for label in hit:
            self.stats[f"dropped.{kind}.{label}"] += 1
        return bool(hit)

    def ipa(self, line: str, marker: str) -> None:
        head, rest = line.split(marker, 1)
        dialects = _labels(head)
        start = 0
        for m in _IPA.finditer(rest):
            labels = _unique(dialects + _labels(rest[start : m.start()]))
            start = m.end()
            if self._dropped("pronunciation", labels):
                continue
            self._add(pb.Pronunciation(ipa=m.group(1), labels=labels))
        if _labels(rest[start:]):
            self.stats["pronunciation.qualifier.unattached"] += 1

    def _add(self, new: pb.Pronunciation) -> None:
        if new.labels:
            for seen in self.out.pronunciations:
                if seen.ipa == new.ipa and seen.labels:
                    _extend_unique(seen.labels, list(new.labels))
                    self.stats["pronunciation.merged"] += 1
                    return
        self.out.pronunciations.append(new)

    def audio(self, line: str) -> None:
        file = _AUDIO_FILE.search(line)
        if file is None:
            self.stats["pronunciation.audio.no_file"] += 1
            return
        name = file.group(1).strip()
        caption = m.group(1) if (m := _CAPTION.search(line)) else ""
        labels = _labels(caption)
        if self._dropped("audio", labels):
            return
        if mention := _MENTION.search(caption):
            spoken = plain_text(mention.group(1)).strip(_QUOTES)
        else:  # "Audio 2", or the caption itself: <cap:bać się>
            spoken = plain_text(_BRACKETED.sub("", caption)).strip(" :;")
            if config().caption.fullmatch(spoken):
                spoken = ""
        if any(a.file == name for a in self.out.audio):
            self.stats["pronunciation.audio.duplicate"] += 1  # {{audio}} beside a=
            return
        label = "" if spoken == self.title else spoken
        self.out.audio.append(pb.Audio(file=name, label=label, labels=labels))

    def homophones(self, line: str) -> None:
        for item in _NEXT_TERM.split(line):
            term = _TERM.search(item)
            if term is None:
                continue
            labels = _labels(item[: term.start()]) + _labels(item[term.end() :])
            if self._dropped("relation", labels):
                continue
            self.out.homophones.append(
                pb.Relation(
                    type=pb.Relation.Type.TYPE_HOMOPHONE,
                    term=plain_text(term.group(1)),
                    labels=_unique(labels),
                )
            )


def _labels(html: str) -> list[str]:
    return [t for m in _LABEL.findall(html) if (t := plain_text(m))]


def _terms(line: str) -> list[str]:
    return [t for m in _TERM.findall(line) if (t := plain_text(m))]


def _unique(values: list[str]) -> list[str]:
    return list(dict.fromkeys(values))


def _extend_unique(target: Any, values: list[str]) -> None:
    for value in values:
        if value not in target:
            target.append(value)


def frequency(
    title: str, calls: list[dict[str, str]], stats: Counter[str]
) -> pb.Frequency | None:
    """{{pl-freq 1990}} in Trivia: the best rank among the calls for this word (R6.13).

    A call whose `head=` is the title or the title with a part of speech ("co
    (pronoun)") counts the word; another head ("znaleźć się") is another term.
    """
    cfg = config().frequency
    best: pb.Frequency | None = None
    for args in calls:
        head = args.get(cfg["head"], "").strip()
        if (
            head
            and head != title
            and not re.fullmatch(rf"{re.escape(title)} \(.*\)", head)
        ):
            stats["frequency.other_term"] += 1
            continue
        rank, count = _int(args.get(cfg["rank"])), _int(args.get(cfg["count"]))
        if rank is None:
            stats["frequency.unparsed"] += 1
            continue
        if count is None:
            stats["frequency.no_count"] += 1  # the rank stands without it
            count = 0
        if best is None or rank < best.rank:
            best = pb.Frequency(rank=rank, count=count, source=cfg["source"])
    return best


def _int(value: str | None) -> int | None:
    value = (value or "").strip()
    return int(value) if value.isdigit() else None
