# AI Agents

A layer of AI agents that sit **on top of** the read-only ETL validation
framework and automate the ETL-testing lifecycle. The guiding rule:

> **Claude GENERATES and REASONS.  The framework EXECUTES and VERIFIES.**

The agents produce mapping documents, test cases, code, data and defect
reports; `pytest` + SQL Server actually run things. No agent "pretends" to run
tests.

## The agents

| Step | File | What it does | Output |
|------|------|--------------|--------|
| 1 | `agent_1_mapping_doc.py` | Source→Target **mapping document** (3 sheets, one per layer; full column metadata + transformation rules) | `output/MappingDocument_<ts>.xlsx` |
| 2 | `agent_2_test_cases.py` | **Test cases** for all 3 layers, each tied to a reusable validation | `output/TestCases_<ts>.xlsx` |
| 3 | `agent_3_generate_code.py` | **pytest code** from the test cases (calls the existing validations) | `generated_tests/test_gen_*.py` |
| 4 | `agent_4_test_data.py` | Synthetic **source test data** (positive + negative) as INSERT scripts — **writes `.sql` only, never executes** | `output/testdata/*.sql` |
| 5 | `agent_5_execute.py` | **Executes** the suite via pytest, parses JUnit, AI summary | `output/ExecutionSummary_<ts>.md` (+ `.json`, `.xml`) |
| 6 | `agent_6_defect_raiser.py` | Turns failures into **defect tickets** | `output/Defects_<ts>.xlsx` (+ `.md`) |
| — | `assistant.py` | **End-to-end assistant** - menu + optional Claude chat mode | orchestrates 1-6 |

Shared foundation:
* `base.py` - `.env` loading, Claude client (`ask_claude`, `ask_claude_json`),
  output paths, `have_api_key()`.
* `schema_introspect.py` - real column metadata / constraints from
  `INFORMATION_SCHEMA` (read-only), with a YAML fallback when the DB is offline.
* `xlsx_util.py` - shared styled-Excel writer.

## Running

```bash
# individual agents
python -m agents.agent_1_mapping_doc
python -m agents.agent_2_test_cases
python -m agents.agent_3_generate_code
python -m agents.agent_4_test_data                       # writes .sql scripts only
python -m agents.agent_5_execute --target existing       # or: --target generated / --no-reset
python -m agents.agent_6_defect_raiser

# the assistant
python -m agents.assistant                 # menu
python -m agents.assistant --pipeline      # run steps 1->5 once
python -m agents.assistant --chat          # natural-language (needs API key)

# run the generated tests explicitly (not part of the default `pytest`)
pytest agents/generated_tests
```

## API key (optional but recommended)

Every agent works **without** a key using deterministic logic derived from the
config + database; when `ANTHROPIC_API_KEY` is set in `.env` (see `.env.example`)
Claude **enriches** the output (clearer transformation rules, extra edge/negative
test cases, execution narrative, defect root-cause & fixes, and chat mode).

```
# .env
ANTHROPIC_API_KEY=sk-ant-...
```
Model: `claude-opus-4-8`.

## Notes

* Outputs land in `agents/output/` and `agents/generated_tests/` - both are
  git-ignored and safe to delete/regenerate.
* The generated INSERT scripts are **never executed automatically** - run them
  yourself (e.g. with `sqlcmd`), exactly like the framework's reset script.
* The framework still emails a report after each `pytest` run if
  `email.enabled: true` in `config/settings.yaml`; agent 4 triggers that path.
