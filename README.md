# IDX Exchange Agentic AI Project

## Overview

This repository contains my individual project work for the IDX Exchange Summer 2026 internship.

The project explores an **Agentic AI workflow** for conversational real estate search, recommendation, and explanation. Instead of treating property search as a single retrieval task, the system decomposes the workflow into multiple specialized AI agents responsible for natural language understanding, conversational memory, structured search, market analysis, recommendation ranking, explanation generation, and compliance enforcement.

Users can describe property requirements in natural language, refine their preferences through multiple conversational turns, and receive explainable property recommendations generated from a production-oriented MLS database.

The workflow is orchestrated using **LangGraph**, follows a modular **multi-agent architecture**, and adopts the **Repository Pattern** to separate business logic from data access. This design allows individual components to evolve independently while maintaining a consistent end-to-end workflow.

Current capabilities include:

- Natural language property search
- Multi-turn conversational memory
- Fair Housing compliance guardrails
- LangGraph workflow orchestration
- MySQL-backed MLS search
- Market-aware recommendation pipeline
- Explainable AI recommendations
- Interactive Streamlit interface
- Automated regression testing with Pytest

---

# Current Features

## Natural Language Property Search

The system accepts conversational property search requests and converts them into a structured property intent that serves as the interface between natural language understanding and downstream search components.

Rather than relying on keyword matching alone, the Intent Agent extracts structured search constraints from free-form user requests.

The current parser supports:

- City
- Maximum budget
- Minimum bedrooms
- Minimum bathrooms
- Property type
- Hard search keywords
- Soft user preferences

Example:

```text
Find townhouses in Irvine
under 1.2 million
with a garage,
preferably with a pool and a view.

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

Separating hard constraints from soft preferences enables the recommendation system to distinguish between mandatory search requirements and desirable lifestyle features during downstream ranking.

Current intent parsing focuses on deterministic extraction using rule-based patterns. The modular design allows future integration of LLM-assisted parsing without changing the surrounding workflow.

---

## Multi-turn Conversational Search

Real estate searches naturally evolve over multiple conversational turns.

Instead of requiring users to restate every search criterion, the workflow maintains a session-aware memory that accumulates meaningful search preferences throughout the conversation.

Example:

```text
Turn 1

Find townhouses in Irvine

↓

{
    city: Irvine
    property_type: Townhouse
}
```

```text
Turn 2

Under 1.2 million

↓

{
    city: Irvine
    property_type: Townhouse
    max_price: 1200000
}
```

```text
Turn 3

At least 3 bedrooms
with a garage,
preferably with a pool.

↓

{
    city: Irvine
    property_type: Townhouse
    max_price: 1200000
    min_bedrooms: 3
    keywords: ["garage"]
    preferences: ["pool"]
}
```

The SessionMemory component is responsible for:

- Persisting meaningful search preferences
- Ignoring empty or unknown fields
- Updating scalar constraints when users change requirements
- Merging and deduplicating keyword lists
- Maintaining separate hard and soft preferences
- Providing defensive memory snapshots
- Supporting complete session reset

To prevent unintended behavior, requests blocked by the compliance layer never modify the active conversation memory.

This design enables a more natural conversational experience while keeping the property search workflow deterministic and predictable.

---

## Fair Housing Compliance Guardrails

The workflow includes a rule-based Fair Housing compliance layer that evaluates both incoming user requests and generated model responses.

Compliance checking occurs at two independent stages:

```text
User Query
      │
      ▼
Query Compliance
      │
      ▼
Agent Workflow
      │
      ▼
Generated Response
      │
      ▼
Output Compliance
```

This dual-layer design reduces the likelihood of unsafe requests entering the workflow while also preventing potentially problematic generated content from reaching the user.

Current compliance results are classified into three risk levels:

| Risk Level | Behavior |
|------------|----------|
| Green | Continue normally |
| Yellow | Continue with neutral, objective language |
| Red | Block before workflow execution |

Current rule coverage includes:

- Protected-class housing preferences
- Familial status discrimination
- Religion-based housing requests
- National origin discrimination
- Sex and gender restrictions
- Disability-related exclusionary requests
- Subjective neighborhood safety language
- School-quality proxy language
- Demographic steering

The compliance system also distinguishes between exclusionary language and legitimate accessibility-related housing needs.

For example,

```text
Avoid homes near disabled residents.
```

is treated differently from

```text
Find a wheelchair-accessible home.
```

Each compliance decision includes:

- Risk level
- Matched rule category
- Matched text
- Explanation
- Block decision
- Safe rewrite guidance
- Refusal message (when required)
- Rule version

The current implementation provides a deterministic baseline that can later be extended using LLM-assisted compliance classification.

---

## LangGraph Workflow Orchestration

The entire property search workflow is implemented as a LangGraph StateGraph.

Instead of treating property search as a single function call, the workflow coordinates multiple specialized agents through a shared AgentState.

The current state stores information including:

- Original user query
- Query compliance result
- Parsed property intent
- Session memory snapshot
- Search candidates
- Recommendation results
- Generated explanation
- Output compliance result
- Final response
- Workflow control state

The current execution path is:

```text
START
   │
   ▼
Query Compliance
   │
   ├──────────── Block ───────────► END
   │
   ▼
Intent Agent
   │
   ▼
Session Memory
   │
   ▼
Search Agent
   │
   ▼
Recommendation Pipeline
   │
   ▼
Explanation Agent
   │
   ▼
Output Compliance
   │
   ▼
END
```

Conditional routing allows the workflow to terminate immediately when unsafe requests are detected, preventing unnecessary computation and ensuring that blocked requests never reach downstream components.

The recommendation pipeline itself is composed of multiple independent analysis agents and is described in the following section of this README.

---

## Structured Property Search

Once a structured PropertyIntent has been generated, the Search Agent retrieves candidate properties using deterministic filtering.

Current hard filtering supports:

- City
- Budget
- Bedrooms
- Bathrooms
- Property type
- Required keywords

Keyword matching is performed over MLS listing remarks, allowing users to search for specific property characteristics such as:

- garage
- backyard
- fireplace
- remodeled kitchen

Hard constraints determine which listings are eligible for retrieval.

Soft preferences are intentionally excluded from database filtering and are instead evaluated during the downstream recommendation stage. This separation preserves recall while allowing the recommendation system to rank properties according to user lifestyle preferences.

---

## MySQL-backed Search Layer

The project supports both lightweight local development and production-oriented database search through a unified repository interface.

The search layer follows the Repository Pattern:

```text
PropertyIntent
        │
        ▼
PropertyQueryBuilder
        │
        ▼
SearchRepository
      ├── CSVSearchRepository
      └── MySQLSearchRepository
        │
        ▼
PropertyFormatter
        │
        ▼
ListingSchema
```

Responsibilities are intentionally separated:

| Component | Responsibility |
|----------|----------------|
| PropertyQueryBuilder | Generate parameterized SQL |
| SearchRepository | Execute database queries |
| PropertyFormatter | Convert raw MLS records into typed objects |
| ListingSchema | Standardize downstream data representation |

The MySQL implementation provides:

- Parameterized SQL generation
- SQL injection protection
- Repository abstraction
- Typed Pydantic models
- Replaceable data sources
- Consistent search interface

Because higher-level agents depend only on the repository interface rather than a specific database implementation, the workflow can easily switch between CSV datasets, local MySQL instances, or future production MLS services without changing business logic.

---

# Recommendation Pipeline

After the Search Agent retrieves candidate properties using deterministic hard filters, the system performs a second-stage recommendation workflow that analyzes each candidate from multiple perspectives before generating the final ranking.

Instead of ranking properties using only search relevance, the recommendation pipeline introduces several specialized analysis agents that evaluate different aspects of a listing independently.

The current recommendation workflow consists of three specialized analysis agents and one aggregation agent.

| Agent | Responsibility |
|--------|----------------|
| PreferenceMatchAgent | Measures how well a listing satisfies user soft preferences. |
| ComparableValueAgent | Estimates whether the asking price appears attractive relative to recent comparable sales. |
| NegotiationAgent | Estimates potential negotiation opportunity using market behavior. |
| RecommendationAgent | Aggregates all analysis into a unified recommendation score. |

The overall workflow is shown below.

```text
PropertyIntent
        │
        ▼
Search Agent
(Hard Constraints)
        │
        ▼
Retrieved Candidate Listings
        │
        ▼
 ┌────────────────────────────────────────────┐
 │ PreferenceMatchAgent                       │
 │ ComparableValueAgent                       │
 │ NegotiationAgent                           │
 └────────────────────────────────────────────┘
        │
        ▼
RecommendationAgent
        │
        ▼
Top Ranked Properties
        │
        ▼
ExplanationAgent
```

This architecture separates retrieval from ranking.

The Search Agent determines which properties satisfy mandatory user requirements, while the Recommendation Pipeline estimates which of those properties are likely to provide the best overall purchasing opportunity.

---

## Recommendation Score

The final recommendation score combines three complementary evaluation signals.

The current MVP uses an interpretable heuristic weighting strategy: 

| Component | Weight |
|-----------|-------:|
| Preference Match | 40% |
| Comparable Value | 35% |
| Negotiation Opportunity | 25% |

These initial weights are designed for deterministic MVP behavior and can later be refined through systematic evaluation. 

Each component represents a different dimension of decision making.

**Preference Match**

Measures how well a listing satisfies optional lifestyle preferences extracted from the user's natural language query.

Examples include:

- Pool
- View

These preferences influence ranking without excluding otherwise suitable listings.

---

**Comparable Value**

Estimates whether a property's asking price appears attractive relative to similar recently sold properties.

Instead of evaluating price in isolation, the analysis compares each listing against recent comparable sales from the surrounding market using a price-per-square-foot (PPSF) approach. This provides market context and allows the recommendation system to assess value relative to similar homes rather than the overall housing market.

The analysis also considers the quality of the comparable set, allowing confidence to vary depending on how closely recent sales match the target property.

---

**Negotiation Opportunity**

Estimates the likelihood that a property may offer greater pricing flexibility than similar listings.

Rather than predicting the final sale price, the analysis evaluates market signals associated with buyer negotiation opportunities. Current signals include:

- Days on Market relative to comparable listings
- Average sale-to-list price ratio observed in recent comparable sales

These signals are combined into a negotiation score that estimates whether current market conditions appear more or less favorable for buyers. 

---

The weighted recommendation score provides a unified ranking while preserving the individual component scores for explanation and future model improvements.

---

## Preference Match Analysis

Many user requirements are preferences rather than mandatory constraints.

For example,

```text
Find a home
with a garage,
preferably with a pool
and a view.
```

In this example,

```text
garage
```

is treated as a hard search requirement, while

```text
pool
view
```

are treated as soft preferences.

The Search Agent first retrieves properties satisfying all mandatory constraints.

The PreferenceMatchAgent then evaluates how many optional preferences are satisfied by each candidate property.

This two-stage design increases search recall while still allowing listings that better match user lifestyle preferences to appear higher in the final ranking.

---

## Comparable Value Analysis

Price alone provides limited information about whether a property represents a good buying opportunity.

The ComparableValueAgent evaluates each listing using recent comparable sales from the surrounding market rather than relying solely on the asking price.

Current analysis includes:

- Comparable property selection
- Price-per-square-foot (PPSF) comparison
- Comparable confidence estimation

The PPSF comparison measures how the listing's asking price relates to similar recently sold properties, while the confidence estimation reflects how representative the comparable sales are for the target property.

To improve robustness, comparable properties are retrieved using a progressive matching strategy. The system first attempts to identify highly similar properties using strict matching criteria. If an insufficient number of comparable sales are available, the search is gradually relaxed before falling back to broader market-level comparisons.

This multi-stage retrieval strategy helps maintain reliable comparable analysis across different property types and market conditions while preserving the highest-quality matches whenever possible.

The current implementation is intentionally modular so that more advanced valuation models can be incorporated in future iterations without changing the overall recommendation workflow.

---

## Negotiation Analysis

The NegotiationAgent estimates whether current market conditions may provide favorable negotiation opportunities for buyers.

Current analysis considers:

- Days on Market relative to comparable listings
- Average sale-to-list price ratio in recent comparable sales

Properties that remain on the market longer than similar homes may indicate increased pricing flexibility.

In addition, recent comparable sales provide insight into local negotiation behavior. Markets with lower average sale-to-list price ratios generally suggest that buyers have been able to purchase properties below their asking prices.

The resulting negotiation score is used as one component of the overall recommendation score rather than a prediction of the final transaction price.

---

## Explainable Recommendations

Rather than returning only a ranked property list, the system generates an explanation describing why each recommendation appears near the top of the results.

Each recommendation includes:

- Recommendation Score
- Recommendation Label
- Preference Match Score
- Comparable Value Score
- Negotiation Score
- Supporting Reasons

Example output:

```text
Recommendation Score: 91.8

Strong Match

Preference Match
✓ Pool
✓ View

Comparable Value
Asking PPSF appears favorable
relative to recent comparable sales.

Negotiation
Property has remained on the market
longer than comparable listings,
suggesting additional negotiation opportunity.
```

Providing transparent reasoning allows users to understand how different factors contribute to the final recommendation instead of treating the ranking as a black box.

The explanation layer is generated after recommendation ranking and is subsequently passed through the output compliance module before being returned to the user.

---

# Interactive Streamlit Application

A Streamlit application provides an interactive interface for the complete LangGraph workflow.

Current functionality includes:

- Natural language property search
- Multi-turn conversational memory
- Structured intent visualization
- Session memory visualization
- Recommendation pipeline execution
- Explainable recommendations
- Query compliance feedback
- Output compliance validation
- Session search history
- Start New Search support

The Streamlit application stores the LangGraph workflow inside the user session, allowing conversational search preferences to persist across multiple interactions.

The current prototype uses internal MLS datasets that are not included in this repository. Public demonstration screenshots using synthetic data are planned for a future milestone. 

---

# Current Architecture

The complete Week 5 workflow is illustrated below.

```text
                              User Query
                                   │
                                   ▼
                         Query Compliance
                                   │
                     ┌─────────────┴─────────────┐
                     │                           │
                 Blocked                    Continue
                     │                           │
                     ▼                           ▼
                    END                   Intent Agent
                                               │
                                               ▼
                                         Session Memory
                                               │
                                               ▼
                                         Search Agent
                                               │
                                               ▼
                                   Retrieved Candidate Listings
                                               │
                  ┌────────────────────────────┼────────────────────────────┐
                  │                            │                            │
                  ▼                            ▼                            ▼
      PreferenceMatchAgent        ComparableValueAgent         NegotiationAgent
                  │                            │                            │
                  └───────────────┬────────────┴───────────────┬────────────┘
                                  │
                                  ▼
                       RecommendationAgent
                                  │
                                  ▼
                         Top Ranked Properties
                                  │
                                  ▼
                          ExplanationAgent
                                  │
                                  ▼
                         Output Compliance
                                  │
                                  ▼
                           Final Response
```

This architecture cleanly separates retrieval, analysis, recommendation, explanation, and compliance into independent components.

The modular design makes it straightforward to improve individual agents without changing the overall workflow and provides a clear foundation for future evaluation and ranking improvements. 

---

## Technology Stack

The project combines modern Python tooling with a modular multi-agent architecture for conversational property search and recommendation.

| Category | Technology |
|----------|------------|
| Language | Python 3.10 |
| Workflow Orchestration | LangGraph |
| LLM Framework | LangChain |
| Data Validation | Pydantic |
| Database | MySQL |
| Frontend | Streamlit |
| Testing | Pytest |
| Version Control | Git & GitHub |

---

# Local Setup

## Install Dependencies

```bash
python -m venv .venv
```

```bash
# Windows
.venv\Scripts\activate

# macOS / Linux
source .venv/bin/activate
```

```bash
pip install -r requirements.txt
```

---

## Configure Environment Variables

Create a local `.env` file from the provided template:

```bash
# Windows
copy .env.example .env

# macOS / Linux
cp .env.example .env
```

The application configuration includes:

- OpenAI provider settings
- MySQL connection settings
- Search backend selection

API keys and database credentials must be supplied locally and should never be committed to version control.

---

## Data Access

The full application uses internal IDX Exchange MLS datasets that are not included in this repository.

A lightweight CSV repository is available for isolated development and testing, while a fully synthetic public demonstration dataset is planned for a future milestone. 

---

## Run the Demo

Run the Streamlit application:

```bash
python -m streamlit run src/app/streamlit_app.py
```

The application will be available locally at:

```
http://localhost:8501
```

The Streamlit interface supports:

- Natural language property search
- Multi-turn conversational memory
- Recommendation pipeline with score ratings
- Explainable recommendations
- Compliance feedback
- Session history

---

# Testing

The project includes automated unit tests covering the major workflow components.

Run all tests:

```bash
pytest -v
```

Automated tests currently cover:

- Intent parsing
- Session memory
- Property query builder
- Search repositories
- Property formatter
- Fair Housing compliance
- LangGraph workflow
- PreferenceMatchAgent
- ComparableValueAgent
- NegotiationAgent
- RecommendationAgent

Current status:

```text
76 tests passed
```

Individual modules can also be tested independently during development.

Example:

```bash
pytest tests/test_recommendation_agent.py
pytest tests/test_negotiation_agent.py
pytest tests/test_comparable_value_agent.py
pytest tests/test_preference_match_agent.py
```

---

# Manual Testing

The project has been manually validated using representative conversational property search scenarios.

Example scenarios include:

### Scenario 1

```text
Find 3 bedroom homes in Irvine
under $1.2 million.
```

---

### Scenario 2

```text
Find townhouses in Irvine
with a garage.
```

---

### Scenario 3

```text
I would also prefer
a pool
and a view.
```

---

### Scenario 4

```text
Show me homes
with wheelchair accessibility.
```

---

### Scenario 5

```text
Find homes
in neighborhoods
without children.
```

Expected behavior:

- Green requests proceed normally.
- Yellow requests are rewritten using neutral language.
- Red requests are blocked before workflow execution.

---

## Example Queries

Additional sample queries are available in examples/sample_queries.md.

These examples demonstrate the supported natural language search capabilities of the current prototype. 

---

## Project Status

Current progress includes:

- Natural language intent parsing
- Multi-turn conversational property search
- Session-based preference memory
- Memory-aware intent parsing
- LangGraph StateGraph orchestration
- Conditional compliance routing
- Query-level Fair Housing guardrails
- Output-level compliance guardrails
- Red / yellow / green risk classification
- Safe rewrites and refusal handling
- MySQL-backed property search
- CSV search repository for lightweight development
- Repository Pattern
- Parameterized SQL query generation
- Keyword-based property search
- Comparable market analysis
- Preference matching 
- Negotiation analysis 
- Recommendation pipeline
- Explainable recommendations
- Interactive Streamlit demo
- Persistent Streamlit session memory
- Session search history
- Automated regression testing with Pytest