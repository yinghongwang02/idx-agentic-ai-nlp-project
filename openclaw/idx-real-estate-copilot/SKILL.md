---
name: idx-real-estate-copilot
description: >
  Use the IDX Exchange Real Estate Unified Copilot for property searches,
  local real-estate market analysis, similar-home recommendations, and
  grounded real-estate knowledge questions.
---

# IDX Real Estate Copilot

Use this skill when the user asks for:

- property or listing searches;
- local real-estate market statistics or trends;
- similar-home recommendations;
- real-estate terminology or MLS field explanations;
- mixed requests combining these capabilities.

## Execution

Run the existing IDX Unified Copilot through its Python adapter.

The project root is:

`D:\IDX_Exchange\idx-agentic-ai-nlp-project`

From that directory, execute:

`python -m scripts.openclaw_copilot_adapter "<USER_QUERY>" --json`

Replace `<USER_QUERY>` with the user's complete original request.

## Response handling

Read the JSON result from stdout.

- If `ok` is `true`, return `final_response` to the user.
- Preserve the factual content produced by the IDX Unified Copilot.
- Do not invent listings, prices, market statistics, recommendations, or knowledge answers.
- If `final_response` reports that no matching listings were found, return that result rather than fabricating alternatives.
- If `ok` is `false`, report that the IDX Unified Copilot could not complete the request.

## Safety

- Treat the IDX Unified Copilot as the source of truth for real-estate results.
- Do not bypass the existing LangGraph routing or compliance logic.
- Do not directly query the IDX MySQL database from this skill.
- Do not send email or perform other outbound actions from this skill.
- Email delivery remains behind the project's existing human-approval and outbound-safety workflow.