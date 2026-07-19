#!/usr/bin/env python3
"""
安装最满足你需求的 skill：双源支持 GitHub (git clone / ZIP fallback) + SkillHub CLI。

用法:
    python skill_install.py <name> --dir <skills_dir> \\
        [--source github|skillhub] [--repo-url <url>] [--agent-type <type>]

输出:
    格式为 "<STATUS>:<detail>" 的单行文本到 stdout。
    错误信息到 stderr。

退出码:
    0  安装成功 / 已安装
    1  安装失败
"""

import argparse
import os
import shutil
import subprocess
import sys
import tempfile
import urllib.request
import zipfile


# ── GitHub 安装 ─────────────────────────────────────────────


def install_github(name: str, skills_dir: str, repo_url: str) -> int:
    """
    从 GitHub 安装 skill。

    策略:
    1. git clone（优先）
    2. ZIP 下载 + 解压（git 不可用时的 fallback）
    3. 安装后校验 SKILL.md 存在性
    """
    target_dir = os.path.join(skills_dir, name)

    # 已安装检查
    if os.path.isfile(os.path.join(target_dir, "SKILL.md")):
        print(f"ALREADY_INSTALLED:{name}")
        return 0

    # 策略 1: git clone
    clone_ok = _try_git_clone(repo_url, target_dir)
    if clone_ok:
        if _validate_skill(target_dir, name):
            print(f"SUCCESS:{name}")
            return 0
        _cleanup(target_dir)

    # 策略 2: ZIP 下载
    zip_ok = _try_zip_download(repo_url, target_dir)
    if zip_ok:
        if _validate_skill(target_dir, name):
            print(f"SUCCESS:{name}")
            return 0
        _cleanup(target_dir)

    # 全部失败
    print(
        f"ERROR:{name}:无法从 GitHub 下载该仓库，请检查仓库 URL 是否正确，或稍后重试。",
        file=sys.stderr,
    )
    return 1


def _try_git_clone(repo_url: str, target_dir: str) -> bool:
    """尝试 git clone，成功返回 True。"""
    try:
        # 先清理可能残留的空目录
        if os.path.exists(target_dir):
            shutil.rmtree(target_dir, ignore_errors=True)

        result = subprocess.run(
            ["git", "clone", "--depth", "1", repo_url, target_dir],
            capture_output=True,
            text=True,
            timeout=60,
        )
        return result.returncode == 0 and os.path.isdir(target_dir)
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False
    except Exception:
        return False


def _try_zip_download(repo_url: str, target_dir: str) -> bool:
    """通过 GitHub archive API 下载 ZIP 并解压。返回是否成功。"""
    # https://github.com/user/repo -> owner/repo
    parts = repo_url.rstrip("/").split("/")
    if len(parts) < 2:
        return False
    owner, repo = parts[-2], parts[-1]
    if repo.endswith(".git"):
        repo = repo[:-4]

    zip_url = f"https://api.github.com/repos/{owner}/{repo}/zipball/main"

    headers = {"User-Agent": "search-one-skill"}
    github_token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    if github_token:
        headers["Authorization"] = f"Bearer {github_token}"

    req = urllib.request.Request(zip_url, headers=headers)

    tmp_path = None
    extract_dir = None

    try:
        # 下载 ZIP
        with urllib.request.urlopen(req, timeout=60) as resp:
            with tempfile.NamedTemporaryFile(suffix=".zip", delete=False) as tmp:
                tmp.write(resp.read())
                tmp_path = tmp.name

        # 解压到临时目录
        extract_dir = tempfile.mkdtemp()
        with zipfile.ZipFile(tmp_path, "r") as zf:
            zf.extractall(extract_dir)

        # GitHub ZIP 会包裹一层 owner-repo-xxxxx 目录
        entries = os.listdir(extract_dir)
        if len(entries) == 1:
            source = os.path.join(extract_dir, entries[0])
            if os.path.isdir(source):
                # 移动到目标
                if os.path.exists(target_dir):
                    shutil.rmtree(target_dir, ignore_errors=True)
                shutil.move(source, target_dir)
                return True

        # 扁平结构，直接移动 extract_dir 内容
        if os.path.exists(target_dir):
            shutil.rmtree(target_dir, ignore_errors=True)
        os.makedirs(target_dir, exist_ok=True)
        for entry in os.listdir(extract_dir):
            src = os.path.join(extract_dir, entry)
            dst = os.path.join(target_dir, entry)
            shutil.move(src, dst)
        return True

    except Exception:
        return False
    finally:
        if tmp_path and os.path.exists(tmp_path):
            os.unlink(tmp_path)
        if extract_dir and os.path.exists(extract_dir):
            shutil.rmtree(extract_dir, ignore_errors=True)


def _validate_skill(target_dir: str, name: str) -> bool:
    """校验安装目录中是否存在 SKILL.md。"""
    return os.path.isfile(os.path.join(target_dir, "SKILL.md"))


def _cleanup(target_dir: str):
    """删除无效安装目录。"""
    shutil.rmtree(target_dir, ignore_errors=True)


# ── SkillHub 安装 ───────────────────────────────────────────


def install_skillhub(name: str, skills_dir: str, agent_type: str | None = None) -> int:
    """
    通过 SkillHub CLI 安装 skill。

    优先使用全局 skillhub，其次 npx。
    """
    target_dir = os.path.join(skills_dir, name)

    # 已安装检查
    if os.path.isfile(os.path.join(target_dir, "SKILL.md")):
        print(f"ALREADY_INSTALLED:{name}")
        return 0

    # 尝试全局 skillhub
    ok = _try_skillhub_install(["skillhub"], name, skills_dir, agent_type)
    if ok is not None:
        if ok:
            print(f"SUCCESS:{name}")
            return 0
        else:
            print(f"ERROR:{name}:SkillHub 安装失败，请检查网络或稍后重试。", file=sys.stderr)
            return 1

    # 尝试 npx
    ok = _try_skillhub_install(
        ["npx", "-y", "@astron-team/skillhub"], name, skills_dir, agent_type
    )
    if ok is not None:
        if ok:
            print(f"SUCCESS:{name}")
            return 0
        else:
            print(f"ERROR:{name}:SkillHub 安装失败，请检查网络或稍后重试。", file=sys.stderr)
            return 1

    # CLI 完全不可用
    print(
        f"ERROR:{name}:SkillHub CLI 不可用。请确认已安装 Node.js，"
        f"然后执行 npm install -g @astron-team/skillhub 安装 CLI。",
        file=sys.stderr,
    )
    return 1


def _try_skillhub_install(
    base_cmd: list[str], name: str, skills_dir: str, agent_type: str | None
) -> bool | None:
    """
    尝试执行 SkillHub install。成功 True，失败 False，CLI 不可用 None。
    """
    cmd = [*base_cmd, "install", name, "--dir", skills_dir]
    if agent_type:
        cmd.extend(["--agent", agent_type])

    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=60
        )
        if result.returncode == 0:
            return True
        return False
    except FileNotFoundError:
        return None
    except subprocess.TimeoutExpired:
        return False
    except Exception:
        return None


# ── CLI 入口 ────────────────────────────────────────────────


def main():
    parser = argparse.ArgumentParser(
        description="安装最满足你需求的 skill（GitHub + SkillHub）"
    )
    parser.add_argument("name", help="Skill 名称")
    parser.add_argument(
        "--dir",
        required=True,
        help="目标 skills 目录（当前 Agent 的 skills 根目录）",
    )
    parser.add_argument(
        "--source",
        choices=["github", "skillhub"],
        required=True,
        help="安装来源",
    )
    parser.add_argument(
        "--repo-url",
        help="GitHub 仓库 URL（source=github 时必填）",
    )
    parser.add_argument(
        "--agent-type",
        help="Agent 类型（SkillHub 安装时传给 --agent）",
    )
    args = parser.parse_args()

    if args.source == "github":
        if not args.repo_url:
            print(
                "ERROR:--repo-url 在 source=github 时必填。",
                file=sys.stderr,
            )
            sys.exit(1)
        sys.exit(install_github(args.name, args.dir, args.repo_url))

    elif args.source == "skillhub":
        sys.exit(install_skillhub(args.name, args.dir, args.agent_type))

    else:
        print(f"ERROR:未知来源 {args.source}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
