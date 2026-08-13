# IDX Exchange Agentic AI Project

## Overview

A production-style LangGraph-based real-estate copilot that combines
structured MLS retrieval, full-corpus semantic search, hybrid
recommendation, session memory, Fair Housing guardrails, sold-comparable
market analysis, and bounded parallel property analysis.

The system supports two complementary user workflows:

1.  **Natural-language property search** --- converts conversational
    requirements into structured MLS retrieval and explainable
    market-aware recommendations.
2.  **Similar-home recommendation** --- combines structured property
    similarity with embedding-based semantic similarity, then validates
    recommended listings against recent sold comparables.

> This repository contains my individual project work for the IDX
> Exchange Summer 2026 internship. Internal MLS data is not included.

## Key Engineering Highlights

-   LangGraph orchestration with conditional query blocking and output
    screening
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
-   Reusable listing-level `PropertyAnalysisSubgraph`
-   Hierarchical parallel analysis with bounded four-worker candidate
    concurrency
-   Deterministic Top-K ranking with stable listing-key tie-breaking
-   Typed, validated, immutable recommendation scoring configuration
-   Candidate-level failure isolation and structured error reporting
-   Retrieval evaluation comparing structured, keyword, semantic, and
    hybrid search
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

## Core Workflow

### 1. Natural-Language Intent Parsing

The `IntentAgent` converts conversational requests into a structured
`PropertyIntent`.

Supported fields include:

-   City
-   Maximum budget
-   Minimum bedrooms
-   Minimum bathrooms
-   Property type
-   Hard search keywords
-   Soft user preferences

Example:

``` text
Find townhouses in Irvine under 1.2 million
with a garage, preferably with a pool and a view.

↓

PropertyIntent
{
    city: Irvine
    max_price: 1200000
    property_type: Townhouse
    keywords: ["garage"]
    preferences: ["pool", "view"]
}
```

Hard constraints determine candidate eligibility. Soft preferences
remain outside SQL filtering and influence downstream ranking instead.

### 2. Multi-Turn Session Memory

`SessionMemory` allows incomplete follow-up queries to inherit prior
search criteria.

``` text
Turn 1: Find townhouses in Irvine
Turn 2: Under 1.2 million
Turn 3: At least 3 bedrooms with a garage, preferably with a pool
```

The resulting intent retains city, property type, budget, bedroom count,
hard keywords, and soft preferences. Blocked compliance requests do not
modify memory.

### 3. Query and Output Compliance

The workflow applies rule-based Fair Housing safeguards at two
boundaries:

``` text
User Query → Query Compliance → Workflow → Output Compliance → Final Response
```

  Risk level   Behavior
  ------------ --------------------------------------------
  Green        Continue normally
  Yellow       Continue using neutral, objective language
  Red          Block before downstream workflow execution

Current coverage includes protected-class requests, familial-status
exclusions, religion, national origin, sex or gender restrictions,
disability-related exclusion, subjective safety language, school
proxies, and demographic steering.

The guardrail distinguishes exclusionary language from legitimate
accessibility requests.

### 4. Structured MySQL Property Search

The active-listing search path follows the Repository Pattern:

``` text
PropertyIntent
    ↓
PropertyQueryBuilder
    ↓
SearchRepository
    ├── CSVSearchRepository
    └── MySQLSearchRepository
    ↓
PropertyFormatter
    ↓
ListingSchema
```

The MySQL implementation uses parameterized SQL and converts raw rows
into typed Pydantic objects. Current hard filtering supports city,
price, bedrooms, bathrooms, property type, and required listing-remark
keywords.

### 5. Property Analysis Subgraph

Each candidate listing is analyzed by a dedicated
`PropertyAnalysisSubgraph`.

The subgraph produces three recommendation signals:

  -----------------------------------------------------------------------
  Signal                              Responsibility
  ----------------------------------- -----------------------------------
  Preference Match                    Measures alignment with optional
                                      user preferences

  Comparable Value                    Evaluates asking value relative to
                                      recent similar sales

  Negotiation                         Estimates buyer leverage from
                                      comparable-market signals
  -----------------------------------------------------------------------

The subgraph returns one structured `RecommendationScore`;
collection-level ranking remains the responsibility of the parent graph.

### 6. Market and Comparable Retrieval

`MarketAgent` uses recent sold records from `california_sold` to produce
city-level and listing-specific market context.

Comparable retrieval first searches for recent sold properties within a
recent-sale window using strict similarity criteria. When insufficient
comparable sales are available, the search progressively relaxes
matching constraints before falling back to broader market-level
comparables:

``` text
strict → relaxed → broad → market_fallback
```

Matching may consider:

-   City and postal code
-   Property subtype
-   Bedroom and bathroom ranges
-   Living-area tolerance
-   Recent sale window

This preserves evidence coverage when strict comparables are sparse.

### 7. Configurable Recommendation Scoring

The default recommendation policy combines three normalized scores:

  Component            Default weight
  ------------------ ----------------
  Preference Match                40%
  Comparable Value                35%
  Negotiation                     25%

``` text
Overall Score =
    Preference Match × 0.40
  + Comparable Value × 0.35
  + Negotiation × 0.25
```

Weights and label thresholds are stored in an immutable
`RecommendationConfig`. Validation ensures that weights are
non-negative, sum to 1.0, and that score thresholds remain ordered.

  Score       Label
  ----------- ----------------
  80--100     Strong Match
  65--79.99   Good Match
  50--64.99   Moderate Match
  Below 50    Limited Match

The scoring policy can be replaced through dependency injection without
changing the subgraph or parent workflow.

### 8. Deterministic Top-K Ranking

Parallel tasks complete in nondeterministic order, so completion order
is never treated as recommendation order.

Final ranking uses:

``` text
1. Overall score descending
2. Listing key ascending as a deterministic tie-breaker
```

This preserves stable Top-5 results across sequential and parallel
execution.

### 9. Explainable Recommendations

Each final recommendation retains:

-   Overall recommendation score
-   Recommendation label
-   Preference-match score
-   Comparable-value score
-   Negotiation score
-   Supporting reason signals

The explanation layer consumes ranked `RecommendationScore` objects and
is screened by output compliance before reaching the user.

### 10. Semantic Retrieval

Active MLS listings are converted into canonical embedding text and
encoded through an `EmbeddingProvider` abstraction. The resulting
vectors are L2-normalized and indexed with FAISS `IndexFlatIP`, making
inner-product search equivalent to cosine-similarity ranking for
normalized vectors.

The embedding pipeline supports batch generation, metadata alignment
validation, token auditing, and checkpoint/resume for recoverable
full-corpus builds.

### 11. Hybrid Search

Hybrid search combines structured MLS eligibility filtering with
semantic reranking. Hard constraints such as city, budget, bedroom
count, bathroom count, property type, and required keywords remain
deterministic, while softer preferences are represented through
embedding similarity.

This design prevents pure semantic retrieval from returning attractive
but structurally ineligible listings.

### 12. Hybrid Similar-Home Recommendation

Given a target listing ID, the recommendation service scores compatible
active listings using a **60-point Property-Attribute Similarity component** and
a **40-point semantic similarity component**.

Unlike hybrid property search, this path does not apply user-defined SQL
hard constraints before ranking. It scores compatible listings from the
full embedded active-listing corpus, with property type used as a
compatibility guardrail.

The final hybrid score therefore balances objective property similarity
with qualitative similarity captured from listing descriptions.

### 13. Sold-Comp Validation

The Top-K similar-home recommendations are passed through existing
sold-comparable market analysis. The system reports asking PPSF,
comparable median PPSF, asking-to-comp PPSF ratio, comparable median
close price, comparable-value score, match level, comparable count, and
evidence quality.

This validation does not change what "similar" means; it adds a separate
market-evidence layer explaining whether each similar listing also
appears attractively or weakly priced relative to recent comparable
sales.

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

The Streamlit application exposes two complementary workflows.

### Property Search

-   Natural-language MLS search
-   Hard constraints and soft preferences
-   Multi-turn session memory
-   Structured intent and memory inspection
-   Fair Housing query/output safeguards
-   MySQL-backed candidate retrieval
-   Bounded parallel property analysis
-   Market-aware recommendation scoring
-   Explainable Top-5 recommendations
-   Session history and search reset

### Similar Home Recommendation

-   Target-listing lookup by MLS listing ID
-   Property-attribute + semantic hybrid similarity
-   Full-corpus embedding coverage
-   Top-K similar active listings
-   Property-type compatibility handling
-   Sold-comparable validation
-   Asking and comparable median PPSF
-   Comparable-value score
-   Comparable-evidence quality
-   Expandable similarity and market-evidence breakdowns

The two workflows intentionally remain separate at the UI boundary:
property search answers **what satisfies the user's requirements**,
while similar-home recommendation answers **what resembles a selected
property**.

The workflow object is stored in the Streamlit session so conversational
search criteria persist across turns.

The full application currently depends on internal IDX Exchange MLS
datasets that cannot be redistributed. A public demonstration can use
synthetic active-listing and sold-comparable repositories while
preserving the higher-level architecture. 

## Technology Stack

  Category                 Technology
  ------------------------ ----------------------
  Language                 Python 3.10
  Workflow orchestration   LangGraph
  LLM framework            LangChain
  Embeddings               OpenAI Embeddings
  Vector retrieval         FAISS
  Token auditing           tiktoken
  Numerical processing     NumPy
  Data validation          Pydantic
  Database                 MySQL
  Frontend                 Streamlit
  Concurrency              `ThreadPoolExecutor`
  Testing                  Pytest
  Version control          Git and GitHub

## Local Setup

### Install dependencies

``` bash
python -m venv .venv
```

``` bash
# Windows
.venv\Scripts\activate

# macOS / Linux
source .venv/bin/activate
```

``` bash
pip install -r requirements.txt
```

### Configure environment variables

Create a local `.env` file from the provided template:

``` bash
# Windows
copy .env.example .env

# macOS / Linux
cp .env.example .env
```

Required local configuration includes MySQL host, port, user, password,
database, and any configured model-provider credentials. Secrets must
not be committed.

### Run the application

``` bash
python -m streamlit run src/app/streamlit_app.py
```

The application is normally available at:

``` text
http://localhost:8501
```

## Testing and Validation

Run all tests:

``` bash
pytest -v
```

Current result:

``` text
144 passed
```

Run the fast suite without MySQL-backed integration tests:

``` bash
pytest -m "not integration" -v
```

Run the sequential/parallel consistency regression:

``` bash
pytest tests/test_candidate_parallel_consistency.py -v
```

Run the real MySQL-backed parallel smoke test:

``` bash
python -m src.dev_test_candidate_parallel
```

Run the latency benchmark:

``` bash
python -m src.dev_benchmark_candidate_parallel
```

Run semantic-search tests:

``` bash
pytest tests/test_semantic_search.py -v
```

Run hybrid-search tests:

``` bash
pytest tests/test_hybrid_search.py -v
```

Run hybrid similar-home recommendation tests:

``` bash
pytest tests/test_hybrid_similarity.py -v
```

Run the full-corpus retrieval comparison:

``` bash
python -m src.dev_evaluate_retrieval
```

Validation currently covers:

-   Intent parsing and hard/soft preference separation
-   Session-memory inheritance and reset behavior
-   Fair Housing query and output rules
-   Query-builder and repository behavior
-   Property formatting and typed schemas
-   Market, comparable-value, preference, and negotiation analysis
-   Configurable recommendation weights and thresholds
-   Recommendation labels, ranking, tie-breaking, and output schema
-   Property-analysis subgraph fan-out/fan-in behavior
-   Parent LangGraph routing and error handling
-   Sequential/parallel candidate coverage and score consistency
-   MySQL-backed smoke testing
-   Multi-run latency benchmarking
-   Listing embedding-text construction and missing-value handling
-   FAISS index construction, normalization, persistence, and reload
    validation
-   Semantic-search query validation and metadata/index alignment
-   Hybrid structured-semantic search behavior
-   Retrieval metrics across structured, keyword, semantic, and hybrid
    modes
-   Hybrid similar-home scoring, target exclusion, and property-type
    compatibility
-   Sold-comparable recommendation validation and evidence-quality
    reporting

## Repository Structure

``` text
src/
├── agents/                  # Specialized workflow and market-analysis agents
├── app/                     # Streamlit application
├── compliance/              # Fair Housing rule definitions
├── config/                  # Application and recommendation configuration
├── embeddings/              # Listing-text preparation and embedding utilities
├── evaluation/              # Retrieval evaluation cases and metrics
├── memory/                  # Multi-turn session memory
├── providers/               # LLM and embedding provider abstractions
├── recommendation/          # Ranking, hybrid similarity, scoring, and explanation
├── schemas/                 # Pydantic and TypedDict contracts
├── search/                  # Structured, semantic, hybrid, and repository search
├── workflow/                # Parent LangGraph and property-analysis subgraph
├── dev_build_listing_embeddings.py
├── dev_build_faiss_index.py
├── dev_semantic_search.py
├── dev_hybrid_search.py
├── dev_hybrid_recommendation.py
├── dev_evaluate_retrieval.py
├── dev_test_candidate_parallel.py
└── dev_benchmark_candidate_parallel.py

tests/                       # Unit, regression, retrieval, and integration tests

docs/
└── architecture.md          # Detailed architecture and design decisions

artifacts/
├── benchmarks/
│   ├── candidate_parallel_baseline.csv
│   └── retrieval_comparison_full.csv
└── embeddings/              # Generated embedding/index artifacts; excluded as appropriate

examples/
└── sample_queries.md
```

Internal MLS datasets are intentionally excluded. Public demonstrations
should use synthetic data. 

## Current Implementation

  -----------------------------------------------------------------------
  Status                              Capability
  ----------------------------------- -----------------------------------
  Implemented                         LangGraph parent workflow with
                                      conditional compliance routing

  Implemented                         Multi-turn memory-aware intent
                                      parsing

  Implemented                         MySQL active-listing and
                                      sold-comparable repositories

  Implemented                         Reusable parallel property-analysis
                                      subgraph

  Implemented                         Bounded candidate-level concurrency

  Implemented                         Configurable deterministic
                                      recommendation scoring

  Implemented                         Sequential/parallel consistency
                                      regression

  Implemented                         Multi-run candidate-analysis
                                      latency benchmark

  Implemented                         Full-corpus embedding pipeline with
                                      checkpoint/resume

  Implemented                         52,794-listing FAISS semantic index

  Implemented                         Query-time semantic search

  Implemented                         Hybrid structured-semantic property
                                      search

  Implemented                         Retrieval evaluation across four
                                      search modes

  Implemented                         Hybrid similar-home recommendation

  Implemented                         Sold-comparable validation for
                                      similar-home recommendations

  Implemented                         Streamlit similar-home
                                      recommendation interface
  -----------------------------------------------------------------------

Future architectural evolution and planned extensions are documented in
`docs/architecture.md`.

## Project Status

The Week 6 milestone established the core production-style MVP: a tested
LangGraph workflow with reusable property-analysis subgraphs,
hierarchical parallel execution, deterministic recommendation behavior,
configurable scoring, Fair Housing safeguards, MySQL-backed active/sold
retrieval, and quantitative latency validation.

Week 7 extends that MVP with a **52,794-listing full-corpus embedding
index**, FAISS semantic retrieval, hybrid structured-semantic search,
retrieval evaluation, hybrid similar-home recommendation,
sold-comparable validation, and an expanded Streamlit interface.

The original LangGraph property-search architecture remains intact. The
new retrieval and similar-home recommendation capabilities are
complementary services that reuse existing market-analysis components
rather than duplicating the core property-analysis subgraph.

The current automated test suite contains **144 passing tests**.
