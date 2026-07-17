<p align="right">
  <strong>English</strong> · <a href="./README.zh-CN.md">简体中文</a>
</p>

<p align="center">
  <img src="./assets/readme/hero.svg" width="100%" alt="search_one_skill — Search and install AI Agent skills from GitHub and SkillHub directly inside your conversation">
</p>

Search for Agent skills across GitHub and SkillHub in one command, then install with another. No browser, no copy-paste, no leaving your conversation.

<p align="center">
  <img src="./assets/readme/workflow.svg" width="100%" alt="Two-step workflow: Step 1 dual-source search produces TOP 5 results, Step 2 installs via git clone, ZIP, or SkillHub CLI">
</p>

## Install

```bash
git clone https://github.com/lishiyu7/search_one_skill.git ~/.claude/skills/search_one_skill
```

Requires Python 3.9+. SkillHub CLI and `GITHUB_TOKEN` are optional.

## Quick start

Agent sees a user asking for a skill → searches both sources → user picks → installs.

```
User: 找个亚马逊广告运营的 skill

Agent: (translates → searches → returns TOP 5)

       | # | Skill              | 推荐理由                            |
       |---|--------------------|----------------------------------|
       | 1 | amazon-ad-analyst   | 广告诊断，SP/SD 分析，ACoS 异常识别 ⭐234 |
       | 2 | amazon-inventory    | 库存补货测算，库销比+周转周期              |

       最优推荐是 #1 amazon-ad-analyst。你想安装哪一个？

User: 1

Agent: SUCCESS: amazon-ad-analyst 已安装 ✓
```

## How it works

Two Python scripts. Zero npm dependencies required.

| Script | What it does | Sources |
|--------|-------------|---------|
| `skill_search.py` | Searches both sources in parallel, normalizes scores, merges and returns TOP 5 as JSON | GitHub REST API · SkillHub CLI |
| `skill_install.py` | Routes install by source: `git clone` → ZIP fallback for GitHub, CLI for SkillHub | GitHub · SkillHub |

### Search pipeline

The Agent translates the user's Chinese task description into English keywords, then calls `skill_search.py`. The script searches GitHub (`topic:skill` + keyword) and SkillHub (`skillhub search`) in parallel, merges results by a log-scale star score, and outputs the top 5.

GitHub returns star-ranked repos tagged `topic:skill`; SkillHub returns curated skills via CLI. Both are searched simultaneously — SkillHub silently degrades if unavailable.

### Install pipeline

Once the user picks a skill, `skill_install.py` routes by source:

- **GitHub**: tries `git clone --depth 1` first, falls back to ZIP download from the archive API
- **SkillHub**: delegates to `skillhub install`

After install, it validates that `SKILL.md` exists in the target directory. Invalid installs are cleaned up automatically.

## Prerequisites

| Requirement | Why | Optional? |
|------------|-----|-----------|
| Python 3.9+ | Runs both scripts | Required |
| Git | Faster GitHub installs | Recommended (auto-falls back to ZIP) |
| SkillHub CLI (`npm install -g @astron-team/skillhub`) | SkillHub source | Optional |
| `GITHUB_TOKEN` env var | 5000 req/hr instead of 60 | Optional |

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
│       └── workflow.svg
└── README.md
```

## License

MIT
