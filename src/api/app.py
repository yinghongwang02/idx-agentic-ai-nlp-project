from __future__ import annotations

from functools import lru_cache

from fastapi import (
    Depends,
    FastAPI,
    HTTPException,
    status,
)

from src.api.schemas import (
    ChatRequest,
    HealthResponse,
    OrchestrationResponse,
    RecommendationRequest,
    SearchRequest,
)
from src.config.settings import settings
from src.orchestration.composition import (
    create_orchestrator,
)
from src.orchestration.orchestrator import (
    Orchestrator,
)
from src.schemas.orchestrator_state_schema import (
    OrchestratorState,
)


app = FastAPI(
    title="IDX Exchange Real Estate Copilot API",
    description=(
        "FastAPI interface for the Week 9 unified "
        "real-estate multi-agent orchestrator."
    ),
    version="0.1.0",
)


# =====================================================================
# Dependency construction
# =====================================================================


@lru_cache(maxsize=1)
def get_orchestrator() -> Orchestrator:
    """
    Build the real orchestrator once per API process.

    The composition root loads MySQL-backed repositories,
    listing embeddings, knowledge FAISS artifacts, providers,
    and capability adapters.
    """

    return create_orchestrator()


# =====================================================================
# Response mapping
# =====================================================================


def build_response(
    state: OrchestratorState,
) -> OrchestrationResponse:
    """
    Map internal LangGraph state into the stable public API schema.
    """

    route = state.get("route")

    if route is None:
        raise RuntimeError(
            "Orchestrator returned no route."
        )

    return OrchestrationResponse(
        route=route,
        routes=state.get(
            "routes",
            [],
        ),
        route_reason=state.get(
            "route_reason",
            "",
        ),
        agents_invoked=state.get(
            "agents_invoked",
            [],
        ),
        final_response=state.get(
            "final_response",
            "",
        ),
        errors=state.get(
            "errors",
            [],
        ),
        session_id=state.get(
            "session_id",
        ),
    )


def invoke_orchestrator(
    orchestrator: Orchestrator,
    query: str,
    *,
    session_id: str | None = None,
) -> OrchestrationResponse:
    try:
        result = orchestrator.invoke(
            query,
            session_id=session_id,
        )

        return build_response(
            result
        )

    except HTTPException:
        raise

    except Exception as exc:
        raise HTTPException(
            status_code=(
                status.HTTP_500_INTERNAL_SERVER_ERROR
            ),
            detail=(
                "Orchestration request failed: "
                f"{type(exc).__name__}: {exc}"
            ),
        ) from exc


# =====================================================================
# Health
# =====================================================================


@app.get(
    "/health",
    response_model=HealthResponse,
    tags=["system"],
)
def health() -> HealthResponse:
    """
    Lightweight process health check.

    This intentionally does not call MySQL, OpenAI, or FAISS.
    """

    return HealthResponse(
        status="ok",
        environment=settings.app_env,
    )


# =====================================================================
# Property search
# =====================================================================


@app.post(
    "/search",
    response_model=OrchestrationResponse,
    tags=["search"],
)
def search(
    request: SearchRequest,
    orchestrator: Orchestrator = Depends(
        get_orchestrator
    ),
) -> OrchestrationResponse:
    return invoke_orchestrator(
        orchestrator,
        request.query,
        session_id=request.session_id,
    )

# =====================================================================
# Similar-home recommendation
# =====================================================================


@app.post(
    "/recommend",
    response_model=OrchestrationResponse,
    tags=["recommendation"],
)
def recommend(
    request: RecommendationRequest,
    orchestrator: Orchestrator = Depends(
        get_orchestrator
    ),
) -> OrchestrationResponse:
    query = (
        "Show me homes similar to "
        f"listing {request.listing_id}."
    )

    return invoke_orchestrator(
        orchestrator,
        query,
        session_id=request.session_id,
    )

# =====================================================================
# Unified chat endpoint
# =====================================================================


@app.post(
    "/chat",
    response_model=OrchestrationResponse,
    tags=["orchestration"],
)
def chat(
    request: ChatRequest,
    orchestrator: Orchestrator = Depends(
        get_orchestrator
    ),
) -> OrchestrationResponse:
    return invoke_orchestrator(
        orchestrator,
        request.query,
        session_id=request.session_id,
    )