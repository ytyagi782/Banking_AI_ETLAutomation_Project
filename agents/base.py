"""
agents/base.py
==============
The shared foundation every AI agent imports. It answers three questions:

  1. Where is the Claude API key, and do we have one?
  2. How do I call Claude - for plain text, and for STRUCTURED (validated) output?
  3. Where do the agents write their artifacts, and how are files timestamped?

Golden rule (see agents/__init__.py):

    Claude GENERATES and REASONS.   The framework EXECUTES and VERIFIES.

Every agent in this package is deliberately written so it still produces a
useful artifact WITHOUT an API key (deterministic fallback from config + DB).
When ANTHROPIC_API_KEY is present, Claude ENRICHES that artifact. Ask helpers
below make that pattern easy: call `have_api_key()` first, then either
`ask_claude(...)` / `ask_claude_json(...)` or your own fallback.
"""

import os
import re
import glob
import datetime

from dotenv import load_dotenv

from utilities import config_loader
from utilities.logger import get_logger

log = get_logger()

# Artifact versioning (same idea as the logger / report versioning):
#   files are named <prefix>_<N><ext> where N cycles 1..VERSION_CYCLE and then
#   restarts at 1; only the newest KEEP_VERSIONS of each prefix are kept.
VERSION_CYCLE = 5
KEEP_VERSIONS = 2

# Load the .env file at import time so ANTHROPIC_API_KEY / EMAIL_APP_PASSWORD
# are available to every agent (same file the reporting engine already uses).
load_dotenv(config_loader.abs_path(".env"))

# The model the whole package talks to. Keep this in ONE place.
MODEL = "claude-opus-4-8"

# Where agents write their artifacts (all git-ignored - see .gitignore).
OUTPUT_DIR = config_loader.abs_path("agents", "output")
TESTDATA_DIR = os.path.join(OUTPUT_DIR, "testdata")
GENERATED_TESTS_DIR = config_loader.abs_path("agents", "generated_tests")

_API_KEY_ENV = "ANTHROPIC_API_KEY"


# --------------------------------------------------------------------------
# paths / timestamps
# --------------------------------------------------------------------------
def timestamp():
    """A filename-friendly timestamp, matching the reporting engine's format."""
    return datetime.datetime.now().strftime("%Y%m%d_%H%M%S")


def ensure_dir(path):
    """Create a directory (and parents) if it does not exist. Returns the path."""
    os.makedirs(path, exist_ok=True)
    return path


def output_path(filename):
    """Absolute path inside agents/output/ (the folder is created if missing)."""
    ensure_dir(OUTPUT_DIR)
    return os.path.join(OUTPUT_DIR, filename)


def latest_output(prefix, ext=".xlsx"):
    """
    Return the newest file in agents/output/ whose name starts with `prefix`
    and ends with `ext` (e.g. latest_output("TestCases_")). None if none exist.
    """
    matches = glob.glob(os.path.join(OUTPUT_DIR, f"{prefix}*{ext}"))
    return max(matches, key=os.path.getmtime) if matches else None


# --------------------------------------------------------------------------
# versioned artifacts:  <prefix>_<N><ext>   (N cycles 1..VERSION_CYCLE, keep KEEP_VERSIONS)
# --------------------------------------------------------------------------
def _versioned_files(prefix, ext, directory):
    """All files named <prefix>_<digits><ext> in the directory."""
    pat = re.compile(re.escape(prefix) + r"_(\d+)" + re.escape(ext) + r"$")
    return [f for f in glob.glob(os.path.join(directory, f"{prefix}_*{ext}"))
            if pat.search(os.path.basename(f))]


def next_version(prefix, ext, directory=None):
    """
    Next version number for <prefix><ext>, cycling 1..VERSION_CYCLE then back to
    1. "Latest" is the most recently written file (by mtime), so wrapping is
    handled correctly - same approach as utilities/logger._next_version.
    """
    directory = directory or OUTPUT_DIR
    files = _versioned_files(prefix, ext, directory)
    if not files:
        return 1
    newest = max(files, key=os.path.getmtime)
    m = re.search(r"_(\d+)" + re.escape(ext) + r"$", os.path.basename(newest))
    last = int(m.group(1)) if m else 0
    return (last % VERSION_CYCLE) + 1


def prune_versions(prefix, ext, directory=None):
    """Keep only the newest KEEP_VERSIONS files named <prefix>_<N><ext>."""
    directory = directory or OUTPUT_DIR
    files = sorted(_versioned_files(prefix, ext, directory),
                   key=os.path.getmtime, reverse=True)
    for old in files[KEEP_VERSIONS:]:
        try:
            os.remove(old)
        except OSError:
            pass


def versioned_output_path(prefix, ext, directory=None):
    """
    Return agents/output/<prefix>_<N><ext> for the next version N (folder made
    if missing). Write the file, then call prune_versions(prefix, ext) to drop
    anything beyond KEEP_VERSIONS.
    """
    directory = directory or OUTPUT_DIR
    ensure_dir(directory)
    v = next_version(prefix, ext, directory)
    return os.path.join(directory, f"{prefix}_{v}{ext}")


# --------------------------------------------------------------------------
# API key
# --------------------------------------------------------------------------
def have_api_key():
    """True if an Anthropic API key is configured (in .env or the environment)."""
    key = os.getenv(_API_KEY_ENV, "").strip()
    # ignore the documented placeholder value
    return bool(key) and not key.startswith("sk-ant-your_key")


def _require_key():
    if not have_api_key():
        raise RuntimeError(
            f"No Claude API key found. Set {_API_KEY_ENV} in your .env file "
            f"to enable AI generation. "
            f"Agents that support it will fall back to deterministic output; "
            f"this step needs the key."
        )


def _client():
    """Build an Anthropic client (imported lazily so the package loads w/o a key)."""
    _require_key()
    import anthropic
    return anthropic.Anthropic(api_key=os.getenv(_API_KEY_ENV).strip())


# --------------------------------------------------------------------------
# Claude calls
# --------------------------------------------------------------------------
def ask_claude(system, user, max_tokens=4000, temperature=0.2):
    """
    Ask Claude a question and return its plain-text answer.

    Raises a clear error if no API key is configured - callers that want a
    fallback should check `have_api_key()` first.
    """
    client = _client()
    log.info(f"[agents] Claude call ({MODEL}, max_tokens={max_tokens})")
    resp = client.messages.create(
        model=MODEL,
        max_tokens=max_tokens,
        temperature=temperature,
        system=system,
        messages=[{"role": "user", "content": user}],
    )
    # concatenate any text blocks in the response
    parts = [b.text for b in resp.content if getattr(b, "type", None) == "text"]
    return "".join(parts).strip()


def ask_claude_json(system, user, schema_model, max_tokens=4000, temperature=0.2):
    """
    Ask Claude for STRUCTURED output validated against a pydantic model.

    We give the model a single tool whose input schema IS the pydantic model's
    JSON schema and force it to call that tool (tool_choice). The tool input is
    then validated by pydantic, so callers get a typed object back - no brittle
    string parsing.

    `schema_model` is a pydantic BaseModel subclass. Returns an instance of it.
    """
    client = _client()
    schema = schema_model.model_json_schema()
    tool_name = "emit_" + schema_model.__name__.lower()

    log.info(f"[agents] Claude structured call ({MODEL}) -> {schema_model.__name__}")
    resp = client.messages.create(
        model=MODEL,
        max_tokens=max_tokens,
        temperature=temperature,
        system=system,
        tools=[{
            "name": tool_name,
            "description": f"Return the result as a {schema_model.__name__} object.",
            "input_schema": schema,
        }],
        tool_choice={"type": "tool", "name": tool_name},
        messages=[{"role": "user", "content": user}],
    )
    for block in resp.content:
        if getattr(block, "type", None) == "tool_use" and block.name == tool_name:
            return schema_model.model_validate(block.input)
    raise RuntimeError("Claude did not return the expected structured tool call.")


# --------------------------------------------------------------------------
# small shared console helper (keeps every agent's CLI output consistent)
# --------------------------------------------------------------------------
def banner(title):
    """Print (and log) a consistent section banner used by every agent's main()."""
    line = "=" * 70
    print(line)
    print(title)
    print(line)
    log.info(title)


def ai_status():
    """One-line human summary of whether AI enrichment is available."""
    return ("Claude AI: ENABLED (key found - output will be AI-enriched)"
            if have_api_key()
            else "Claude AI: OFF (no ANTHROPIC_API_KEY - using deterministic fallback)")
