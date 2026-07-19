#!/usr/bin/env python3
"""
搜索最满足你需求的 skill：双源检索 GitHub (topic:skill) + SkillHub CLI。

用法:
    python skill_search.py "<英文关键词>" [--agent-type <type>] [--source all|github|skillhub] [--limit 5]

输出:
    JSON 数组到 stdout，供 Agent 解析。
    错误信息输出到 stderr，不会污染 stdout 的 JSON。

退出码:
    0  成功（含 0 条结果）
    2  所有源均失败
"""

import argparse
import json
import math
import os
import subprocess
import sys
import urllib.error
import urllib.parse
import urllib.request

# ── GitHub 搜索 ─────────────────────────────────────────────


def search_github(query: str, limit: int = 5) -> tuple[list[dict], bool]:
    """
    通过 GitHub Search API 搜索 topic:skill 仓库。

    返回 (results, rate_limited)。
    - results: 标准化结果列表
    - rate_limited: True 表示遇到了 403 限流
    """
    q = f"topic:skill {query}".strip()
    encoded = urllib.parse.quote(q)
    url = (
        f"https://api.github.com/search/repositories"
        f"?q={encoded}&sort=stars&order=desc&per_page={limit * 2}"
    )

    headers = {
        "Accept": "application/vnd.github.v3+json",
        "User-Agent": "search-one-skill",
    }

    github_token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    if github_token:
        headers["Authorization"] = f"Bearer {github_token}"

    req = urllib.request.Request(url, headers=headers)

    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            body = resp.read().decode()
    except urllib.error.HTTPError as e:
        err_body = ""
        try:
            err_body = e.read().decode()
        except Exception:
            pass
        if e.code == 403 and "rate limit" in err_body.lower():
            return [], True
        if e.code == 422:
            # 查询语法错误，尝试只用关键词
            return _github_fallback(query, limit, headers)
        return [], False
    except Exception:
        return [], False

    data = json.loads(body)
    items = data.get("items", [])

    results = []
    max_stars = 1

    for item in items:
        if item.get("archived") or item.get("fork"):
            continue
        stars = item.get("stargazers_count", 0)
        if stars > max_stars:
            max_stars = stars
        results.append({
            "name": item.get("name", ""),
            "source": "github",
            "repo_url": item.get("html_url", ""),
            "description": item.get("description") or "",
            "stars": stars,
        })

    # log-scale 归一化
    for r in results:
        if max_stars > 0 and r["stars"] > 0:
            r["score"] = round(
                math.log(r["stars"] + 1) / math.log(max_stars + 1), 4
            )
        else:
            r["score"] = 0.0

    return results, False


def _github_fallback(query: str, limit: int, headers: dict) -> tuple[list[dict], bool]:
    """当 topic:skill 语法出错时，回退到纯关键词搜索。"""
    encoded = urllib.parse.quote(query.strip())
    url = (
        f"https://api.github.com/search/repositories"
        f"?q={encoded}&sort=stars&order=desc&per_page={limit * 2}"
    )
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode())
    except Exception:
        return [], False

    items = data.get("items", [])
    results = []
    max_stars = 1

    for item in items:
        if item.get("archived") or item.get("fork"):
            continue
        stars = item.get("stargazers_count", 0)
        if stars > max_stars:
            max_stars = stars
        results.append({
            "name": item.get("name", ""),
            "source": "github",
            "repo_url": item.get("html_url", ""),
            "description": item.get("description") or "",
            "stars": stars,
        })

    for r in results:
        if max_stars > 0 and r["stars"] > 0:
            r["score"] = round(
                math.log(r["stars"] + 1) / math.log(max_stars + 1), 4
            )
        else:
            r["score"] = 0.0

    return results, False


# ── SkillHub 搜索 ───────────────────────────────────────────


def search_skillhub(query: str, agent_type: str | None = None, limit: int = 5) -> list[dict]:
    """
    通过 SkillHub CLI 搜索。CLI 不可用或未认证时静默返回空列表。
    优先使用全局安装的 skillhub，其次 npx。
    """
    results = _try_skillhub_cmd(["skillhub"], query, agent_type, limit)
    if results is not None:
        return results

    results = _try_skillhub_cmd(
        ["npx", "-y", "@astron-team/skillhub"], query, agent_type, limit
    )
    if results is not None:
        return results

    return []


def _try_skillhub_cmd(
    base_cmd: list[str], query: str, agent_type: str | None, limit: int
) -> list[dict] | None:
    """尝试执行 SkillHub CLI，成功返回结果列表，失败返回 None。"""
    cmd = [*base_cmd, "search", query, "--json", "--limit", str(limit)]
    if agent_type:
        cmd.extend(["--platform", agent_type])

    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=20
        )
        if result.returncode != 0:
            return None
        data = json.loads(result.stdout)
    except (
        FileNotFoundError,
        subprocess.TimeoutExpired,
        json.JSONDecodeError,
    ):
        return None

    items = data if isinstance(data, list) else data.get("data", data.get("results", []))
    if not isinstance(items, list):
        return None

    results = []
    for item in items:
        raw_score = item.get("score", item.get("relevance", 0))
        try:
            raw_score = float(raw_score)
        except (TypeError, ValueError):
            raw_score = 0.0
        # SkillHub 分数可能是 0-100，归一化到 0-1
        if raw_score > 1:
            raw_score = raw_score / 100.0
        results.append({
            "name": item.get("name", ""),
            "source": "skillhub",
            "repo_url": None,
            "description": item.get("description") or "",
            "stars": None,
            "score": round(raw_score, 4),
        })

    return results


# ── 合并与排序 ──────────────────────────────────────────────


def merge_and_sort(
    github_results: list[dict],
    skillhub_results: list[dict],
    limit: int = 5,
) -> list[dict]:
    """合并双源结果，按 score 降序，取 TOP N（不做去重）。"""
    merged = github_results + skillhub_results
    merged.sort(key=lambda x: x["score"], reverse=True)
    return merged[:limit]


# ── CLI 入口 ────────────────────────────────────────────────


def main():
    parser = argparse.ArgumentParser(
        description="搜索最满足你需求的 skill（GitHub + SkillHub）"
    )
    parser.add_argument(
        "query",
        help="搜索关键词（英文，Agent 应在调用前完成 CN→EN 翻译）",
    )
    parser.add_argument(
        "--agent-type",
        help="Agent 类型，映射到 SkillHub 的 --platform",
        default=None,
    )
    parser.add_argument(
        "--source",
        choices=["all", "github", "skillhub"],
        default="all",
        help="搜索源（默认 all）",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=5,
        help="返回结果数上限（默认 5）",
    )
    args = parser.parse_args()

    github_results: list[dict] = []
    skillhub_results: list[dict] = []
    github_ok = True

    if args.source in ("all", "github"):
        github_results, rate_limited = search_github(args.query, limit=args.limit * 2)
        if rate_limited:
            print(
                "RATE_LIMITED:GitHub API 请求次数已达上限。"
                "设置环境变量 GITHUB_TOKEN 可提升限额至 5000 次/小时。",
                file=sys.stderr,
            )
            github_ok = False

    if args.source in ("all", "skillhub"):
        skillhub_results = search_skillhub(
            args.query, agent_type=args.agent_type, limit=args.limit * 2
        )

    # 判断是否所有源均失败
    if args.source == "all" and not github_ok and not skillhub_results:
        print("ALL_SOURCES_FAILED:所有搜索源均不可用，请稍后重试。", file=sys.stderr)
        sys.exit(2)
    if args.source == "github" and not github_ok:
        print("ALL_SOURCES_FAILED:GitHub 搜索不可用，请稍后重试。", file=sys.stderr)
        sys.exit(2)
    if args.source == "skillhub" and not skillhub_results:
        # SkillHub 静默失败是正常的（CLI 未安装或未认证）
        pass

    merged = merge_and_sort(github_results, skillhub_results, limit=args.limit)

    print(json.dumps(merged, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
