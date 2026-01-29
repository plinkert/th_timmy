# Changelog

All notable changes to the Threat Hunting Lab project are documented in this file.

## [Unreleased]

### Added

- **2025-01-27**: Migrated 5 playbooks to YAML format (`elk.yml`, `ms_defender.yml`). One file per tool with `manual` and `api` sections; queries referenced via `query_id`/`query_ids`. Added `output`, `triage`, and `response` sections to metadata.yml. `query_loader` supports both YAML format and legacy single-file queries (.sql, .kql, .json). Optional `required_indices` for SIEM in data_sources.
