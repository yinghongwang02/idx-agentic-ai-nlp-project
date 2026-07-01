# IDX Exchange Agentic AI Project

## Overview

This project explores a modular multi-agent workflow for real estate search and recommendation.

The current implementation focuses on building the engineering foundation of an extensible agentic AI system before integrating real LLMs, MLS databases, and Retrieval-Augmented Generation (RAG).

---

## Current Features (Week 1)

- Modular multi-agent workflow prototype
- Structured property intent parsing
- Property search over MLS-style sample listings
- Rule-based property recommendation
- Template-based response generation
- Typed workflow contracts using Pydantic

---

## Current Workflow

```text
                User Query
                     │
                     ▼
              Workflow Controller
                     │
                     ▼
              Intent Agent
                     │
                     ▼
              Search Agent
                     │
                     ▼
         Recommendation Agent
                     │
                     ▼
            Explanation Agent
                     │
                     ▼
                 Response
```

Each agent is responsible for a single task and communicates through validated data contracts, allowing future components to be replaced without changing the overall workflow.

---

## Project Structure

```text
src/
├── agents/
├── schemas/
├── skills/
├── workflow/
├── config/
└── main.py

data/
docs/
tests/
```

---

## Tech Stack

- Python 3.10
- LangGraph
- LangChain
- OpenAI SDK
- Pydantic
- Pandas

---

## Current Status

The current implementation uses a lightweight workflow prototype and MLS-style sample data to validate the end-to-end agent pipeline.

The project prioritizes modular architecture and well-defined data contracts before integrating production LLMs, real MLS databases, and retrieval systems.

---

## Roadmap

### Week 2
- LLM-based intent understanding
- Expanded property search capabilities
- Structured filter generation

### Week 3
- Database-backed MLS search
- Parameterized query layer
- Result formatting

### Week 4+
- Multi-turn conversational workflow
- Retrieval-Augmented Generation (RAG)
- Market analytics
- Streamlit interface

