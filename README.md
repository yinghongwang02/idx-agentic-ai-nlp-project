# IDX Exchange Agentic AI Project

## Overview

A production-style LangGraph-based real-estate copilot that combines
structured MLS retrieval, full-corpus semantic search, hybrid
recommendation, document-aware knowledge RAG, session memory, Fair Housing
guardrails, sold-comparable market analysis, and bounded parallel property
analysis.

The system supports three complementary user workflows:

1.  **Natural-language property search** --- converts conversational
    requirements into structured MLS retrieval and explainable
    market-aware recommendations.
2.  **Similar-home recommendation** --- combines structured property
    similarity with embedding-based semantic similarity, then validates
    recommended listings against recent sold comparables.
3.  **Knowledge Assistant** --- retrieves project-document evidence for
    real-estate concepts, MLS-field mappings, and handbook/reference
    questions, then generates a grounded answer from that context.

> This repository contains my individual project work for the IDX
> Exchange Summer 2026 internship. Internal MLS data is not included.

## Key Engineering Highlights

-   LangGraph orchestration with conditional query blocking and output
    screening
-   **Bounded parallel candidate analysis** using a reusable
    `PropertyAnalysisSubgraph` and up to four concurrent candidate analyses;
    benchmarked at **2.21× speedup** and **54.7% lower median candidate-analysis
    latency** while preserving deterministic Top-5 outputs
-   Natural-language intent parsing with hard constraints and soft
    preferences
-   Multi-turn session memory for progressive property-search refinement
-   Parameterized MySQL retrieval over active listings and recent sold
    comparables
-   Full-corpus OpenAI embedding pipeline with checkpoint/resume support
-   FAISS cosine-similarity retrieval over MLS listing embeddings
-   Hybrid search combining structured eligibility filtering with
    semantic reranking
-   Hybrid similar-home recommendation combining structured and semantic
    similarity
-   Sold-comparable validation with PPSF-based value signals and
    evidence-quality scoring
-   Deterministic Top-K ranking with stable listing-key tie-breaking
-   Typed, validated, immutable recommendation scoring configuration
-   Candidate-level failure isolation and structured error reporting
-   Retrieval evaluation comparing structured, keyword, semantic, and
    hybrid search
-   Document-aware knowledge RAG over project-maintained MLS mappings,
    real-estate terminology, California disclosure references, and handbook content
-   21-case knowledge-retrieval benchmark with source, section, content,
    cross-document, and unsupported-query coverage
-   Top-K sensitivity analysis selecting Top-6 retrieval after improving
    source recall from 94.4% to 100.0%
-   Lightweight grounded LLM generation with retrieved-source attribution
    and unsupported-query fallback
-   144 passing automated tests plus MySQL-backed smoke and performance
    validation

## Core MVP Performance --- Week 6

Week 6 established the core production-style MVP by restructuring
property analysis into reusable LangGraph subgraphs and adding bounded
parallel execution, deterministic ranking, configurable scoring,
regression validation, and quantitative performance benchmarking.

  Area                                     Result
  ---------------------------------------- -------------------------------------------
  Candidate pool                           Up to 50 listings
  Parallel execution                       Maximum 4 candidate analyses concurrently
  Sequential median latency                50.60 s
  Parallel median latency                  22.92 s
  Speedup                                  2.21×
  Median latency reduction                 54.7%
  Successful candidate analyses            50 / 50
  Candidate errors                         0
  Sequential/parallel output consistency   PASS
  Automated tests                          111 passed

The latency benchmark measures the **candidate property-analysis
stage**, not the full Streamlit request lifecycle. Both execution modes
used the same parsed intent and the same 50 candidate objects. Three
alternating sequential/parallel pairs were measured, and Top-5
recommendation outputs were checked after every pair.

Raw benchmark results are available in:

``` text
artifacts/benchmarks/candidate_parallel_baseline.csv
```

## Retrieval and Hybrid Recommendation --- Week 7

Week 7 extends the core LangGraph MVP with embedding-based retrieval and
a complementary similar-home recommendation workflow without changing
the existing property-analysis subgraph.

### Retrieval Pipeline

The system builds semantic representations for the active MLS corpus:

``` text
MLS Active Listings
        ↓
Canonical Listing Text
        ↓
EmbeddingProvider
        ↓
OpenAI Embeddings
        ↓
L2 Normalization
        ↓
FAISS IndexFlatIP
        ↓
Cosine-Similarity Retrieval
```

The embedding builder supports batched generation and checkpoint/resume
so full-corpus indexing can recover from interrupted API runs without
recomputing completed batches.

The current full-corpus index contains **52,794 active MLS listings with
52,794 distinct listing IDs**.

### Hybrid Property Search

Pure semantic retrieval captures qualitative preferences well but does
not guarantee hard MLS constraints such as city, budget, bedroom count,
or property type.

The hybrid retrieval path therefore separates eligibility from
preference ranking:

``` text
Natural-Language Request
        ↓
Structured MLS Constraints
        ↓
MySQL Candidate Retrieval
        ↓
Eligible Candidate Set
        ↓
Semantic Preference Embedding
        ↓
Embedding Similarity
        ↓
Semantic Reranking
        ↓
Top-K Results
```

Structured constraints determine which listings are eligible, while
semantic similarity determines which eligible listings best match softer
preferences such as modern design, natural light, open layouts, views,
or lifestyle characteristics.

### Retrieval Evaluation

A lightweight retrieval benchmark compares four retrieval strategies:

  Mode         Hard constraints   Soft semantic preferences
  ------------ ------------------ ---------------------------
  Structured   Yes                Limited
  Keyword      Yes                Exact lexical matching
  Semantic     No                 Strong
  Hybrid       Yes                Strong

Full-corpus evaluation showed the expected trade-off: pure semantic
retrieval captured qualitative intent but did not enforce structured MLS
constraints, while hybrid retrieval preserved hard-constraint compliance
and semantically reranked eligible candidates.

Across the three evaluation scenarios, hybrid retrieval maintained a
**100% hard-constraint pass rate** while achieving strong preference
coverage.

Raw evaluation output:

``` text
artifacts/benchmarks/retrieval_comparison_full.csv
```

### Hybrid Similar-Home Recommendation

Hybrid search answers **which homes satisfy a user's requirements**. The
similar-home recommendation workflow answers a different question:
**which active listings are most similar to a home the user already
likes**.

Given a target listing, the system applies property-type compatibility
rules, computes property-attribute and semantic similarity across the
full active-listing embedding corpus, and returns the highest-ranked
compatible listings. 

``` text
Target Listing
        ↓
Full Embedded Active-Listing Corpus
        ↓
Property-Type Compatibility
        ↓
Compatible Candidate Listings
        ↓
┌──────────────────────────┐
│ Property-Attribute       │
│ Similarity        max 60 │
└──────────────────────────┘
             +
┌──────────────────────────┐
│ Semantic Similarity      │
│ cosine similarity max 40 │
└──────────────────────────┘
        ↓
Hybrid Similarity Score
        ↓
Top-K Similar Listings
```

The property-attribute component emphasizes measurable property characteristics,
while the semantic component captures softer characteristics expressed
in listing text, including architectural style, renovation quality,
natural light, open layouts, views, and lifestyle features.

Property-type compatibility is enforced before final ranking so a
semantically similar but structurally incompatible listing does not
outrank an appropriate same-type property.

### Sold-Comparable Recommendation Validation

Similarity and market value are intentionally treated as separate
questions. After the Top-K similar active listings are selected, each
recommendation is independently validated against recent sold
comparables using the existing market-analysis components.

``` text
Top-K Similar Listing
        ↓
MarketAgent
        ↓
Recent Sold Comparables
        ↓
ComparableValueAgent
        ↓
Asking PPSF vs. Comparable Median PPSF
        ↓
Comparable Value + Evidence Quality
```

The validation layer reports two distinct signals:

  -----------------------------------------------------------------------
  Signal                              Meaning
  ----------------------------------- -----------------------------------
  Comparable Value                    How the asking price compares with
                                      recent sold-comparable evidence

  Evidence Quality                    How strongly the available
                                      comparable set supports that value
                                      conclusion
  -----------------------------------------------------------------------

Comparable evidence quality reflects factors such as match strictness,
comparable count, and usable PPSF coverage. This keeps recommendation
similarity separate from pricing evidence and makes the final
recommendation easier to inspect.

## Document-Aware Knowledge RAG --- Week 8

Week 8 adds a separate knowledge-RAG path for questions about real-estate
terminology, California agency/disclosure concepts, and project-specific MLS
field mappings. It does not replace property search: listing retrieval returns
properties, while knowledge retrieval returns explanatory document chunks.

### Knowledge Pipeline

The corpus currently uses the project-maintained `mls_field_mapping.md`,
real-estate terminology and law/reference documents, and the internship
handbook. Documents are chunked with source/section metadata, embedded through
the existing provider abstraction, L2-normalized, and indexed in FAISS.

The knowledge corpus currently includes:

- `docs/mls_field_mapping.md` — project-maintained mappings between raw MLS fields and project-facing field names.
- `docs/real_estate_terminology.md` — curated real-estate terminology and concept references used for document retrieval.
- `docs/real_estate_law.md` — curated California agency/disclosure reference material used for knowledge retrieval.
- `handbook.pdf` — internship handbook content used as an additional project knowledge source.

These documents are used as project knowledge sources; the project-maintained
MLS mapping is not presented as official IDX MLS documentation. 

``` text
Knowledge Documents
    ↓
Chunk + Source/Section Metadata
    ↓
Embeddings + FAISS
    ↓
Top-K Semantic Retrieval
    ↓
Grounded LLM Generation
    ↓
Answer + Retrieved Sources
```

`mls_field_mapping.md` is project-maintained documentation and is not presented
as official IDX MLS documentation.

### Retrieval Evaluation

A **21-case** benchmark contains 18 answerable questions and 3 unsupported
questions. Answerable cases cover terminology, California agency/disclosure
concepts, MLS field mappings, and cross-document retrieval. The evaluator
tracks Top-1 expected-source accuracy and Top-K expected-source, section, and
content hits, with simple failure diagnostics.

A Top-K sensitivity check produced:

| Metric | Top-4 | Top-6 |
| --- | ---: | ---: |
| Top-1 source accuracy | 88.9% | 88.9% |
| Expected-source hit rate | 94.4% | **100.0%** |
| Expected-section hit rate | 83.3% | **88.9%** |
| Expected-content hit rate | 94.4% | 94.4% |

Top-6 is the current default because it recovered the missing mapping document
for the cross-document list-to-close case. The unchanged Top-1 metric shows
that increasing K improved retrieval coverage rather than ranking quality.
Remaining misses are mainly Top-1 ambiguity, section-label alignment, and one
strict multi-term content expectation.

The three unsupported cases had Top-1 similarity scores of 0.4043, 0.4216,
and 0.3409. Because this sample is too small to calibrate a reliable cutoff,
the implementation does **not** hard-code a similarity threshold from these
values.

Top-6 is also the default used by the current knowledge-retrieval code and
Streamlit Knowledge Assistant. The evaluator keeps `--top-k` configurable so
the sensitivity result is reproducible without changing code:

``` bash
# Current/default evaluation depth
python -m src.dev_evaluate_knowledge_retrieval --top-k 6

# Reproduce the Top-4 comparison
python -m src.dev_evaluate_knowledge_retrieval --top-k 4
```

Representative benchmark questions include:

-   `What does DOM mean in real estate?`
-   `Which field stores days on market in california_sold?`
-   `Which MLS field maps to bedroom count?`
-   `Which california_sold fields would you use to calculate a list-to-close price ratio?`
-   `Does California allow dual agency?`
-   unsupported/current-information checks such as
    `What is the current average mortgage rate in California?`

### Grounded Generation

`GroundedKnowledgeAnswerer` reuses the existing `BaseLLMProvider` interface.
It sends the retrieved Top-6 chunks to the LLM with instructions to use only
that context and to abstain when the context is insufficient.

A five-question smoke test covered DOM terminology, a project MLS bedroom
mapping, a cross-document list-to-close field question, California dual
agency, and an unsupported current mortgage-rate question. The four supported
questions produced context-consistent answers; the unsupported question
returned the configured insufficient-information fallback instead of a
mortgage-rate estimate.

The reported source list represents **retrieved context**, not sentence-level
citation attribution. No reranker, RAGAS-style generation benchmark, or
calibrated confidence threshold is claimed in the current implementation.

## Architecture

### Core Property-Search Workflow

``` mermaid
flowchart TD
    U[User Query] --> QC[Query Compliance]

    QC -->|Red / blocked| REFUSAL[Return Refusal]
    REFUSAL --> END1([End])

    QC -->|Green or Yellow| INTENT[Intent Parsing + Session Memory]
    INTENT --> SEARCH[Structured MySQL Search]
    SEARCH --> CANDIDATES[Up to 50 Candidates]

    CANDIDATES --> PARALLEL[Bounded Candidate-Level Analysis<br/>ThreadPoolExecutor<br/>max_workers = 4]
    PARALLEL --> SUBGRAPH[Property Analysis Subgraph<br/>one invocation per listing]
    SUBGRAPH --> ERRORS[Isolate Candidate Errors]
    ERRORS --> RANK[Deterministic Top-K Ranking]

    RANK --> TOP5[Top 5 Recommendations]
    TOP5 --> EXPLAIN[Explanation Agent]
    EXPLAIN --> OC[Output Compliance]

    OC -->|Green| RESPONSE[Return Explanation]
    OC -->|Yellow| REWRITE[Return Safe Rewrite]
    OC -->|Red| BLOCK[Block Generated Output]

    RESPONSE --> END2([End])
    REWRITE --> END2
    BLOCK --> END2
```

### Property Analysis Subgraph

Each listing is analyzed through a reusable LangGraph subgraph:

``` mermaid
flowchart TD
    START([Listing + PropertyIntent])

    START --> MARKET[Market Context]
    START --> PREF[Soft Preference Match]

    MARKET --> VALUE[Comparable Value]
    MARKET --> NEG[Negotiation Analysis]

    PREF --> FANIN[Fan-In]
    VALUE --> FANIN
    NEG --> FANIN

    FANIN --> SCORE[Configurable Recommendation Scoring]
    CONFIG[RecommendationConfig] --> SCORE
    SCORE --> OUTPUT[RecommendationScore]
```

The system therefore uses two levels of parallelism:

1.  Up to four listing-level subgraphs run concurrently.
2.  Inside each subgraph, Market Context and Preference Match run
    independently, followed by parallel Comparable Value and Negotiation
    analysis.

For detailed workflow boundaries, concurrency design, failure handling,
state contracts, and limitations, see
[`docs/architecture.md`](docs/architecture.md).

### Retrieval and Similar-Home Recommendation Extension

Week 7 adds retrieval and similar-home recommendation capabilities
alongside the existing LangGraph property-search workflow rather than
replacing the reusable property-analysis subgraph.

``` mermaid
flowchart TD
    TARGET[Target Listing] --> GUARD[Property-Type Compatibility]
    GUARD --> STRUCT[Property-Attribute Similarity]
    GUARD --> SEM[Embedding Similarity]

    STRUCT --> HYBRID[Hybrid Similarity]
    SEM --> HYBRID

    HYBRID --> TOPK[Top-K Similar Active Listings]

    TOPK --> MARKET[Existing MarketAgent]
    MARKET --> COMPS[Recent Sold Comparables]
    COMPS --> VALUE[Existing ComparableValueAgent]

    VALUE --> VALIDATION[Comparable Value + Evidence Quality]
    TOPK --> OUTPUT[Recommendation Results]
    VALIDATION --> OUTPUT
```

This extension reuses the existing market and comparable-value logic,
avoiding a second overlapping market-analysis path.

## Parallel Execution and Failure Isolation

The parent workflow supports both execution modes:

``` text
Sequential mode
Candidate 1 → Candidate 2 → ... → Candidate 50

Parallel mode
Up to 4 candidate subgraphs execute concurrently
```

A candidate failure is recorded as:

``` text
{
    listing_key: ...,
    error: ...
}
```

Successful candidates continue to final ranking. A single malformed
listing or repository error therefore does not automatically discard the
entire batch.

## Performance Validation

The performance harness:

-   parses and searches once;
-   reuses the same 50 candidate objects in both modes;
-   performs an unmeasured warm-up;
-   runs three alternating sequential/parallel pairs;
-   records successful and failed candidate counts;
-   verifies Top-5 output consistency after every pair;
-   reports median latency rather than a single run.

Measured runs:

``` text
Sequential: 52.13 s, 50.60 s, 50.59 s
Parallel:   23.12 s, 22.92 s, 22.36 s
```

Result:

``` text
50.60 s → 22.92 s
54.7% lower median candidate-analysis latency
2.21× speedup
0 candidate errors
Identical sequential/parallel recommendation outputs
```

The measured improvement reflects the combined effect of bounded
candidate-level concurrency and parallel branches within the
listing-level subgraph. The benchmark does not attempt to attribute the
speedup to each layer independently.

## Interactive Streamlit Application

The Streamlit application now exposes three complementary tabs: **Property Search**, 
**Similar Home Recommendation**, and **Knowledge Assistant**.

### Property Search

-   Natural-language MLS search with hard constraints and soft preferences
-   Multi-turn session memory and search history
-   Fair Housing query/output safeguards
-   MySQL-backed candidate retrieval
-   Bounded parallel property analysis
-   Market-aware scoring and explainable Top-5 recommendations

### Similar Home Recommendation

-   Target-listing lookup by MLS listing ID
-   Property-attribute + semantic hybrid similarity
-   Full-corpus embedding coverage
-   Top-K similar active listings
-   Sold-comparable validation and PPSF-based evidence
-   Expandable similarity and market-evidence breakdowns

### Knowledge Assistant

The Week 8 demo exposes the document-aware RAG path directly in Streamlit.
Users can enter a project-knowledge question, choose the number of retrieved
chunks, inspect the grounded answer, and expand the retrieved evidence with
source, section, chunk ID, and similarity score. The sidebar also keeps a
separate **Knowledge RAG History**.

The current code/demo defaults to **Top-6** retrieved chunks, matching the
retrieval sensitivity result. The UI control remains adjustable for interactive
inspection; quantitative Top-4/Top-6 comparisons should be reproduced with the
CLI evaluator rather than inferred from one demo query.

Recommended demo questions:

-   **Terminology:** `What does DOM mean in real estate?`
-   **Project field mapping:** `Which field stores days on market in california_sold?`
-   **Project field mapping:** `Which MLS field maps to bedroom count?`
-   **Cross-document:** `Which california_sold fields would you use to calculate a list-to-close price ratio?`
-   **California agency:** `Does California allow dual agency?`
-   **Handbook:** `What does the handbook say about RAG?`
-   **Unsupported/fallback check:** `What is the current average mortgage rate in California?`

The first five categories overlap with the retrieval/generation evaluation and
are useful for demonstrating terminology retrieval, project-specific mappings,
cross-document evidence, legal/reference retrieval, and abstention behavior.
The handbook question is useful as an interactive corpus demo.

The three UI paths intentionally remain separate:

-   property search answers **what satisfies the user's requirements**;
-   similar-home recommendation answers **what resembles a selected property**;
-   the Knowledge Assistant answers **what the project knowledge documents
    support**.

The workflow object is stored in the Streamlit session so conversational
property-search criteria persist across turns. Knowledge questions maintain
their own RAG history in the sidebar.


## Technology Stack

Python 3.10, LangGraph, LangChain, OpenAI embeddings/LLM providers, FAISS,
NumPy, Pydantic, MySQL, Streamlit, Pytest, and `ThreadPoolExecutor`.

## Local Setup

``` bash
python -m venv .venv
# Windows: .venv\Scripts\activate
pip install -r requirements.txt
python -m streamlit run src/app/streamlit_app.py
```

Create `.env` from `.env.example` and configure local MySQL and model-provider
credentials. Secrets and internal MLS data must not be committed.

## Testing and Validation

``` bash
pytest -v
python -m src.dev_evaluate_retrieval
python -m src.dev_evaluate_knowledge_retrieval              # default Top-6
python -m src.dev_evaluate_knowledge_retrieval --top-k 6      # explicit current setting
python -m src.dev_evaluate_knowledge_retrieval --top-k 4      # sensitivity comparison
python -m src.dev_test_grounded_knowledge
python -m src.dev_benchmark_candidate_parallel
```

Current automated suite: **144 passing tests**. Validation includes workflow
routing, compliance, session memory, repository/query behavior, market and
recommendation scoring, sequential/parallel consistency, semantic/hybrid
listing retrieval, similar-home scoring, knowledge retrieval evaluation, and
grounded-generation smoke testing.

## Repository Structure

``` text
src/
├── agents/          # Workflow and market-analysis agents
├── app/             # Streamlit application
├── embeddings/      # Listing embedding utilities
├── evaluation/      # Retrieval evaluation cases and metrics
├── knowledge/       # Grounded knowledge answering
├── memory/          # Multi-turn session memory
├── providers/       # LLM and embedding provider abstractions
├── recommendation/  # Ranking, similarity, scoring, explanation
├── search/          # Structured, semantic, hybrid, knowledge retrieval
└── workflow/        # Parent graph and property-analysis subgraph

docs/
├── architecture.md
├── mls_field_mapping.md
├── real_estate_terminology.md
└── real_estate_law.md

artifacts/
├── benchmarks/
├── embeddings/
└── knowledge/
```

Internal MLS datasets are excluded; public demos should use synthetic data.

## Project Status

Week 6 established the tested LangGraph MVP with bounded parallel property
analysis and a measured **2.21×** candidate-analysis speedup (**54.7%** lower
median latency). Week 7 added the **52,794-listing** embedding index, semantic
and hybrid retrieval, similar-home recommendation, sold-comp validation, and
the expanded Streamlit workflow.

Week 8 adds document-aware knowledge RAG and exposes it through a third
Streamlit **Knowledge Assistant** tab with adjustable retrieval depth,
grounded answers, expandable evidence, and separate RAG history. On the
current 18 answerable-case benchmark, Top-6 retrieval reached **100.0%
expected-source hit rate**; a five-question grounded-generation smoke test
also demonstrated unsupported-query abstention. These are project-benchmark
results, not claims of general production accuracy.
