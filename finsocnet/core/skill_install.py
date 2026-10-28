"""Skill installer core (specs/07 §5, `.agents/skills/skill-installer/references/review_checklist.md`).

Nothing staged is ever executed: files are fetched, hashed, scanned as text/bytes and copied. Subprocess is used only for `git clone`
(hooks disabled) on a remote URL; no staged path is passed to any interpreter."""

from __future__ import annotations

import hashlib
import io
import json
import os
import re
import shutil
import subprocess
import tarfile
import zipfile
from datetime import datetime, timedelta, timezone
from pathlib import Path, PurePosixPath
from typing import Any

import yaml

from finsocnet.core import config, http, ids
from finsocnet.core.output import CliError
from finsocnet.core.records import schema_errors

NAME_RE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
MAX_FILES, MAX_TOTAL, MAX_FILE, MAX_ARCHIVE, MAX_RATIO = 200, 10 * 2**20, 2 * 2**20, 20 * 2**20, 100
STAGING_TTL = timedelta(days=7)
BIN_MAGIC = [(b"\x7fELF", "ELF"), (b"MZ", "PE"), (b"\xfe\xed\xfa\xce", "Mach-O"), (b"\xfe\xed\xfa\xcf", "Mach-O"), (b"\xca\xfe\xba\xbe", "Mach-O/class"), (b"\xcf\xfa\xed\xfe", "Mach-O")]
BIN_EXT = {".so", ".dll", ".dylib", ".exe", ".pyc", ".whl", ".jar"}
TEXT_EXT = {".md", ".py", ".txt", ".json", ".yaml", ".yml", ".toml", ".sh", ".js", ".ts", ".html", ".css", ".csv", ".sql", ".cfg", ".ini", ".rst", ".j2", ".ps1", ".bat"}


# --- paths and lock --------------------------------------------------------------------------------------

def skills_dir() -> Path:
    return config.repo_root() / ".agents" / "skills"


def staging_root() -> Path:
    return config.data_dir() / "skill-staging"


def backups_root() -> Path:
    return config.data_dir() / "skill-backups"


def lock_path() -> Path:
    return config.repo_root() / "config" / "skills.lock.json"


def read_lock() -> dict[str, Any]:
    p = lock_path()
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else {"version": 1, "skills": {}}


def write_lock(lock: dict[str, Any]) -> None:
    lock_path().parent.mkdir(parents=True, exist_ok=True)
    lock_path().write_text(json.dumps(lock, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def core_skill_names() -> set[str]:
    locked = set(read_lock()["skills"])
    return {d.name for d in skills_dir().iterdir() if d.is_dir()} - locked if skills_dir().exists() else set()


def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def hash_dir(root: Path) -> dict[str, str]:
    return {p.relative_to(root).as_posix(): sha256_bytes(p.read_bytes()) for p in sorted(root.rglob("*")) if p.is_file() and not p.is_symlink()}


def new_staging_id() -> str:
    return "st-" + datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S") + "-" + os.urandom(2).hex()


def staging_dir(sid: str) -> Path:
    if not re.fullmatch(r"st-\d{14}-[0-9a-f]{4}", sid):
        raise CliError("USAGE", f"bad staging id {sid!r}")
    d = staging_root() / sid
    if not d.exists():
        raise CliError("NOT_FOUND", f"staging {sid} does not exist (staging is pruned after 7 days)")
    return d


def prune_staging() -> int:
    n = 0
    if staging_root().exists():
        for d in staging_root().iterdir():
            if d.is_dir() and datetime.now(timezone.utc) - datetime.fromtimestamp(d.stat().st_mtime, timezone.utc) > STAGING_TTL:
                shutil.rmtree(d, ignore_errors=True)
                n += 1
    return n


# --- safe extraction -------------------------------------------------------------------------------------

class Limits:
    def __init__(self) -> None:
        self.files = 0
        self.total = 0
        self.blocks: list[dict[str, Any]] = []

    def block(self, rule: str, file: str, why: str) -> None:
        self.blocks.append({"rule": rule, "file": file, "reason": why})


def _safe_rel(name: str, limits: Limits) -> str | None:
    p = PurePosixPath(name.replace("\\", "/"))
    if p.is_absolute() or re.match(r"^[A-Za-z]:", name) or ".." in p.parts:
        limits.block("B2", name, "absolute path, drive letter or '..' segment")
        return None
    return p.as_posix().lstrip("./")


def _store(dest: Path, rel: str, data: bytes, limits: Limits) -> None:
    limits.files += 1
    limits.total += len(data)
    if limits.files > MAX_FILES:
        limits.block("B4", rel, f"more than {MAX_FILES} files")
        return
    if len(data) > MAX_FILE:
        limits.block("B4", rel, f"file larger than {MAX_FILE} bytes")
        return
    if limits.total > MAX_TOTAL:
        limits.block("B4", rel, f"total larger than {MAX_TOTAL} bytes")
        return
    out = dest / rel
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_bytes(data)  # data only; the file mode stays 0644 (never executable)


def safe_extract_zip(data: bytes, dest: Path, prefix: str = "") -> Limits:
    limits = Limits()
    if len(data) > MAX_ARCHIVE:
        limits.block("B4", "<archive>", "archive larger than 20 MB")
        return limits
    with zipfile.ZipFile(io.BytesIO(data)) as z:
        infos = z.infolist()
        if sum(i.file_size for i in infos) > MAX_ARCHIVE or (len(data) and sum(i.file_size for i in infos) / len(data) > MAX_RATIO):
            limits.block("B4", "<archive>", "uncompressed size or compression ratio too large")
            return limits
        for i in infos:
            if i.is_dir():
                continue
            mode = (i.external_attr >> 16) & 0o170000
            if mode == 0o120000:
                limits.block("B1", i.filename, "symlink entry")
                continue
            if mode in (0o020000, 0o060000, 0o010000, 0o140000):
                limits.block("B3", i.filename, "device or special file")
                continue
            rel = _safe_rel(i.filename, limits)
            if rel is None or (prefix and not rel.startswith(prefix)):
                continue
            _store(dest, rel[len(prefix):].lstrip("/") if prefix else rel, z.read(i), limits)
    return limits


def safe_extract_tar(data: bytes, dest: Path, prefix: str = "", strip: int = 0) -> Limits:
    limits = Limits()
    if len(data) > MAX_ARCHIVE:
        limits.block("B4", "<archive>", "archive larger than 20 MB")
        return limits
    with tarfile.open(fileobj=io.BytesIO(data), mode="r:*") as t:
        members = t.getmembers()
        if sum(m.size for m in members) > MAX_ARCHIVE:
            limits.block("B4", "<archive>", "uncompressed size larger than 20 MB")
            return limits
        for m in members:
            if m.isdir():
                continue
            if m.issym() or m.islnk():
                limits.block("B1", m.name, "symlink or hard link entry")
                continue
            if not m.isfile():
                limits.block("B3", m.name, "device or special file")
                continue
            name = "/".join(PurePosixPath(m.name).parts[strip:]) if strip else m.name
            rel = _safe_rel(name, limits)
            if rel is None or (prefix and not rel.startswith(prefix)):
                continue
            _store(dest, rel[len(prefix):].lstrip("/") if prefix else rel, t.extractfile(m).read(), limits)  # type: ignore[union-attr]
    return limits


def copy_local(src: Path, dest: Path) -> Limits:
    limits = Limits()
    if src.is_file():
        if src.suffix in (".zip", ".skill"):
            return safe_extract_zip(src.read_bytes(), dest)
        if src.suffixes[-2:] == [".tar", ".gz"] or src.suffix == ".tgz":
            return safe_extract_tar(src.read_bytes(), dest)
        _store(dest, "SKILL.md" if src.name.lower() == "skill.md" else src.name, src.read_bytes(), limits)
        return limits
    for p in sorted(src.rglob("*")):
        if p.is_symlink():
            limits.block("B1", p.relative_to(src).as_posix(), "symlink")
            continue
        if p.is_file():
            if ".git" in p.relative_to(src).parts:
                continue
            _store(dest, p.relative_to(src).as_posix(), p.read_bytes(), limits)
    return limits


# --- links -----------------------------------------------------------------------------------------------

GH_TREE = re.compile(r"^https?://github\.com/([\w.-]+)/([\w.-]+?)(?:\.git)?/(?:tree|blob)/([^/]+)/(.+?)/?$")
GH_ROOT = re.compile(r"^https?://github\.com/([\w.-]+)/([\w.-]+?)(?:\.git)?/?$")
GH_RAW = re.compile(r"^https?://raw\.githubusercontent\.com/([\w.-]+)/([\w.-]+)/([^/]+)/(.+)$")
GH_SHORT = re.compile(r"^([\w.-]+)/([\w.-]+)(?:@([\w.-]+)|/(.+))?$")


def parse_link(link: str) -> dict[str, Any]:
    """Classify a pasted link (references/link_formats.md)."""
    link = link.strip()
    if Path(link).expanduser().exists() and not link.startswith("http"):
        return {"kind": "local", "path": str(Path(link).expanduser())}
    m = GH_TREE.match(link)
    if m:
        path = m.group(4)
        if path.lower().endswith("/skill.md"):
            path = path[: -len("/SKILL.md")]
        elif path.lower() == "skill.md":
            path = ""
        return {"kind": "github", "repo": f"{m.group(1)}/{m.group(2)}", "ref": m.group(3), "path": path}
    m = GH_RAW.match(link)
    if m:
        path = m.group(4)
        path = path[: -len("/SKILL.md")] if path.lower().endswith("/skill.md") else "" if path.lower() == "skill.md" else path
        return {"kind": "github", "repo": f"{m.group(1)}/{m.group(2)}", "ref": m.group(3), "path": path}
    m = GH_ROOT.match(link)
    if m:
        return {"kind": "github", "repo": f"{m.group(1)}/{m.group(2)}", "ref": None, "path": ""}
    if re.search(r"\.(zip|skill|tar\.gz|tgz)(\?|$)", link):
        return {"kind": "archive", "url": link}
    if link.lower().endswith("skill.md") and link.startswith("http"):
        return {"kind": "skill_md", "url": link}
    if re.match(r"^https?://.*\.git$", link) or link.startswith("file://") or re.match(r"^https?://(gitlab\.com|codeberg\.org)/", link):
        return {"kind": "git", "url": re.sub(r"/(-/)?(tree|src/branch)/.*$", "", link)}
    m = GH_SHORT.match(link)
    if m and not link.startswith("http") and "." not in m.group(1):
        return {"kind": "github", "repo": f"{m.group(1)}/{m.group(2)}", "ref": None, "path": m.group(4) or "", "skill_name": m.group(3)}
    if link.startswith("http"):
        return {"kind": "web", "url": link}
    raise CliError("USAGE", f"cannot understand the link {link!r}", "see references/link_formats.md")


def gh_get(path: str) -> Any:
    h = {"Accept": "application/vnd.github+json"}
    if os.getenv("GITHUB_TOKEN"):
        h["Authorization"] = f"Bearer {os.environ['GITHUB_TOKEN']}"
    return http.get_json(f"https://api.github.com{path}", platform="github", headers=h)


def gh_resolve_commit(repo: str, ref: str | None) -> tuple[str, str]:
    if ref is None:
        ref = gh_get(f"/repos/{repo}")["default_branch"]
    return ref, gh_get(f"/repos/{repo}/commits/{ref}")["sha"]


def frontmatter_of(text: str) -> dict[str, Any] | None:
    if not text.startswith("---"):
        return None
    parts = text.split("---", 2)
    if len(parts) < 3:
        return None
    try:
        d = yaml.safe_load(parts[1])
    except yaml.YAMLError:
        return None
    return d if isinstance(d, dict) else None


def resolve(link: str) -> dict[str, Any]:
    spec = parse_link(link)
    out: dict[str, Any] = {"link": link, "kind": spec["kind"], "candidates": [], "links": []}
    installed = read_lock()["skills"]
    core = core_skill_names()

    def conflict(name: str, commit: str | None = None) -> dict[str, Any] | None:
        if name in core:
            return {"with": "core", "name": name}
        if name in installed:
            return {"with": "installed", "name": name, "same_source": installed[name]["source"].get("repo") == spec.get("repo")}
        return None

    if spec["kind"] == "github":
        ref, commit = gh_resolve_commit(spec["repo"], spec["ref"])
        tree = gh_get(f"/repos/{spec['repo']}/git/trees/{commit}?recursive=1")
        files = [t for t in tree["tree"] if t["type"] == "blob"]
        roots = sorted({t["path"].rsplit("/SKILL.md", 1)[0] if "/" in t["path"] else "" for t in files if t["path"].rsplit("/", 1)[-1] == "SKILL.md"})
        base = spec["path"].strip("/")
        if base:
            roots = [r for r in roots if r == base or r.startswith(base + "/")] or ([base] if any(t["path"].startswith(base + "/") for t in files) else [])
        for i, r in enumerate(roots, 1):
            mine = [t for t in files if (t["path"].startswith(r + "/") if r else True)]
            md = next((t for t in mine if t["path"] == (f"{r}/SKILL.md" if r else "SKILL.md")), None)
            fm = None
            if md:
                try:
                    raw = http.get_text(f"https://raw.githubusercontent.com/{spec['repo']}/{commit}/{md['path']}", platform="github")
                    fm = frontmatter_of(raw)
                except CliError:
                    fm = None
            name = (fm or {}).get("name") or (r.rsplit("/", 1)[-1] or spec["repo"].split("/")[1])
            if spec.get("skill_name") and name != spec["skill_name"]:
                continue
            out["candidates"].append({"candidate": len(out["candidates"]) + 1, "name": name, "description": (fm or {}).get("description"), "path": r,
                                      "source": {"kind": "github", "repo": spec["repo"], "ref": ref, "commit": commit, "path": r, "url": f"https://github.com/{spec['repo']}/tree/{ref}/{r}".rstrip("/")},
                                      "files": len(mine), "bytes": sum(t.get("size", 0) for t in mine), "conflict": conflict(name)})
        if not out["candidates"]:
            raise CliError("NOT_FOUND", "no SKILL.md found at that link")
    elif spec["kind"] == "local":
        root = Path(spec["path"])
        out["candidates"].append({"candidate": 1, "name": root.stem if root.is_file() else root.name, "description": None, "path": "", "source": {"kind": "local", "url": str(root)}, "files": None, "bytes": None, "conflict": None})
    elif spec["kind"] in ("archive", "git", "skill_md"):
        out["candidates"].append({"candidate": 1, "name": None, "description": None, "path": "", "source": {"kind": spec["kind"], "url": spec["url"]}, "files": None, "bytes": None, "conflict": None})
    else:
        out["links"] = [spec["url"]]
        out["note"] = "web page: read it with web-reader and pick a GitHub, archive or SKILL.md link from it"
    return out


# --- fetch -----------------------------------------------------------------------------------------------

def fetch(link: str, skill: str | None = None) -> dict[str, Any]:
    prune_staging()
    spec = parse_link(link)
    sid = new_staging_id()
    root = staging_root() / sid
    skill_dir = root / "skill"
    skill_dir.mkdir(parents=True)
    source: dict[str, Any] = {"kind": spec["kind"], "url": link}
    limits = Limits()
    if spec["kind"] == "github":
        cands = resolve(link)["candidates"]
        if skill:
            cands = [c for c in cands if skill in (c["name"], c["path"])]
        if len(cands) != 1:
            shutil.rmtree(root)
            raise CliError("USAGE", f"{len(cands)} candidates match; pass --skill <name|path>", "use `resolve` to list them")
        c = cands[0]
        source = {**c["source"]}
        r = http.request("GET", f"https://codeload.github.com/{spec['repo']}/tar.gz/{c['source']['commit']}", platform="github", timeout=120)
        limits = safe_extract_tar(r.content, skill_dir, prefix=(c["path"] + "/") if c["path"] else "", strip=1)
    elif spec["kind"] == "local":
        limits = copy_local(Path(spec["path"]), skill_dir)
        source = {"kind": "local", "url": spec["path"]}
    elif spec["kind"] == "archive":
        data = http.request("GET", spec["url"], platform="web", timeout=120).content
        limits = safe_extract_zip(data, skill_dir) if spec["url"].split("?")[0].endswith((".zip", ".skill")) else safe_extract_tar(data, skill_dir)
        _flatten_single_dir(skill_dir)
    elif spec["kind"] == "skill_md":
        text = http.get_text(spec["url"], platform="web")
        _store(skill_dir, "SKILL.md", text.encode(), limits)
    elif spec["kind"] == "git":
        import tempfile
        tmp = Path(tempfile.mkdtemp(prefix="finsocnet-clone-")) / "clone"  # outside staging: no staged path ever reaches a subprocess
        env = {**os.environ, "GIT_LFS_SKIP_SMUDGE": "1", "GIT_TERMINAL_PROMPT": "0"}
        cp = subprocess.run(["git", "clone", "--depth", "1", "--no-recurse-submodules", "-c", "core.hooksPath=/dev/null", spec["url"], str(tmp)], capture_output=True, text=True, env=env, timeout=180)
        if cp.returncode != 0:
            shutil.rmtree(root, ignore_errors=True)
            shutil.rmtree(tmp.parent, ignore_errors=True)
            raise CliError("NOT_FOUND", f"git clone failed: {cp.stderr.strip()[:200]}")
        commit = subprocess.run(["git", "-C", str(tmp), "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip()
        shutil.rmtree(tmp / ".git", ignore_errors=True)
        sub = tmp
        found = [p.parent for p in tmp.rglob("SKILL.md")]
        if skill:
            found = [p for p in found if p.name == skill or p.relative_to(tmp).as_posix() == skill]
        if len(found) != 1:
            shutil.rmtree(root, ignore_errors=True)
            shutil.rmtree(tmp.parent, ignore_errors=True)
            raise CliError("USAGE", f"{len(found)} skills in the repository; pass --skill <name|path>")
        limits = copy_local(found[0], skill_dir)
        source = {"kind": "git", "url": spec["url"], "commit": commit, "path": found[0].relative_to(tmp).as_posix()}
        shutil.rmtree(tmp.parent, ignore_errors=True)
    else:
        shutil.rmtree(root)
        raise CliError("UNSUPPORTED", "this link is a web page, not a skill", "read it with web-reader and pass a GitHub, archive or SKILL.md link")
    manifest = {"staging_id": sid, "source": source, "fetched_at": ids.utc_now(), "block_findings": limits.blocks,
                "files": {rel: {"sha256": h, "bytes": (skill_dir / rel).stat().st_size, "type": "text" if (skill_dir / rel).suffix.lower() in TEXT_EXT else "other"} for rel, h in hash_dir(skill_dir).items()}}
    (root / "manifest.json").write_text(json.dumps(manifest, indent=1), encoding="utf-8")
    return {"staging_id": sid, "files": len(manifest["files"]), "block_findings": limits.blocks, "dir": str(skill_dir.relative_to(config.repo_root())), "source": source}


def _flatten_single_dir(skill_dir: Path) -> None:
    entries = list(skill_dir.iterdir())
    if len(entries) == 1 and entries[0].is_dir() and not (skill_dir / "SKILL.md").exists():
        inner = entries[0]
        for p in list(inner.iterdir()):
            shutil.move(str(p), str(skill_dir / p.name))
        inner.rmdir()


# --- check -----------------------------------------------------------------------------------------------

SECRET_RE = re.compile(r"(?i)(api[_-]?key|token|secret|password|passwd|bearer)\s*[:=]\s*['\"]?[A-Za-z0-9_\-./+=]{12,}")
RULES: list[tuple[str, re.Pattern[str], set[str]]] = [
    ("H1", re.compile(r"(curl|wget)[^\n|]*\|\s*(ba|z)?sh|iex\s*\(\s*iwr|\b(eval|exec)\s*\(.{0,80}(b64decode|urlopen|requests\.get|fromhex)|\b(pip3?|uv pip|npm|pnpm|yarn)\s+install|\bnpx\s|\buvx\s|git clone[^\n]*&&", re.I), {".md", ".py", ".sh", ".js", ".ts", ".txt", ".ps1", ".bat", ".yaml", ".yml", ".toml"}),
    ("H2", re.compile(r"~/\.(ssh|aws|netrc)|\.config/gcloud|data/sessions|store\.age|cookies\.txt|browser-profile|Login Data|age_identity|os\.environ\b(?!\.get\(|\[)|\bprintenv\b|(?<![\w.])\.env\b", re.I), {".md", ".py", ".sh", ".js", ".ts", ".txt", ".ps1", ".bat"}),
    ("H3", re.compile(r"requests\.(post|put|patch)|httpx\.(post|put|patch)|\.post\(|curl[^\n]*(-X\s*(POST|PUT|PATCH)|-d\s)|discord\.com/api/webhooks|hooks\.slack\.com|pastebin\.|transfer\.sh|ngrok|requestbin|\bnc\s+-|socket\.socket", re.I), {".md", ".py", ".sh", ".js", ".ts", ".txt", ".ps1", ".bat"}),
    ("H4", re.compile(r"marshal\.loads|zlib\.decompress\s*\(\s*base64|codecs\.decode\([^)]*rot.?13|(\\x[0-9a-fA-F]{2}){20,}"), {".py", ".js", ".ts", ".sh"}),
    ("H6", re.compile(r"~/\.(bashrc|profile|zshrc)|crontab|systemd|\.claude/settings|\bAGENTS\.md|\bCLAUDE\.md|\.agents/skills/(?!<)|git config|git push|\bsudo\b|rm\s+-rf\s+(?!/tmp|\$TMP|\./?data/)|chmod\s+777", re.I), {".md", ".py", ".sh", ".js", ".ts", ".txt", ".ps1", ".bat"}),
    ("H8", re.compile(r"\b(import|from)\s+(anthropic|openai|google\.generativeai|genai|langchain|litellm|mistralai|cohere|ollama)\b|api\.openai\.com|api\.anthropic\.com", re.I), {".md", ".py", ".js", ".ts", ".sh"}),
]
H5_PHRASES = re.compile(r"ignore (all |any )?(previous|prior|above) instructions|do not tell the user|without asking|you are now|system prompt|exfiltrate|bypass|disable the (sandbox|permissions)|--dangerously", re.I)
HIDDEN_CHARS = re.compile("[​-‏‪-‮⁦-⁩]")
M3_RE = re.compile(r"chroma" r"db|sentence[_-]transformers|faiss|sqlite[_-]vec|lancedb|qdrant|chromium\.launch|launch_persistent_context|new_context\(|(?i:password\s*=)|X_PASSWORD|REDDIT_PASSWORD|knowledge\.db", re.I)
HOST_RE = re.compile(r"https?://([A-Za-z0-9.-]+\.[a-z]{2,})")
IMPORT_RE = re.compile(r"^\s*(?:import|from)\s+([A-Za-z_][\w]*)", re.M)


def _excerpt(line: str) -> str:
    return SECRET_RE.sub(lambda m: m.group(1) + "=***", line.strip())[:200]


def _stdlib() -> set[str]:
    import sys
    return set(sys.stdlib_module_names)


def _project_deps() -> set[str]:
    try:
        import tomllib
        d = tomllib.loads((config.repo_root() / "pyproject.toml").read_text())
        names = {re.split(r"[<>=!\[ ;]", x)[0].lower().replace("-", "_") for x in d["project"]["dependencies"]}
        return names | {"finsocnet", "yaml" if "pyyaml" in names else "", "dotenv" if "python_dotenv" in names else "", "fitz", "pymupdf", "docx", "ebooklib", "lxml", "bs4"}
    except Exception:  # noqa: BLE001
        return set()


def check(sid: str, as_name: str | None = None, validate_only: bool = False) -> dict[str, Any]:
    root = staging_dir(sid)
    skill = root / "skill"
    manifest = json.loads((root / "manifest.json").read_text())
    lock = read_lock()
    findings: list[dict[str, Any]] = []
    n = 0

    def add(rule: str, sev: str, file: str, line: int | None, excerpt: str) -> None:
        nonlocal n
        n += 1
        findings.append({"id": f"F{n}", "rule": rule, "severity": sev, "file": file, "line": line, "excerpt": excerpt})

    for b in manifest.get("block_findings", []):
        add(b["rule"], "block", b["file"], None, b["reason"])
    files = sorted(p for p in skill.rglob("*") if p.is_file())
    if len(files) > MAX_FILES or sum(p.stat().st_size for p in files) > MAX_TOTAL:
        add("B4", "block", "<skill>", None, "file count or total size over limit")

    md_path = skill / "SKILL.md"
    fm = None
    name = as_name
    if not md_path.exists():
        add("B5", "block", "SKILL.md", None, "SKILL.md is missing")
    else:
        text = md_path.read_text("utf-8", "replace")
        fm = frontmatter_of(text)
        if fm is None:
            add("B5", "block", "SKILL.md", 1, "no YAML frontmatter")
        else:
            name = as_name or fm.get("name")
            if not isinstance(fm.get("name"), str) or not NAME_RE.match(str(name)) or len(str(name)) > 64:
                add("B5", "block", "SKILL.md", 1, f"invalid name {fm.get('name')!r}")
            elif not as_name and fm["name"] != (manifest["source"].get("path", "").rsplit("/", 1)[-1] or fm["name"]) and manifest["source"].get("kind") == "github" and manifest["source"].get("path"):
                add("B5", "block", "SKILL.md", 1, "frontmatter name differs from the folder name; use --as to rename")
            if not fm.get("description") or len(str(fm["description"])) > 1024:
                add("B5", "block", "SKILL.md", 1, "description missing or longer than 1024 characters")
            if fm.get("compatibility") and len(str(fm["compatibility"])) > 500:
                add("B5", "block", "SKILL.md", 1, "compatibility longer than 500 characters")
            if "allowed-tools" in fm and re.search(r"(^|[\s,])(\*|Bash|Bash\(\*\))($|[\s,])", str(fm["allowed-tools"])):
                add("H7", "high", "SKILL.md", 1, f"allowed-tools: {fm['allowed-tools']}")
            if not fm.get("license"):
                add("INFO", "info", "SKILL.md", 1, "no license in frontmatter")
        if len(text.splitlines()) > 500:
            add("INFO", "info", "SKILL.md", None, "SKILL.md is longer than 500 lines")
    if name and name in core_skill_names() and not as_name:
        add("B6", "block", "SKILL.md", None, f"name {name!r} belongs to a FinSocNet skill; install with --as <new-name>")
    elif name and name in core_skill_names():
        add("B6", "block", "SKILL.md", None, f"--as {name!r} still collides with a FinSocNet skill")

    hosts: set[str] = set()
    imports: set[str] = set()
    deps: list[str] = []
    for p in files:
        rel = p.relative_to(skill).as_posix()
        data = p.read_bytes()
        ext = p.suffix.lower()
        if ext in BIN_EXT or any(data.startswith(m) for m, _ in BIN_MAGIC if m != b"MZ" or ext not in TEXT_EXT):
            add("B3", "block", rel, None, "executable binary or compiled artifact")
            continue
        if data.count(b"\x00") > 0 and ext not in (".png", ".jpg", ".jpeg", ".gif", ".pdf", ".zip"):
            add("INFO", "info", rel, None, "binary-looking file")
            continue
        if rel.split("/")[-1] in ("requirements.txt", "package.json", "Cargo.toml", "pyproject.toml"):
            deps.append(f"{rel} present")
            add("M2", "medium", rel, None, "dependency manifest present (the installer never installs dependencies)")
        if ext not in TEXT_EXT and ext not in {".png", ".jpg", ".jpeg", ".gif", ".pdf", ".svg"}:
            add("INFO", "info", rel, None, f"unknown extension {ext or '(none)'}")
        if ext not in TEXT_EXT:
            continue
        text = data.decode("utf-8", "replace")
        lines = text.splitlines()
        if ext in {".md", ".yaml", ".yml", ".json"}:
            for i, l in enumerate(lines, 1):
                if HIDDEN_CHARS.search(l) or ("﻿" in l and i > 1):
                    add("H5", "high", rel, i, "zero-width or bidi control character")
                m = H5_PHRASES.search(l)
                if m:
                    add("H5", "high", rel, i, _excerpt(l))
            if rel == "SKILL.md" and re.search(r"<!--", text):
                add("H5", "high", rel, text[:text.index("<!--")].count("\n") + 1, "HTML comment in SKILL.md")
        if re.search(r"[A-Za-z0-9+/=]{200,}", text) and re.search(r"[A-Za-z0-9+/]{200,}={0,2}", text):
            add("H4", "high", rel, None, "base64-like string of 200+ characters")
        if any(len(l) > 1000 for l in lines) and ext in {".py", ".js", ".ts"}:
            add("H4", "high", rel, None, "a code line longer than 1000 characters")
        for rule, rx, exts in RULES:
            if ext in exts:
                for i, l in enumerate(lines, 1):
                    if rx.search(l):
                        add(rule, "high", rel, i, _excerpt(l))
        if ext in {".py", ".js", ".ts", ".sh"}:
            for h in HOST_RE.findall(text):
                hosts.add(h.lower())
            for i, l in enumerate(lines, 1):
                if M3_RE.search(l):
                    add("M3", "medium", rel, i, _excerpt(l))
        if ext == ".py":
            block = re.search(r"# /// script\n(.*?)# ///", text, re.S)
            if block:
                deps.append(f"{rel}: PEP 723 block")
            imports |= {m.lower() for m in IMPORT_RE.findall(text)}
            if re.search(r"open\([^)]*['\"]w|write_text|\.write\(", text) and not re.search(r"data/|tempfile|args\.|--out", text):
                add("M4", "medium", rel, None, "writes files (check where)")
    unknown = sorted(i for i in imports - _stdlib() - _project_deps() - {""} if not i.startswith("_"))
    if unknown:
        add("M2", "medium", "scripts", None, "imports not in pyproject.toml: " + ", ".join(unknown[:12]))
        deps += unknown
    for h in sorted(hosts):
        add("M1", "medium", "scripts", None, f"network host: {h}")

    locked = lock["skills"].get(name or "", {})
    unchanged_hashes = locked.get("files", {})
    ftr = [{"path": rel, "sha256": sha, "bytes": (skill / rel).stat().st_size, "unchanged": unchanged_hashes.get(rel) == sha}
           for rel, sha in hash_dir(skill).items()]
    counts = {s: sum(1 for f in findings if f["severity"] == s) for s in ("block", "high", "medium", "info")}
    result = {"staging_id": sid, "name": name, "frontmatter": fm, "findings": findings, "counts": counts, "files_to_read": ftr, "dependencies": deps, "hosts": sorted(hosts),
              "conflict": ({"with": "core", "name": name} if name in core_skill_names() else {"with": "installed", "name": name} if name in lock["skills"] else None), "installable": counts["block"] == 0}
    (root / "check.json").write_text(json.dumps(result, indent=1), encoding="utf-8")
    return result


def diff(sid: str, against: str) -> dict[str, Any]:
    import difflib
    cur = skills_dir() / against
    if not cur.exists():
        raise CliError("NOT_FOUND", f"{against} is not installed")
    new = staging_dir(sid) / "skill"
    old_h, new_h = hash_dir(cur), hash_dir(new)
    changed = sorted(k for k in new_h if k in old_h and new_h[k] != old_h[k])
    out = {"added": sorted(set(new_h) - set(old_h)), "removed": sorted(set(old_h) - set(new_h)), "changed": changed, "diffs": {}}
    for k in changed:
        a = (cur / k).read_text("utf-8", "replace").splitlines()
        b = (new / k).read_text("utf-8", "replace").splitlines()
        out["diffs"][k] = "\n".join(list(difflib.unified_diff(a, b, f"installed/{k}", f"staged/{k}", lineterm=""))[:200])
    return out


# --- review, install, remove, list ----------------------------------------------------------------------

def verify_review(sid: str, review: dict[str, Any]) -> None:
    root = staging_dir(sid)
    details: list[dict[str, Any]] = []
    errs = schema_errors("skill_review", review)
    if errs:
        raise CliError("REVIEW_INCOMPLETE", "review.json failed schema validation", details=[{"path": e["path"], "problem": e["problem"]} for e in errs])
    if review["staging_id"] != sid:
        details.append({"path": "/staging_id", "problem": f"review is for {review['staging_id']}"})
    chk = json.loads((root / "check.json").read_text()) if (root / "check.json").exists() else None
    if chk is None:
        raise CliError("REVIEW_INCOMPLETE", "run `check` before `install`")
    skill = root / "skill"
    for rel, sha in hash_dir(skill).items():
        got = review["files_read"].get(rel)
        if got is None:
            details.append({"path": f"/files_read/{rel}", "problem": "file not reviewed"})
        elif got != sha:
            details.append({"path": f"/files_read/{rel}", "problem": "hash differs: the staged file changed after `check`; run `check` again and re-read it"})
    assessed = {f["id"]: f for f in review["findings"]}
    for f in chk["findings"]:
        if f["severity"] == "high":
            a = assessed.get(f["id"])
            if a is None:
                details.append({"path": f"/findings/{f['id']}", "problem": f"high finding {f['rule']} has no assessment"})
            elif a["assessment"] == "blocking":
                details.append({"path": f"/findings/{f['id']}", "problem": "assessed as blocking"})
    if any(o.get("severity") == "blocking" for o in review.get("own_findings", [])):
        details.append({"path": "/own_findings", "problem": "an own finding is blocking"})
    if review["verdict"] != "approve":
        details.append({"path": "/verdict", "problem": "verdict is not approve"})
    if not review["purpose_match"]:
        details.append({"path": "/purpose_match", "problem": "purpose does not match the description"})
    if details:
        raise CliError("REVIEW_INCOMPLETE", f"review is incomplete ({len(details)} problem(s))", details=details)


def install(sid: str, review: dict[str, Any], user_confirmed: bool, as_name: str | None, replace: bool, run_id: int, reviewed_by: dict[str, Any] | None = None) -> dict[str, Any]:
    if not user_confirmed:
        raise CliError("USAGE", "--user-confirmed is required: ask the user first")
    root = staging_dir(sid)
    chk = check(sid, as_name)  # re-scan: the files are re-hashed and re-scanned at install time
    if chk["counts"]["block"]:
        raise CliError("BLOCKED", "block findings prevent installation", details=[{"path": f["file"], "problem": f"{f['rule']}: {f['excerpt']}"} for f in chk["findings"] if f["severity"] == "block"])
    verify_review(sid, review)
    manifest = json.loads((root / "manifest.json").read_text())
    name = as_name or chk["name"]
    lock = read_lock()
    target = skills_dir() / name
    if target.exists():
        entry = lock["skills"].get(name)
        src_old, src_new = (entry or {}).get("source", {}), manifest["source"]
        same_source = entry is not None and ((src_old.get("repo") and src_old.get("repo") == src_new.get("repo")) or (src_old.get("url") and src_old.get("url") == src_new.get("url")))
        if not (replace and same_source):
            raise CliError("CONFLICT", f"skill {name!r} already exists and is not an installed skill from the same source", "use --as <new-name>, or --replace for an update from the same source")
    tmp = skills_dir() / f"{name}.tmp-{os.urandom(2).hex()}"
    shutil.copytree(root / "skill", tmp)
    if as_name and chk["frontmatter"] and chk["frontmatter"].get("name") != as_name:
        md = tmp / "SKILL.md"
        md.write_text(re.sub(r"(?m)^name:\s*.+$", f"name: {as_name}", md.read_text("utf-8"), count=1), encoding="utf-8")
    backup = None
    if target.exists():
        backup = backups_root() / f"{name}-{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}"
        backup.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(target), str(backup))
    os.rename(tmp, target)
    lock["skills"][name] = {"source": manifest["source"], "installed_at": ids.utc_now(), "run_id": run_id, "renamed_from": chk["frontmatter"]["name"] if as_name and chk["frontmatter"] and chk["frontmatter"].get("name") != as_name else None,
                            "files": hash_dir(target), "review": {"verdict": review["verdict"], "high_accepted": [f"{f['rule']}: {f['note']}" for f in review["findings"] if f["assessment"] == "accepted"],
                                                                  "summary": review["summary"], "reviewed_by": reviewed_by or {}}, "dependencies": review.get("dependencies", [])}
    write_lock(lock)
    shutil.rmtree(root, ignore_errors=True)
    return {"installed": name, "path": str(target.relative_to(config.repo_root())), "backup": str(backup.relative_to(config.repo_root())) if backup else None, "dependencies": review.get("dependencies", []),
            "note": "not committed: review `git status`, then commit the new folder and config/skills.lock.json"}


def remove(name: str, user_confirmed: bool) -> dict[str, Any]:
    if not user_confirmed:
        raise CliError("USAGE", "--user-confirmed is required: ask the user first")
    lock = read_lock()
    if name in core_skill_names() or name not in lock["skills"]:
        raise CliError("CONFLICT", f"{name!r} is not an installed third-party skill", "core FinSocNet skills cannot be removed with skill-installer")
    target = skills_dir() / name
    backup = backups_root() / f"{name}-{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}"
    backup.parent.mkdir(parents=True, exist_ok=True)
    if target.exists():
        shutil.move(str(target), str(backup))
    del lock["skills"][name]
    write_lock(lock)
    return {"removed": name, "backup": str(backup.relative_to(config.repo_root()))}


def list_skills(installed_only: bool = False) -> list[dict[str, Any]]:
    lock = read_lock()["skills"]
    out = []
    for d in sorted(skills_dir().iterdir()) if skills_dir().exists() else []:
        if not d.is_dir() or not (d / "SKILL.md").exists():
            continue
        fm = frontmatter_of((d / "SKILL.md").read_text("utf-8", "replace")) or {}
        entry = lock.get(d.name)
        row = {"name": d.name, "type": "installed" if entry else "core", "version": str((fm.get("metadata") or {}).get("version", "")), "description": str(fm.get("description", ""))[:120]}
        if entry:
            row.update({"source": entry["source"].get("url"), "commit": (entry["source"].get("commit") or "")[:7], "locally_modified": hash_dir(d) != entry["files"]})
        if entry or not installed_only:
            out.append(row)
    return out


def outdated(name: str | None = None) -> list[dict[str, Any]]:
    out = []
    for n, e in read_lock()["skills"].items():
        if name and n != name:
            continue
        d = skills_dir() / n
        row: dict[str, Any] = {"name": n, "locally_modified": d.exists() and hash_dir(d) != e["files"], "upstream_changed": None}
        src = e["source"]
        if src.get("kind") == "github":
            try:
                row["upstream_commit"] = gh_get(f"/repos/{src['repo']}/commits/{src['ref']}")["sha"]
                row["upstream_changed"] = row["upstream_commit"] != src.get("commit")
            except CliError as ex:
                row["error"] = ex.message
        out.append(row)
    return out
