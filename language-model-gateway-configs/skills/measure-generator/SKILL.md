---
name: measure-generator
description: Generate Python code that calculates a HEDIS quality measure for a single patient given a FHIR R4 Bundle of their resources, outputting a FHIR MeasureReport. Use when the user asks to implement, generate, create, or build code for a HEDIS measure, a quality measure calculation, or a measure engine, even if they do not explicitly say "HEDIS" but reference a specific measure name or abbreviation (e.g., CBP, AMR, BCS-E).
allowed-tools: Read Glob Grep WebSearch
license: Internal use only
metadata:
  owner: icanbwell
  last_reviewed: 2026-03-27
  scope: HEDIS MY 2025 measure code generation from FHIR data
---

# HEDIS Measure Code Generator

## Skill Card

**Goal**: Generate production-quality Python code that calculates a specific HEDIS MY 2025 measure for an individual patient, consuming a FHIR R4 Bundle and producing a FHIR R4 MeasureReport.

**Use when**:
- User asks to implement a HEDIS measure calculation
- User provides a measure name or abbreviation and wants runnable code
- User asks to generate a measure engine for a FHIR-based quality calculation
- User references a specific HEDIS measure (e.g., "CBP", "Controlling High Blood Pressure", "AMR")
- User asks for code that evaluates patient data against a quality measure

**Do not use when**:
- User asks general questions about HEDIS specifications (answer directly)
- User wants to query a FHIR server (use fhir-query-builder skill instead)
- User asks about measure reporting or submission processes (answer directly)

**Required inputs**:
- The HEDIS measure name or abbreviation (e.g., "CBP" or "Controlling High Blood Pressure")
- Optionally: measurement year (default: 2025)
- Optionally: specific value set codes to include

**Outputs**:
- A complete, runnable Python file that:
  - Accepts a FHIR R4 Bundle (dict) as input
  - Returns a FHIR R4 MeasureReport (dict) as output
  - Includes value set constants, helper functions, and a main entry point
  - Passes validation via `scripts/validate_measure_code.py`

## Mandatory Workflow

### Step 1: Identify the Measure

Match the user's request to a HEDIS MY 2025 measure. Read `references/hedis-measures-index.md` if the measure name is ambiguous or abbreviated.

If the measure cannot be identified, ask: "Which HEDIS measure would you like to implement? Please provide the abbreviation (e.g., CBP) or full name."

### Step 2: Read the Measure Specification

Read the HEDIS specification for the requested measure from `references/HEDIS MY 2025 Volume 2 Technical Update 2025-03-31.docx`. Search for the measure name or abbreviation in the document. Extract:

1. **Description** - What the measure calculates
2. **Definitions** - Key terms and thresholds
3. **Eligible Population** - Ages, enrollment, benefits, event/diagnosis criteria
4. **Required Exclusions** - All exclusion criteria
5. **Administrative Specification** - Denominator and numerator logic
6. **Value Sets Referenced** - All value set names mentioned

### Step 3: Read the Code Pattern References

Read these references to understand the required code structure:
- `references/measure-spec-pattern.md` - How HEDIS concepts map to code and FHIR resources
- `references/fhir-measure-report-template.md` - The MeasureReport output structure and builder template
- `scripts/example_cbp_measure.py` - A complete working example for the CBP measure

### Step 4: Generate the Code

Produce a single Python file following this structure:

```
Module docstring (measure name, description, input/output)
│
├── Value Set Constants (ICD-10, CPT, LOINC, SNOMED, RxNorm codes)
├── Helper Functions (age calc, date parsing, resource extraction, code matching)
├── check_eligible_population(bundle, measurement_year) -> (bool, list[str])
├── check_exclusions(bundle, measurement_year) -> (bool, list[str])
├── check_numerator(bundle, measurement_year) -> (bool, list[str])
├── build_measure_report(...) -> dict
├── calculate_<measure>_measure(bundle, measurement_year) -> dict  [main entry]
└── if __name__ == "__main__": example usage with sample bundle
```

**Code requirements**:
- Pure Python, no external dependencies (only stdlib: `uuid`, `datetime`, `json`, `collections`)
- All functions return a tuple of `(result_bool, evaluated_resource_references)` for traceability
- Value sets use representative codes with a clear comment that production should load full sets from VSAC
- The main function name must follow the pattern `calculate_<abbreviation>_measure`
- Include type hints throughout
- Include an `if __name__ == "__main__"` block with a realistic example FHIR Bundle

### Step 5: Validate the Code

Run the validation script to verify the generated code:

```
echo '{"code": "<generated-code>", "measure_abbreviation": "<abbrev>"}' | python3 scripts/validate_measure_code.py
```

If validation fails, fix the issues and re-validate. Do not present code to the user until validation passes.

### Step 6: Present the Code

Provide the complete Python file to the user. Explain:
- What the measure calculates
- The eligible population criteria
- The key exclusions
- The numerator logic
- How to run it with a FHIR Bundle

## Gotchas

- **Value sets are representative, not exhaustive.** The generated code includes sample codes from each value set for demonstration. Production implementations must load full value sets from the HEDIS Value Set Directory or VSAC. Always add a comment noting this.
- **Age is calculated as of December 31.** HEDIS always uses end-of-year age, not age at encounter. Use `(as_of.month, as_of.day) < (birth.month, birth.day)` for the birthday check.
- **"Different dates of service" means calendar dates, not encounters.** Two encounters on the same date count as one date of service.
- **BP readings exclude acute inpatient and ED settings.** For CBP/BPD/BPC-E, filter out Observations where the encounter class is IMP or EMER.
- **Multiple BPs on same date: use lowest systolic and lowest diastolic.** These do not need to be from the same reading.
- **Lab claims with POS code 81 are excluded** from many diagnosis-based criteria. Note this in exclusion logic.
- **Frailty + Advanced Illness exclusion** has age-dependent logic: 66-80 requires both frailty AND advanced illness; 81+ requires only frailty. This applies across all product lines, not just Medicare.
- **Medication measures** require matching on NDC or RxNorm codes from the Medication List Directory. Generic name matching is insufficient.
- **ECDS measures** (those ending in -E) use electronic clinical data and may have different data source requirements than standard measures.
- **The FHIR Bundle should contain all patient resources.** The code assumes a complete Bundle (Patient, Conditions, Encounters, Observations, Procedures, MedicationDispenses, Coverage).

## Measures With Special Handling

| Pattern | Measures | Notes |
|---|---|---|
| Multiple indicators | TRC, COA, WCC | Each indicator is a separate group in MeasureReport |
| Medication ratio | AMR | Numerator is a ratio calculation, not a simple yes/no |
| Multi-year lookback | SPC, SPD, OMW | Eligible population looks back 1-2 years before MY |
| Inverse measure | PSA, URI, AAB, LBP | Lower rate = better. Numerator is the "bad" event |
| Risk adjusted | PCR, HFS, AHU, EDU, HPC | Require comorbidity/risk adjustment tables |
| 14-day separation | CIS-E, IMA-E, TFC, W30, AIS-E | Multiple events must be >=14 days apart |

## Example

**User**: "Generate code for the Controlling High Blood Pressure (CBP) measure"

**Output**: A Python file similar to `scripts/example_cbp_measure.py` that:
1. Checks if the patient is 18-85 with 2+ HTN visits in the lookback period
2. Applies exclusions (hospice, death, palliative care, pregnancy, ESRD, frailty)
3. Finds the most recent BP reading in the measurement year
4. Determines if BP < 140/90 mm Hg
5. Returns a FHIR MeasureReport with population counts and measure score

## Edge Cases

- **Patient not in eligible population**: Return MeasureReport with initial-population=0, all others=0, no measureScore.
- **Patient excluded**: Return MeasureReport with initial-population=1, denominator-exclusion=1, denominator=0, numerator=0, no measureScore.
- **Patient in denominator but not compliant**: Return MeasureReport with denominator=1, numerator=0, measureScore=0.0.
- **No BP/lab readings found**: Patient is not compliant (numerator=0).
- **Multiple rates/indicators**: Create separate group entries for each indicator.
- **Missing FHIR resources**: Gracefully handle missing resource types. Never raise on incomplete data.

## Policy

- Always include the NCQA copyright notice in the module docstring.
- Note that value sets are representative samples and must be replaced with full VSAC sets for production.
- Generated code is for internal quality improvement purposes only.
- Do not hardcode patient data; the code must work with any FHIR Bundle.
