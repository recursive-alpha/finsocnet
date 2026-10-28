#!/usr/bin/env python3
"""platform-skill-builder CLI: probe a site, manage and check recipes, scaffold the skill, or run a recipe's operations.

    site.py probe <url>
    site.py recipes
    site.py validate <name>
    site.py check <name> [--query Q] [--source S] [--item URL] [--target T]
    site.py scaffold <name> [--force]
    site.py run <name> search|list|profile|fetch ...      (same flags as any platform skill)
"""

import argparse
import sys

from finsocnet.adapters import site_recipe, site_tools
from finsocnet.core import config, output
from finsocnet.core.output import CliError, Result
from finsocnet.core.platform import run_platform_cli


def main() -> None:
    if len(sys.argv) > 3 and sys.argv[1] == "run":
        name = sys.argv[2]
        run_platform_cli(site_recipe.SiteRecipe(name), argv=sys.argv[3:])
        return
    output.begin()
    p = argparse.ArgumentParser(prog="site.py")
    sub = p.add_subparsers(dest="cmd", required=True)
    a = sub.add_parser("probe"); a.add_argument("url")
    sub.add_parser("recipes")
    for n in ("validate", "scaffold"):
        b = sub.add_parser(n); b.add_argument("name")
        if n == "scaffold":
            b.add_argument("--force", action="store_true")
    c = sub.add_parser("check"); c.add_argument("name")
    for f in ("query", "source", "item", "target"):
        c.add_argument(f"--{f}")
    args = p.parse_args()

    def run() -> Result:
        if args.cmd == "probe":
            return Result(site_tools.probe(args.url))
        if args.cmd == "recipes":
            return Result({"recipes": [{"name": q.stem, "path": str(q.relative_to(config.repo_root()))} for q in sorted((config.repo_root() / "config" / "sites").glob("*.yaml"))]})
        if args.cmd == "validate":
            site_recipe.load_recipe(args.name)
            return Result({"name": args.name, "valid": True})
        if args.cmd == "check":
            return Result(site_tools.check(args.name, query=args.query, source=args.source, item=args.item, target=args.target))
        return Result(site_tools.scaffold(args.name, force=args.force))

    output.run_command(f"site.{args.cmd}", run)


if __name__ == "__main__":
    main()
