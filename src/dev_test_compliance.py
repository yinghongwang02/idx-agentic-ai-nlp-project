from src.agents.compliance_agent import ComplianceAgent


def print_report(
    case_number: int,
    text: str,
    target: str = "query",
) -> None:
    agent = ComplianceAgent()

    if target == "output":
        report = agent.check_output(text)
    else:
        report = agent.check_query(text)

    print("=" * 90)
    print(f"Case {case_number}")
    print("Target:", target)
    print("Text:", text)
    print("Report:")
    print(report.model_dump())


def main() -> None:
    print_report(
        case_number=1,
        text="Find townhouses in Irvine under 1.2 million with a garage.",
    )

    print_report(
        case_number=2,
        text="Find homes in the safest neighborhood with good schools.",
    )

    print_report(
        case_number=3,
        text="Show me homes in a Christian neighborhood.",
    )

    print_report(
        case_number=4,
        text="Find apartments with no children nearby.",
    )

    print_report(
        case_number=5,
        text="I want a single-family home with white kitchen cabinets.",
    )

    print_report(
        case_number=6,
        text=(
            "This property is ideal because the neighborhood is mostly "
            "young professionals."
        ),
        target="output",
    )


if __name__ == "__main__":
    main()