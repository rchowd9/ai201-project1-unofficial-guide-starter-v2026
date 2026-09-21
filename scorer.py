"""
Deciding what counts as a correct answer.

`run_eval.py` finds this file automatically and calls `judge` once per run. It
expects exactly one thing:

    judge(question, expects, answer, results) -> bool

Everything else in here exists to make that one boolean defensible.

─── The judgment calls, stated plainly ──────────────────────────────────────

Three decisions had to be made before any of this could be written down, and
each one could reasonably have gone the other way:

1. `judge` scores THE ANSWER, not the retrieval. A run passes when the answer
   the model wrote contains the `expects` string. Criterion 1 in criteria.md is
   about whether the *retrieved chunks* contain the answer, which is a
   different question — retrieval can succeed while generation fumbles. That's
   `retrieved_contains_answer` below, and `breakdown` reports both so a miss
   can be traced to a stage.

2. A refusal counts as a FAIL, not as a blank. All five test questions are
   covered by the corpus, so "I don't have enough information" is the system
   being wrong about its own knowledge. Refusals are only correct for the
   OUT_OF_SCOPE list, which `run_eval.py` scores separately through the gate.

3. Matching is normalized, not literal. `expects` is "10am" but a model may
   write "10 a.m." or "10:00 AM", and all three are the same correct answer.
   Scoring those as failures would measure the model's punctuation rather than
   its accuracy. `_surface_forms` handles the variation; `python scorer.py`
   runs the self-test that shows what it does and does not accept.

What normalization deliberately does NOT do is accept a paraphrase. If an
answer says "late morning" instead of "10am", that fails. The `expects`
strings were chosen in week 1 to be near-verbatim from the corpus, so a
grounded answer should reproduce them.
"""

import re
import unicodedata

# Both refusal paths. `gate.REFUSAL` is the hard refusal, returned before the
# model is ever called. The second is the model refusing on its own, which
# GROUNDING_INSTRUCTION in generate.py explicitly asks it to do. Either way the
# system declined to answer, so both are matched on the shared phrase rather
# than importing gate (which would pull in chromadb just to read a string).
REFUSAL_MARKERS = (
    "don't have enough information",
    "do not have enough information",
    "dont have enough information",
)

# Number words the guides actually use, both directions. "six times a year"
# should match an answer that writes "6 times a year".
_NUMBER_WORDS = {
    "one": "1", "two": "2", "three": "3", "four": "4", "five": "5",
    "six": "6", "seven": "7", "eight": "8", "nine": "9", "ten": "10",
    "eleven": "11", "twelve": "12",
}
_WORD_NUMBERS = {digit: word for word, digit in _NUMBER_WORDS.items()}

_CLOCK = re.compile(r"\b(\d{1,2})\s*(am|pm)\b")


def _normalize(text: str) -> str:
    """
    Lowercase, fold unicode, drop periods, collapse whitespace.

    Dropping periods is what turns "a.m." into "am" and "1963." into "1963".
    Curly apostrophes and en-dashes get folded too, because models emit them
    and the corpus does not.
    """
    text = unicodedata.normalize("NFKC", text)
    text = text.replace("’", "'").replace("‘", "'")
    text = text.replace("“", '"').replace("”", '"')
    text = text.replace("–", "-").replace("—", "-")
    text = text.lower()
    text = text.replace(".", "")
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def _fold(text: str) -> str:
    """
    Lowercase and fold unicode, but KEEP periods.

    Filenames need this. `_normalize` drops periods to make "a.m." match "am",
    which also turns "guide_halden_bay.md" into "guide_halden_bay md" and
    makes the extension impossible to match on.
    """
    text = unicodedata.normalize("NFKC", text)
    return text.lower()


def _filenames(text: str) -> set[str]:
    """Every .md/.txt filename mentioned in `text`."""
    return set(re.findall(r"[\w/-]+\.(?:md|txt)", _fold(text)))


def _tight(text: str) -> str:
    """
    Normalized, with spaces removed entirely.

    This is what makes "10am" match "10 am". Matching on the tight form alone
    would be too loose for prose, so `matches` tries the spaced form first and
    only falls back to tight for short, wordless expectations.
    """
    return _normalize(text).replace(" ", "")


def _surface_forms(expects: str) -> set[str]:
    """
    The ways a correct answer might spell `expects`.

    Kept deliberately small and mechanical: clock times, and numbers written
    as words instead of digits. It does not attempt synonyms.
    """
    base = _normalize(expects)
    forms = {base}

    # "10am" also matches "10 am", "10:00am", "10 o'clock".
    for hour, meridiem in _CLOCK.findall(base):
        forms.update(
            {
                f"{hour}{meridiem}",
                f"{hour} {meridiem}",
                f"{hour}:00{meridiem}",
                f"{hour}:00 {meridiem}",
                f"{hour} o'clock",
                f"{hour} oclock",
            }
        )

    # "six times a year" <-> "6 times a year", and the reverse.
    for word, digit in _NUMBER_WORDS.items():
        if re.search(rf"\b{word}\b", base):
            forms.add(re.sub(rf"\b{word}\b", digit, base))
    for digit, word in _WORD_NUMBERS.items():
        if re.search(rf"\b{digit}\b", base):
            forms.add(re.sub(rf"\b{digit}\b", word, base))

    return {f for f in forms if f}


def matches(expects: str, text: str) -> bool:
    """True if `text` contains `expects` in any accepted surface form."""
    if not expects:
        return False

    haystack = _normalize(text)
    forms = _surface_forms(expects)

    if any(form in haystack for form in forms):
        return True

    # Fall back to the space-stripped comparison only for short expectations
    # with no word characters beyond a unit — "10am", "8:30". On a phrase like
    # "six times a year" this would risk matching across unrelated words.
    if len(_normalize(expects)) <= 8:
        tight_haystack = _tight(text)
        return any(_tight(form) in tight_haystack for form in forms)

    return False


def is_refusal(answer: str) -> bool:
    """True if the system declined to answer, by either route."""
    normalized = _normalize(answer)
    return any(marker.replace(".", "") in normalized for marker in REFUSAL_MARKERS)


# ─── The individual criteria ─────────────────────────────────────────────────
# Each one is a separate function so `breakdown` can report them independently
# and a miss can be pinned to a stage. run_eval.py only calls `judge`.


def retrieved_contains_answer(expects: str, results) -> bool:
    """
    Criterion 1: did retrieval put the answer in front of the model at all?

    Scored against the chunk text, so this is true even when the model then
    failed to use it. That separation is what makes a diagnosis possible:
    retrieval miss and generation miss look identical from the answer alone.
    """
    return any(matches(expects, r.text) for r in results)


def answer_is_correct(expects: str, answer: str) -> bool:
    """The answer is not a refusal and contains what a right answer needs."""
    if is_refusal(answer):
        return False
    return matches(expects, answer)


def names_source(answer: str, results) -> bool:
    """
    Criterion 2: does the answer name at least one source document?

    Looks for any .md or .txt filename, then confirms it was one of the
    documents actually retrieved — an answer that cites a plausible-looking
    filename nobody handed it is worse than one that cites nothing.
    """
    cited = _filenames(answer)
    if not cited:
        return False
    retrieved = {_fold(r.source) for r in results}
    return bool(cited & retrieved)


def cites_only_retrieved_sources(answer: str, results) -> bool:
    """
    Criterion 5: every filename the answer cites was actually retrieved.

    criteria.md makes the case for this one: several guides carry an identical
    "Practical notes" block, so a right answer attached to the wrong town's
    filename is actively misleading travel advice.
    """
    cited = _filenames(answer)
    if not cited:
        return False
    retrieved = {_fold(r.source) for r in results}
    return cited.issubset(retrieved)


def judge(question: str, expects: str, answer: str, results) -> bool:
    """
    The headline verdict `run_eval.py` writes into the Run columns.

    Decision 1 in the module docstring: this scores the answer, so a run
    passes when the model wrote something correct. Source-naming is tracked
    separately rather than folded in here, because an answer that is right but
    uncited is a different failure from one that is simply wrong, and the run
    log is more useful when those don't collapse into the same blank cell.
    """
    return answer_is_correct(expects, answer)


def breakdown(question: str, expects: str, answer: str, results) -> dict:
    """
    Every criterion for one run, for aggregating the per-criterion table the
    README asks for. `run_eval.py` doesn't call this — you do.
    """
    return {
        "retrieved_contains_answer": retrieved_contains_answer(expects, results),
        "answer_is_correct": answer_is_correct(expects, answer),
        "names_source": names_source(answer, results),
        "cites_only_retrieved_sources": cites_only_retrieved_sources(answer, results),
        "refused": is_refusal(answer),
    }


# ─── Self-test ───────────────────────────────────────────────────────────────
# `python scorer.py` checks the matcher against the cases that motivated it.
# Worth running before trusting a run log: a scorer with a bug in it produces
# confident numbers that are wrong, which is the one outcome worse than blanks.

_CASES = [
    # (expects, text, should_match)
    ("10am", "The lots fill by 10am on summer weekends.", True),
    ("10am", "They fill by 10 a.m. (guide_halden_bay.md)", True),
    ("10am", "Arrive before 10:00 AM to be safe.", True),
    ("10am", "They fill up in the late morning.", False),
    ("six times a year", "The road floods about six times a year.", True),
    ("six times a year", "It floods roughly 6 times a year, per guide_walking.md.", True),
    ("six times a year", "The road floods at spring tides.", False),
    ("Thornby Wells", "Thornby Wells is the easiest — flat and compact.", True),
    ("Thornby Wells", "thornby wells, according to guide_accessibility.md", True),
    ("Thornby Wells", "Marchwood has level tram boarding.", False),
    ("Northgate", "The best eating is in the Northgate district.", True),
    ("1963", "No station — the line closed in 1963.", True),
    ("1963", "There is no railway station at Kestrelford.", False),
]


def _self_test() -> int:
    failures = 0

    for expects, text, want in _CASES:
        got = matches(expects, text)
        if got != want:
            failures += 1
            print(f"  FAIL  matches({expects!r}, {text!r}) -> {got}, wanted {want}")

    # A refusal must fail the judge even when it happens to contain the string.
    refusal = "I don't have enough information about that."
    if not is_refusal(refusal):
        failures += 1
        print(f"  FAIL  is_refusal({refusal!r}) -> False")
    if answer_is_correct("10am", refusal):
        failures += 1
        print("  FAIL  a refusal scored as correct")

    # Source citation. These caught a real bug: `_normalize` strips periods to
    # make "a.m." match "am", which also destroys the ".md" extension, so
    # filenames have to be pulled out with `_fold` instead.
    class _R:
        def __init__(self, source):
            self.source = source
            self.text = ""

    retrieved = [_R("guide_halden_bay.md"), _R("guide_seasons.md")]
    source_cases = [
        # (answer, names_source, cites_only_retrieved_sources)
        ("They fill by 10am (guide_halden_bay.md).", True, True),
        ("Per guide_halden_bay.md and guide_seasons.md, before 10am.", True, True),
        # Cites something real plus something never retrieved.
        ("See guide_halden_bay.md and guide_kestrelford.md.", True, False),
        # Cites only a document that was never retrieved.
        ("According to guide_kestrelford.md, before 10am.", False, False),
        # No citation at all.
        ("The lots fill by 10am on summer weekends.", False, False),
    ]
    for answer, want_names, want_only in source_cases:
        if names_source(answer, retrieved) != want_names:
            failures += 1
            print(f"  FAIL  names_source({answer!r}) -> {not want_names}")
        if cites_only_retrieved_sources(answer, retrieved) != want_only:
            failures += 1
            print(f"  FAIL  cites_only_retrieved_sources({answer!r}) -> {not want_only}")

    print("scorer self-test:", "all passed" if not failures else f"{failures} failed")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(_self_test())
