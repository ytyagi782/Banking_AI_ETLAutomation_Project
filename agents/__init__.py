"""
agents/
=======
AI agents that sit ON TOP OF the existing ETL validation framework and help
students learn ETL testing + agentic AI together.

Each agent is a small, readable Python program with three parts you can point
students at:

    1. a SYSTEM PROMPT      -> who the agent is and what good output looks like
    2. some TOOLS / CONTEXT -> real data pulled from the project (config + DB)
    3. one CLAUDE CALL      -> the model turns that context into an artifact

The golden rule of this whole package:

    Claude GENERATES and REASONS.   The framework EXECUTES and VERIFIES.

So the agents produce mapping documents, test cases, code, and defect reports;
pytest and SQL Server actually run things. Never let the model "pretend" to run
tests - that is what tests/ and utilities/ are for.

Agents (numbered to match the six-step workflow):
    agent_1_mapping_doc.py   - generate the Source->Target mapping document
    agent_2_test_cases.py    - generate test cases from the mapping document
    agent_3_generate_code.py - generate pytest code from the test cases
    agent_4_test_data.py     - generate source test data + INSERT scripts
                               (WRITES .sql files only - never executes them)
    agent_5_execute.py       - execute the tests (pytest) and summarise results
    agent_6_defect_raiser.py - turn test failures into defect reports
    assistant.py             - end-to-end AI assistant (ties everything together)
"""
