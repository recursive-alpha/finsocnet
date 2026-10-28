"""Platform adapters (specs/05). Each module defines one `PlatformAdapter` subclass; the skill scripts under
`.agents/skills/<skill>/scripts/` only call `run_platform_cli(Adapter())`. Pure `parse_*` functions are tested with
recorded fixtures in `tests/fixtures/<platform>/`."""
