# Project Map: FIRE-Max Finance Automation

This document serves as the index for the project structure and explains the "Local Sync" strategy for interfacing with Google Drive.

## Directory Structure

| Directory | Purpose |
| :--- | :--- |
| `execution/` | Contains all Python scripts for logic and automation. |
| `directives/` | Stores Markdown Standard Operating Procedures (SOPs) and logic rules. |
| `data/stubs/` | Holds 5-row sample CSVs of bank statements for testing. |
| `logs/` | Tracks file movements, processing errors, and execution history. |
| `config.json` | **Single Source of Truth** for G: Drive paths and app settings. |

## Local Sync Strategy

The automation relies on a deterministic mapping between the local environment and the Google Drive "Local Sync" folder.

### 1. Configuration
All absolute paths to Google Drive folders are stored in `config.json`. **Hardcoding paths in scripts is strictly prohibited.**

### 2. Workflow
1.  **Ingestion:** Scripts in `execution/` read `config.json` to find the `inbox` path.
2.  **Detection:** The system acts as a "watcher" or periodically scans the `inbox` for new files (e.g., PDFs, CSVs).
3.  **Processing:**
    *   Files are parsed locally.
    *   Data is extracted and mapped according to `directives/identity_registry.md`.
4.  **Action:**
    *   **Archive:** Successfully processed source files are moved from `inbox` to `archive`.
    *   **Update:** Extracted data is written to the `master_record` (Google Sheet) or local intermediate files.
5.  **Logging:** All actions (successes, failures, moves) are logged to `logs/`.

## Key Files
- `config.json`: Database of external paths.
- `directives/identity_registry.md`: The brain of the categorization logic.
