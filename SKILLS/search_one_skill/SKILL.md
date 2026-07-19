---
name: search-one-skill
description: Use when the user wants to find, search, or discover agent skills matching a task description — dual-source search across GitHub and SkillHub with guided installation
---

# Skill 搜索与安装工作流

## Overview

双源 skill 发现与安装工作流：同时搜索 GitHub 和 SkillHub，按相关性排序取 TOP 5，用户确认后安装。核心原则：**多关键词覆盖、先搜后装、用户确认、本地检查、翻译优先。**

## When to Use

**触发场景：**

- 用户说"帮我找 X 的 skill""搜索/推荐 skill""有什么好用的 skill"
- 用户描述了一个任务，需要匹配合适的 skill
- 用户想发现尚未安装的能力

**不适用场景：**

- 用户已知确切 skill 名称，只想直接使用（非搜索行为）
- 用户在创建/编辑 skill

## 工作流概览（2 步）

1. **Skill 检索**：按用户任务描述，翻译为英文后发散 2-3 组关键词变体，双源搜索（GitHub + SkillHub）匹配的 skill，合并去重取 TOP 5
2. **决策 + 下载安装**：用户确认选择后，按来源执行安装

## 双源架构

| 来源     | 搜索方式                           | 安装方式                       | 认证                                  |
| -------- | ---------------------------------- | ------------------------------ | ------------------------------------- |
| GitHub   | REST API（`topic:skill` + 关键词） | `git clone`，fallback ZIP 下载 | 匿名（60次/h），建议设 `GITHUB_TOKEN` |
| SkillHub | CLI（`skillhub search`）           | CLI（`skillhub install`）      | 可选，未登录时静默跳过                |

- 默认**同时搜索两个源**，合并归一化排序，取 TOP 5
- SkillHub 不可用时静默降级为纯 GitHub 搜索
- 支持 `--source github|skillhub|all` 精确控制

---

## Step 1：Skill 检索

### 1.1 判断用户意图

- **描述明确**：直接按描述发起检索
- **描述模糊**（如"找个 skill""推荐个技能"）：
  - 先检查对话上下文中是否有可推断的需求
  - 如有则基于上下文发起检索
  - 如无则追问用户想找什么方向的 skill

### 1.2 中文 → 英文翻译 + 关键词发散

用户使用中文描述时，**使用大模型翻译为 2-3 组英文关键词变体**，覆盖不同角度和近义词，避免单关键词遗漏。

**为什么需要多关键词？** GitHub 搜索依赖文本匹配（仓库名、描述、README）。同义词和不同表述方式会命中完全不同的仓库。例如：
- `"resume builder"` 搜不到 `resume-jd-optimizer-cn`（用了 "optimizer" 而非 "builder"）
- `"resume optimizer"` 就能搜到

**关键词发散规则：**
1. 将中文描述翻译为 1 组核心英文关键词
2. **至少再发散 1-2 组变体**，考虑：近义词替换（builder → optimizer/ generator / writer）、功能侧重切换（编辑 → 优化 / 匹配 / 评分）、场景补充（通用 → Chinese / ATS / JD-driven）
3. 关键词保持简洁（2-4 个单词），不做长句查询

> 翻译和发散在 Agent 层完成，搜索脚本接收英文关键词作为参数。

### 1.3 Agent 类型识别

调用搜索/安装脚本时需传入当前 Agent 类型（`--agent-type`），用于 SkillHub 的平台过滤（`--platform`）。

按以下优先级识别：

1. **System Prompt**：若运行环境提供 system prompt（如 Catdesk、Hermes 等），从中识别 Agent 框架名
2. **IDENTITY.md**：若运行环境无 system prompt（如 Claude 等），检查本地是否存在 `IDENTITY.md`，从中读取 Agent 框架标识
3. **自行判断**：若以上均无法识别，根据你所在的运行时框架自行判断

> 若确实无法识别，可省略该参数。SkillHub 支持以下 platform：`claude`、`codex`、`cursor`、`gemini-cli`、`windsurf`、`openhands`。不在此列表内的值将被忽略。

### 1.4 调用检索脚本（多关键词）

**对每组关键词变体分别调用搜索脚本：**

```bash
{python} {skill_dir}/scripts/skill_search.py "<关键词变体1>" --agent-type <Agent类型> --limit 5
{python} {skill_dir}/scripts/skill_search.py "<关键词变体2>" --agent-type <Agent类型> --limit 5
{python} {skill_dir}/scripts/skill_search.py "<关键词变体3>" --agent-type <Agent类型> --limit 5
```

> 可并行执行（互不依赖），提升搜索速度。

**合并与去重规则：**

1. 合并所有变体的搜索结果，按 `name` 去重（保留 score 最高的）
2. 按 score 重新降序排列
3. 取 TOP 5 作为最终结果

可选参数：

- `--source github`：仅搜索 GitHub
- `--source skillhub`：仅搜索 SkillHub
- `--source all`：双源搜索（默认）
- `--limit 5`：返回条数（默认 5）

> `{python}` 按本机实际选择：macOS / Linux 通常为 `python3`，Windows 通常为 `python` 或 `py`。下同。

### 1.5 脚本输出

脚本输出 JSON 数组到 stdout，每条结果包含：

```json
{
  "name": "skill 名称",
  "source": "github | skillhub",
  "repo_url": "https://github.com/...  (GitHub 源有值，SkillHub 源为 null)",
  "description": "技能描述",
  "score": 0.92,
  "stars": 128  (仅 GitHub 源有值)
}
```

### 1.6 输出规则

- 输出 **TOP 5**：按 score 从高到低推荐，最多 5 个（不足就少输出）
- 0 条结果时告知用户：**"没有找到完全匹配的 skill，建议换个关键词或更简短的描述再试一次。"**
- 展示格式：`# | Skill | 推荐理由`（仅此三列，**不要自行添加额外信息**）
- 推荐理由：结合 description 字段和 stars（GitHub 源）汇总
- **最优推荐**：返回结果的第 1 条即为最优推荐，已由脚本按 score 排序，直接推荐即可。**不要自行重新分析或排序**，不要添加"综合你的需求，我比较推荐 XXX"等自行分析的结论

### 1.7 输出模板

> 严格参照以下格式，将 `{...}` 占位符替换为实际值：

```
为你找到以下相关 skill：

| # | Skill | 推荐理由 |
|---|-------|---------|
| 1 | {name} | {reason} |
| 2 | {name} | {reason} |

最优推荐是 #1 {name}（{reason}）。你想安装哪一个？告诉我编号或名字就行。
```

### 1.8 异常处理

> 脚本执行出错或返回非零退出码时，**禁止**将原始错误信息直接展示给用户，需按以下规则处理：

| 异常场景             | 判别方式                                   | 处理方式                 | 输出示例                                                                                                    |
| -------------------- | ------------------------------------------ | ------------------------ | ----------------------------------------------------------------------------------------------------------- |
| GitHub 限流          | stderr 含 `RATE_LIMITED`                   | 告知用户设置 token       | "GitHub API 请求次数已达上限（60次/小时）。设置环境变量 `GITHUB_TOKEN` 可提升至 5000 次/小时，或稍后重试。" |
| 所有源均失败         | 退出码 2 或 stderr 含 `ALL_SOURCES_FAILED` | 告知用户稍后重试         | "搜索服务暂时不可用，请稍后再试。"                                                                          |
| 返回 0 条结果        | stdout 为 `[]`                             | 告知用户换描述重试       | "没有找到完全匹配的 skill，建议换个关键词或更简短的描述再试一次。"                                          |
| 脚本执行报错（其他） | 非零退出码                                 | 翻译为用户友好的中文提示 | "搜索服务遇到了一点问题，建议稍后重试。如持续出现，可反馈给 skill 作者。"                                   |

### 1.9 GitHub Token 配置

搜索过程中，若遇到 GitHub 限流（退出码 2），**仅在此时**提示用户：

```
GitHub API 请求次数已达上限（匿名 60 次/小时）。
设置环境变量 GITHUB_TOKEN 可提升至 5000 次/小时。

获取方式：GitHub → Settings → Developer settings → Personal access tokens → Generate new token（无需勾选任何权限）。
设置方法：export GITHUB_TOKEN=<你的token>
```

> 日常使用中 60 次/小时足够，仅在触发限流时才提示。**不要主动检查或要求用户预先设置。**

---

## Step 2：决策 + 下载安装

### 2.1 确认用户选择

当用户通过以下方式确认时，进入安装流程：

- **说编号**：如 "1""第一个"
- **说名称**：如 "装 resume-builder"
- **说意图**：如 "安装""装这个""就它了""用这个"

### 2.2 本地检查

检查 `{skills_dir}/{name}/SKILL.md` 是否存在（`{skills_dir}` 为当前 Agent 的 skills 目录，`{name}` 为用户选择的 skill 名称（即 GitHub 仓库名））。

- **已安装**：告知用户 **"该 skill 已安装，无需重复安装，是否直接运行？"**
- **未安装**：执行安装流程

### 2.3 执行安装

按搜索结果的 `source` 字段选择安装方式：

**GitHub 源**（`source: "github"`）：

```bash
{python} {skill_dir}/scripts/skill_install.py <name> --dir <当前Agent的skills目录> --source github --repo-url <repo_url>
```

安装策略：

1. 尝试 `git clone --depth 1 <repo_url> <skills_dir>/<name>`
2. 若 git 不可用，fallback 为 ZIP 下载（GitHub archive API）
3. 安装完成后校验 `SKILL.md` 是否存在，不存在则清理并报错

**SkillHub 源**（`source: "skillhub"`）：

```bash
{python} {skill_dir}/scripts/skill_install.py <name> --dir <当前Agent的skills目录> --source skillhub --agent-type <Agent类型>
```

### 2.4 安装结果

| stdout 前缀          | 状态                           | Agent 输出                                                           |
| -------------------- | ------------------------------ | -------------------------------------------------------------------- |
| `SUCCESS:`           | 安装成功                       | "{name} 已安装成功。要用这个来完成你的任务吗？"                      |
| `ALREADY_INSTALLED:` | 已安装（本地 SKILL.md 已存在） | "该 skill 已安装，无需重复安装，是否直接运行？"                      |
| `ERROR:`             | 安装失败                       | "{name} 安装失败，原因：{描述}。建议稍后重试，或换一个 skill 试试。" |

---

## 核心工具

| 命令               | 用途                                           |
| ------------------ | ---------------------------------------------- |
| `skill_search.py`  | 双源检索 skill（GitHub API + SkillHub CLI）    |
| `skill_install.py` | 双源安装 skill（git clone/ZIP + SkillHub CLI） |

---

## 完整使用示例

**用户**：找个写简历的 skill

**Agent 内部**：翻译+发散为 3 组关键词变体 → `"resume builder"`、`"resume optimizer chinese"`、`"cv generator"`，识别 Agent 类型

**Agent 执行**（并行）：

```bash
python3 {skill_dir}/scripts/skill_search.py "resume builder" --agent-type claude
python3 {skill_dir}/scripts/skill_search.py "resume optimizer chinese" --agent-type claude
python3 {skill_dir}/scripts/skill_search.py "cv generator" --agent-type claude
```

合并去重后，按 score 降序取 TOP 5。

**Agent 输出**：

为你找到以下相关 skill：

| #   | Skill                      | 推荐理由                                                                     |
| --- | -------------------------- | ---------------------------------------------------------------------------- |
| 1   | resume-jd-optimizer-cn     | JD 驱动的中文简历优化，解析岗位 JD、诊断简历缺口、ATS 友好 ⭐135               |
| 2   | resume-builder-skill       | 基于工作轨迹智能提取核心能力，一键生成专业简历 ⭐6                              |

最优推荐是 #1 resume-jd-optimizer-cn（JD 驱动中文简历优化，⭐135）。你想安装哪一个？告诉我编号或名字就行。

**用户**：1 → Agent 确认本地未安装 → 执行安装

---

## Common Mistakes

| 错误行为                       | 为什么会出现           | 正确做法                                                      |
| ------------------------------ | ---------------------- | ------------------------------------------------------------- |
| 跳过中文→英文翻译              | "脚本应该能处理中文"   | GitHub API 对英文最优，**始终翻译为英文关键词**再搜           |
| 只生成一组关键词               | "翻译一个就够了"       | **至少生成 2-3 组关键词变体**，覆盖近义词和不同表述角度       |
| 未经确认自动安装               | "最优推荐很明显"       | **始终等待用户明确选择**，不自动安装                          |
| 未检查本地就安装               | "应该没装过"           | 始终先检查 `{skills_dir}/{name}/SKILL.md` 是否存在            |
| 自行重新排序结果               | "我比脚本更懂用户需求" | 脚本已按 score 排序，**信任排序**，不要自行分析               |
| 直接展示原始错误信息           | "用户应该看到完整错误" | 按异常处理表翻译为**用户友好的中文提示**                      |
| 主动检查/要求设置 GITHUB_TOKEN | "提前配置更好"         | **仅在触发限流时**（退出码 2）才提示，日常使用 60 次/小时足够 |
| 安装后不校验 SKILL.md          | "clone 成功就行"       | GitHub 源安装后**必须校验** SKILL.md 存在性，否则清理并报错   |

## Red Flags - 自查清单

以下想法出现时，**STOP 并回到规则**：

- "这个中文描述够清楚了，不需要翻译" → 翻译为英文再搜
- "翻译一组关键词就够了" → 至少 2-3 组变体，覆盖近义词
- "就装第 1 个吧，不用问了" → 等用户确认
- "SkillHub 挂了，我直接用 GitHub" → 可以，但告知用户
- "这个 skill 肯定没装过" → 先检查本地
- "脚本输出有点奇怪，我重新排个序" → 信任脚本排序
- "我先帮用户检查下 GITHUB_TOKEN" → 仅在限流时提示
- "clone 成功了，应该没问题" → 校验 SKILL.md

---

## 注意事项

1. **多关键词覆盖**：中文→英文翻译后必须发散 2-3 组关键词变体，覆盖近义词和不同角度
2. **本地优先**：安装前须确认本地是否已安装该 skill，避免重复下载
3. **安装确认**：需等用户选择后才安装，**不自动安装**
4. **CN→EN 翻译**：调用搜索脚本前，先由大模型将用户中文描述翻译为英文关键词
5. **GitHub 目录名**：安装到 `{skills_dir}/{仓库名}/`，不做重命名
6. **安装校验**：GitHub 源安装后须校验 SKILL.md 存在性，无效则自动清理
7. **SkillHub 可选**：SkillHub CLI 不可用或未认证时静默跳过，不影响 GitHub 搜索
