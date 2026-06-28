# Reef Spore Current Automaton Dataset

## Overview

This synthetic dataset contains deterministic reef-spore current automaton programs. Each row represents a program trace over six pools (`P0` to `P5`). The goal is to reconstruct the final measured state of a requested target pool after executing the program from left to right.

The dataset was generated locally using the included `generate_raw.py` script with a fixed random seed. It is intended for a from-scratch benchmark: participants should implement an automaton interpreter and learn calibration corrections from public training rows. No external source data, pretrained model outputs, or LLM-generated labels are used.

Public columns contain only the nominal program and public reef context. Final targets include systematic measurement effects tied to tide phase, reef zone, lunar window, repeated operation patterns, and target-pool position.

## File Structure

The uploaded raw dataset zip contains exactly these top-level files:

| File | Description |
|---|---|
| `data.csv` | Raw generated automaton cases. Each row contains the program, public context columns, final target columns, operation-count helper columns, and hidden diagnostic grouping columns used only for splitting and private evaluation. |
| `generate_raw.py` | Deterministic generator used to create `data.csv` from a fixed random seed. |

The challenge preparation step, configured separately in the challenge editor, converts the raw rows into the public training file, public test file, sample submission file, and private answers file used during scoring.

## Raw Columns

| Column | Type | Description |
|---|---|---|
| `case_id` | string | Raw program identifier. It is remapped before public release. |
| `target_pool` | string | Pool whose final state is requested (`P0` through `P5`). |
| `program_text` | string | Ordered semicolon-separated automaton program. |
| `operation_count` | int | Number of operations in the program. |
| `tide_phase` | categorical | Tide context: `ebb`, `slack`, or `flood`. |
| `reef_zone` | categorical | Reef context: `lagoon`, `crest`, or `fore_reef`. |
| `moon_window` | categorical | Lunar window: `new_moon`, `quarter`, or `full_moon`. |
| `spore_mass` | float | Final measured spore mass. |
| `branch_pct` | float | Final branching-coral lineage percentage. |
| `plate_pct` | float | Final plating-coral lineage percentage. |
| `free_pct` | float | Final free-drifting/silt signal percentage. |
| `count_drift`, `count_splice`, `count_settle`, `count_graze`, `count_mutate`, `count_pulse`, `count_bleach`, `count_limit` | int | Raw helper counts derived from the program. These are included in raw data for auditability but removed from public prepared files. |
| `operation_bin_private` | categorical | Hidden operation-length group for worst-group scoring. |
| `mass_bin_private` | categorical | Hidden mass group for worst-group scoring. |
| `structure_private` | categorical | Hidden structural-pattern group for worst-group scoring. |

## Public Prepared Columns

Participants work with prepared CSV files created from the raw dataset.

| Column | Type | Public Train | Public Test | Description |
|---|---|---|---|---|
| `case_id` | string | yes | yes | Opaque remapped row identifier. |
| `target_pool` | string | yes | yes | Requested target pool. |
| `program_text` | string | yes | yes | Ordered automaton program to execute. |
| `operation_count` | int | yes | yes | Number of automaton operations. |
| `tide_phase` | categorical | yes | yes | Public tide context. |
| `reef_zone` | categorical | yes | yes | Public reef-zone context. |
| `moon_window` | categorical | yes | yes | Public lunar-window context. |
| `spore_mass` | float | yes | no | Final measured spore mass. |
| `branch_pct` | float | yes | no | Final branch lineage percentage. |
| `plate_pct` | float | yes | no | Final plate lineage percentage. |
| `free_pct` | float | yes | no | Final free/silt signal percentage. |

The sample submission contains `case_id`, `spore_mass`, `branch_pct`, `plate_pct`, and `free_pct`.

## Data Characteristics

- 3,600 raw cases.
- Programs contain roughly 23 to 42 operations.
- Operations include drift, splice, settle, graze, mutate, pulse, bleach, and limit operations.
- The target cannot be solved from metadata alone because ordered automaton execution determines the nominal state.
- A literal interpreter alone is intentionally imperfect because measured targets include public-context calibration effects.
- Hidden groups evaluate robustness across program length, final mass bands, and structural patterns such as pulse-heavy, bleach-heavy, and splice-heavy traces.

## License and Source

The dataset is generated locally from the included script and is released as CC0 1.0 Public Domain. No external source data is used.
