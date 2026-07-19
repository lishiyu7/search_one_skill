<p align="right">
  <strong>English</strong> · <a href="./README.zh-CN.md">简体中文</a>
</p>

<p align="center">
  <img src="./assets/readme/hero.svg" width="100%" alt="search_one_skill — Search and install the skill that best meets your needs from GitHub and SkillHub directly inside your conversation">
</p>

Search for the skill that best meets your needs across GitHub and SkillHub in one command, then install with another. No browser, no copy-paste, no leaving your conversation.

## Install

```bash
git clone https://github.com/lishiyu7/search_one_skill.git ~/.claude/skills/search_one_skill
```

Requires Python 3.9+. SkillHub CLI and `GITHUB_TOKEN` are optional.

## Quick start

Agent sees a user asking for a skill → searches both sources → user picks → installs.

> User: find a resume skill

> Agent: (translates → searches → returns TOP 5 recommended skills)

| #   | Skill               | Reason                                                                               |
| --- | ------------------- | ------------------------------------------------------------------------------------ |
| 1   | resume-builder      | Intelligent resume generation, multi-template support, ATS-friendly formatting ⭐234 |
| 2   | cover-letter-writer | Auto-generate personalized cover letters based on job descriptions                   |

> Agent: Best match: #1 resume-builder. Which one would you like to install?

> User: 1

> Agent: SUCCESS: resume-builder installed ✓

[view full example](./assets/readme/example.md)

## How it works

Two Python scripts. Zero npm dependencies required.

| Script             | What it does                                                                           | Sources                        |
| ------------------ | -------------------------------------------------------------------------------------- | ------------------------------ |
| `skill_search.py`  | Searches both sources in parallel, normalizes scores, merges and returns TOP 5 as JSON | GitHub REST API · SkillHub CLI |
| `skill_install.py` | Routes install by source: `git clone` → ZIP fallback for GitHub, CLI for SkillHub      | GitHub · SkillHub              |

### Search pipeline

The Agent translates the user's Chinese task description into English keywords, then calls `skill_search.py`. The script searches GitHub (`topic:skill` + keyword) and SkillHub (`skillhub search`) in parallel, merges results by a log-scale star score, and outputs the top 5.

GitHub returns star-ranked repos tagged `topic:skill`; SkillHub returns curated skills via CLI. Both are searched simultaneously — SkillHub silently degrades if unavailable.

### Install pipeline

Once the user picks a skill, `skill_install.py` routes by source:

- **GitHub**: tries `git clone --depth 1` first, falls back to ZIP download from the archive API
- **SkillHub**: delegates to `skillhub install`

After install, it validates that `SKILL.md` exists in the target directory. Invalid installs are cleaned up automatically.

## Prerequisites

| Requirement                                           | Why                       | Optional?                            |
| ----------------------------------------------------- | ------------------------- | ------------------------------------ |
| Python 3.9+                                           | Runs both scripts         | Required                             |
| Git                                                   | Faster GitHub installs    | Recommended (auto-falls back to ZIP) |
| SkillHub CLI (`npm install -g @astron-team/skillhub`) | SkillHub source           | Optional                             |
| `GITHUB_TOKEN` env var                                | 5000 req/hr instead of 60 | Optional                             |

## Files

```
search_one_skill/
├── SKILL.md                  # Agent workflow instructions (the skill itself)
├── scripts/
│   ├── skill_search.py       # Dual-source search: GitHub API + SkillHub CLI
│   └── skill_install.py      # Dual-source install: git clone / ZIP / skillhub
├── assets/
│   └── readme/
│       ├── hero.svg
│       ├── workflow.svg
│       └── example.md
└── README.md
```

## License

MIT
