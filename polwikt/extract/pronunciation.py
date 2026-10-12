"""IPA from a Pronunciation section's expanded {{pl-pr}} / {{IPA}} lines (R6.1).

M5 takes what an entry needs to show a pronunciation: each IPA transcription with the
labels on its line ("Chełmno-Dobrzyń"). Lines labelled with a `drop_labels` entry
(the `mp=` Middle Polish line, R6.6a) are dropped and counted. Audio, rhymes,
syllabification and homophones are M9.
"""

from __future__ import annotations

import re
from collections import Counter

from wikitextprocessor import WikiNode

from polwikt.expand.run import expand_text
from polwikt.expand.wtp import PolwiktWtp
from polwikt.parse.text import plain_text
from polwikt.proto import polwikt_pb2 as pb

_IPA_LINE = "International Phonetic Alphabet|IPA]]"
_IPA = re.compile(r'<span class="IPA[^"]*">([/\[][^<]*[/\]])</span>')
_LABEL = re.compile(r'<span class="ib-content[^"]*">(.*?)</span>')


def pronunciations(
    wtp: PolwiktWtp,
    section: WikiNode,
    drop_labels: frozenset[str],
    stats: Counter[str],
) -> list[pb.Pronunciation]:
    body = "".join(
        wtp.node_to_wikitext(c)
        for c in section.children
        if not (isinstance(c, WikiNode) and str(c.kind.name).startswith("LEVEL"))
    )
    out: list[pb.Pronunciation] = []
    for line in expand_text(wtp, body).text.splitlines():
        if _IPA_LINE not in line:
            continue
        labels = [plain_text(m) for m in _LABEL.findall(line.split(_IPA_LINE, 1)[0])]
        dropped = drop_labels.intersection(labels)
        ipas = _IPA.findall(line)
        if dropped:
            for label in sorted(dropped):
                stats[f"dropped.pronunciation.{label}"] += len(ipas)
            continue
        out.extend(pb.Pronunciation(ipa=ipa, labels=labels) for ipa in ipas)
    return out
