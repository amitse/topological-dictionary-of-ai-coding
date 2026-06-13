#!/usr/bin/env python3
"""
Fetch the latest curriculum and concept content from
mattpocock/dictionary-of-ai-coding and write the generated website data to
``docs/data.json``.

Usage:
    python scripts/fetch_content.py

Environment variables:
    GITHUB_TOKEN  Optional GitHub personal access token (increases rate limit)
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

SOURCE_REPO = "mattpocock/dictionary-of-ai-coding"
SOURCE_REPO_URL = f"https://github.com/{SOURCE_REPO}"
REPO_API = f"https://api.github.com/repos/{SOURCE_REPO}"
RAW_BASE = f"https://raw.githubusercontent.com/{SOURCE_REPO}/main"
CURRICULUM_URL = f"{RAW_BASE}/internal/Curriculum.md"
DATA_JSON = Path(__file__).parent.parent / "docs" / "data.json"
# Keep cards concise while preserving enough context for the modal detail view.
MAX_DESC_LENGTH = 520
MAX_BODY_LENGTH = 2400

SECTION_ICONS = {
    "The Model": "🧠",
    "Sessions, Context Windows & Turns": "💬",
    "Tools & Environment": "🛠️",
    "Failure Modes": "⚠️",
    "Handoffs": "🤲",
    "Memory and Steering": "🧭",
    "Patterns of Work": "⚙️",
}

# Fallback curriculum mirrors upstream internal/Curriculum.md and preserves the
# intended topological order when the network is unavailable.
FALLBACK_CURRICULUM = [
    {
        "id": 1,
        "title": "The Model",
        "icon": "🧠",
        "concepts": [
            "AI", "Model", "Parameters", "Training", "Inference", "Token",
            "Next-token prediction", "Non-determinism", "Model provider", "Harness",
            "Model provider request", "Input tokens", "Output tokens",
            "Prefix cache", "Cache tokens",
        ],
    },
    {
        "id": 2,
        "title": "Sessions, Context Windows & Turns",
        "icon": "💬",
        "concepts": [
            "Stateless", "Context", "Context window", "Stateful", "Agent",
            "System prompt", "Session", "Turn",
        ],
    },
    {
        "id": 3,
        "title": "Tools & Environment",
        "icon": "🛠️",
        "concepts": [
            "Environment", "Filesystem", "Tool", "Tool call", "Tool result",
            "MCP", "Permission request", "Permission mode", "Agent mode", "Sandbox",
        ],
    },
    {
        "id": 4,
        "title": "Failure Modes",
        "icon": "⚠️",
        "concepts": [
            "Sycophancy", "Hallucination", "Parametric knowledge", "Knowledge cutoff",
            "Contextual knowledge", "Attention relationship", "Attention budget",
            "Attention degradation", "Smart zone",
        ],
    },
    {
        "id": 5,
        "title": "Handoffs",
        "icon": "🤲",
        "concepts": [
            "Clearing", "Handoff", "Primary source", "Secondary source",
            "Handoff artifact", "Spec", "Ticket", "Compaction", "Autocompact",
        ],
    },
    {
        "id": 6,
        "title": "Memory and Steering",
        "icon": "🧭",
        "concepts": [
            "Memory system", "AGENTS.md", "Progressive disclosure", "Context pointer",
            "Skill", "Subagent",
        ],
    },
    {
        "id": 7,
        "title": "Patterns of Work",
        "icon": "⚙️",
        "concepts": [
            "Human-in-the-loop", "AFK", "Automated check", "Automated review",
            "Human review", "Vibe coding", "Design concept", "Grilling",
            "Prototyping", "DX", "AX",
        ],
    },
]

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

QUIZZES: dict[int, list[dict[str, Any]]] = {
    1: [
        {
            "question": "What is the atomic unit a language model reads and writes?",
            "options": ["Token", "Pixel", "Byte", "Word"],
            "answer": 0,
            "explanation": "A token is the atomic unit — roughly word-sized but not exactly.",
        },
        {
            "question": "What wraps a model with tools, system prompt, and context management to make it an agent?",
            "options": ["Session", "Harness", "Sandbox", "Training"],
            "answer": 1,
            "explanation": "The harness is everything around the model that turns it into an agent.",
        },
        {
            "question": "What changes during inference?",
            "options": ["The model's parameters", "The training set", "The generated output tokens", "The provider's source code"],
            "answer": 2,
            "explanation": "Inference runs fixed parameters to generate output tokens; training is what changes parameters.",
        },
        {
            "question": "Why can identical prompts produce different responses?",
            "options": ["Because tools always mutate state", "Because files are reread randomly", "Because prompts are discarded", "Because next-token sampling is non-deterministic"],
            "answer": 3,
            "explanation": "Non-determinism means the same context can sample different next tokens.",
        },
    ],
    2: [
        {
            "question": "What is the finite space the model sees on every single request?",
            "options": ["Context window", "System prompt", "Session history", "Memory system"],
            "answer": 0,
            "explanation": "The context window is the finite surface through which the model perceives anything.",
        },
        {
            "question": "What is a model harnessed with tools and a system prompt called?",
            "options": ["Harness", "Agent", "Session", "Turn"],
            "answer": 1,
            "explanation": "An agent is a model harnessed with tools, a system prompt, and context management.",
        },
        {
            "question": "What does stateless mean for the raw model?",
            "options": ["It saves every turn internally", "It mutates its parameters during a chat", "It carries no information between requests", "It can see the filesystem directly"],
            "answer": 2,
            "explanation": "The model has no hidden session memory; each request must resend the relevant context.",
        },
        {
            "question": "What is one turn in a coding-agent session?",
            "options": ["A complete project milestone", "A single token prediction", "A saved browser tab", "One user message plus the agent work before yielding back"],
            "answer": 3,
            "explanation": "A turn starts with a user message and includes all agent work until it yields back.",
        },
    ],
    3: [
        {
            "question": "What is a tool call in AI agent systems?",
            "options": ["The model's output naming a tool and its arguments", "A harness function that runs shell commands", "A user request to execute external code", "An API call to a remote service endpoint"],
            "answer": 0,
            "explanation": "A tool call is structured model output; the harness reads and executes it.",
        },
        {
            "question": "What protocol allows external servers to plug tools into a harness?",
            "options": ["API — Application Program Interface", "MCP — Model Context Protocol", "CLI — Command Line Interface", "SDK — Software Development Kit"],
            "answer": 1,
            "explanation": "MCP is the protocol for plugging external tool servers into a harness.",
        },
        {
            "question": "What is the environment in an agent run?",
            "options": ["Only the model provider's GPU cluster", "Only the browser UI", "The world the agent can perceive and act on through tools", "A list of cached prompts"],
            "answer": 2,
            "explanation": "The environment is what the agent works in through tool results and tool calls.",
        },
        {
            "question": "What does a permission request do?",
            "options": ["Deletes the context window", "Changes the model's training data", "Publishes the final answer", "Pauses before a gated tool call and asks the user"],
            "answer": 3,
            "explanation": "Permission requests gate actions the harness is not allowed to run automatically.",
        },
    ],
    4: [
        {
            "question": "What is the term for confidently wrong model output?",
            "options": ["Hallucination", "Sycophancy", "Degradation", "Compaction"],
            "answer": 0,
            "explanation": "Hallucination is confidently wrong output, including made-up facts or ignored context.",
        },
        {
            "question": "What is contextual knowledge?",
            "options": ["Facts frozen in model weights", "Information supplied in the current context window", "The provider's pricing table", "The user's long-term browser history"],
            "answer": 1,
            "explanation": "Contextual knowledge is knowledge the model can use because it is present in the current context.",
        },
        {
            "question": "As a session grows longer, what tends to happen to meaningful attention relationships?",
            "options": ["They become permanently cached", "They reset after each tool call", "They weaken as attention budget spreads over more tokens", "They update the model parameters"],
            "answer": 2,
            "explanation": "Attention degradation weakens signal as more tokens compete for attention.",
        },
        {
            "question": "What is sycophancy?",
            "options": ["A deterministic build failure", "A provider-side cache hit", "A context-window limit", "Confidently agreeable output that favors agreement over correction"],
            "answer": 3,
            "explanation": "Sycophancy is model behavior that over-agrees instead of correcting the user.",
        },
    ],
    5: [
        {
            "question": "What is an in-memory handoff where session history is summarized into a fresh session?",
            "options": ["Compaction", "Clearing", "Spec", "Ticket"],
            "answer": 0,
            "explanation": "Compaction summarizes prior session history to seed a fresh session.",
        },
        {
            "question": "What kind of artifact describes a multi-session piece of work?",
            "options": ["Ticket", "Spec", "Handoff", "Artifact"],
            "answer": 1,
            "explanation": "A spec captures the design concept for work that spans sessions.",
        },
        {
            "question": "What is a primary source in a handoff?",
            "options": ["A rewritten summary with no links", "A model's guess about code", "The original artifact or system of record", "A stale browser cache"],
            "answer": 2,
            "explanation": "Primary sources are the original artifacts future agents should trust most.",
        },
        {
            "question": "What does clearing do?",
            "options": ["Adds a new MCP server", "Creates a Git tag", "Runs a linter", "Drops current session context so the next run starts fresh"],
            "answer": 3,
            "explanation": "Clearing removes accumulated session state so future work starts from a clean context.",
        },
    ],
    6: [
        {
            "question": "Which file does a harness load into context at session start as a project brief?",
            "options": ["AGENTS.md", "README.md", "SKILLS.md", "CONTEXT.md"],
            "answer": 0,
            "explanation": "AGENTS.md is a standing project brief loaded by compatible harnesses.",
        },
        {
            "question": "What is an agent spawned by another agent via a tool call?",
            "options": ["Session", "Subagent", "Harness", "Context"],
            "answer": 1,
            "explanation": "A subagent runs in its own session and reports back as a tool result.",
        },
        {
            "question": "What does progressive disclosure optimize?",
            "options": ["Showing every document all the time", "Maximizing output tokens", "Loading only the context needed right now", "Disabling memory systems"],
            "answer": 2,
            "explanation": "Progressive disclosure keeps context focused and points to additional details only when needed.",
        },
        {
            "question": "What is a context pointer?",
            "options": ["A model parameter", "A browser cookie", "A random quiz answer", "A reference that tells the agent where to pull more context from"],
            "answer": 3,
            "explanation": "Context pointers let an agent load deeper context only when the task calls for it.",
        },
    ],
}


def make_request(url: str) -> dict[str, Any] | list[Any] | str:
    req = urllib.request.Request(url)
    req.add_header("Accept", "application/vnd.github.v3+json")
    req.add_header("User-Agent", "topological-dictionary-sync/2.0")
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
    return re.sub(r" +", "-", s.strip())


def parse_frontmatter(content: str) -> tuple[dict[str, str], str]:
    """Extract YAML-ish frontmatter and body from a markdown file."""
    meta: dict[str, str] = {}
    if content.startswith("---"):
        parts = content.split("---", 2)
        if len(parts) >= 3:
            fm = parts[1].strip()
            body = parts[2].strip()
            for line in fm.splitlines():
                if ":" in line:
                    key, _, value = line.partition(":")
                    meta[key.strip()] = value.strip()
            return meta, body
    return meta, content.strip()


def markdown_to_plain_text(text: str) -> str:
    """Strip the simple Markdown patterns used in upstream dictionary entries."""
    text = re.sub(r"```.*?```", "", text, flags=re.DOTALL)
    text = re.sub(r"`([^`]+)`", r"\1", text)
    text = re.sub(r"\[([^\]]+)\]\([^\)]+\)", r"\1", text)
    text = re.sub(r"\*\*([^\*]+)\*\*", r"\1", text)
    text = re.sub(r"\*([^\*]+)\*", r"\1", text)
    return text


def first_paragraph(text: str) -> str:
    """Extract the first real paragraph, skipping headings and empty lines."""
    para_lines: list[str] = []
    in_para = False
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped:
            if in_para:
                break
            continue
        if stripped.startswith("#"):
            continue
        para_lines.append(stripped)
        in_para = True

    full = markdown_to_plain_text(" ".join(para_lines))
    sentences = re.split(r"(?<=[.!?]) +", full)
    desc = " ".join(sentences[:3])
    if len(desc) > MAX_DESC_LENGTH:
        desc = desc[:MAX_DESC_LENGTH - 3] + "..."
    return desc


def full_body(text: str) -> str:
    """Return shallow-but-useful full concept body for detail views."""
    lines = [line.strip() for line in text.splitlines() if line.strip() and not line.strip().startswith("#")]
    body = markdown_to_plain_text("\n\n".join(lines))
    return body[:MAX_BODY_LENGTH] + ("..." if len(body) > MAX_BODY_LENGTH else "")


def parse_aliases(raw: str) -> list[str]:
    if not raw:
        return []
    if raw.startswith("["):
        return [a.strip().strip("'\"") for a in raw.strip("[]").split(",") if a.strip()]
    return [raw.strip().strip("'\"")]


def parse_curriculum(markdown: str) -> list[dict[str, Any]]:
    """Parse upstream curriculum headings, accepting em dash or copied hyphen separators."""
    sections: list[dict[str, Any]] = []
    current: dict[str, Any] | None = None
    # Upstream uses an em dash; allow hyphen-minus too so copied curriculum
    # markdown can still be parsed during local/manual sync runs.
    heading_re = re.compile(r"^##\s+Section\s+(\d+)\s+[—-]\s+(.+)$")

    for line in markdown.splitlines():
        heading = heading_re.match(line.strip())
        if heading:
            if current:
                sections.append(current)
            title = heading.group(2).strip()
            current = {
                "id": int(heading.group(1)),
                "title": title,
                "icon": SECTION_ICONS.get(title, "📚"),
                "concepts": [],
            }
            continue
        if current and line.strip().startswith("- "):
            current["concepts"].append(line.strip()[2:].strip())

    if current:
        sections.append(current)

    if not sections or any(not section["concepts"] for section in sections):
        raise ValueError("Curriculum did not contain usable sections")
    return sorted(sections, key=lambda section: section["id"])


def fetch_curriculum() -> list[dict[str, Any]]:
    print("Fetching topological curriculum order from upstream…")
    try:
        content = make_request(CURRICULUM_URL)
        if not isinstance(content, str):
            raise ValueError(f"Expected curriculum markdown, got {type(content).__name__}")
        curriculum = parse_curriculum(content)
        print(f"  Loaded {len(curriculum)} curriculum sections.")
        return curriculum
    except Exception as exc:
        print(f"  ⚠ Could not fetch curriculum: {exc}; using fallback order.", file=sys.stderr)
        return FALLBACK_CURRICULUM


def fetch_concepts(curriculum: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    """Return {title -> {desc, body, aliases, sourceUrl}} for curriculum concepts."""
    print("Fetching curriculum concept markdown from raw GitHub content…")
    titles = [title for section in curriculum for title in section["concepts"]]
    results: dict[str, dict[str, Any]] = {}

    for title in titles:
        filename = f"{title}.md"
        source_path = urllib.parse.quote(filename)
        raw_url = f"{RAW_BASE}/dictionary/{source_path}"
        try:
            content = make_request(raw_url)
            if not isinstance(content, str):
                raise ValueError(f"Expected str response, got {type(content).__name__}")
        except Exception as exc:
            print(f"  ⚠ Could not fetch {filename}: {exc}", file=sys.stderr)
            continue

        meta, body = parse_frontmatter(content)
        results[title] = {
            "desc": first_paragraph(body),
            "body": full_body(body),
            "aliases": parse_aliases(meta.get("aliases", "")),
            "sourceUrl": f"{SOURCE_REPO_URL}/blob/main/dictionary/{source_path}",
        }

    print(f"  Fetched {len(results)} of {len(titles)} concepts.")
    return results


def quiz_fingerprint(quiz: list[dict[str, Any]] | None) -> str | None:
    """Return a stable version seed for deterministic client-side quiz shuffling."""
    if quiz is None:
        return None
    digest = hashlib.sha256(json.dumps(quiz, sort_keys=True).encode("utf-8")).hexdigest()
    return digest[:12]


def build_site_data(curriculum: list[dict[str, Any]], concept_data: dict[str, dict[str, Any]]) -> dict[str, Any]:
    sections: list[dict[str, Any]] = []
    missing: list[str] = []

    for section in curriculum:
        concepts: list[dict[str, Any]] = []
        for position, title in enumerate(section["concepts"], start=1):
            data = concept_data.get(title, {})
            if not data:
                missing.append(title)
            concepts.append({
                "id": make_id(title),
                "title": title,
                "icon": CONCEPT_ICONS.get(title, "📌"),
                "desc": data.get("desc", f"{title} — a key concept in AI coding."),
                "body": data.get("body", data.get("desc", f"{title} — a key concept in AI coding.")),
                "aliases": data.get("aliases", []),
                "sourceUrl": data.get("sourceUrl", f"{SOURCE_REPO_URL}/tree/main/dictionary"),
                "topologicalIndex": position,
            })

        quiz = QUIZZES.get(section["id"])
        sections.append({
            "id": section["id"],
            "title": section["title"],
            "icon": section.get("icon") or SECTION_ICONS.get(section["title"], "📚"),
            "concepts": concepts,
            "quiz": quiz,
            "quizVersion": quiz_fingerprint(quiz),
        })

    if missing:
        print("  ⚠ Missing upstream concept data for: " + ", ".join(missing), file=sys.stderr)

    return {
        "schemaVersion": 2,
        "source": {
            "repository": SOURCE_REPO,
            "url": SOURCE_REPO_URL,
            "curriculumUrl": f"{SOURCE_REPO_URL}/blob/main/internal/Curriculum.md",
        },
        "sections": sections,
    }


def write_data_json(data: dict[str, Any]) -> None:
    DATA_JSON.parent.mkdir(parents=True, exist_ok=True)
    DATA_JSON.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Updated {DATA_JSON}")


def main() -> None:
    curriculum = fetch_curriculum()
    concept_data = fetch_concepts(curriculum)
    if not concept_data:
        print("No concept data fetched — keeping existing data.json.", file=sys.stderr)
        sys.exit(0)

    write_data_json(build_site_data(curriculum, concept_data))
    print("Done ✓")


if __name__ == "__main__":
    main()
