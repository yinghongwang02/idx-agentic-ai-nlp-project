from typing import Final


RED_RULES: Final[list[dict[str, object]]] = [
    {
        "category": "race_or_color",
        "patterns": [
            r"\bwhite neighborhood\b",
            r"\bblack neighborhood\b",
            r"\basian neighborhood\b",
            r"\bhispanic neighborhood\b",
            r"\bno black people\b",
            r"\bno asian people\b",
            r"\bwhites only\b",
        ],
        "reason": (
            "The request appears to prefer or exclude housing based on "
            "race or color."
        ),
    },
    {
        "category": "national_origin",
        "patterns": [
            r"\bamerican[- ]only\b",
            r"\bno immigrants?\b",
            r"\bno foreigners?\b",
            r"\bavoid immigrant neighborhoods?\b",
        ],
        "reason": (
            "The request appears to prefer or exclude housing based on "
            "national origin."
        ),
    },
    {
        "category": "religion",
        "patterns": [
            r"\bchristian neighborhood\b",
            r"\bjewish neighborhood\b",
            r"\bmuslim neighborhood\b",
            r"\bchristians? only\b",
            r"\bno muslims?\b",
            r"\bno jews?\b",
        ],
        "reason": (
            "The request appears to prefer or exclude housing based on "
            "religion."
        ),
    },
    {
        "category": "sex_or_gender",
        "patterns": [
            r"\bmen only\b",
            r"\bwomen only\b",
            r"\bmales? only\b",
            r"\bfemales? only\b",
            r"\bno men\b",
            r"\bno women\b",
        ],
        "reason": (
            "The request appears to prefer or exclude housing based on "
            "sex or gender."
        ),
    },
    {
        "category": "familial_status",
        "patterns": [
            r"\bno children\b",
            r"\bno kids\b",
            r"\badults only\b",
            r"\bwithout children\b",
            r"\bavoid families with children\b",
            r"\bno families\b",
        ],
        "reason": (
            "The request appears to prefer or exclude housing based on "
            "familial status."
        ),
    },
    {
        "category": "disability",
        "patterns": [
            r"\bno disabled people\b",
            r"\bno disabilities\b",
            r"\bno wheelchair users?\b",
            r"\bable[- ]bodied only\b",
            r"\bavoid disabled residents?\b",
            r"\bavoid\b.{0,30}\bdisabled residents?\b",
        ],
        "reason": (
            "The request appears to prefer or exclude housing based on "
            "disability."
        ),
    },
]


YELLOW_RULES: Final[list[dict[str, object]]] = [
    {
        "category": "demographic_steering",
        "patterns": [
            r"\bfamily[- ]friendly neighborhood\b",
            r"\bmostly families\b",
            r"\byoung professionals? neighborhood\b",
            r"\bneighborhood\s+(?:is\s+)?mostly\s+young professionals?\b",
            r"\bolder residents?\b",
            r"\bpeople like me\b",
            r"\bpeople like us\b",
        ],
        "reason": (
            "The request may be using resident demographics as a housing "
            "selection criterion."
        ),
    },
    {
        "category": "subjective_safety",
        "patterns": [
            r"\bsafe neighborhood\b",
            r"\bsafest neighborhood\b",
            r"\blow[- ]crime neighborhood\b",
            r"\bavoid dangerous areas?\b",
            r"\bavoid bad neighborhoods?\b",
        ],
        "reason": (
            "Subjective neighborhood safety language may require an "
            "objective, source-based response rather than steering."
        ),
    },
    {
        "category": "school_proxy",
        "patterns": [
            r"\bgood schools?\b",
            r"\bbest schools?\b",
            r"\btop[- ]rated schools?\b",
            r"\bgood school district\b",
            r"\bbest school district\b",
        ],
        "reason": (
            "School-quality language should be handled with objective "
            "school data and user-selected criteria."
        ),
    },
]