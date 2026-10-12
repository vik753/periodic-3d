"""Find vocabulary terms in English source texts (task U.2).

A source string is split into sentences. A sentence is skipped when it speaks about the
past, a proposal, a study or a ban ("formerly", "not registered", "has been proposed"):
the site shows only uses that a source states as current. Inside a sentence every term
pattern is searched; a match that overlaps a match of a higher-priority term is dropped.
"""

from __future__ import annotations

import html
import re
from dataclasses import dataclass, field

from .vocabulary import ROLE_TERMS, TERMS, Term

# Words that make a sentence unusable as evidence of a current use.
NEGATIVE = re.compile(
    r"""
    formerly | \bformer\b | /former | in\ the\ past | no\ longer | previously
    | not\ (?:currently\ |presently\ |now\ |yet\ |commercially\ )?(?:used|registered|approved|marketed|available|
        produced|manufactured|sold|authori[sz]ed)
    | never\ (?:been\ )?(?:used|marketed|commerciali[sz]ed)
    | discontinued | withdrawn | banned | obsolete | (?:was|were)\ once | once\ used | historically
    | phased[ -]out | (?:has|have)\ been\ replaced | replaced\ by | superseded
    | labels?\ match | srp: | pc\ code | pesticide\ code | no\ (?:longer\ )?(?:registered|registrations?)
    | (?:has|have)\ been\ (?:proposed|suggested|investigated|studied|tested|evaluated|explored|reported\ as)
    | (?:is|are)\ being\ (?:investigated|studied|tested|evaluated|developed|explored)
    | potential(?:ly)?\ (?:use|uses|useful|application|applications|candidate)
    | may\ (?:be|have|also\ be)\ (?:used|useful|applied) | could\ be\ (?:used|applied) | might\ be
    | proposed\ (?:for|as)
    | no\ commercial\ (?:uses?|applications?) | (?:has|have)\ been\ widely\ (?:used|employed) | prohibited
    | (?:is|are)\ of\ (?:interest|potential) | (?:is|are)\ expected | will\ (?:be|become) | would\ be
    | experimental(?!\ animals) | investigational | under\ (?:investigation|development|study) | in\ development
    | clinical\ trials? | not\ approved | illegal | illicit | (?:drugs?\ of|for)\ abuse | recreational | abused
    | poisoning\ by | toxic\ effects? | exposure\ to | exposed\ to | occupational\ exposure | adverse
    | transformation\ products? | metabolites? | degradation\ products? | impurit(?:y|ies) | by-?products?\ of
    | contaminants? | residues? | (?:was|were|had\ been)\ (?:used|employed|utili[sz]ed|applied)
    | (?:during|in)\ (?:world\ war|the\ 19\d\ds|the\ 18\d\ds|ancient)
    """,
    re.IGNORECASE | re.VERBOSE,
)
# Past tense is allowed for yearly reports ("…were used in building construction, 42%").
NEGATIVE_PAST_OK = re.compile(
    NEGATIVE.pattern.replace(r"| (?:was|were|had\ been)\ (?:used|employed|utili[sz]ed|applied)", ""),
    re.IGNORECASE | re.VERBOSE,
)
# A sentence of a mixed source (toxicology databases) must say that something is used.
CUE = re.compile(
    r"\b(?:use[sd]?|using|usage|employ(?:s|ed|ing)?|appli(?:ed|cations?)|utili[sz](?:e|es|ed|ing|ation)|serves?\ as"
    r"|ingredients?|components?|additives?|manufactur\w*|production\ of|produce[sd]?|to\ make|making"
    r"|agents?|treatment\ of|treat(?:s|ed|ing)?|added\ to|for\ the|found\ in\ (?:products|consumer))\b",
    re.IGNORECASE,
)
# Strings without information about uses (not negative either).
UNINFORMATIVE = re.compile(
    r"^\s*(?:not\ known\ or\ reasonably\ ascertainable|other(?:\ \(specify\))?|others?|safer\ chemical\ classes.*"
    r"|(?:green|yellow)\ (?:circle|half-circle|triangle).*|cir\ ingredient:.*|jecfa\ functional\ classes"
    r"|epa\ safer\ chemical\ functional\ use\ classes|fda\ approved\ animal\ drug\ products\ \(green\ book\)"
    r"|active\ ingredients|cir\ \(cosmetic\ ingredient\ review\)|eu\ pesticides\ database:.*|cosmetics\ ingredient"
    r"|pfas|non-polymer\ pfas|uses|consumer\ uses|industry\ uses)\s*$",
    re.IGNORECASE | re.VERBOSE,
)
_REFERENCES = re.compile(
    r"\[(?:ref|category|source)[^\]]*\]|\[[A-Z][A-Za-z&.,' ]{1,40}(?:,\ p\.\ ?\d+)?\]|\(L\d+\)|\(Ref\.[^)]*\)",
    re.VERBOSE,
)
# Haz-Map "[Category: …]" lines name activities with exposure, not uses.
EXPOSURE = re.compile(r"\[Category:", re.IGNORECASE)
_SPLIT = re.compile(r"(?<=[.!?])\s+(?=[A-Z(\"'])|\s*[;|▸•]\s*|\s*\n\s*|\s+->\s+")
# "…in the production of dyes, insecticides" (the text before a match): the substance goes
# into the product; it is not the product.
MADE_FROM = re.compile(
    r"(?:production|manufactur\w*|synthesis|preparation|making|formulation) of (?:(?:the|other|various|many|some) )?"
    r"(?:[\w()/-]+,? (?:and |or )?){0,12}$"
    r"|(?:to|used to|help) (?:make|produce|manufacture|synthesi[sz]e) (?:[\w()/-]+,? (?:and |or )?){0,12}$"
    r"|(?:making|producing|manufacturing|synthesi[sz]ing) (?:[\w()/-]+,? (?:and |or )?){0,12}$"
    r"|(?:inert |inactive |other )?(?:ingredients?|components?|carriers?|diluents?|solvents?|vehicles?|excipients?)"
    r" (?:in|of|for) (?:[\w()/-]+,? (?:and |or )?){0,6}$"
    r"|(?:in|for) (?:the )?formulations? (?:of )?(?:[\w()/-]+,? (?:and |or )?){0,6}$",
    re.IGNORECASE,
)
_SPACES = re.compile(r"\s+")
_SENTENCE_END = re.compile(r"[a-z)][.!?](?:\s|$)")
LABEL_MAX = 160
_BOUNDARY = r"(?<![a-z0-9]){}(?![a-z0-9])"


def clean(text: str) -> str:
    text = html.unescape(text).replace("_", " ").replace(" ", " ")
    return _SPACES.sub(" ", _REFERENCES.sub(" ", text)).strip()


def sentences(text: str) -> list[str]:
    return [part.strip(" .,:") for part in _SPLIT.split(clean(text)) if len(part.strip(" .,:")) >= 3]


@dataclass(frozen=True)
class Context:
    """How to read the strings of one source under one heading."""

    spheres: frozenset[str] | None = None  # allowed spheres; None: all
    categories: bool = False  # the strings are category labels: category patterns apply
    cue: bool = False  # each sentence must contain a use cue
    default: str | None = None  # term for an informative string that matched nothing
    past_ok: bool = False
    labels_only: bool = False  # read only short label strings ("Vasodilator Agents"), not study texts
    fixed: bool = False  # every informative string means the default term, patterns are not used


@dataclass
class Hit:
    term: str
    sentence: str | None  # None: the context default


@dataclass
class _Compiled:
    term: Term
    general: re.Pattern[str] | None
    category: re.Pattern[str] | None


def _compile(patterns: tuple[str, ...]) -> re.Pattern[str] | None:
    if not patterns:
        return None
    return re.compile(_BOUNDARY.format("(?:" + "|".join(f"(?:{p})" for p in patterns) + ")"), re.IGNORECASE)


@dataclass
class Matcher:
    terms: tuple[Term, ...] = TERMS
    _compiled: list[_Compiled] = field(init=False)

    def __post_init__(self) -> None:
        ordered = sorted(self.terms, key=lambda term: -term.priority)
        self._compiled = [_Compiled(t, _compile(t.patterns), _compile(t.category_patterns)) for t in ordered]

    def sentence_terms(self, sentence: str, context: Context) -> list[str]:
        accepted: list[tuple[int, int, int]] = []  # start, end, priority
        found: list[str] = []
        for item in self._compiled:
            term = item.term
            if context.spheres is not None and term.sphere not in context.spheres:
                continue
            patterns = [item.general]
            if context.categories:
                patterns.append(item.category)
            hit = False
            for pattern in patterns:
                if pattern is None:
                    continue
                for match in pattern.finditer(sentence):
                    start, end = match.span()
                    if any(s < end and start < e and p > term.priority for s, e, p in accepted):
                        continue
                    if term.id in ROLE_TERMS and MADE_FROM.search(sentence[max(0, start - 200) : start]):
                        continue
                    accepted.append((start, end, term.priority))
                    hit = True
            if hit and term.id not in found:
                found.append(term.id)
        return found

    def find(self, strings: list[str], context: Context) -> list[Hit]:
        """Terms in the strings of one annotation, with the sentence that supports each."""
        negative = NEGATIVE_PAST_OK if context.past_ok else NEGATIVE
        hits: list[Hit] = []
        informative = 0
        for text in strings:
            if EXPOSURE.search(text):
                continue
            if context.labels_only and (len(text) > LABEL_MAX or _SENTENCE_END.search(text)):
                continue
            for sentence in sentences(text):
                if UNINFORMATIVE.match(sentence):
                    informative += 1
                    continue
                if negative.search(sentence):
                    continue
                informative += 1
                if context.fixed:
                    continue
                if context.cue and not CUE.search(sentence):
                    continue
                hits += [Hit(term, sentence) for term in self.sentence_terms(sentence, context)]
        if not hits and informative and context.default:
            hits.append(Hit(context.default, None))
        return hits
