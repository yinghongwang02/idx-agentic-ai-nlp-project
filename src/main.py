from src.workflow.mock_workflow import run_mock_workflow


if __name__ == "__main__":
    query = "Find 3 bed homes in Irvine under 900k"
    result = run_mock_workflow(query)
    print(result)