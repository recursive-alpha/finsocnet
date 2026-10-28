"""GitHub REST API (specs/05 §3.10)."""

from __future__ import annotations

import base64
import os
import re
from typing import Any

from finsocnet.core import http
from finsocnet.core.output import CliError
from finsocnet.core.platform import PlatformAdapter, content_record, item_ref, list_result, profile_record, save_raw
from finsocnet.core.segments import code_segments, paragraph_segments, refs

API = "https://api.github.com"
CODE_EXT = {".py", ".pine", ".js", ".ts", ".rs", ".go", ".cpp", ".c", ".java", ".r", ".jl", ".ipynb", ".md", ".txt", ".yaml", ".yml", ".json", ".toml", ".sql", ".mq4", ".mq5", ".cs"}


def headers() -> dict[str, str]:
    h = {"Accept": "application/vnd.github+json"}
    if os.getenv("GITHUB_TOKEN"):
        h["Authorization"] = f"Bearer {os.environ['GITHUB_TOKEN']}"
    return h


def parse_ref(item: str) -> tuple[str, str, str | None]:
    """`owner/repo`, `https://github.com/owner/repo[/blob/<branch>/<path>]`, `owner/repo:path` -> (owner, repo, path)."""
    m = re.match(r"(?:https?://github\.com/)?([\w.-]+)/([\w.-]+?)(?:\.git)?(?:/blob/[^/]+/(.+)|:(.+)|/?$)", item.strip())
    if not m:
        raise CliError("USAGE", f"cannot read a repository from {item!r}", "use owner/repo, owner/repo:path or a GitHub URL")
    return m.group(1), m.group(2), m.group(3) or m.group(4)


def repo_ref(r: dict[str, Any]) -> dict[str, Any]:
    return item_ref(r["html_url"], f"github:{r['full_name']}", "repo", r["full_name"], r["owner"]["login"], r.get("pushed_at"), r.get("description"),
                    {"stars": r.get("stargazers_count"), "forks": r.get("forks_count"), "language": r.get("language")})


def readme_record(repo: dict[str, Any], readme: dict[str, Any], raw_path: str | None) -> dict[str, Any]:
    text = base64.b64decode(readme["content"]).decode("utf-8", "replace") if readme.get("encoding") == "base64" else readme.get("content", "")
    segs = paragraph_segments(text) or [{"seq": 0, "kind": "paragraph", "locator": {"para": 0}, "text": repo.get("description") or repo["full_name"]}]
    r = refs(text)
    return content_record(f"github:{repo['full_name']}", "github", "repo", segs, url=repo["html_url"], title=repo["full_name"], description=repo.get("description"),
                          author={"handle": repo["owner"]["login"], "profile_url": repo["owner"]["html_url"]}, published_at=repo.get("created_at"), language="en",
                          metrics={"stars": repo.get("stargazers_count"), "forks": repo.get("forks_count")}, links=r["links"], mentions=r["mentions"], raw_path=raw_path, fetch_method="api",
                          extra={"topics": repo.get("topics", []), "language": repo.get("language"), "license": (repo.get("license") or {}).get("spdx_id"), "default_branch": repo.get("default_branch")},
                          source={"id": f"github:user:{repo['owner']['login'].lower()}", "kind": "user", "title": repo["owner"]["login"]})


def file_record(repo: dict[str, Any], path: str, text: str, sha: str, raw_path: str | None) -> dict[str, Any]:
    segs = code_segments(text, path) or [{"seq": 0, "kind": "code", "locator": {"path": path, "line_start": 1, "line_end": 1}, "text": "(empty file)"}]
    return content_record(f"github:{repo['full_name']}:{path}@{sha[:7]}", "github", "file", segs, url=f"{repo['html_url']}/blob/{repo.get('default_branch', 'main')}/{path}", title=f"{repo['full_name']}/{path}",
                          author={"handle": repo["owner"]["login"]}, language="en", raw_path=raw_path, fetch_method="api", parent_content_id=f"github:{repo['full_name']}",
                          extra={"path": path, "sha": sha}, source={"id": f"github:user:{repo['owner']['login'].lower()}", "kind": "user", "title": repo["owner"]["login"]})


class GitHub(PlatformAdapter):
    platform = "github"
    capabilities = frozenset({"search", "profile", "list", "fetch", "tree"})
    opts = {"search": [(("--topic",), {"default": "algorithmic-trading"}), (("--language",), {})]}

    def _get(self, path: str, **params: Any) -> Any:
        return http.get_json(f"{API}{path}", platform="github", params=params or None, headers=headers())

    def search(self, query, *, limit=20, since=None, topic="algorithmic-trading", language=None, **_):
        q = f"{query} topic:{topic}" if topic else query
        if language:
            q += f" language:{language}"
        if since:
            q += f" pushed:>={since}"
        return [repo_ref(r) for r in self._get("/search/repositories", q=q, sort="stars", per_page=min(limit, 100)).get("items", [])][:limit]

    def profile(self, target, **_):
        u = self._get(f"/users/{target.rsplit('/', 1)[-1]}")
        return profile_record("github", f"github:user:{u['login'].lower()}", u["login"], display_name=u.get("name"), bio=u.get("bio"), followers=u.get("followers"), avatar_url=u.get("avatar_url"),
                              profile_url=u["html_url"], location=u.get("location"), joined_at=(u.get("created_at") or "")[:10], links=[x for x in [u.get("blog")] if x])

    def list(self, source, *, limit=50, cursor=None, since=None, **_):
        user = source.rsplit("/", 1)[-1]
        d = self._get(f"/users/{user}/repos", sort="pushed", per_page=min(limit, 100), page=int(cursor or 1))
        return list_result([repo_ref(r) for r in d][:limit], str(int(cursor or 1) + 1) if len(d) >= min(limit, 100) else None, {"id": f"github:user:{user.lower()}"})

    def fetch(self, item, **_):
        owner, repo, path = parse_ref(item)
        meta = self._get(f"/repos/{owner}/{repo}")
        if path:
            f = self._get(f"/repos/{owner}/{repo}/contents/{path}")
            text = base64.b64decode(f["content"]).decode("utf-8", "replace")
            return file_record(meta, path, text, f["sha"], save_raw("github", f"{owner}_{repo}_{path}", f))
        rd = self._get(f"/repos/{owner}/{repo}/readme")
        return readme_record(meta, rd, save_raw("github", f"{owner}_{repo}_readme", rd))

    def tree(self, item, *, branch=None, **_):
        owner, repo, _p = parse_ref(item)
        branch = branch or self._get(f"/repos/{owner}/{repo}")["default_branch"]
        d = self._get(f"/repos/{owner}/{repo}/git/trees/{branch}", recursive=1)
        files = [{"path": t["path"], "size": t.get("size"), "readable": "." + t["path"].rsplit(".", 1)[-1].lower() in CODE_EXT} for t in d.get("tree", []) if t["type"] == "blob"]
        return {"repo": f"{owner}/{repo}", "branch": branch, "files": files, "truncated": d.get("truncated", False)}
