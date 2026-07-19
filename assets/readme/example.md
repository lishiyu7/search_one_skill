# search-one-skill

双源 skill 发现与安装工作流：GitHub + SkillHub 同时搜索，按相关性排序，用户确认后安装。

## 安装

```bash
# 将本目录 symlink 到 Agent 的 skills 目录即可
ln -s $(pwd) ~/.agents/skills/search-one-skill
ln -s ../../.agents/skills/search-one-skill ~/.claude/skills/search-one-skill
```

零配置开箱即用。GitHub 匿名访问 60 次/小时，SkillHub 通过 `npx` 按需加载。

## 真实使用示例

**用户**：搜索简历优化相关的 skill

**Agent 内部**：中文"简历优化"翻译并发散为 3 组英文关键词变体：

| 关键词变体                | 策略                                         |
| ------------------------- | -------------------------------------------- |
| `resume optimizer`        | 核心翻译                                     |
| `resume builder`          | 近义词替换 (optimizer → builder)             |
| `CV optimization chinese` | 场景补充 (CV 替代 Resume, 加入 Chinese 语境) |

三组并行搜索，合并去重后输出：

> 为你找到以下相关 skill：

| #   | Skill                  | 推荐理由                                                         |
| --- | ---------------------- | ---------------------------------------------------------------- |
| 1   | resume-jd-optimizer-cn | JD 驱动的中文简历优化，解析岗位 JD、诊断简历缺口、ATS 友好 ⭐135 |
| 2   | resume-builder-skill   | 基于工作轨迹智能提取核心能力，一键生成专业简历 ⭐6               |
| 3   | resume-deep-optimizer  | 深度诊断简历质量，多维度量化评分，人岗匹配分析（SkillHub）       |
| 4   | resume-optimizer       | 专业简历生成器，PDF 导出、ATS 优化、多格式（SkillHub）           |
| 5   | resume-cv-builder      | 创建专业 Resume/CV，支持 Markdown/HTML/LaTeX/PDF（SkillHub）     |

### 为什么需要多关键词？

只用 `resume builder` 搜不到 `resume-jd-optimizer-cn`（那个仓库用 "optimizer" 而非 "builder"）。GitHub 搜索是纯文本匹配，同义词和不同表述方式命中完全不同的仓库。发散 2-3 组关键词变体后，覆盖面显著提升。

### 双源对比

| 来源     | 结果示例                                    | 特点                                |
| -------- | ------------------------------------------- | ----------------------------------- |
| GitHub   | `resume-jd-optimizer-cn` ⭐135              | 社区公开仓库，有 stars 作为质量信号 |
| SkillHub | `resume-deep-optimizer`、`resume-optimizer` | 官方发布的 skill 包，描述更结构化   |

## 目录结构

```
search-one-skill/
├── SKILL.md              # Skill 定义与工作流规则
├── README.md             # 本文件
└── scripts/
    ├── skill_search.py   # 双源检索（GitHub API + SkillHub CLI）
    └── skill_install.py  # 双源安装（git clone/ZIP + SkillHub CLI）
```
