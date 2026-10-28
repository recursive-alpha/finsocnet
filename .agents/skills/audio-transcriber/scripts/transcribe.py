#!/usr/bin/env python3
"""Local Whisper transcription (specs/05-platform-skills.md §2.2). Standard envelope; not a platform adapter."""

from __future__ import annotations

import argparse
import sys

from finsocnet.core import config, output, transcribe
from finsocnet.core.output import CliError, Result
from finsocnet.core.session_cli import _Parser


def main(argv: list[str] | None = None) -> None:
    output.begin()
    output.setup_logging(config.log_level())
    p = _Parser(prog="transcribe.py")
    sub = p.add_subparsers(dest="cmd", required=True, parser_class=_Parser)
    t = sub.add_parser("transcribe")
    t.add_argument("source", help="local audio/video file or any yt-dlp-supported URL")
    t.add_argument("--language", default="auto")
    t.add_argument("--content-id")
    t.add_argument("--diarize", action="store_true", help="reserved (whisperX/pyannote); not available in v2")
    t.add_argument("--format", choices=["json", "text"], default="json")
    try:
        args = p.parse_args(list(sys.argv[1:] if argv is None else argv))
    except CliError as e:
        output.fail("audio-transcriber", e.code, e.message, e.hint)
        return

    def run() -> Result:
        if args.diarize:
            raise CliError("UNSUPPORTED", "speaker diarization is not implemented in v2", "the agent attributes speakers while transforming (03 §6)")
        res = transcribe.transcribe(args.source, args.language, args.content_id)
        return Result(res)

    output.run_command("audio-transcriber.transcribe", run, args.format)


if __name__ == "__main__":
    main()
