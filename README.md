# Topological Dictionary of AI Coding

A **static tech tree website** built from the vocabulary of
[mattpocock/dictionary-of-ai-coding](https://github.com/mattpocock/dictionary-of-ai-coding),
topologically sorted into a progressive learning path and deployed via GitHub Pages.

🌐 **Live site →** https://amitse.github.io/topological-dictionary-of-ai-coding/

---

## What is this?

The [AI Coding Dictionary](https://github.com/mattpocock/dictionary-of-ai-coding) by Matt Pocock
defines 68 core concepts for understanding AI coding — from tokens and models to agents, handoffs,
and working patterns.

This repository takes those concepts and:

1. **Topologically sorts** them into 7 sections using the upstream curriculum order
   (you need to understand _The Model_ before you can understand _Sessions_, which precede _Tools_,
   and so on).
2. **Presents them as a tech tree** — an interactive website where each section is locked until
   you demonstrate understanding of the previous one.
3. **Unlocks via quiz** — each section transition requires passing a short 2-question quiz
   (inspired by the [teach skill](https://github.com/mattpocock/skills/tree/main/skills/productivity/teach)).
   Progress is stored in your browser's `localStorage`.
4. **Stays up to date** — a GitHub Action fetches the upstream curriculum and concept Markdown,
   writes the generated JSON data, and deploys the site every Monday morning.

## Section Map (Topological Order)

| # | Section | Concepts |
|---|---------|----------|
| 1 | 🧠 The Model | AI, Model, Parameters, Training, Inference, Token, Next-token prediction, Non-determinism, Model provider, Harness, Model provider request, Input tokens, Output tokens, Prefix cache, Cache tokens |
| 2 | 💬 Sessions, Context Windows & Turns | Stateless, Context, Context window, Stateful, Agent, System prompt, Session, Turn |
| 3 | 🛠️ Tools & Environment | Environment, Filesystem, Tool, Tool call, Tool result, MCP, Permission request, Permission mode, Agent mode, Sandbox |
| 4 | ⚠️ Failure Modes | Sycophancy, Hallucination, Parametric knowledge, Knowledge cutoff, Contextual knowledge, Attention relationship, Attention budget, Attention degradation, Smart zone |
| 5 | 🤲 Handoffs | Clearing, Handoff, Primary source, Secondary source, Handoff artifact, Spec, Ticket, Compaction, Autocompact |
| 6 | 🧭 Memory and Steering | Memory system, AGENTS.md, Progressive disclosure, Context pointer, Skill, Subagent |
| 7 | ⚙️ Patterns of Work | Human-in-the-loop, AFK, Automated check, Automated review, Human review, Vibe coding, Design concept, Grilling, Prototyping, DX, AX |

## Repository Structure

```
docs/
  index.html          # Self-contained static website (served by GitHub Pages)
  data.json           # Generated topological curriculum, concept content, and quizzes
scripts/
  fetch_content.py    # Fetches latest upstream content and updates docs/data.json
.github/workflows/
  pages.yml           # Deploys docs/ to GitHub Pages on push to main
  sync.yml            # Runs every Monday — syncs concept content from source repo
```

## Running the Sync Locally

```bash
# Optional: set GITHUB_TOKEN to avoid rate limits
export GITHUB_TOKEN=your_token_here
python scripts/fetch_content.py
```

Then serve the `docs/` directory with any static file server so `index.html` can fetch
`data.json`.

## Source

Content © [Matt Pocock](https://github.com/mattpocock) /
[dictionary-of-ai-coding](https://github.com/mattpocock/dictionary-of-ai-coding)
— used under the terms of the source repository's licence.
Quiz design inspired by the [teach skill](https://github.com/mattpocock/skills/tree/main/skills/productivity/teach).
