"""
agents/assistant.py   -   STEP 6
================================
The end-to-end AI ASSISTANT that ties every agent together.

Two ways to drive it:

  * MENU mode (default) - a numbered menu. Each option runs one agent; there is
    also a "run the whole pipeline" option and a DB-connection check. Predictable
    and works with no API key.

        python -m agents.assistant

  * CHAT mode (--chat, needs ANTHROPIC_API_KEY) - a natural-language loop where
    Claude decides which agent/tool to call from what you type ("generate the
    mapping doc", "run the tests then raise defects"). This showcases tool-use;
    the tools are the same agent functions the menu calls.

        python -m agents.assistant --chat

Either way, the actual work is done by the agents (which reason with Claude and
execute with the framework) - the assistant only orchestrates them.
"""

import argparse

from utilities.logger import get_logger
from agents import base
from agents import (
    agent_1_mapping_doc,
    agent_2_test_cases,
    agent_3_generate_code,
    agent_4_test_data,
    agent_5_execute,
    agent_6_defect_raiser,
)

log = get_logger()


# --------------------------------------------------------------------------
# thin wrappers so both menu and chat share one implementation per step
# --------------------------------------------------------------------------
def do_mapping():
    return agent_1_mapping_doc.generate()


def do_test_cases():
    return agent_2_test_cases.generate()


def do_generate_code():
    return agent_3_generate_code.generate()


def do_test_data():
    return agent_4_test_data.generate()


def do_execute(target="existing", no_reset=False):
    return agent_5_execute.execute(target=target, no_reset=no_reset)


def do_defects():
    return agent_6_defect_raiser.raise_defects()


def do_check_connections():
    # reuse main.py's read-only connection check
    from main import check_connections
    ok = check_connections()
    print("All connections OK." if ok else "Some connections FAILED.")
    return ok


def do_full_pipeline(target="existing"):
    """Run steps 1 -> 5 in order and report the artifacts produced."""
    base.banner("FULL PIPELINE  -  mapping -> test cases -> code -> data -> "
                "execute -> defects")
    artifacts = {}
    artifacts["mapping_doc"] = do_mapping()
    artifacts["test_cases"] = do_test_cases()
    artifacts["generated_code"] = do_generate_code()
    artifacts["test_data"] = do_test_data()
    results = do_execute(target=target)
    artifacts["execution_summary"] = results["summary_md"]
    defects = do_defects()
    artifacts["defects"] = defects["xlsx"]

    print("\n" + "=" * 70)
    print("PIPELINE COMPLETE - artifacts:")
    for k, v in artifacts.items():
        if isinstance(v, list):
            print(f"  {k}: {len(v)} file(s)")
        else:
            print(f"  {k}: {v}")
    print("=" * 70)
    return artifacts


# --------------------------------------------------------------------------
# MENU mode
# --------------------------------------------------------------------------
MENU = """
============================================================
  Banking ETL - AI Assistant  (menu)
============================================================
  1) Generate Mapping Document        (agent 1)
  2) Generate Test Cases              (agent 2)
  3) Generate Test Code               (agent 3)
  4) Generate Test Data (SQL scripts only, not executed) (agent 4)
  5) Execute Test Cases               (agent 5)
  6) Raise Issues / Defects           (agent 6)
  7) Run FULL pipeline (1 -> 5)
  8) Check database connections
  0) Quit
------------------------------------------------------------"""


def run_menu():
    print(base.ai_status())
    while True:
        print(MENU)
        choice = input("Choose an option: ").strip()
        try:
            if choice == "1":
                do_mapping()
            elif choice == "2":
                do_test_cases()
            elif choice == "3":
                do_generate_code()
            elif choice == "4":
                do_test_data()
            elif choice == "5":
                t = input("Target [existing/generated] (default existing): ").strip()
                nr = ""
                if t not in ("generated",):
                    nr = input("Skip reset & validate CURRENT data? [y/N]: ").strip().lower()
                res = do_execute(
                    target=t if t in ("existing", "generated") else "existing",
                    no_reset=(nr in ("y", "yes")))
                # execution only DETECTS failures; offer to raise defects (step 6)
                if res["totals"]["failed"]:
                    ans = input(f"\n{res['totals']['failed']} test(s) failed. "
                                "Raise defects for them now? [Y/n]: ").strip().lower()
                    if ans in ("", "y", "yes"):
                        do_defects()
                else:
                    print("\nAll executed tests passed - no defects to raise.")
            elif choice == "6":
                do_defects()
            elif choice == "7":
                t = input("Execute target [existing/generated] (default existing): ").strip()
                do_full_pipeline(target=t if t in ("existing", "generated") else "existing")
            elif choice == "8":
                do_check_connections()
            elif choice in ("0", "q", "quit", "exit"):
                print("Bye.")
                return
            else:
                print("Unknown option.")
        except Exception as exc:
            log.error(f"[assistant] step failed: {exc}")
            print(f"\n[error] {exc}\n")


# --------------------------------------------------------------------------
# CHAT mode (Claude tool-use)
# --------------------------------------------------------------------------
_TOOLS = [
    {"name": "generate_mapping_document",
     "description": "Generate the Source->Target mapping document (Excel, 3 sheets).",
     "input_schema": {"type": "object", "properties": {}}},
    {"name": "generate_test_cases",
     "description": "Generate test cases (Excel) from the mapping/config for all 3 layers.",
     "input_schema": {"type": "object", "properties": {}}},
    {"name": "generate_test_code",
     "description": "Generate pytest code from the latest test-cases workbook.",
     "input_schema": {"type": "object", "properties": {}}},
    {"name": "generate_test_data",
     "description": "Generate synthetic source test data + INSERT SQL scripts.",
     "input_schema": {"type": "object", "properties": {}}},
    {"name": "execute_tests",
     "description": "Run the test suite with pytest and summarise results.",
     "input_schema": {"type": "object", "properties": {
         "target": {"type": "string", "enum": ["existing", "generated"],
                    "description": "Which suite to run (default existing)."},
         "no_reset": {"type": "boolean",
                      "description": "Skip the prerequisite reset/reload and "
                      "validate the CURRENT data as-is. Use this to catch "
                      "defects already present in the data (default false)."}}}},
    {"name": "raise_defects",
     "description": "Turn the latest execution failures into defect tickets.",
     "input_schema": {"type": "object", "properties": {}}},
    {"name": "run_full_pipeline",
     "description": "Run every step 1->5 end to end.",
     "input_schema": {"type": "object", "properties": {
         "target": {"type": "string", "enum": ["existing", "generated"]}}}},
    {"name": "check_connections",
     "description": "Check that all four databases are reachable (read-only).",
     "input_schema": {"type": "object", "properties": {}}},
]


def _dispatch(name, args):
    """Run a tool and return a short text result for the model."""
    if name == "generate_mapping_document":
        return f"Mapping document created: {do_mapping()}"
    if name == "generate_test_cases":
        return f"Test cases created: {do_test_cases()}"
    if name == "generate_test_code":
        files = do_generate_code()
        return f"Generated {len(files)} pytest file(s) in agents/generated_tests/."
    if name == "generate_test_data":
        files = do_test_data()
        return f"Generated {len(files)} test-data script(s) in agents/output/testdata/."
    if name == "execute_tests":
        r = do_execute(target=args.get("target", "existing"),
                       no_reset=bool(args.get("no_reset", False)))
        t = r["totals"]
        return (f"Executed {r['target']}: {t['passed']} passed, {t['failed']} "
                f"failed, {t['skipped']} skipped. Summary: {r['summary_md']}")
    if name == "raise_defects":
        d = do_defects()
        return f"Raised {d['count']} defect(s). File: {d['xlsx']}"
    if name == "run_full_pipeline":
        do_full_pipeline(target=args.get("target", "existing"))
        return "Full pipeline complete. See agents/output/ for all artifacts."
    if name == "check_connections":
        return "All databases reachable." if do_check_connections() else \
               "One or more databases are NOT reachable."
    return f"Unknown tool: {name}"


def run_chat():
    if not base.have_api_key():
        print("Chat mode needs ANTHROPIC_API_KEY in your .env. "
              "Falling back to the menu.\n")
        return run_menu()

    import anthropic  # noqa: F401  (client built via base._client)
    client = base._client()
    system = (
        "You are the assistant for a Banking ETL test-automation framework. You "
        "help the user run six agents: mapping document, test cases, test code, "
        "test data, test execution, and defect raising - plus a DB connection "
        "check and a full end-to-end pipeline. Use the tools to actually DO the "
        "work; never claim you ran something without calling the tool. After a "
        "tool runs, tell the user the artifact path(s) plainly. Keep replies short."
    )
    print("Chat mode. Type your request (or 'quit'). Examples: "
          "'generate the mapping document', 'run the tests then raise defects'.\n")
    messages = []
    while True:
        try:
            user = input("you> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nBye.")
            return
        if user.lower() in ("quit", "exit", "q"):
            print("Bye.")
            return
        if not user:
            continue
        messages.append({"role": "user", "content": user})

        # agentic loop: keep going until the model stops requesting tools
        while True:
            resp = client.messages.create(
                model=base.MODEL, max_tokens=1500, system=system,
                tools=_TOOLS, messages=messages)
            messages.append({"role": "assistant", "content": resp.content})

            tool_uses = [b for b in resp.content
                         if getattr(b, "type", None) == "tool_use"]
            # print any text the model said
            for b in resp.content:
                if getattr(b, "type", None) == "text" and b.text.strip():
                    print(f"assistant> {b.text.strip()}")

            if not tool_uses:
                break

            tool_results = []
            for tu in tool_uses:
                print(f"  [running tool: {tu.name}]")
                try:
                    result = _dispatch(tu.name, tu.input or {})
                except Exception as exc:
                    result = f"Tool failed: {exc}"
                tool_results.append({
                    "type": "tool_result", "tool_use_id": tu.id, "content": result})
            messages.append({"role": "user", "content": tool_results})


# --------------------------------------------------------------------------
# entry point
# --------------------------------------------------------------------------
def main():
    ap = argparse.ArgumentParser(description="Banking ETL AI Assistant.")
    ap.add_argument("--chat", action="store_true",
                    help="natural-language chat mode (needs ANTHROPIC_API_KEY)")
    ap.add_argument("--pipeline", action="store_true",
                    help="run the full pipeline once and exit (no menu)")
    ap.add_argument("--target", choices=["existing", "generated"],
                    default="existing", help="execution target for --pipeline")
    args = ap.parse_args()

    base.banner("Banking ETL Automation - AI Assistant")
    if args.pipeline:
        do_full_pipeline(target=args.target)
    elif args.chat:
        run_chat()
    else:
        run_menu()


if __name__ == "__main__":
    main()
