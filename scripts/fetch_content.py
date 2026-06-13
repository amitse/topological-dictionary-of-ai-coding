#!/usr/bin/env python3
"""
Fetch the latest content from mattpocock/dictionary-of-ai-coding and
update the embedded concept data inside docs/index.html.

Usage:
    python scripts/fetch_content.py

Environment variables:
    GITHUB_TOKEN  Optional GitHub personal access token (increases rate limit)
"""

import json
import os
import re
import sys
import urllib.request
import urllib.error
from pathlib import Path

REPO_API = "https://api.github.com/repos/mattpocock/dictionary-of-ai-coding"
RAW_BASE = "https://raw.githubusercontent.com/mattpocock/dictionary-of-ai-coding/main"
DOCS_INDEX = Path(__file__).parent.parent / "docs" / "index.html"

# Curriculum order from internal/Curriculum.md
CURRICULUM = {
    1: {
        "title": "The Model",
        "icon": "🧠",
        "concepts": [
            "AI", "Model", "Parameters", "Training", "Inference", "Token",
            "Next-token prediction", "Non-determinism", "Model provider", "Harness",
            "Model provider request", "Input tokens", "Output tokens",
            "Prefix cache", "Cache tokens",
        ],
    },
    2: {
        "title": "Sessions, Context Windows & Turns",
        "icon": "💬",
        "concepts": [
            "Stateless", "Context", "Context window", "Stateful", "Agent",
            "System prompt", "Session", "Turn",
        ],
    },
    3: {
        "title": "Tools & Environment",
        "icon": "🛠️",
        "concepts": [
            "Environment", "Filesystem", "Tool", "Tool call", "Tool result",
            "MCP", "Permission request", "Permission mode", "Agent mode", "Sandbox",
        ],
    },
    4: {
        "title": "Failure Modes",
        "icon": "⚠️",
        "concepts": [
            "Sycophancy", "Hallucination", "Parametric knowledge", "Knowledge cutoff",
            "Contextual knowledge", "Attention relationship", "Attention budget",
            "Attention degradation", "Smart zone",
        ],
    },
    5: {
        "title": "Handoffs",
        "icon": "🤲",
        "concepts": [
            "Clearing", "Handoff", "Primary source", "Secondary source",
            "Handoff artifact", "Spec", "Ticket", "Compaction", "Autocompact",
        ],
    },
    6: {
        "title": "Memory and Steering",
        "icon": "🧭",
        "concepts": [
            "Memory system", "AGENTS.md", "Progressive disclosure",
            "Context pointer", "Skill", "Subagent",
        ],
    },
    7: {
        "title": "Patterns of Work",
        "icon": "⚙️",
        "concepts": [
            "Human-in-the-loop", "AFK", "Automated check", "Automated review",
            "Human review", "Vibe coding", "Design concept", "Grilling",
            "Prototyping", "DX", "AX",
        ],
    },
}

CONCEPT_ICONS = {
    "AI": "🤖", "Model": "⚙️", "Parameters": "🔢", "Training": "🏋️",
    "Inference": "⚡", "Token": "🔤", "Next-token prediction": "🎯",
    "Non-determinism": "🎲", "Model provider": "☁️", "Harness": "🔧",
    "Model provider request": "📡", "Input tokens": "📥", "Output tokens": "📤",
    "Prefix cache": "💾", "Cache tokens": "🏪", "Stateless": "🧹",
    "Context": "📖", "Context window": "🪟", "Stateful": "🗃️", "Agent": "🤝",
    "System prompt": "📋", "Session": "⏱️", "Turn": "🔄", "Environment": "🌍",
    "Filesystem": "📁", "Tool": "🔨", "Tool call": "📞", "Tool result": "📬",
    "MCP": "🔌", "Permission request": "🙋", "Permission mode": "🔐",
    "Agent mode": "🎚️", "Sandbox": "📦", "Sycophancy": "🪞",
    "Hallucination": "👻", "Parametric knowledge": "📚", "Knowledge cutoff": "📅",
    "Contextual knowledge": "🔍", "Attention relationship": "🕸️",
    "Attention budget": "💰", "Attention degradation": "📉", "Smart zone": "🎯",
    "Clearing": "🧽", "Handoff": "🏃", "Primary source": "📜",
    "Secondary source": "📝", "Handoff artifact": "📄", "Spec": "📐",
    "Ticket": "🎫", "Compaction": "🗜️", "Autocompact": "🤖",
    "Memory system": "🗄️", "AGENTS.md": "📘", "Progressive disclosure": "🎭",
    "Context pointer": "👉", "Skill": "🎓", "Subagent": "🤖",
    "Human-in-the-loop": "👩‍💻", "AFK": "🚶", "Automated check": "✅",
    "Automated review": "🔍", "Human review": "👀", "Vibe coding": "🎸",
    "Design concept": "💡", "Grilling": "🔥", "Prototyping": "🧪",
    "DX": "🧑‍🔧", "AX": "🤖",
}


def make_request(url: str) -> dict | list | str:
    req = urllib.request.Request(url)
    req.add_header("Accept", "application/vnd.github.v3+json")
    req.add_header("User-Agent", "topological-dictionary-sync/1.0")
    token = os.environ.get("GITHUB_TOKEN", "")
    if token:
        req.add_header("Authorization", "token " + token)
    with urllib.request.urlopen(req) as resp:
        body = resp.read().decode("utf-8")
        content_type = resp.headers.get("Content-Type", "")
        if "json" in content_type:
            return json.loads(body)
        return body


def make_id(title: str) -> str:
    """Convert a concept title to a URL-friendly id."""
    s = title.lower()
    s = re.sub(r"[^a-z0-9 ]", "", s)
    s = re.sub(r" +", "-", s.strip())
    return s


def parse_frontmatter(content: str) -> tuple[dict, str]:
    """Extract YAML-ish frontmatter and body from a markdown file."""
    meta: dict = {}
    if content.startswith("---"):
        parts = content.split("---", 2)
        if len(parts) >= 3:
            fm = parts[1].strip()
            body = parts[2].strip()
            for line in fm.splitlines():
                if ":" in line:
                    k, _, v = line.partition(":")
                    meta[k.strip()] = v.strip()
            return meta, body
    return meta, content.strip()


def first_paragraph(text: str) -> str:
    """Extract the first real paragraph (skip headings and empty lines)."""
    lines = text.splitlines()
    para_lines = []
    in_para = False
    for line in lines:
        stripped = line.strip()
        if not stripped:
            if in_para:
                break
            continue
        if stripped.startswith("#"):
            continue
        para_lines.append(stripped)
        in_para = True

    full = " ".join(para_lines)
    # Strip markdown links → plain text
    full = re.sub(r"\[([^\]]+)\]\([^\)]+\)", r"\1", full)
    # Strip bold/italic
    full = re.sub(r"\*\*([^\*]+)\*\*", r"\1", full)
    full = re.sub(r"\*([^\*]+)\*", r"\1", full)

    # Take up to 3 sentences
    sentences = re.split(r"(?<=[.!?]) +", full)
    desc = " ".join(sentences[:3])
    if len(desc) > 400:
        desc = desc[:397] + "..."
    return desc


def fetch_concepts() -> dict:
    """Return {title -> {desc, aliases}} for all concept files."""
    print("Fetching concept file list from GitHub API…")
    try:
        files = make_request(f"{REPO_API}/contents/dictionary")
    except Exception as exc:
        print(f"  ⚠ Could not fetch file list: {exc}", file=sys.stderr)
        return {}

    results: dict = {}
    for item in files:
        if item.get("type") != "file" or not item["name"].endswith(".md"):
            continue
        title = item["name"][:-3]  # strip .md
        raw_url = item.get("download_url")
        if not raw_url:
            raw_url = f"{RAW_BASE}/dictionary/{urllib.request.quote(item['name'])}"
            print(f"  ℹ Using fallback URL for {item['name']}", file=sys.stderr)
        try:
            content = make_request(raw_url)
            if not isinstance(content, str):
                raise ValueError(f"Expected str response, got {type(content).__name__}")
        except Exception as exc:
            print(f"  ⚠ Could not fetch {item['name']}: {exc}", file=sys.stderr)
            continue

        meta, body = parse_frontmatter(content)
        desc = first_paragraph(body)
        aliases_raw = meta.get("aliases", "")
        aliases = []
        if aliases_raw.startswith("["):
            # e.g. [foo, bar, baz]
            aliases = [a.strip().strip("'\"") for a in aliases_raw.strip("[]").split(",") if a.strip()]

        results[title] = {"desc": desc, "aliases": aliases}

    print(f"  Fetched {len(results)} concepts.")
    return results


def build_sections_js(concept_data: dict) -> str:
    """Build the JavaScript SECTIONS array literal for embedding in index.html."""
    # Keep existing quiz questions — they are editorial, not sourced from upstream
    QUIZZES = {
        1: [
            {
                "question": "What is the atomic unit a language model reads and writes?",
                "options": ["Token", "Pixel", "Byte", "Word"],
                "answer": 0,
                "explanation": "A token is the atomic unit — roughly word-sized but not exactly. Common words are one token; rare or long words split into several.",
            },
            {
                "question": "What wraps a model with tools, system prompt, and context management to make it an agent?",
                "options": ["Harness", "Session", "Sandbox", "Training"],
                "answer": 0,
                "explanation": "The harness is everything around the model that turns it into an agent — tools, system prompt, context-window management, permissions.",
            },
        ],
        2: [
            {
                "question": "What is the finite space the model sees on every single request?",
                "options": ["Context window", "System prompt", "Session history", "Memory system"],
                "answer": 0,
                "explanation": "The context window is everything the model sees on each request — it's finite and model-specific, the only surface through which the model perceives anything.",
            },
            {
                "question": "What is a model harnessed with tools and a system prompt called?",
                "options": ["Agent", "Harness", "Session", "Turn"],
                "answer": 0,
                "explanation": "An agent is a model harnessed with tools, a system prompt, and a context window, that takes turns with a user.",
            },
        ],
        3: [
            {
                "question": "What is a tool call in AI agent systems?",
                "options": [
                    "The model's output naming a tool and its arguments",
                    "A harness function that runs shell commands",
                    "A user request to execute external code",
                    "An API call to a remote service endpoint",
                ],
                "answer": 0,
                "explanation": "A tool call is the model's output naming a tool and its arguments — just structured text. The harness has to read it and execute it.",
            },
            {
                "question": "What protocol allows external servers to plug tools into a harness?",
                "options": [
                    "MCP — Model Context Protocol",
                    "API — Application Program Interface",
                    "CLI — Command Line Interface",
                    "SDK — Software Development Kit",
                ],
                "answer": 0,
                "explanation": "MCP (Model Context Protocol) is the protocol for plugging external tool servers into a harness.",
            },
        ],
        4: [
            {
                "question": "What is the term for confidently wrong model output?",
                "options": ["Hallucination", "Sycophancy", "Degradation", "Compaction"],
                "answer": 0,
                "explanation": "Hallucination is confidently-wrong model output — either made-up facts (parametric confabulation) or ignoring given context (faithfulness hallucination).",
            },
            {
                "question": "As a session grows longer, the signal from meaningful attention relationships tends to what?",
                "options": [
                    "Shrink as budget spreads over more tokens",
                    "Grow stronger with more context available",
                    "Stay perfectly consistent throughout the run",
                    "Reset automatically after every tool call",
                ],
                "answer": 0,
                "explanation": "Attention degradation: as the session grows, each token's attention budget spreads across more competitors, weakening the signal on any one meaningful relationship.",
            },
        ],
        5: [
            {
                "question": "What is the term for an in-memory handoff where session history is summarized into a fresh session?",
                "options": ["Compaction", "Clearing", "Spec", "Ticket"],
                "answer": 0,
                "explanation": "Compaction is a handoff done in-memory — the previous session's history is summarised and the summary seeds a fresh session.",
            },
            {
                "question": "What type of handoff artifact describes a multi-session piece of work?",
                "options": ["Spec", "Ticket", "Handoff", "Artifact"],
                "answer": 0,
                "explanation": "A spec is a handoff artifact describing a multi-session piece of work — what's being built, not how each session does its share.",
            },
        ],
        6: [
            {
                "question": "Which file does a harness load into context at the start of each session as a project brief?",
                "options": ["AGENTS.md", "README.md", "SKILLS.md", "CONTEXT.md"],
                "answer": 0,
                "explanation": "AGENTS.md is loaded by the harness into the context window at session start — the project's standing brief to the agent.",
            },
            {
                "question": "What is an agent spawned by another agent via a tool call?",
                "options": ["Subagent", "Session", "Harness", "Context"],
                "answer": 0,
                "explanation": "A subagent is an agent spawned by another agent via a tool call — runs in its own session and reports a single tool result back.",
            },
        ],
    }

    sections_list = []
    for sec_id, sec_info in sorted(CURRICULUM.items()):
        concepts_list = []
        for title in sec_info["concepts"]:
            cid = make_id(title)
            icon = CONCEPT_ICONS.get(title, "📌")
            data = concept_data.get(title, {})
            desc = data.get("desc", f"{title} — a key concept in AI coding.")
            aliases = data.get("aliases", [])
            # JS-escape
            desc_esc = desc.replace("\\", "\\\\").replace('"', '\\"').replace("\n", " ")
            aliases_js = json.dumps(aliases)
            concepts_list.append(
                f'      {{ id: "{cid}", title: "{title}", icon: "{icon}", '
                f'desc: "{desc_esc}", aliases: {aliases_js} }}'
            )

        concepts_js = ",\n".join(concepts_list)
        quiz = QUIZZES.get(sec_id)
        quiz_js = json.dumps(quiz, indent=6) if quiz else "null"

        sections_list.append(
            f"""  {{
    id: {sec_id},
    title: "{sec_info["title"]}",
    icon: "{sec_info["icon"]}",
    concepts: [
{concepts_js}
    ],
    quiz: {quiz_js}
  }}"""
        )

    return "const SECTIONS = [\n" + ",\n".join(sections_list) + "\n];"


SECTIONS_START = "// ============================================================\n// DATA — auto-updated by .github/workflows/sync.yml"
SECTIONS_END = "// ============================================================\n// STATE"


def update_index_html(new_sections_js: str) -> None:
    html = DOCS_INDEX.read_text(encoding="utf-8")

    start_idx = html.find(SECTIONS_START)
    end_idx = html.find(SECTIONS_END)

    if start_idx == -1 or end_idx == -1:
        print("ERROR: Could not find data markers in index.html", file=sys.stderr)
        sys.exit(1)

    new_block = (
        SECTIONS_START
        + "\n"
        + new_sections_js
        + "\n"
    )

    updated = html[:start_idx] + new_block + html[end_idx:]
    DOCS_INDEX.write_text(updated, encoding="utf-8")
    print(f"Updated {DOCS_INDEX}")


def main() -> None:
    concept_data = fetch_concepts()
    if not concept_data:
        print("No concept data fetched — keeping existing data in index.html.", file=sys.stderr)
        sys.exit(0)

    new_sections_js = build_sections_js(concept_data)
    update_index_html(new_sections_js)
    print("Done ✓")


if __name__ == "__main__":
    main()
