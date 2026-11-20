# Product Core

This page owns the installed identity of KN Event Horizon, a domain knowledge aggregator: the
distribution, the import package, and the commands. It serves the
[`project-identity`](../../design/spec.md#project-identity) capability.

## Identity

| Item | Value |
| --- | --- |
| Display name | KN Event Horizon |
| Description | A domain knowledge aggregator |
| Repository | [volod/kn-event-horizon](https://github.com/volod/kn-event-horizon) |
| Distribution | `kn-event-horizon` (`pyproject.toml`) |
| Import package | `kn` (`src/kn/`) |
| Operator command | `kn` -> `kn.cli:main` |
| Plan summary command | `kn-plan` -> `kn.quality.plan_summary:main` |
| Shell helper prefix | `kn_` in `scripts/shared/common.sh` |

The README and the `pyproject.toml` description use the same project description.

## Interfaces

- `kn.project_info()` returns a frozen `ProjectInfo` with `distribution`, `package`, and `version`.
  `src/kn/metadata.py` holds `DISTRIBUTION_NAME` and `PACKAGE_NAME`, and falls back to
  `0.0.0+uninstalled` when distribution metadata is unavailable in a source-only checkout.
- `src/kn/cli.py` owns argument parsing. `kn info` logs
  `kn-event-horizon <version> (kn)`. Later operator subcommands attach to `build_parser()`.
- `kn-plan --root <path>` prints the same plan summary as `make plan-status`.

## Verification

| Check | Command | Expected result |
| --- | --- | --- |
| Installed import | `make doctor` | prints `kn-event-horizon` |
| Installed CLI | `make run` | logs `kn-event-horizon 0.1.0 (kn)` |
| Plan command | `.venv/bin/kn-plan` | the plan summary, same as `make plan-status` |
| API and command tests | `make test` | `tests/test_metadata.py` and `tests/test_cli.py` pass |
| Distribution build | `make build` | `kn_event_horizon-<version>.tar.gz` and a `py3-none-any` wheel |

The identity was set by the `personalize-template-project` task; see
[record 0001](../records/0001-project-identity-personalize-template-project.md).

The plan command reads prerequisites across wrapped lines. The
[specification audit](../records/0003-adhoc-specification-audit.md) records the release
dependencies and seed checks verified during planning.
