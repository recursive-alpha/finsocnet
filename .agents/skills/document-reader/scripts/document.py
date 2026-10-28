#!/usr/bin/env python3
"""Document reader CLI: fetch a file or URL, scan the drop folder (docs/spec/05-platform-skills.md §2.11)."""

from finsocnet.adapters.document import Document
from finsocnet.core import config, content, runs
from finsocnet.core.platform import run_platform_cli, write_record


def _setup(p):
    p.add_argument("--dir", help="folder to scan (default: data/inbox/documents)")
    p.add_argument("--ingest", action="store_true")


def _scan(adapter, args, conn):
    results = []
    for path, rec, err in adapter.scan_dir(args.dir):
        if rec is None:
            results.append({"file": path.name, "status": "skipped", "reason": err})
            continue
        entry = {"file": path.name, "id": rec["id"], "segments": len(rec["segments"]), "record_path": write_record(rec)}
        if args.ingest:
            run_id = runs.resolve_run(conn, args.run)
            entry["ingest"] = content.add_content(conn, rec, run_id)
            done = path.parent / "done"
            done.mkdir(exist_ok=True)
            path.rename(done / path.name)
        results.append(entry)
    return {"files": results, "moved_to_done": bool(args.ingest)}


if __name__ == "__main__":
    run_platform_cli(Document(), extra={"scan": (_setup, _scan)})
