"""
HEDIS MY 2025 - Shared utilities for measure calculation.

Provides FHIR Bundle helpers, common exclusion checks, value set loading,
date utilities, and MeasureReport builder used by all individual measure modules.
"""

import csv
import glob as _glob
import os
import uuid
from collections import defaultdict
from datetime import date, datetime
from typing import Any

# ---------------------------------------------------------------------------
# FHIR Code System URIs
# ---------------------------------------------------------------------------

ICD10CM = "http://hl7.org/fhir/sid/icd-10-cm"
CPT = "http://www.ama-assn.org/go/cpt"
HCPCS = "https://www.cms.gov/Medicare/Coding/HCPCSReleaseCodeSets"
SNOMED = "http://snomed.info/sct"
LOINC = "http://loinc.org"
RXNORM = "http://www.nlm.nih.gov/research/umls/rxnorm"
NDC = "http://hl7.org/fhir/sid/ndc"
CVX = "http://hl7.org/fhir/sid/cvx"
POS = "https://www.cms.gov/Medicare/Coding/place-of-service-codes"
UBREV = "https://www.nubc.org/revenue"

SYSTEM_LOOKUP: dict[str, str] = {
    "ICD10CM": ICD10CM,
    "ICD-10-CM": ICD10CM,
    "CPT": CPT,
    "CPT-4": CPT,
    "HCPCS": HCPCS,
    "SNOMED CT US Edition": SNOMED,
    "SNOMEDCT": SNOMED,
    "SNOMED": SNOMED,
    "LOINC": LOINC,
    "RxNorm": RXNORM,
    "RXNORM": RXNORM,
    "NDC": NDC,
    "CVX": CVX,
    "POS": POS,
    "UBREV": UBREV,
}


# ---------------------------------------------------------------------------
# Value Set Loading
# ---------------------------------------------------------------------------


def load_value_sets_from_csv(
    measure_abbreviation: str,
    base_dir: str | None = None,
) -> dict[str, dict[str, set[str]]]:
    """
    Load value sets for a measure from its CSV file(s).

    Returns a nested dict: {value_set_name: {fhir_system_uri: {code1, code2, ...}}}

    Handles both single files (e.g., cbp.csv) and split files (e.g., cbp-part1.csv).
    """
    if base_dir is None:
        base_dir = os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            "references",
            "value-sets",
            "by-measure",
        )

    abbr_lower = measure_abbreviation.lower()
    pattern_single = os.path.join(base_dir, f"{abbr_lower}.csv")
    pattern_parts = os.path.join(base_dir, f"{abbr_lower}-part*.csv")

    files = _glob.glob(pattern_single) + sorted(_glob.glob(pattern_parts))
    if not files:
        return {}

    result: dict[str, dict[str, set[str]]] = defaultdict(lambda: defaultdict(set))

    for filepath in files:
        with open(filepath, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                vs_name = row.get("Value Set Name", "").strip()
                code = row.get("Code", "").strip()
                code_system = row.get("Code System", "").strip()
                if not vs_name or not code:
                    continue
                fhir_uri = SYSTEM_LOOKUP.get(code_system, code_system)
                result[vs_name][fhir_uri].add(code)

    return dict(result)


def codes_for_system(
    value_sets: dict[str, dict[str, set[str]]],
    value_set_name: str,
    system: str,
) -> set[str]:
    """Get all codes for a specific value set and code system."""
    return value_sets.get(value_set_name, {}).get(system, set())


def all_codes(
    value_sets: dict[str, dict[str, set[str]]],
    value_set_name: str,
) -> dict[str, set[str]]:
    """Get all code systems and codes for a value set."""
    return value_sets.get(value_set_name, {})


def codes_for_any_system(
    value_sets: dict[str, dict[str, set[str]]],
    value_set_name: str,
) -> set[str]:
    """Get all codes across all systems for a value set (flat set)."""
    result: set[str] = set()
    for codes in value_sets.get(value_set_name, {}).values():
        result.update(codes)
    return result


# ---------------------------------------------------------------------------
# Date Utilities
# ---------------------------------------------------------------------------


def parse_date(date_str: str | None) -> date | None:
    """Parse a FHIR date or dateTime string to a Python date."""
    if not date_str:
        return None
    try:
        return date.fromisoformat(date_str[:10])
    except (ValueError, TypeError):
        return None


def calculate_age(birth_date: date, as_of: date) -> int:
    """Calculate age as of a given date (HEDIS uses Dec 31 of measurement year)."""
    age = as_of.year - birth_date.year
    if (as_of.month, as_of.day) < (birth_date.month, birth_date.day):
        age -= 1
    return age


def is_date_in_range(d: date | None, start: date, end: date) -> bool:
    """Check if a date falls within a range (inclusive)."""
    if d is None:
        return False
    return start <= d <= end


def measurement_year_dates(measurement_year: int) -> tuple[date, date]:
    """Return (start, end) dates for the measurement year."""
    return date(measurement_year, 1, 1), date(measurement_year, 12, 31)


def prior_year_dates(measurement_year: int) -> tuple[date, date]:
    """Return (start, end) dates for the year prior to the measurement year."""
    return date(measurement_year - 1, 1, 1), date(measurement_year - 1, 12, 31)


# ---------------------------------------------------------------------------
# FHIR Bundle Helpers
# ---------------------------------------------------------------------------


def get_patient(bundle: dict) -> dict | None:
    """Extract the Patient resource from the bundle."""
    for entry in bundle.get("entry", []):
        resource = entry.get("resource", {})
        if resource.get("resourceType") == "Patient":
            return resource
    return None


def get_patient_id(bundle: dict) -> str:
    """Get the patient ID from the bundle, or 'unknown'."""
    patient = get_patient(bundle)
    return patient.get("id", "unknown") if patient else "unknown"


def get_resources_by_type(bundle: dict, resource_type: str) -> list[dict]:
    """Extract all resources of a given type from the bundle."""
    return [
        entry["resource"]
        for entry in bundle.get("entry", [])
        if entry.get("resource", {}).get("resourceType") == resource_type
    ]


def get_patient_birth_date(bundle: dict) -> date | None:
    """Get the patient's birth date."""
    patient = get_patient(bundle)
    if not patient:
        return None
    return parse_date(patient.get("birthDate"))


def get_patient_gender(bundle: dict) -> str | None:
    """Get the patient's gender."""
    patient = get_patient(bundle)
    if not patient:
        return None
    return patient.get("gender")


# ---------------------------------------------------------------------------
# Code Matching Helpers
# ---------------------------------------------------------------------------


def has_code_in_set(
    codeable_concepts: list[dict],
    code_set: set[str],
    system: str | None = None,
) -> bool:
    """Check if any coding in the codeable concepts matches the code set."""
    for cc in codeable_concepts:
        for coding in cc.get("coding", []):
            if system and coding.get("system") != system:
                continue
            if coding.get("code") in code_set:
                return True
    return False


def resource_has_code(
    resource: dict,
    code_set: set[str],
    system: str | None = None,
) -> bool:
    """Check if a resource's code field matches any code in the set."""
    code = resource.get("code", {})
    return has_code_in_set([code], code_set, system)


def resource_has_any_code(
    resource: dict,
    value_set_codes: dict[str, set[str]],
) -> bool:
    """Check if a resource's code matches any system/codes in a value set mapping."""
    code = resource.get("code", {})
    for coding in code.get("coding", []):
        sys = coding.get("system")
        c = coding.get("code")
        if sys and c and c in value_set_codes.get(sys, set()):
            return True
    return False


def codeable_concept_has_any_code(
    cc: dict,
    value_set_codes: dict[str, set[str]],
) -> bool:
    """Check if a CodeableConcept matches any system/codes in a value set mapping."""
    for coding in cc.get("coding", []):
        sys = coding.get("system")
        c = coding.get("code")
        if sys and c and c in value_set_codes.get(sys, set()):
            return True
    return False


def get_codes_from_resource(resource: dict) -> list[tuple[str, str]]:
    """Extract all (system, code) tuples from a resource's code field."""
    result = []
    for coding in resource.get("code", {}).get("coding", []):
        sys = coding.get("system", "")
        code = coding.get("code", "")
        if sys and code:
            result.append((sys, code))
    return result


def has_code_prefix(
    resource: dict,
    prefixes: tuple[str, ...],
    system: str,
) -> bool:
    """Check if a resource's code starts with any of the given prefixes."""
    for coding in resource.get("code", {}).get("coding", []):
        if coding.get("system") == system:
            c = coding.get("code", "")
            if c.startswith(prefixes):
                return True
    return False


# ---------------------------------------------------------------------------
# Resource Date Extraction
# ---------------------------------------------------------------------------


def get_encounter_date(encounter: dict) -> date | None:
    """Get the start date of an encounter."""
    period = encounter.get("period", {})
    return parse_date(period.get("start"))


def get_encounter_end_date(encounter: dict) -> date | None:
    """Get the end date of an encounter."""
    period = encounter.get("period", {})
    return parse_date(period.get("end"))


def get_encounter_class(encounter: dict) -> str:
    """Get the encounter class code (IMP, EMER, AMB, etc.)."""
    return encounter.get("class", {}).get("code", "")


def get_condition_onset(condition: dict) -> date | None:
    """Get the onset date of a condition."""
    return parse_date(
        condition.get("onsetDateTime")
        or (condition.get("onsetPeriod") or {}).get("start")
    )


def get_procedure_date(procedure: dict) -> date | None:
    """Get the performed date of a procedure."""
    return parse_date(
        procedure.get("performedDateTime")
        or (procedure.get("performedPeriod") or {}).get("start")
    )


def get_observation_date(observation: dict) -> date | None:
    """Get the effective date of an observation."""
    return parse_date(
        observation.get("effectiveDateTime")
        or (observation.get("effectivePeriod") or {}).get("start")
    )


def get_medication_date(med: dict) -> date | None:
    """Get the date from a MedicationDispense or MedicationRequest."""
    return parse_date(
        med.get("whenHandedOver")
        or med.get("authoredOn")
        or (med.get("dosageInstruction") or [{}])[0]
        .get("timing", {})
        .get("event", [None])[0]
    )


def get_medication_codes(med: dict) -> list[tuple[str, str]]:
    """Extract (system, code) tuples from a medication resource."""
    result = []
    mcc = med.get("medicationCodeableConcept", {})
    for coding in mcc.get("coding", []):
        sys = coding.get("system", "")
        code = coding.get("code", "")
        if sys and code:
            result.append((sys, code))
    return result


def medication_has_code(
    med: dict,
    value_set_codes: dict[str, set[str]],
) -> bool:
    """Check if a medication resource matches any code in a value set mapping."""
    for sys, code in get_medication_codes(med):
        if code in value_set_codes.get(sys, set()):
            return True
    return False


# ---------------------------------------------------------------------------
# Encounter Filtering
# ---------------------------------------------------------------------------


def find_encounters_with_codes(
    bundle: dict,
    encounter_codes: dict[str, set[str]],
    start: date,
    end: date,
    class_filter: str | None = None,
) -> list[tuple[dict, date]]:
    """Find encounters matching code sets within a date range.

    Returns list of (encounter, encounter_date) tuples.
    """
    results = []
    for enc in get_resources_by_type(bundle, "Encounter"):
        enc_date = get_encounter_date(enc)
        if not is_date_in_range(enc_date, start, end):
            continue
        if class_filter and get_encounter_class(enc) != class_filter:
            continue
        if resource_has_any_code(enc, encounter_codes):
            results.append((enc, enc_date))
        else:
            for t in enc.get("type", []):
                if codeable_concept_has_any_code(t, encounter_codes):
                    results.append((enc, enc_date))
                    break
    return results


def find_conditions_with_codes(
    bundle: dict,
    condition_codes: dict[str, set[str]],
    start: date | None = None,
    end: date | None = None,
) -> list[tuple[dict, date | None]]:
    """Find conditions matching code sets, optionally within a date range."""
    results = []
    for cond in get_resources_by_type(bundle, "Condition"):
        onset = get_condition_onset(cond)
        if start and end and not is_date_in_range(onset, start, end):
            continue
        if resource_has_any_code(cond, condition_codes):
            results.append((cond, onset))
    return results


def find_procedures_with_codes(
    bundle: dict,
    procedure_codes: dict[str, set[str]],
    start: date,
    end: date,
) -> list[tuple[dict, date | None]]:
    """Find procedures matching code sets within a date range."""
    results = []
    for proc in get_resources_by_type(bundle, "Procedure"):
        proc_date = get_procedure_date(proc)
        if not is_date_in_range(proc_date, start, end):
            continue
        if resource_has_any_code(proc, procedure_codes):
            results.append((proc, proc_date))
    return results


def find_observations_with_codes(
    bundle: dict,
    observation_codes: dict[str, set[str]],
    start: date,
    end: date,
) -> list[tuple[dict, date | None]]:
    """Find observations matching code sets within a date range."""
    results = []
    for obs in get_resources_by_type(bundle, "Observation"):
        obs_date = get_observation_date(obs)
        if not is_date_in_range(obs_date, start, end):
            continue
        if resource_has_any_code(obs, observation_codes):
            results.append((obs, obs_date))
    return results


def find_medications_with_codes(
    bundle: dict,
    medication_codes: dict[str, set[str]],
    start: date,
    end: date,
) -> list[tuple[dict, date | None]]:
    """Find MedicationDispense/MedicationRequest matching codes in a date range."""
    results = []
    for rtype in ("MedicationDispense", "MedicationRequest"):
        for med in get_resources_by_type(bundle, rtype):
            med_date = get_medication_date(med)
            if not is_date_in_range(med_date, start, end):
                continue
            if medication_has_code(med, medication_codes):
                results.append((med, med_date))
    return results


# ---------------------------------------------------------------------------
# Common Exclusion Checks
# ---------------------------------------------------------------------------

# Common exclusion value set names used across many measures
HOSPICE_VS_NAMES = ("Hospice Encounter", "Hospice Intervention")
PALLIATIVE_CARE_VS_NAMES = (
    "Palliative Care Assessment",
    "Palliative Care Encounter",
    "Palliative Care Intervention",
)
FRAILTY_VS_NAMES = (
    "Frailty Device",
    "Frailty Diagnosis",
    "Frailty Encounter",
    "Frailty Symptom",
)
ADVANCED_ILLNESS_VS_NAMES = (
    "Advanced Illness",
    "Acute Inpatient",
    "Nonacute Inpatient",
)
DEMENTIA_VS_NAMES = ("Dementia Medications",)


def check_hospice(
    bundle: dict,
    value_sets: dict[str, dict[str, set[str]]],
    measurement_year: int,
) -> tuple[bool, list[str]]:
    """Check if patient has hospice encounter/intervention during measurement year."""
    evaluated: list[str] = []
    my_start, my_end = measurement_year_dates(measurement_year)

    for vs_name in HOSPICE_VS_NAMES:
        vs_codes = all_codes(value_sets, vs_name)
        if not vs_codes:
            continue
        for enc, _ in find_encounters_with_codes(bundle, vs_codes, my_start, my_end):
            evaluated.append(f"Encounter/{enc.get('id')}")
            return True, evaluated
        for proc, _ in find_procedures_with_codes(bundle, vs_codes, my_start, my_end):
            evaluated.append(f"Procedure/{proc.get('id')}")
            return True, evaluated

    return False, evaluated


def check_death(bundle: dict, measurement_year: int) -> tuple[bool, list[str]]:
    """Check if patient died during measurement year."""
    patient = get_patient(bundle)
    if not patient:
        return False, []

    my_start, my_end = measurement_year_dates(measurement_year)
    deceased = patient.get("deceasedDateTime") or patient.get("deceasedBoolean")
    if deceased:
        if isinstance(deceased, bool) and deceased:
            return True, []
        if isinstance(deceased, str):
            death_date = parse_date(deceased)
            if death_date and is_date_in_range(death_date, my_start, my_end):
                return True, []
    return False, []


def check_palliative_care(
    bundle: dict,
    value_sets: dict[str, dict[str, set[str]]],
    measurement_year: int,
) -> tuple[bool, list[str]]:
    """Check if patient has palliative care during measurement year."""
    evaluated: list[str] = []
    my_start, my_end = measurement_year_dates(measurement_year)

    for vs_name in PALLIATIVE_CARE_VS_NAMES:
        vs_codes = all_codes(value_sets, vs_name)
        if not vs_codes:
            continue
        for enc, _ in find_encounters_with_codes(bundle, vs_codes, my_start, my_end):
            evaluated.append(f"Encounter/{enc.get('id')}")
            return True, evaluated
        for cond, _ in find_conditions_with_codes(bundle, vs_codes, my_start, my_end):
            evaluated.append(f"Condition/{cond.get('id')}")
            return True, evaluated
        for proc, _ in find_procedures_with_codes(bundle, vs_codes, my_start, my_end):
            evaluated.append(f"Procedure/{proc.get('id')}")
            return True, evaluated

    return False, evaluated


def check_frailty_advanced_illness(
    bundle: dict,
    value_sets: dict[str, dict[str, set[str]]],
    measurement_year: int,
) -> tuple[bool, list[str]]:
    """
    Check the frailty + advanced illness exclusion (ages 66+).

    - Age 66-80: requires BOTH frailty AND (advanced illness OR dementia meds).
    - Age 81+: requires only frailty.
    """
    evaluated: list[str] = []
    birth_date = get_patient_birth_date(bundle)
    if not birth_date:
        return False, evaluated

    _, my_end = measurement_year_dates(measurement_year)
    age = calculate_age(birth_date, my_end)
    if age < 66:
        return False, evaluated

    my_start, _ = measurement_year_dates(measurement_year)
    py_start, py_end = prior_year_dates(measurement_year)

    # Check frailty
    has_frailty = False
    for vs_name in FRAILTY_VS_NAMES:
        vs_codes = all_codes(value_sets, vs_name)
        if not vs_codes:
            continue
        if find_encounters_with_codes(bundle, vs_codes, my_start, my_end):
            has_frailty = True
            break
        if find_conditions_with_codes(bundle, vs_codes, my_start, my_end):
            has_frailty = True
            break
        if find_procedures_with_codes(bundle, vs_codes, my_start, my_end):
            has_frailty = True
            break

    if not has_frailty:
        return False, evaluated

    # Age 81+: frailty alone is sufficient
    if age >= 81:
        return True, evaluated

    # Age 66-80: also need advanced illness or dementia meds
    lookback_start = date(measurement_year - 1, 1, 1)
    for vs_name in ADVANCED_ILLNESS_VS_NAMES:
        vs_codes = all_codes(value_sets, vs_name)
        if not vs_codes:
            continue
        if find_conditions_with_codes(bundle, vs_codes, lookback_start, my_end):
            return True, evaluated
        if find_encounters_with_codes(bundle, vs_codes, lookback_start, my_end):
            return True, evaluated

    for vs_name in DEMENTIA_VS_NAMES:
        vs_codes = all_codes(value_sets, vs_name)
        if not vs_codes:
            continue
        if find_medications_with_codes(bundle, vs_codes, lookback_start, my_end):
            return True, evaluated

    return False, evaluated


def check_common_exclusions(
    bundle: dict,
    value_sets: dict[str, dict[str, set[str]]],
    measurement_year: int,
    check_frailty: bool = True,
) -> tuple[bool, list[str]]:
    """
    Run common exclusion checks used by most measures:
    hospice, death, palliative care, and optionally frailty/advanced illness.
    """
    all_evaluated: list[str] = []

    excluded, refs = check_hospice(bundle, value_sets, measurement_year)
    all_evaluated.extend(refs)
    if excluded:
        return True, all_evaluated

    excluded, refs = check_death(bundle, measurement_year)
    all_evaluated.extend(refs)
    if excluded:
        return True, all_evaluated

    excluded, refs = check_palliative_care(bundle, value_sets, measurement_year)
    all_evaluated.extend(refs)
    if excluded:
        return True, all_evaluated

    if check_frailty:
        excluded, refs = check_frailty_advanced_illness(
            bundle, value_sets, measurement_year
        )
        all_evaluated.extend(refs)
        if excluded:
            return True, all_evaluated

    return False, all_evaluated


# ---------------------------------------------------------------------------
# Blood Pressure Helpers (shared by CBP, BPD, BPC-E)
# ---------------------------------------------------------------------------

LOINC_SYSTOLIC = "8480-6"
LOINC_DIASTOLIC = "8462-4"
LOINC_BP_PANEL = "85354-9"


def get_bp_readings(
    bundle: dict,
    start: date,
    end: date,
    exclude_inpatient_ed: bool = True,
) -> list[dict[str, Any]]:
    """
    Extract BP readings from the bundle within a date range.

    Returns list of dicts: {date, systolic, diastolic, obs_id}.
    Excludes acute inpatient/ED settings if specified.
    """
    observations = get_resources_by_type(bundle, "Observation")

    excluded_dates: set[date] = set()
    if exclude_inpatient_ed:
        for enc in get_resources_by_type(bundle, "Encounter"):
            enc_class = get_encounter_class(enc)
            if enc_class in ("IMP", "EMER"):
                enc_date = get_encounter_date(enc)
                if enc_date:
                    excluded_dates.add(enc_date)

    bp_readings: list[dict[str, Any]] = []
    for obs in observations:
        obs_date = get_observation_date(obs)
        if not is_date_in_range(obs_date, start, end):
            continue
        if obs_date in excluded_dates:
            continue

        codings = obs.get("code", {}).get("coding", [])
        loinc_codes = [c.get("code") for c in codings if c.get("system") == LOINC]

        systolic = None
        diastolic = None

        if LOINC_BP_PANEL in loinc_codes:
            for component in obs.get("component", []):
                comp_codes = [
                    c.get("code")
                    for c in component.get("code", {}).get("coding", [])
                    if c.get("system") == LOINC
                ]
                value = component.get("valueQuantity", {}).get("value")
                if LOINC_SYSTOLIC in comp_codes:
                    systolic = value
                elif LOINC_DIASTOLIC in comp_codes:
                    diastolic = value
        elif LOINC_SYSTOLIC in loinc_codes:
            systolic = obs.get("valueQuantity", {}).get("value")
        elif LOINC_DIASTOLIC in loinc_codes:
            diastolic = obs.get("valueQuantity", {}).get("value")

        if systolic is not None or diastolic is not None:
            bp_readings.append(
                {
                    "date": obs_date,
                    "systolic": systolic,
                    "diastolic": diastolic,
                    "obs_id": obs.get("id"),
                }
            )

    return bp_readings


def get_most_recent_bp(
    bp_readings: list[dict[str, Any]],
) -> tuple[float | None, float | None, list[str]]:
    """
    From a list of BP readings, get the lowest systolic and lowest diastolic
    from the most recent date.

    Returns (systolic, diastolic, evaluated_refs).
    """
    if not bp_readings:
        return None, None, []

    by_date: dict[date, list[dict]] = defaultdict(list)
    for bp in bp_readings:
        by_date[bp["date"]].append(bp)

    most_recent_date = max(by_date.keys())
    readings_on_date = by_date[most_recent_date]

    systolics = [r["systolic"] for r in readings_on_date if r["systolic"] is not None]
    diastolics = [
        r["diastolic"] for r in readings_on_date if r["diastolic"] is not None
    ]

    evaluated = [f"Observation/{r['obs_id']}" for r in readings_on_date if r["obs_id"]]

    systolic = min(systolics) if systolics else None
    diastolic = min(diastolics) if diastolics else None

    return systolic, diastolic, evaluated


# ---------------------------------------------------------------------------
# MeasureReport Builder
# ---------------------------------------------------------------------------


def build_measure_report(
    patient_id: str,
    measure_abbreviation: str,
    measure_name: str,
    measurement_year: int,
    initial_population: bool,
    denominator_exclusion: bool,
    numerator: bool,
    evaluated_resources: list[str],
) -> dict[str, Any]:
    """Build a FHIR R4 MeasureReport for an individual patient (single rate)."""
    denominator_count = 1 if (initial_population and not denominator_exclusion) else 0
    numerator_count = 1 if (denominator_count == 1 and numerator) else 0

    report: dict[str, Any] = {
        "resourceType": "MeasureReport",
        "id": str(uuid.uuid4()),
        "meta": {
            "profile": [
                "http://hl7.org/fhir/us/davinci-deqm/StructureDefinition/indv-measurereport-deqm"
            ]
        },
        "status": "complete",
        "type": "individual",
        "measure": f"http://ncqa.org/fhir/Measure/{measure_abbreviation}",
        "subject": {"reference": f"Patient/{patient_id}"},
        "date": datetime.now().isoformat(),
        "period": {
            "start": f"{measurement_year}-01-01",
            "end": f"{measurement_year}-12-31",
        },
        "group": [
            _build_group(
                measure_abbreviation,
                measure_name,
                initial_population,
                denominator_count,
                denominator_exclusion,
                numerator_count,
            )
        ],
        "evaluatedResource": [{"reference": ref} for ref in evaluated_resources],
    }

    return report


def build_multi_rate_measure_report(
    patient_id: str,
    measure_abbreviation: str,
    measure_name: str,
    measurement_year: int,
    groups: list[dict[str, Any]],
    evaluated_resources: list[str],
) -> dict[str, Any]:
    """
    Build a FHIR R4 MeasureReport with multiple rate groups.

    Each group dict should have keys:
        code, display, initial_population, denominator_exclusion, numerator
    """
    report: dict[str, Any] = {
        "resourceType": "MeasureReport",
        "id": str(uuid.uuid4()),
        "meta": {
            "profile": [
                "http://hl7.org/fhir/us/davinci-deqm/StructureDefinition/indv-measurereport-deqm"
            ]
        },
        "status": "complete",
        "type": "individual",
        "measure": f"http://ncqa.org/fhir/Measure/{measure_abbreviation}",
        "subject": {"reference": f"Patient/{patient_id}"},
        "date": datetime.now().isoformat(),
        "period": {
            "start": f"{measurement_year}-01-01",
            "end": f"{measurement_year}-12-31",
        },
        "group": [],
        "evaluatedResource": [{"reference": ref} for ref in evaluated_resources],
    }

    for g in groups:
        ip = g.get("initial_population", False)
        excl = g.get("denominator_exclusion", False)
        denom_count = 1 if (ip and not excl) else 0
        num_count = 1 if (denom_count == 1 and g.get("numerator", False)) else 0
        report["group"].append(
            _build_group(
                g.get("code", measure_abbreviation),
                g.get("display", measure_name),
                ip,
                denom_count,
                excl,
                num_count,
            )
        )

    return report


def _build_group(
    code: str,
    display: str,
    initial_population: bool,
    denominator_count: int,
    denominator_exclusion: bool,
    numerator_count: int,
) -> dict[str, Any]:
    """Build a single group entry for a MeasureReport."""
    group: dict[str, Any] = {
        "code": {
            "coding": [
                {
                    "system": "http://ncqa.org/fhir/CodeSystem/measure-group",
                    "code": code,
                    "display": display,
                }
            ]
        },
        "population": [
            _population_entry(
                "initial-population",
                "Initial Population",
                1 if initial_population else 0,
            ),
            _population_entry("denominator", "Denominator", denominator_count),
            _population_entry(
                "denominator-exclusion",
                "Denominator Exclusion",
                1 if denominator_exclusion else 0,
            ),
            _population_entry("numerator", "Numerator", numerator_count),
        ],
    }

    if denominator_count > 0:
        group["measureScore"] = {
            "value": float(numerator_count) / float(denominator_count)
        }

    return group


def _population_entry(code: str, display: str, count: int) -> dict[str, Any]:
    return {
        "code": {
            "coding": [
                {
                    "system": "http://terminology.hl7.org/CodeSystem/measure-population",
                    "code": code,
                    "display": display,
                }
            ]
        },
        "count": count,
    }


# ---------------------------------------------------------------------------
# Standard Measure Calculation Runner
# ---------------------------------------------------------------------------


def run_measure(
    bundle: dict,
    measure_abbreviation: str,
    measure_name: str,
    measurement_year: int,
    check_eligible_population_fn: Any,
    check_exclusions_fn: Any,
    check_numerator_fn: Any,
) -> dict[str, Any]:
    """
    Standard runner for single-rate measures.

    Takes the three measure-specific functions and runs them in order,
    building the MeasureReport from their results.
    """
    all_evaluated: list[str] = []

    is_eligible, eligible_refs = check_eligible_population_fn(bundle, measurement_year)
    all_evaluated.extend(eligible_refs)

    if not is_eligible:
        return build_measure_report(
            patient_id=get_patient_id(bundle),
            measure_abbreviation=measure_abbreviation,
            measure_name=measure_name,
            measurement_year=measurement_year,
            initial_population=False,
            denominator_exclusion=False,
            numerator=False,
            evaluated_resources=all_evaluated,
        )

    is_excluded, exclusion_refs = check_exclusions_fn(bundle, measurement_year)
    all_evaluated.extend(exclusion_refs)

    is_compliant, numerator_refs = check_numerator_fn(bundle, measurement_year)
    all_evaluated.extend(numerator_refs)

    return build_measure_report(
        patient_id=get_patient_id(bundle),
        measure_abbreviation=measure_abbreviation,
        measure_name=measure_name,
        measurement_year=measurement_year,
        initial_population=True,
        denominator_exclusion=is_excluded,
        numerator=is_compliant,
        evaluated_resources=list(dict.fromkeys(all_evaluated)),
    )
