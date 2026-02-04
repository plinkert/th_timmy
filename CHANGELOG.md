# Changelog

All notable changes to the Threat Hunting Lab project are documented in this file.

## [Unreleased]

### Added

- **2025-01-27**: Migrated 5 playbooks to YAML format (`elk.yml`, `ms_defender.yml`). One file per tool with `manual` and `api` sections; queries referenced via `query_id`/`query_ids`. Added `output`, `triage`, and `response` sections to metadata.yml. `query_loader` supports both YAML format and legacy single-file queries (.sql, .kql, .json). Optional `required_indices` for SIEM in data_sources.
- **2025-01-27**: Query Generator (Step 1.2): `generate_queries()` loads from playbooks via query_loader, filters by tool and mode, substitutes placeholders (`{{timestamp_start}}`, `{{timestamp_end}}`, `{{days}}`), saves to `queries_generated/`. CLI: `python scripts/th_playbook.py generate T1059 T1055 -t elk ms_defender -m manual`.
- **2025-01-27**: n8n UI Hunt Selection (Step 1.4): Form in n8n for selecting hunts, tools, and mode. Hunt API (`hunt_api.py`) provides POST /generate-queries; workflow calls it, stores session_id in `queries_generated/sessions/`. See USER_GUIDE_HUNTER.md and hosts/vm04-orchestrator/README.md.
