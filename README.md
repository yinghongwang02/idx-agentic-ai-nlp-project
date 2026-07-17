# IDX Exchange Agentic AI Project

## Overview

This repository contains my individual project work for the IDX Exchange Summer 2026 internship.

The project explores an Agentic AI workflow for conversational property search. Users can describe property requirements in natural language, refine their preferences across multiple turns, and receive matching MLS-style property recommendations.

The system converts natural language requests into structured property intents, preserves relevant search preferences through session memory, retrieves matching listings from a MySQL-backed MLS database, ranks the results, and generates explanations for the recommendations.

The workflow is orchestrated using LangGraph and includes Fair Housing compliance guardrails for both incoming user queries and generated outputs. A Repository Pattern keeps the search layer modular, allowing different data sources to be used without changing the higher-level agent workflow.

---

## Current Features

### Natural Language Property Search

The system accepts natural language property search requests and converts them into a structured property intent.

The current parser extracts:

- City
- Budget
- Bedrooms
- Bathrooms
- Property type
- Preference keywords

Example:

```text
Find townhouses in Irvine under 1.2 million with a garage

↓

PropertyIntent

{
    city: Irvine
    max_price: 1200000
    property_type: Townhouse
    keywords: ["garage"]
}
```
The structured intent provides a typed interface between natural language understanding and the downstream property search system. 

---

### Multi-turn Conversational Search

The workflow supports follow-up property search requests through session-based memory.

Users do not need to repeat all previous search criteria in every query.

Example:

```text
Turn 1:
Find townhouses in Irvine

↓

{
    city: Irvine
    property_type: Townhouse
}


Turn 2:
Under 1.2 million

↓

{
    city: Irvine
    property_type: Townhouse
    max_price: 1200000
}


Turn 3:
At least 3 bedrooms with a garage

↓

{
    city: Irvine
    property_type: Townhouse
    max_price: 1200000
    min_bedrooms: 3
    keywords: ["garage"]
}
```

The SessionMemory component:

- Stores meaningful search preferences
- Ignores empty or unknown fields
- Updates scalar preferences when the user changes a constraint
- Merges and deduplicates preference keywords
- Provides defensive memory snapshots
- Supports clearing the current search session

Blocked compliance requests are prevented from modifying the active search memory.

---

### Fair Housing Compliance Guardrails

The workflow includes a rule-based Fair Housing compliance layer for both user queries and generated responses.

Compliance results are classified into three risk levels:

- Green — the request can continue normally
- Yellow — the request requires neutral, objective handling
- Red — the request is blocked before property search

Examples of supported compliance checks include:

- Protected-class housing preferences
- Familial-status exclusions
- Religion-based housing requests
- National-origin preferences
- Sex or gender-based restrictions
- Disability-related exclusionary requests
- Subjective neighborhood safety language
- School-quality proxy language
- Demographic steering in generated recommendations

The compliance system also distinguishes exclusionary requests from legitimate accessibility-related property requirements. 

For example:

```bash
Avoid homes near disabled residents.
```

is treated differently from:

```bash
Find a wheelchair-accessible home.
```

Compliance reports include:

- Risk level
- Matched compliance categories
- Matched text
- Reason for the match
- Block decision
- Safe rewrite guidance
- Refusal message when required
- Rule version

The current implementation provides a deterministic compliance baseline that can later be extended with LLM-assisted classification. 

---

### LangGraph Workflow Orchestration

The property search pipeline is implemented as a LangGraph StateGraph.

The workflow maintains a shared AgentState containing information such as:

- User query
- Query compliance result
- Parsed property intent
- Session memory snapshot
- Search results
- Recommendations
- Generated explanation
- Output compliance result
- Final response
- Workflow control and error state

The current graph follows this execution path:

```

START
  │
  ▼
Query Compliance
  │
  ├── Red / Blocked ───────────────► END
  │
  └── Continue
          │
          ▼
   Intent + Memory
          │
          ▼
        Search
          │
          ▼
    Recommendation
          │
          ▼
      Explanation
          │
          ▼
  Output Compliance
          │
          ▼
         END
```

LangGraph conditional routing ensures that blocked requests terminate before intent parsing, memory updates, database search, recommendation, and explanation generation.

This keeps compliance enforcement at the workflow level rather than relying only on individual agents.

--- 

### Structured Property Search

The extracted and memory-enriched property intent is used to retrieve matching MLS-style listings.

The search pipeline combines:

- Structured filtering
  - City
  - Budget
  - Bedrooms
  - Bathrooms
  - Property type

- Keyword matching
  - Search over listing descriptions (`public_remarks`)

The current project supports both a lightweight CSV dataset for local development and a MySQL-backed MLS database for production-oriented search. The search layer is designed to be replaced by a production database without changing the agent workflow.

---

### MySQL-backed Search Layer

The search module now supports a production-oriented MySQL backend while retaining the original CSV repository for lightweight testing and development. 

The Query Builder generates parameterized SQL, while the PropertyFormatter converts raw MLS records into typed ListingSchema objects. 

The search pipeline is organized using a Repository Pattern:

```
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


Key design features include:

- Parameterized SQL queries
- SQL injection protection
- Query Builder abstraction
- Repository Pattern
- Listing formatter for MLS records
- Pydantic-based typed data models

The same search interface can be reused with different data sources without changing the agent workflow.

---

### Property Recommendation

Matching listings are ranked using a simple recommendation strategy based on:

- Days on market
- Listing price

Top recommendations are returned to the user.

---

### Explainable Recommendations

The Explanation Agent generates a natural language response describing the property search results.

Generated text is passed through the output compliance layer before being returned to the user.

This creates two compliance checkpoints:

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
Generated Explanation
    │
    ▼
Output Compliance
    │
    ▼
Final Response
```

Potentially problematic generated language can therefore be replaced with neutral guidance before reaching the user.


For queries passed through the compliance check, the system generates a natural language explanation describing why the listing satisfies the user's request. 

Example:

> Matched because it is in Irvine, under your budget, has at least 3 bedrooms, and the listing remarks mention "backyard".


---

### Interactive Streamlit Demo

The Streamlit application is integrated with the LangGraph workflow and supports persistent session memory.

Features include:

- Natural language property search
- Multi-turn follow-up queries
- Session-based property preference memory
- Live memory visualization
- Structured intent visualization
- MySQL-backed property search
- Property recommendations
- Generated explanations
- Query compliance feedback
- Output compliance guardrails
- Session-based search history
- Start New Search / memory reset

The LangGraph workflow instance is stored in Streamlit session state, allowing search preferences to persist across Streamlit reruns within the same user session.

---

## Current Architecture

```
                         User Query
                              │
                              ▼
                    Query Compliance
                              │
                 ┌────────────┴────────────┐
                 │                         │
              Blocked                  Continue
                 │                         │
                 ▼                         ▼
                END                Intent Agent
                                           │
                                           ▼
                                    Session Memory
                                           │
                                           ▼
                                    PropertyIntent
                                           │
                                           ▼
                                 PropertyQueryBuilder
                                           │
                                           ▼
                                    SearchRepository
                                    ├── CSV
                                    └── MySQL
                                           │
                                           ▼
                                   PropertyFormatter
                                           │
                                           ▼
                                    Recommendation
                                           │
                                           ▼
                                      Explanation
                                           │
                                           ▼
                                  Output Compliance
                                           │
                                           ▼
                                     Final Response
```

---

## Technology Stack

- Python 3.10
- LangGraph
- LangChain
- MySQL
- mysql-connector-python
- Streamlit
- Pandas
- Pydantic
- Pytest

---

## Run the Demo

Install dependencies:

```bash
pip install -r requirements.txt
```

Ensure the MySQL database connection is configured in the local environment.

Run the Streamlit application:

```bash
python -m streamlit run src/app/streamlit_app.py
```

The application will be available locally at:

```
http://localhost:8501
```

---
### Manual Testing

The following four scenarios can be used to manually verify the Week 4 conversational workflow.

1. Multi-turn Search Memory

Run the following queries sequentially without starting a new search session:

```text
Find townhouses in Irvine
```

Then:

```text
Under 1.2 million
```

Then:

```text
At least 3 bedrooms with a garage
```

Expected behavior:

The second query inherits Irvine and Townhouse.
The third query inherits the previous criteria and adds the bedroom and garage preferences.
The Session Memory panel displays the accumulated search preferences.

Expected final intent:

```text
{
    city: Irvine
    max_price: 1200000
    min_bedrooms: 3
    property_type: Townhouse
    keywords: ["garage"]
}
```


2. Start a New Search

Click:

```text
Start New Search
```

Then enter:

```text
Show me condos in Pasadena
```

Expected behavior:

Previous Irvine search preferences are cleared.
The new search does not inherit the previous budget, property type, bedroom, or keyword constraints.
Session Memory contains only the new Pasadena condominium preferences. 


3. Red-risk Compliance Request

Enter:

```text
Show me homes in a Christian neighborhood
```

Expected behavior:

The query is classified as red risk.
The request is blocked before intent parsing and property search.
No MySQL search is performed.
The active session memory is not modified.
A neutral refusal message is returned. 


4. Yellow-risk Compliance Request

Enter:

```text
Find homes in Irvine in the safest neighborhood with good schools
```

Expected behavior:

The query is classified as yellow risk.
The workflow continues using only neutral, objective property criteria that can be safely parsed.
The application displays compliance guidance about subjective safety and school-quality language.
The generated response is passed through output compliance before being shown to the user.


---

## Automated Tests

The project includes regression tests covering individual components and end-to-end workflow behavior.

Current automated tests cover:

- Intent parsing
- Multi-turn intent inheritance
- Session memory updates
- Session memory clearing
- Keyword merging and deduplication
- SQL query generation
- CSV search repository
- MySQL search repository
- MLS property formatting
- Fair Housing compliance classification
- Protected-class request blocking
- Accessibility-related false-positive protection
- Query compliance
- Output compliance
- Blocked-request memory protection
- Python workflow orchestration
- LangGraph workflow orchestration
- Conditional routing
- Workflow exception handling
- Memory snapshots across multiple turns

The current regression suite contains:

```text
53 tests passing
```

Run all tests:

```bash
pytest -v
```

Individual Week 4 workflow tests can also be run with:

```bash
pytest tests/test_week4_workflow.py -v
```

and:

```bash
pytest tests/test_week4_langgraph.py -v
```

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
- Property recommendation
- Explainable recommendations
- Interactive Streamlit demo
- Persistent Streamlit session memory
- Session search history
- Automated regression testing with Pytest