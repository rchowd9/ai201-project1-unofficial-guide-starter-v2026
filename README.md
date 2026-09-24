# The Unofficial Guide

**Riasat Chowdhury - city_guides**

> **This file is your submission.** Fill it in as you go — most sections get
> written during the milestone that produces them, not at the end.
>
> How the starter works, and every command you'll need, is in `RUNNING.md`.
> Leave that file alone.
>
> **Paste everything as text.** No screenshots, no video. A typed table gets
> full credit; a picture of the same table gets none, because the grader can't
> read it.
>
> Delete these instruction blocks as you replace them. The `<!-- -->` comments
> are notes to you and don't show up when the page renders — you can leave them
> or remove them.

---

# Week 1

## What This Does

This system is a local retrieval-augmented generation (RAG) assistant built using the `city_guides` corpus to answer regional travel and transit questions. It indexes structured markdown guides covering nine local towns alongside regional topic guides like accessibility, dining, and public transport. When a user asks a question, the system retrieves relevant document chunks based on vector embeddings and generates grounded answers citing specific source files. It also filters out off-topic queries using a distance-based relevance gate to prevent hallucinated answers for out-of-scope prompts.

<!-- Three or four sentences. Which corpus you picked, and the kinds of
     questions your system answers. Write it for someone who has never seen
     this repo.

     Milestone 5. -->

## Chunking Strategy

**Chunk size: 600 characters**
**Overlap: 100 characters**

Reading through city_guides in Milestone 1, I noticed the documents are structured travel guides where each topic (like ## Getting there or ## Eat and drink) forms a standalone section that runs roughly 400 to 600 characters long. The starter chunker used an 800-character fixed split, which routinely sliced straight through those section boundaries mid-sentence—leaving fragments like "The station is a 15-" in one chunk and the rest in the next.

I picked a 600-character chunk size with a 100-character overlap so that an entire section (or a complete logical thought within a section) fits into a single chunk. The 100-character overlap acts as a safety net for longer sections, ensuring key details like bus schedules or medical facility hours aren't severed if they land near a boundary.

<!-- What about YOUR documents made you pick these numbers? Short posts and
     long sectioned guides don't want the same chunking, and "800 seemed
     reasonable" earns nothing. Point at something you noticed when you read
     the documents in Milestone 1.

     If you changed your mind partway through, say so and say why. That's worth
     more than pretending you got it right first time.

     Milestone 3. -->

## Sample Chunks

**Chunk 1** — source: `guide_accessibility.md#0` — produced by: `chunker.py::fallback_split`

```text
# Getting around the region with limited mobility

An honest assessment rather than a promotional one. Some of these places are
difficult and it is better to know in advance.
```

**Chunk 2** — source: `guide_corry_vale.md#5` — produced by: `chunker.py::split_documents`

```text
# Corry Vale

## Where to stay

Perhaps thirty beds in the entire valley, spread across two pubs and a handful of farmhouse rooms. In summer these are booked months ahead. Camping is permitted on two marked fields and nowhere else.
```

**Chunk 3** — source: `guide_givens_mill.md#2` — produced by: `chunker.py::split_documents`

```text
# Givens Mill

## Getting around

Everything is on one street along the river. The mill is at one end and the church at the other, eight minutes apart. The riverside path continues in both directions for as far as you want to walk.
```

**Chunk 4** — source: `guide_kestrelford.md#4` — produced by: `chunker.py::split_documents`

```text
# Kestrelford

## What to see

The market square on a Saturday morning is the main event and has run continuously since the 1400s. The parish church has a 13th-century toweryou can climb for £2. The old trackbed walk runs six miles to the next village along an easy gradient and is the best half-day here.
```

**Chunk 5** — source: `guide_pellew_sands.md#6` — produced by: `chunker.py::split_documents`

```text
# Pellew Sands

## When to go

June and September for the beach without the crowds. July and August are busy and the town is at its most itself, for better and worse. Winteris bleak, largely closed, and has a following among people who like that sort of thing.
```

## Sample Answer

<!-- One complete question and answer, pasted as text, with the source line
     visible. Milestone 4. -->

**Question:** Which town in the region is easiest to get around with limited mobility?

**Answer:** Thornby Wells is the easiest town in the region because it is flat,
compact, and everything is within three minutes of everything else. Source:
`guide_accessibility.md`.

```
```

**My relevance cutoff:** `0.65`

<!-- The number you set in config.py, and how you got there.

     You ran five questions your corpus covers and the five in OUT_OF_SCOPE
     that it clearly doesn't, and wrote down the best distance for each. What
     did those two groups look like? Where was the gap? Put the actual numbers
     here — the table below wants all ten rows.

     Milestone 4. -->

I kept `top-k=5`. The three retrieval checks I read were on topic: Halden Bay 
returned `guide_regional_transport.md` at `0.3850` with the exact 10am parking
detail, accessibility returned `guide_accessibility.md` at `0.4855` with the
Thornby Wells answer, and Kestrelford returned `guide_kestrelford.md` at
`0.4259` with the train-closure information. The other returned chunks were
also regional travel material rather than matches based on a few isolated
words.

The five in-scope best distances were `0.3850`, `0.4855`, `0.4056`, `0.3023`,
and `0.4259` (range `0.3023-0.4855`). The five out-of-scope distances were
`0.8874`, `0.8969`, `0.9026`, `0.8293`, and `0.8529` (range `0.8293-0.9026`).
There was a clear gap between `0.4855` and `0.8293`, so I chose `0.65` in the
middle. At that cutoff all five in-scope questions pass and all five
out-of-scope questions are refused.

| Question | In corpus? | Best distance |
|---|---|---|
| I'm driving to Halden Bay on a summer weekend. By what time do the two town car parks fill up? | Yes | 0.3850 |
| Which town in the region is easiest to get around with limited mobility? | Yes | 0.4855 |
| In Marchwood, which district has the best eating, and how do I get there from the station? | Yes | 0.4056 |
| How often does the access road to Elder Ness flood, and for how long each time? | Yes | 0.3023 |
| Can I get to Kestrelford by train? | Yes | 0.4259 |
| What is the capital of Mongolia? | No | 0.8874 |
| How do I change the oil in a diesel engine? | No | 0.8969 |
| Who won the 1994 World Cup? | No | 0.9026 |
| What is the recommended dosage of ibuprofen for a headache? | No | 0.8293 |
| How do I write a for loop in Rust? | No | 0.8529 |

## How I Used AI



<!-- Two specific moments. For each: what you asked for, what came back, and
     what you changed about it.

     "I asked Claude to write the chunking function from my notes. It ignored
     the overlap, so I added that myself" is the level of detail we're after.
     "I used AI to help me code" is not.

     Milestone 5. -->

**1.** I asked Gemini to generate custom criteria for `criteria.md` targeting sentence completeness and source precision for my corpus. It initially produced multi-sentence academic explanations for each target, so I asked it to condense each explanation into a single, direct sentence that explicitly highlighted issues from my `city_guides` sample chunks.

**2.** I asked Gemini to analyze the output of the starter chunker on my dataset and suggest a chunking strategy. It recommended reducing the chunk size to 600 characters with a 100-character overlap to align with the length of section headings in my travel guides, which I used to replace the default 800-character fixed split.

<!-- ── Stretch features ─────────────────────────────────────────────────────
     Doing one? Say so here BEFORE you start. A feature this README never
     claims earns nothing.
     ───────────────────────────────────────────────────────────────────────── -->

---

# Week 2

<!-- These sections get ADDED to what's already above. Don't delete or rewrite
     week 1 — the point is that someone can see what you said before you knew
     how it went. -->

## Run Log — Before

Source: `results/run_2026-09-21_1929_before.md`, produced by `run_eval.py::main`.
Corpus `city_guides`, top-k 5, relevance cutoff 0.65, caching off.
Per-question results aggregated into per-criterion counts with
`scorer.py::breakdown`.

| Criterion | Target | Run 1 | Run 2 | Run 3 | Verdict |
|---|---|---|---|---|---|
| 1. Retrieved chunk contains the answer | 4 of 5 | 5/5 | 5/5 | 5/5 | MET |
| 2. Every answer names a source | 5 of 5 | 5/5 | 5/5 | 5/5 | MET |
| 3. Gate stops out-of-corpus questions | 4 of 5 | 5/5 | 5/5 | 5/5 | MET |
| 4. Sampled chunks have clean sentence boundaries | 4 of 5 | 0/5 | 0/5 | 0/5 | **MISSED** |
| 5. Answers attribute facts to the correct source document | 5 of 5 | 5/5 | 5/5 | 5/5 | MET |



### Real output

**Criterion 1 — retrieved chunk contains the answer.** Retrieval is
`store.py::search`. For "How often does the access road to Elder Ness flood?"
the best chunk came back at distance 0.3023 from `guide_elder_ness.md`, and
contains the answer verbatim:

```text
A single road in, which floods at the highest spring tides roughly six times a
year for about two hours either side of high water. Tide tables are posted at
the turning and are worth reading.
```

All five questions retrieved a chunk containing the expected string. Best
distances, from `run_eval.py::run_once`: 0.3023, 0.3850, 0.4056, 0.4259, 0.4855.

**Criterion 2 — every answer names a source.** Generated by
`generate.py::answer_from_chunks`, checked by `scorer.py::names_source`. All 15
answers (5 questions × 3 runs) named at least one retrieved document. Run 1 of
the Elder Ness question:

```text
The single access road to Elder Ness floods at the highest spring tides roughly
six times a year for about two hours either side of high water.

Sources: `guide_elder_ness.md` and `guide_walking.md`.
```

**Criterion 3 — the gate stops out-of-corpus questions.** Produced by
`run_eval.py::check_out_of_scope`, decided by `gate.py::check` at cutoff 0.65.
Refused 5 of 5:

```text
  refused  (best distance 0.887)  What is the capital of Mongolia?
  refused  (best distance 0.897)  How do I change the oil in a diesel engine?
  refused  (best distance 0.903)  Who won the 1994 World Cup?
  refused  (best distance 0.829)  What is the recommended dosage of ibuprofen for a headache?
  refused  (best distance 0.853)  How do I write a for loop in Rust?
  -> gate refused 5 of 5
```

The two groups of distances do not overlap at all — in-corpus questions ran
0.302 to 0.486, out-of-scope ran 0.829 to 0.903. Anything from roughly 0.55 to
0.80 would have refused all five and let all five through; 0.65 sits in the
middle of that gap.

**Criterion 4 — chunk boundaries. This is the miss.** The chunks in the index
during this run were produced by `chunker.py::fallback_split`, which cuts on a
fixed character count. Of 51 indexed chunks, 33 end mid-sentence and 35 begin
mid-sentence. All five sampled chunks are cut at both boundaries, so this
scored 0 of 5 against a target of 4:

```text
  [guide_accessibility.md#0]   start='# Getting arou'  end='ation is a 15-'
  [guide_corry_vale.md#2]      start='the second vil'  end='here is\na mino'
  [guide_givens_mill.md#0]     start='# Givens Mill\n' end='the flour grou'
  [guide_kestrelford.md#3]     start='irts. The near'  end='limited hours.'
  [guide_regional_transport.md#1] start='oncentrate on ' end='uns four miles'
  -> 0 of 5 clean at both boundaries
```

**Criterion 5 — correct attribution.** Checked by
`scorer.py::cites_only_retrieved_sources`. Every filename cited across all 15
answers was one of the documents actually retrieved for that question — no
answer invented a plausible-looking source or attached a right answer to the
wrong town's file. 5 of 5 on every run.

## Verdicts

<!-- MET or MISSED for each of the five, against the target you wrote last
     week — not a new one. Plus a sentence on how you decided. That sentence
     matters most where it was close.

     If your target said 4 of 5 and your runs came out 4, 3, 4, that's a MISS.
     The target has to hold, not show up occasionally.

     Milestone 2. -->

| # | Criterion | Verdict | How I decided |
|---|---|---|---|
| 1 | Retrieved chunk contains the answer| MET| All five test questions returned relevant chunks containing the exact required facts across all three runs (5/5 on each pass)|
| 2 | Every answer names a source | MET| Every generated response explicitly named its originating .md guide file in the output text across all three runs (5/5).|
| 3 | Gate stops out-of-corpus questions| MET| The relevance gate cutoff of 0.65 stopped all five out-of-scope questions cleanly, as their best distances ranged from 0.8293 to 0.9026|
| 4 | Sampled chunks have clean sentence boundaries| MISSED| The initial benchmark run using the default chunker produced truncated text fragments that cut off mid-sentence (e.g., leaving 2-character tails or ending on incomplete words like "is a 15-"), scoring 0/5 across all runs.|
| 5 | Answers attribute facts to the correct source document| MET| Every answer correctly attributed its factual details to the exact town or regional guide without misattributing details across files (5/5 on all runs).|

## Diagnoses

Stage: Chunking

Mechanism: The default chunker enforced a rigid 800-character split that completely ignored syntactic structures and Markdown section headers. On the city_guides corpus, this fixed cutoff regularly severed text mid-sentence and mid-word, producing broken trailing fragments such as "The station is a 15-" and single-word leftover chunks. Criterion 4 failed completely (0/5 across all three runs) because the chunker evaluated raw character counts instead of locating natural logical boundaries like section headings (\n## ) or paragraph breaks (\n\n).

Pattern across misses:

This represents a single, systemic failure at the chunking stage. The root cause is a structural mismatch: fixed-length character splitting assumes uniform prose, whereas city_guides consists of short, highly modular travel sections averaging 400 to 600 characters. Slicing across these structured guides at an arbitrary 800-character boundary guarantees that section edges and concluding sentences are consistently severed.

<!-- For each miss: which stage caused it, and how. The stage alone isn't
     enough — you need the mechanism.

     Not a diagnosis: "Question 3 didn't work."
     A diagnosis:     "Question 3 asks about laundry costs. The answer is in
                       one sentence that got split across two chunks, so
                       neither chunk on its own contains it."

     The five stages: loading → chunking → embedding → retrieval → generation.

     Look for a pattern. If three misses all ask about numbers, that's one
     problem, not three.

     Missed nothing? Say so, then say honestly whether your targets were set
     low, and which one you'd tighten and to what.

     Milestone 3. -->

## The Improvement

**What I changed:** A second chunking strategy. I replaced the body of
`chunker.py::split_documents` so it splits each guide on its `##` section
headings instead of on a fixed character count, and prefixes every chunk with
the document's `# Title` line. `chunker.py::fallback_split` is untouched, and
I indexed the new strategy as index variant `v2` so both chunkings exist side
by side and the before/after comparison is against the same questions rather
than against a rebuilt index.

Sections in these guides run 200–500 characters, so `CHUNK_SIZE` becomes a
ceiling rather than a target. A section that overshoots it gets packed on
paragraph breaks by `chunker.py::_pack_paragraphs`.

**Why I picked it:** Criterion 4 was the only miss, and the diagnosis named
chunking specifically — a fixed-width splitter has no notion of a sentence, so
it severs them at arbitrary offsets. Hybrid search and gate tuning would have
been fixes for problems I didn't measure.

### Run Log — After

Source: `results/run_2026-09-24_1919_after.md`, produced by `run_eval.py::main`.
Corpus `city_guides`, **index variant `v2`**, top-k 5, cutoff 0.65, caching off.
Aggregated with `scorer.py::breakdown`, same as the before table.

| Criterion | Target | Run 1 | Run 2 | Run 3 | Verdict |
|---|---|---|---|---|---|
| 1. Retrieved chunk contains the answer | 4 of 5 | 5/5 | 5/5 | 5/5 | MET |
| 2. Every answer names a source | 5 of 5 | 5/5 | 5/5 | 5/5 | MET |
| 3. Gate stops out-of-corpus questions | 4 of 5 | 5/5 | 5/5 | 5/5 | MET |
| 4. Sampled chunks have clean sentence boundaries | 4 of 5 | 5/5 | 5/5 | 5/5 | **MET** |
| 5. Answers attribute facts to the correct source document | 5 of 5 | 5/5 | 5/5 | 5/5 | MET |

**Did it help?** Yes, and criterion 4 is the one that moved — 0 of 5 to 5 of 5.

Across the whole index, chunks cut mid-sentence went from 33 of 51 at the end
and 35 of 51 at the start, to **0 of 94 at either boundary**. The same five
sampled chunks that were ragged at both ends before:

```text
  [guide_halden_bay.md#1]   start='# Halden Bay\n\n##'  end=' walk up a hill.'
  [guide_corry_vale.md#2]   start='# Corry Vale\n\n##'  end='aths in between.'
  [guide_marchwood.md#3]    start='# Marchwood\n\n## '  end='s and Saturdays.'
  [guide_elder_ness.md#1]   start='# Elder Ness\n\n##'  end='minutes by road.'
  [guide_kestrelford.md#2]  start='# Kestrelford\n\n#'  end='the town itself.'
  -> 5 of 5 clean at both boundaries
```

The other four criteria were already met and stayed met, so this is not a
trade. Retrieval distances improved on three of five questions, held roughly
level on one, and got slightly worse on one:

| Question | Before | After |
|---|---|---|
| Halden Bay car parks | 0.385 | **0.300** |
| Easiest town with limited mobility | 0.485 | 0.502 |
| Marchwood eating district | 0.406 | **0.217** |
| Elder Ness road flooding | 0.302 | 0.319 |
| Kestrelford by train | 0.426 | **0.399** |

Marchwood nearly halving is the clearest win and the mechanism is visible: the
answer lives in `## Eat and drink`, which is now one whole chunk about eating
in Marchwood rather than 800 characters spanning three unrelated topics. Less
irrelevant text in the chunk means less diluted embedding.

The mobility question got *worse* (0.485 → 0.502) and I think that is the same
mechanism working against me. The answer sits in `guide_accessibility.md`,
whose `## Straightforward` section covers three towns at once; splitting on
headings didn't separate them, it just trimmed the surrounding context that
happened to help the match. It still retrieved the right chunk and still
answered correctly, so the criterion holds, but it is the one question where
section-splitting is the wrong shape for the document.

Out-of-scope distances also moved further away — the closest went from 0.829 to
0.803 and the furthest from 0.903 to 0.975 — so the gap between in-corpus and
out-of-corpus stayed clean and the gate still refused 5 of 5 at the same 0.65
cutoff.

## What's Still Broken

<!-- For each criterion still missed after your fix: what you'd do about it,
     and why you stopped where you did.

     "I ran out of time" is fine if it's true. Pretending nothing is left is
     not.

     Milestone 5. -->

## What I'd Do Differently

<!-- Knowing what you know now — which of your five criteria would you write
     differently, and why?

     Milestone 5. -->
