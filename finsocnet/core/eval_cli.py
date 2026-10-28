"""`finsocnet eval prepare|score|run` (docs/spec/06-explore-improve-eval.md §3). Scripts never call an LLM (ADR-002):
the harness agent produces the outputs, these functions only prepare inputs and score outputs deterministically."""

from __future__ import annotations

import argparse
import logging
import json
import re
import sqlite3
import sys
import tempfile
from pathlib import Path
from typing import Any

from finsocnet.core import cards as cards_mod, config, content as content_mod, migrations, output
from finsocnet.core.db import connect
from finsocnet.core.output import CliError, Result

SETS = ("transform", "dedup", "search", "attribution")
LINE_RE = re.compile(r"^\[#(\d+) \| ([^\]]*)\] ?(.*)$")
CONTENT_TYPE = {"youtube": "video", "podcast": "episode", "reddit": "thread", "book": "book", "stackexchange": "question",
                "tradingview": "script", "forum": "post", "x": "post", "medium": "article", "discord": "chat_window"}
TERMS_MATCH = 0.6


def evals_dir() -> Path:
    return config.repo_root() / "evals"


def case_files(set_name: str) -> list[tuple[str, Path]]:
    base = evals_dir() / set_name
    if not base.exists():
        return []
    if set_name == "transform":
        return [(d.name, d) for d in sorted(base.iterdir()) if d.is_dir()]
    return [(f.stem, f) for f in sorted(base.glob("*.json"))]


def read(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


# --- prepare --------------------------------------------------------------------------------------------

def prepare(set_name: str, out: Path) -> dict[str, Any]:
    if set_name not in SETS:
        raise CliError("USAGE", f"set must be one of {', '.join(SETS)}")
    out.mkdir(parents=True, exist_ok=True)
    written = []
    for name, path in case_files(set_name):
        if set_name == "transform":
            data = read(path / "input.json")
            fn = f"{name}.input.json"
        elif set_name == "dedup":
            d = read(path)
            data = {"new_card": d["new_card"], "candidates": d["candidates"]}
            fn = f"{name}.input.json"
        elif set_name == "search":
            d = read(path)
            data = {"question": d["question"]}
            fn = f"{name}.input.json"
        else:
            d = read(path)
            data = {"chunk_view": d["chunk_view"], "cast": d["cast"]}
            fn = f"{name}.input.json"
        (out / fn).write_text(json.dumps(data, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
        written.append(fn)
    produce = {"transform": "<case>.cards.json (array of cards, [] when there is no knowledge)",
               "dedup": "<case>.decision.json ({decision, target_card_id})",
               "search": "<case>.query_card.json",
               "attribution": "<case>.attribution.json ({seq: person_id})"}[set_name]
    return {"set": set_name, "cases": len(written), "dir": str(out), "agent_must_write": produce,
            "then": f"finsocnet eval score {set_name} --outputs <dir>"}


# --- helpers --------------------------------------------------------------------------------------------

def parse_chunk_view(view: str) -> list[dict[str, Any]]:
    segs: list[dict[str, Any]] = []
    for line in view.splitlines():
        m = LINE_RE.match(line)
        if m:
            seq, desc, text = int(m.group(1)), m.group(2), m.group(3)
            kind = "code" if "code " in desc else "page" if "page " in desc else "post" if desc.startswith("comment") else "transcript"
            segs.append({"seq": seq, "kind": kind, "text": text})
        elif segs and not line.startswith(("CONTENT", "SOURCE", "PEOPLE", "SEGMENTS")):
            segs[-1]["text"] += "\n" + line
    return segs


def scratch_db(root: Path) -> sqlite3.Connection:
    logging.getLogger("finsocnet.migrations").setLevel(logging.WARNING)
    conn = connect(root / "eval.db")
    migrations.migrate(conn)
    from finsocnet.core.kb_cli import load_seed
    load_seed(conn)
    return conn


def _accepts(expected: Any, actual: Any) -> bool:
    if isinstance(expected, list):
        return actual in expected or (actual is None and "NONE" in expected) or (actual == "NONE" and None in expected)
    return actual == expected


def card_matches(expected: dict[str, Any], produced: dict[str, Any]) -> bool:
    if not _accepts(expected["kind"], produced.get("kind")):
        return False
    if not _accepts(expected["category"], produced.get("category")):
        return False
    if "action" in expected and not _accepts(expected["action"], produced.get("action")):
        return False
    exp_terms = set(expected.get("terms", []))
    if exp_terms and len(exp_terms & set(produced.get("terms", []))) / len(exp_terms) < TERMS_MATCH:
        return False
    if expected.get("segment_seq") is not None and produced.get("citation", {}).get("segment_seq") != expected["segment_seq"]:
        return False
    return True


# --- scoring --------------------------------------------------------------------------------------------

def score_transform(outputs: Path) -> dict[str, Any]:
    failures: list[dict[str, str]] = []
    exp_total = prod_total = matched = valid = 0
    nocard_cases = nocard_ok = 0
    with tempfile.TemporaryDirectory() as tmp:
        conn = scratch_db(Path(tmp))
        run = conn.execute("INSERT INTO agent_runs (skill) VALUES ('eval')").lastrowid
        for name, path in case_files("transform"):
            inp, exp = read(path / "input.json"), read(path / "expected.json")["cards"]
            out_file = outputs / f"{name}.cards.json"
            if not out_file.exists():
                failures.append({"case": name, "reason": "no output file"})
                exp_total += len(exp)
                nocard_cases += not exp
                continue
            produced = read(out_file)
            if not isinstance(produced, list):
                failures.append({"case": name, "reason": "output is not an array"})
                continue
            conn.execute("DELETE FROM card_citations")
            cid = inp.get("content_id") or f"youtube:{name}"
            segs = parse_chunk_view(inp["chunk_view"])
            for p in inp.get("cast", []):
                if p.get("person_id"):
                    conn.execute("INSERT OR IGNORE INTO persons (id, canonical_name) VALUES (?, ?)", (p["person_id"], p.get("name", p["person_id"])))
            plat = cid.split(":")[0]
            if not conn.execute("SELECT 1 FROM contents WHERE id = ?", (cid,)).fetchone():
                content_mod.add_content(conn, {"id": cid, "platform": plat, "content_type": CONTENT_TYPE.get(plat, "post"),
                                               "segments": [{"seq": s["seq"], "kind": s["kind"], "locator": {}, "text": s["text"]} for s in segs]}, run)
            exp_total += len(exp)
            prod_total += len(produced)
            if not exp:
                nocard_cases += 1
                if not produced:
                    nocard_ok += 1
                else:
                    failures.append({"case": name, "reason": f"expected no cards, produced {len(produced)}"})
            free = list(exp)
            for i, card in enumerate(produced):
                probs, _ = cards_mod.validate_card(conn, card)
                if not probs:
                    valid += 1
                else:
                    failures.append({"case": name, "reason": f"card {i} invalid: {probs[0]['code']} {probs[0]['problem']}"})
                hit = next((e for e in free if card_matches(e, card)), None)
                if hit:
                    free.remove(hit)
                    matched += 1
            for e in free:
                if exp:
                    failures.append({"case": name, "reason": f"expected {e['kind']} card on segment {e.get('segment_seq')} not produced"})
        conn.close()
    return {"set": "transform", "n": len(case_files("transform")), "metrics": {
        "validity": round(valid / prod_total, 3) if prod_total else None,
        "recall": round(matched / exp_total, 3) if exp_total else None,
        "precision": round(matched / prod_total, 3) if prod_total else None,
        "no_card_accuracy": round(nocard_ok / nocard_cases, 3) if nocard_cases else None}, "failures": failures}


MERGING = {"same", "refines"}
NON_MERGING = {"new", "related", "contradicts"}


def score_dedup(outputs: Path) -> dict[str, Any]:
    failures, correct, n, wrong_merge, non_merge_cases = [], 0, 0, 0, 0
    for name, path in case_files("dedup"):
        case = read(path)
        n += 1
        out_file = outputs / f"{name}.decision.json"
        expected, target = case["expected_decision"], case.get("expected_target")
        non_merge_cases += expected in NON_MERGING
        if not out_file.exists():
            failures.append({"case": name, "reason": "no output file"})
            continue
        got = read(out_file)
        dec, tgt = got.get("decision"), got.get("target_card_id")
        if expected in NON_MERGING and dec in MERGING:
            wrong_merge += 1
        if dec == expected and (target is None or tgt == target):
            correct += 1
        else:
            failures.append({"case": name, "reason": f"expected {expected}" + (f" -> {target}" if target else "") + f", got {dec}" + (f" -> {tgt}" if tgt else "")})
    return {"set": "dedup", "n": n, "metrics": {"accuracy": round(correct / n, 3) if n else None,
            "wrong_merge_rate": round(wrong_merge / non_merge_cases, 3) if non_merge_cases else None}, "failures": failures}


def score_attribution(outputs: Path) -> dict[str, Any]:
    failures, total, ok = [], 0, 0
    cases = case_files("attribution")
    for name, path in cases:
        exp = read(path)["expected"]
        out_file = outputs / f"{name}.attribution.json"
        got = read(out_file) if out_file.exists() else {}
        if not out_file.exists():
            failures.append({"case": name, "reason": "no output file"})
        for seq, person in exp.items():
            total += 1
            if str(got.get(str(seq))) == str(person):
                ok += 1
            elif out_file.exists():
                failures.append({"case": name, "reason": f"segment {seq}: expected {person}, got {got.get(str(seq))}"})
    return {"set": "attribution", "n": len(cases), "metrics": {"accuracy": round(ok / total, 3) if total else None}, "failures": failures}


def score_search(outputs: Path) -> dict[str, Any]:
    fixture = evals_dir() / "search" / "fixture_db.sql"
    if not fixture.exists():
        raise CliError("NOT_FOUND", "evals/search/fixture_db.sql does not exist")
    failures, hits, mrr_sum, n = [], 0, 0.0, 0
    exp_total = 0
    with tempfile.TemporaryDirectory() as tmp:
        conn = scratch_db(Path(tmp))
        conn.executescript(fixture.read_text(encoding="utf-8"))
        keys = {r["id"]: (re.search(r"fixture_key:\s*(\S+)", r["notes"] or "") or [None, None])[1] for r in conn.execute("SELECT id, notes FROM knowledge_cards")}
        for name, path in case_files("search"):
            case = read(path)
            n += 1
            out_file = outputs / f"{name}.query_card.json"
            if not out_file.exists():
                failures.append({"case": name, "reason": "no output file"})
                exp_total += len(case["expected_card_refs"])
                continue
            try:
                res = cards_mod.search_cards(conn, read(out_file), None, 10)["results"]
            except CliError as e:
                failures.append({"case": name, "reason": f"invalid query card: {e.message}"})
                exp_total += len(case["expected_card_refs"])
                continue
            ranked = [keys.get(r["card"]["id"]) for r in res]
            expected = set(case["expected_card_refs"])
            exp_total += len(expected)
            found = expected & set(ranked)
            hits += len(found)
            first = next((i for i, k in enumerate(ranked, 1) if k in expected), None)
            mrr_sum += 1 / first if first else 0
            if expected - found:
                failures.append({"case": name, "reason": f"missing {sorted(expected - found)} in top 10"})
            if set(case.get("must_not", [])) & set(ranked):
                failures.append({"case": name, "reason": f"returned forbidden {sorted(set(case['must_not']) & set(ranked))}"})
        conn.close()
    return {"set": "search", "n": n, "metrics": {"recall@10": round(hits / exp_total, 3) if exp_total else None,
            "mrr": round(mrr_sum / n, 3) if n else None}, "failures": failures}


SCORERS = {"transform": score_transform, "dedup": score_dedup, "attribution": score_attribution, "search": score_search}
TARGETS = {"transform": {"validity": (">=", 1.0), "recall": (">=", 0.80), "precision": (">=", 0.75)},
           "dedup": {"accuracy": (">=", 0.85), "wrong_merge_rate": ("<=", 0.03)},
           "search": {"recall@10": (">=", 0.80)}, "attribution": {"accuracy": (">=", 0.85)}}


def with_targets(report: dict[str, Any]) -> dict[str, Any]:
    t = TARGETS.get(report["set"], {})
    report["targets"] = {k: {"target": f"{op} {v}", "met": (report["metrics"].get(k) is not None and (report["metrics"][k] >= v if op == ">=" else report["metrics"][k] <= v))}
                         for k, (op, v) in t.items()}
    return report


# --- CLI ------------------------------------------------------------------------------------------------

def main(argv: list[str] | None = None) -> None:
    output.begin()
    output.setup_logging(config.log_level())
    p = argparse.ArgumentParser(prog="finsocnet eval")
    sub = p.add_subparsers(dest="cmd", required=True)
    a = sub.add_parser("prepare")
    a.add_argument("set", choices=SETS)
    a.add_argument("--out", required=True)
    b = sub.add_parser("score")
    b.add_argument("set", choices=SETS)
    b.add_argument("--outputs", required=True)
    b.add_argument("--out")
    c = sub.add_parser("run")
    c.add_argument("--all", action="store_true")
    c.add_argument("--out")
    try:
        args = p.parse_args(argv if argv is not None else sys.argv[1:])
    except SystemExit as e:  # argparse already printed usage
        raise
    command = f"eval.{args.cmd}"

    def run() -> Result:
        if args.cmd == "prepare":
            return Result(prepare(args.set, config.resolve_path(args.out)))
        if args.cmd == "score":
            rep = with_targets(SCORERS[args.set](config.resolve_path(args.outputs)))
            if args.out:
                Path(config.resolve_path(args.out)).write_text(json.dumps(rep, indent=1) + "\n", encoding="utf-8")
            return Result(rep)
        steps = [{"set": s, "cases": len(case_files(s)), "steps": [f"finsocnet eval prepare {s} --out data/work/<run>/eval_inputs/",
                 "write the outputs with the CURRENT skill instructions into data/work/<run>/eval_outputs/",
                 f"finsocnet eval score {s} --outputs data/work/<run>/eval_outputs/ --out data/work/<run>/eval_{s}.json"]} for s in SETS if case_files(s)]
        return Result({"sets": steps, "note": "eval never calls an LLM; you (the agent) produce the outputs"})

    output.run_command(command, run)


if __name__ == "__main__":
    main()
