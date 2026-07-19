<p align="right">
  <a href="./README.md">English</a> · <strong>简体中文</strong>
</p>

<p align="center">
  <img src="./assets/readme/hero.svg" width="100%" alt="search_one_skill — 搜索并安装最满足你需求的 skill，支持 GitHub 和 SkillHub 双源">
</p>

在对话中一键搜索 Agent 技能，覆盖 GitHub 和 SkillHub 两个来源，再用一条命令完成安装。无需浏览器，无需复制粘贴，无需离开对话。

<p align="center">
  <img src="./assets/readme/workflow.svg" width="100%" alt="两步工作流：第一步双源搜索输出 TOP 5，第二步通过 git clone、ZIP 或 SkillHub CLI 安装">
</p>

## 安装

```bash
git clone https://github.com/lishiyu7/search_one_skill.git ~/.claude/skills/search_one_skill
```

需要 Python 3.9+。SkillHub CLI 和 `GITHUB_TOKEN` 为可选项。

## 快速开始

Agent 看到用户需求 → 双源搜索 → 用户选择 → 安装完成。

> 用户：找个写简历的 skill

> Agent：（翻译 → 搜索 → 返回 TOP 5）

| #   | Skill               | 推荐理由                                     |
| --- | ------------------- | -------------------------------------------- |
| 1   | resume-builder      | 智能简历生成，多模板切换，ATS 友好排版 ⭐234 |
| 2   | cover-letter-writer | 求职信自动生成，基于职位描述个性化定制       |

最优推荐是 #1 resume-builder。你想安装哪一个？

> 用户：1

> Agent：SUCCESS: resume-builder 已安装 ✓

→ [查看完整的多关键词搜索示例](./assets/readme/example.md)

## 工作原理

两个 Python 脚本，零 npm 依赖。

| 脚本               | 功能                                                              | 数据源                         |
| ------------------ | ----------------------------------------------------------------- | ------------------------------ |
| `skill_search.py`  | 双源并行搜索，分数归一化，合并输出 TOP 5 JSON                     | GitHub REST API · SkillHub CLI |
| `skill_install.py` | 按来源路由安装：GitHub 优先 git clone → ZIP 兜底，SkillHub 走 CLI | GitHub · SkillHub              |

### 搜索流程

Agent 将用户的中文任务描述翻译为英文关键词，然后调用 `skill_search.py`。脚本并行搜索 GitHub（`topic:skill` + 关键词）和 SkillHub（`skillhub search`），按对数标度 Star 分数合并排序，输出前 5 条。

GitHub 返回标记了 `topic:skill` 的 Star 排名仓库；SkillHub 通过 CLI 返回精选技能。两者同时搜索——SkillHub 不可用时静默降级。

### 安装流程

用户选定后，`skill_install.py` 按来源路由：

- **GitHub**：优先 `git clone --depth 1`，不可用时从 Archive API 下载 ZIP
- **SkillHub**：委托 `skillhub install`

安装后校验目标目录下是否存在 `SKILL.md`，无效安装自动清理。

## 前置要求

| 依赖                                                   | 用途                                     | 是否必须                   |
| ------------------------------------------------------ | ---------------------------------------- | -------------------------- |
| Python 3.9+                                            | 运行脚本                                 | 必须                       |
| Git                                                    | GitHub 源安装更快                        | 推荐（不可用时自动转 ZIP） |
| SkillHub CLI（`npm install -g @astron-team/skillhub`） | SkillHub 源                              | 可选                       |
| `GITHUB_TOKEN` 环境变量                                | API 限额 5000 次/小时（匿名 60 次/小时） | 可选                       |

## 文件结构

```
search_one_skill/
├── SKILL.md                  # Agent 工作流指令（skill 本身）
├── scripts/
│   ├── skill_search.py       # 双源搜索：GitHub API + SkillHub CLI
│   └── skill_install.py      # 双源安装：git clone / ZIP / skillhub
├── assets/
│   └── readme/
│       ├── hero.svg
│       ├── workflow.svg
│       └── example.md
└── README.md
```

## 许可

MIT
