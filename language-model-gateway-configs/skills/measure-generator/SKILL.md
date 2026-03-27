---
name: measure-generator
description: Calculate or improve HEDIS quality measures for a single patient given a FHIR R4 Bundle. Use when the user asks to run, calculate, implement, improve, debug, or extend a HEDIS measure, or references a specific measure name or abbreviation (e.g., CBP, AMR, BCS-E). Pre-built measure modules exist in measures/ for all 87 HEDIS MY 2025 measures.
allowed-tools: Read Glob Grep WebSearch Bash Edit Write
license: Internal use only
metadata:
  owner: icanbwell
  last_reviewed: 2026-03-27
  scope: HEDIS MY 2025 measure calculation and code generation from FHIR data
---

# HEDIS Measure Calculator

## Skill Card

**Goal**: Calculate HEDIS MY 2025 measures for individual patients using pre-built Python modules, or generate/improve measure calculation code.

**Use when**:
- User asks to calculate/run a HEDIS measure for a patient FHIR Bundle
- User asks to implement, improve, debug, or extend a HEDIS measure calculation
- User references a specific HEDIS measure (e.g., "CBP", "Controlling High Blood Pressure", "AMR")
- User asks about measure logic, eligible population, exclusions, or numerator criteria

**Do not use when**:
- User asks general questions about HEDIS specifications (answer directly)
- User wants to query a FHIR server (use fhir-query-builder skill instead)
- User asks about measure reporting or submission processes (answer directly)

## Architecture

All measure code lives in `measures/`:

```
measures/
├── __init__.py
├── hedis_common.py              # Shared utilities (DO NOT DUPLICATE)
├── measure_cbp.py               # One file per measure
├── measure_amr.py
├── measure_cis_e.py             # ECDS measures use underscores (CIS-E -> cis_e)
└── ...                          # 87 measure files total
```

### Shared Module: `measures/hedis_common.py`

All reusable code lives here. Individual measure files MUST import from it. Key capabilities:

| Category | Functions |
|---|---|
| **Value Set Loading** | `load_value_sets_from_csv(abbreviation)` → `{vs_name: {system_uri: {codes}}}` |
| **Value Set Access** | `all_codes(vs, name)`, `codes_for_system(vs, name, uri)`, `codes_for_any_system(vs, name)` |
| **Bundle Helpers** | `get_patient()`, `get_patient_id()`, `get_resources_by_type()`, `get_patient_birth_date()`, `get_patient_gender()` |
| **Date Utilities** | `parse_date()`, `calculate_age()`, `is_date_in_range()`, `measurement_year_dates()`, `prior_year_dates()` |
| **Code Matching** | `has_code_in_set()`, `resource_has_code()`, `resource_has_any_code()`, `codeable_concept_has_any_code()`, `has_code_prefix()`, `medication_has_code()` |
| **Resource Dates** | `get_encounter_date()`, `get_condition_onset()`, `get_procedure_date()`, `get_observation_date()`, `get_medication_date()` |
| **Finders** | `find_encounters_with_codes()`, `find_conditions_with_codes()`, `find_procedures_with_codes()`, `find_observations_with_codes()`, `find_medications_with_codes()` |
| **Common Exclusions** | `check_common_exclusions()`, `check_hospice()`, `check_death()`, `check_palliative_care()`, `check_frailty_advanced_illness()` |
| **BP Helpers** | `get_bp_readings()`, `get_most_recent_bp()` |
| **Report Builders** | `build_measure_report()`, `build_multi_rate_measure_report()` |
| **Runner** | `run_measure(bundle, abbr, name, year, eligible_fn, exclusion_fn, numerator_fn)` |
| **Constants** | `ICD10CM`, `CPT`, `HCPCS`, `SNOMED`, `LOINC`, `RXNORM`, `NDC`, `CVX` (FHIR system URIs) |

### Individual Measure Files

Each `measure_<abbr>.py` follows this pattern:

```python
from .hedis_common import (load_value_sets_from_csv, run_measure, ...)

VALUE_SETS = load_value_sets_from_csv("<ABBREVIATION>")

def check_eligible_population(bundle, measurement_year) -> (bool, list[str]): ...
def check_exclusions(bundle, measurement_year) -> (bool, list[str]): ...
def check_numerator(bundle, measurement_year) -> (bool, list[str]): ...

def calculate_<abbr>_measure(bundle, measurement_year=2025) -> dict:
    return run_measure(bundle, "<ABBR>", "<Full Name>", measurement_year,
                       check_eligible_population, check_exclusions, check_numerator)
```

Value sets are loaded at import time from `references/value-sets/by-measure/` CSV files via `load_value_sets_from_csv()`, which handles both single files and split part files automatically.

### Value Set Data

Value sets live in `references/value-sets/`:
- `by-measure/<abbr>.csv` (or `<abbr>-part*.csv` for large sets) — per-measure codes
- `measures-to-value-sets.csv` — maps measures to value set OIDs
- `value-sets-to-codes-part*.csv` — complete code-level data (split for size)
- `direct-reference-codes.csv` — direct reference codes by measure

### Measure Specifications

HEDIS specifications live in `references/measures/`:
- `INDEX.md` — table of all 87 measures with abbreviations
- `<abbr>.md` — individual measure specification
- `../HEDIS-MY-2025-overview.md` — general guidelines and definitions
- `../HEDIS-MY-2025-appendices.md` — appendices

## Mandatory Workflow

### When the user asks to CALCULATE a measure:

1. Identify the measure abbreviation from the user's request. Check `references/measures/INDEX.md` if ambiguous.
2. Read the corresponding `measures/measure_<abbr>.py` file.
3. Show the user how to run it:

```python
import json
from measures.measure_cbp import calculate_cbp_measure

result = calculate_cbp_measure(patient_bundle, measurement_year=2025)
print(json.dumps(result, indent=2))
```

4. If the user provides a FHIR Bundle, run the calculation and show the MeasureReport result.

### When the user asks to CREATE or IMPROVE a measure:

#### Step 1: Identify the Measure

Match the user's request to a HEDIS MY 2025 measure. Read `references/measures/INDEX.md` if the measure name is ambiguous.

#### Step 2: Check for Existing Implementation

Read `measures/measure_<abbr>.py` if it exists. If it does, understand the current logic before making changes.

#### Step 3: Read the Measure Specification

Read the HEDIS specification from `references/measures/<abbreviation>.md`. Extract:
1. **Description** — What the measure calculates
2. **Definitions** — Key terms and thresholds
3. **Eligible Population** — Ages, enrollment, benefits, event/diagnosis criteria
4. **Required Exclusions** — All exclusion criteria
5. **Administrative Specification** — Denominator and numerator logic
6. **Value Sets Referenced** — All value set names mentioned

#### Step 4: Review the Value Sets

Read the value set CSV header from `references/value-sets/by-measure/<abbreviation>.csv` (or the first part file) to understand available value set names. Value sets are loaded at runtime by `load_value_sets_from_csv()` — do NOT hardcode codes inline.

#### Step 5: Write or Update the Code

**If creating a new measure file**, follow the pattern in existing measure files:
- Import everything needed from `hedis_common` — NEVER duplicate shared utilities
- Load value sets: `VALUE_SETS = load_value_sets_from_csv("<ABBREVIATION>")`
- Implement `check_eligible_population`, `check_exclusions`, `check_numerator`
- Use `run_measure()` for single-rate measures, `build_multi_rate_measure_report()` for multi-rate
- File name: `measure_<abbr>.py` (hyphens become underscores: CIS-E → `measure_cis_e.py`)

**If improving an existing measure**, make targeted changes. Do not rewrite the entire file.

#### Step 6: Validate

Run a syntax check:
```bash
python3 -c "from measures.measure_<abbr> import calculate_<abbr>_measure; print('OK')"
```

#### Step 7: Present

Explain what the measure calculates, the key logic, and how to run it.

## Gotchas

- **Value sets are loaded from CSV at runtime.** The `load_value_sets_from_csv()` function in hedis_common handles single and split CSV files automatically. Never hardcode value set codes in measure files.
- **Age is calculated as of December 31.** HEDIS uses end-of-year age. Use `calculate_age(birth_date, date(year, 12, 31))`.
- **"Different dates of service" means calendar dates, not encounters.** Two encounters on the same date count as one date of service.
- **BP readings exclude acute inpatient and ED settings.** For CBP/BPD/BPC-E, use `get_bp_readings(bundle, start, end, exclude_inpatient_ed=True)`.
- **Multiple BPs on same date: use lowest systolic and lowest diastolic.** Use `get_most_recent_bp()`.
- **Frailty + Advanced Illness exclusion** has age-dependent logic: 66-80 requires both frailty AND advanced illness; 81+ requires only frailty. Use `check_frailty_advanced_illness()` from hedis_common.
- **Common exclusions** (hospice, death, palliative care, frailty) are handled by `check_common_exclusions()`. Only add measure-specific exclusions in the measure file.
- **ECDS measures** (ending in -E) use electronic clinical data. Their value set abbreviation uses a hyphen (e.g., "CIS-E") but the Python file uses underscores (e.g., `measure_cis_e.py`).
- **Survey/descriptive measures** (HOS, FRM, MUI, PAO, CPA, CPC, CCC, ENP, LDM, RDM, DMH, DSU) have stub files that return empty MeasureReports — they cannot be calculated from individual FHIR data.

## Measures With Special Handling

| Pattern | Measures | Notes |
|---|---|---|
| Multiple indicators | TRC, COA, WCC, DDE, CIS-E, IMA-E, AIS-E | Each indicator is a separate group in MeasureReport. Use `build_multi_rate_measure_report()`. |
| Two rates (7d/30d) | FUH, FUM, FUI, FUA | Follow-up measures with 7-day and 30-day rates |
| Two rates (init/cont) | IET, ADD-E | Initiation and continuation/engagement phases |
| Two rates (prenatal/postpartum) | PPC | Timeliness of prenatal care + postpartum care |
| Medication ratio | AMR | Numerator is a ratio calculation (controller/total >= 0.50) |
| Medication adherence | SAA, PBH | PDC (proportion of days covered) calculation |
| Multi-year lookback | SPC, SPD, OMW | Eligible population looks back 1-2 years before MY |
| Inverse measure | PSA, URI, AAB, LBP, HDO, UOP | Lower rate = better. Numerator is the "bad" event. |
| Risk adjusted | PCR, HFS, AHU, EDU, HPC | Observed rates only at individual level (no risk adjustment) |
| 14-day separation | CIS-E, IMA-E, TFC, W30, AIS-E | Multiple events must be ≥14 days apart |
| Survey/descriptive | HOS, FRM, MUI, PAO, CPA, CPC, CCC, ENP, LDM, RDM, DMH, DSU | Stub files — not calculable from FHIR data |

## Example

**User**: "Calculate CBP for this patient bundle"

```python
from measures.measure_cbp import calculate_cbp_measure

result = calculate_cbp_measure(patient_bundle, measurement_year=2025)
# Returns FHIR MeasureReport with:
#   initial-population: 1 (age 18-85 with 2+ HTN visits)
#   denominator-exclusion: 0 (no hospice/death/palliative/pregnancy/ESRD/frailty)
#   denominator: 1
#   numerator: 1 (most recent BP < 140/90)
#   measureScore: 1.0
```

## Edge Cases

- **Patient not in eligible population**: MeasureReport with initial-population=0, all others=0, no measureScore.
- **Patient excluded**: MeasureReport with initial-population=1, denominator-exclusion=1, denominator=0, numerator=0, no measureScore.
- **Patient in denominator but not compliant**: MeasureReport with denominator=1, numerator=0, measureScore=0.0.
- **No qualifying data found**: Patient is not compliant (numerator=0).
- **Multiple rates/indicators**: Separate group entries for each indicator.
- **Missing FHIR resources**: Gracefully handle missing resource types. Never raise on incomplete data.

## Policy

- Always include the NCQA copyright notice in module docstrings.
- Value set codes are sourced from the HEDIS MY 2025 Value Set Directory.
- Generated code is for internal quality improvement purposes only.
- Do not hardcode patient data; code must work with any FHIR Bundle.
- All shared code goes in `hedis_common.py` — never duplicate utilities in measure files.
