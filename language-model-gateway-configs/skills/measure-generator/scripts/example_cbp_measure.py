"""
HEDIS MY 2025 - Controlling High Blood Pressure (CBP)

The percentage of members 18-85 years of age who had a diagnosis of hypertension
(HTN) and whose blood pressure (BP) was adequately controlled (<140/90 mm Hg)
during the measurement year.

Input: FHIR R4 Bundle containing all resources for a single patient.
Output: FHIR R4 MeasureReport with individual measure results.
"""

import uuid
from datetime import date, datetime
from typing import Any

# ---------------------------------------------------------------------------
# Value Sets (representative codes - not exhaustive)
# In production, load full value sets from VSAC or the HEDIS Value Set Directory.
# ---------------------------------------------------------------------------

ESSENTIAL_HYPERTENSION_ICD10 = {
    "I10",  # Essential (primary) hypertension
    "I11.0",  # Hypertensive heart disease with heart failure
    "I11.9",  # Hypertensive heart disease without heart failure
    "I12.0",  # Hypertensive chronic kidney disease with stage 5 CKD or ESRD
    "I12.9",  # Hypertensive chronic kidney disease with stage 1-4 or unspecified
    "I13.0",  # Hypertensive heart and CKD with heart failure and stage 1-4
    "I13.10",  # Hypertensive heart and CKD without heart failure
    "I13.2",  # Hypertensive heart and CKD with heart failure and stage 5 or ESRD
}

OUTPATIENT_ENCOUNTER_CODES_CPT = {
    "99201",
    "99202",
    "99203",
    "99204",
    "99205",  # Office/outpatient visit new
    "99211",
    "99212",
    "99213",
    "99214",
    "99215",  # Office/outpatient visit established
    "99241",
    "99242",
    "99243",
    "99244",
    "99245",  # Consultation
}

TELEHEALTH_ENCOUNTER_CODES_CPT = {
    "99441",
    "99442",
    "99443",  # Telephone E/M
    "98966",
    "98967",
    "98968",  # Telephone services
    "98969",
    "98970",
    "98971",
    "98972",  # Online digital E/M
    "99421",
    "99422",
    "99423",  # Online digital E/M (physician)
}

HOSPICE_ENCOUNTER_SNOMED = {"385763009"}  # Hospice care
PALLIATIVE_CARE_ICD10 = {"Z51.5"}
PREGNANCY_ICD10_PREFIXES = ("O", "Z33", "Z34", "Z3A")

ESRD_DIAGNOSIS_ICD10 = {"N18.5", "N18.6"}
DIALYSIS_CPT = {
    "90935",
    "90937",
    "90945",
    "90947",
    "90957",
    "90958",
    "90959",
    "90960",
    "90961",
    "90962",
    "90963",
    "90964",
    "90965",
    "90966",
}

LOINC_SYSTOLIC = "8480-6"
LOINC_DIASTOLIC = "8462-4"
LOINC_BP_PANEL = "85354-9"

ACUTE_INPATIENT_CLASS = "IMP"
ED_CLASS = "EMER"


# ---------------------------------------------------------------------------
# Helper Functions
# ---------------------------------------------------------------------------


def calculate_age(birth_date: date, as_of: date) -> int:
    """Calculate age as of a given date."""
    age = as_of.year - birth_date.year
    if (as_of.month, as_of.day) < (birth_date.month, birth_date.day):
        age -= 1
    return age


def parse_date(date_str: str | None) -> date | None:
    """Parse a FHIR date string to a Python date."""
    if not date_str:
        return None
    return date.fromisoformat(date_str[:10])


def get_patient(bundle: dict) -> dict | None:
    """Extract the Patient resource from the bundle."""
    for entry in bundle.get("entry", []):
        resource = entry.get("resource", {})
        if resource.get("resourceType") == "Patient":
            return resource
    return None


def get_resources_by_type(bundle: dict, resource_type: str) -> list[dict]:
    """Extract all resources of a given type from the bundle."""
    results = []
    for entry in bundle.get("entry", []):
        resource = entry.get("resource", {})
        if resource.get("resourceType") == resource_type:
            results.append(resource)
    return results


def has_code_in_set(
    codeable_concepts: list[dict], code_set: set[str], system: str | None = None
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
    resource: dict, code_set: set[str], system: str | None = None
) -> bool:
    """Check if a resource's code field matches any code in the set."""
    code = resource.get("code", {})
    return has_code_in_set([code], code_set, system)


def get_encounter_date(encounter: dict) -> date | None:
    """Get the start date of an encounter."""
    period = encounter.get("period", {})
    return parse_date(period.get("start"))


def is_date_in_range(d: date | None, start: date, end: date) -> bool:
    """Check if a date falls within a range (inclusive)."""
    if d is None:
        return False
    return start <= d <= end


# ---------------------------------------------------------------------------
# Eligible Population
# ---------------------------------------------------------------------------


def check_eligible_population(
    bundle: dict, measurement_year: int
) -> tuple[bool, list[str]]:
    """
    Check if the patient meets the CBP eligible population criteria.

    Returns (is_eligible, list_of_evaluated_resource_references).
    """
    evaluated = []
    patient = get_patient(bundle)
    if not patient:
        return False, evaluated

    patient_id = patient.get("id", "unknown")
    evaluated.append(f"Patient/{patient_id}")

    # Age: 18-85 as of Dec 31 of measurement year
    birth_date = parse_date(patient.get("birthDate"))
    if not birth_date:
        return False, evaluated

    as_of = date(measurement_year, 12, 31)
    age = calculate_age(birth_date, as_of)
    if not (18 <= age <= 85):
        return False, evaluated

    # Event/Diagnosis: At least 2 outpatient/telehealth visits on different dates
    # with hypertension diagnosis between Jan 1 of prior year and Jun 30 of MY
    conditions = get_resources_by_type(bundle, "Condition")
    encounters = get_resources_by_type(bundle, "Encounter")

    htn_condition_ids = []
    for cond in conditions:
        if resource_has_code(
            cond, ESSENTIAL_HYPERTENSION_ICD10, "http://hl7.org/fhir/sid/icd-10-cm"
        ):
            htn_condition_ids.append(cond.get("id"))
            evaluated.append(f"Condition/{cond.get('id')}")

    if not htn_condition_ids:
        return False, evaluated

    # Find qualifying outpatient/telehealth encounters with HTN diagnosis
    qualifying_visit_dates: list[date] = []
    lookback_start = date(measurement_year - 1, 1, 1)
    lookback_end = date(measurement_year, 6, 30)

    for enc in encounters:
        enc_date = get_encounter_date(enc)
        if not is_date_in_range(enc_date, lookback_start, lookback_end):
            continue

        # Check if outpatient or telehealth
        enc_codes = enc.get("type", [])
        is_qualifying_type = False
        for t in enc_codes:
            for coding in t.get("coding", []):
                code = coding.get("code", "")
                if (
                    code in OUTPATIENT_ENCOUNTER_CODES_CPT
                    or code in TELEHEALTH_ENCOUNTER_CODES_CPT
                ):
                    is_qualifying_type = True
                    break

        if not is_qualifying_type:
            # Also check class for outpatient
            enc_class = enc.get("class", {}).get("code", "")
            if enc_class in ("AMB", "VR"):
                is_qualifying_type = True

        if not is_qualifying_type:
            continue

        # Check if encounter has HTN diagnosis
        reason_codes = enc.get("reasonCode", [])
        diagnosis_codes = [
            d.get("condition", {}).get("reference", "")
            for d in enc.get("diagnosis", [])
        ]

        has_htn = has_code_in_set(
            reason_codes,
            ESSENTIAL_HYPERTENSION_ICD10,
            "http://hl7.org/fhir/sid/icd-10-cm",
        )

        if not has_htn:
            for diag_ref in diagnosis_codes:
                for cond_id in htn_condition_ids:
                    if cond_id and cond_id in diag_ref:
                        has_htn = True
                        break

        if has_htn and enc_date and enc_date not in qualifying_visit_dates:
            qualifying_visit_dates.append(enc_date)
            evaluated.append(f"Encounter/{enc.get('id')}")

    if len(qualifying_visit_dates) < 2:
        return False, evaluated

    return True, evaluated


# ---------------------------------------------------------------------------
# Required Exclusions
# ---------------------------------------------------------------------------


def check_exclusions(bundle: dict, measurement_year: int) -> tuple[bool, list[str]]:
    """
    Check if the patient meets any required exclusion criteria.

    Returns (is_excluded, list_of_evaluated_resource_references).
    """
    evaluated = []
    patient = get_patient(bundle)
    if not patient:
        return False, evaluated

    my_start = date(measurement_year, 1, 1)
    my_end = date(measurement_year, 12, 31)

    # Exclusion: Death during measurement year
    deceased = patient.get("deceasedDateTime") or patient.get("deceasedBoolean")
    if deceased:
        if isinstance(deceased, bool) and deceased:
            return True, evaluated
        if isinstance(deceased, str):
            death_date = parse_date(deceased)
            if death_date and is_date_in_range(death_date, my_start, my_end):
                return True, evaluated

    # Exclusion: Hospice
    encounters = get_resources_by_type(bundle, "Encounter")
    for enc in encounters:
        enc_date = get_encounter_date(enc)
        if not is_date_in_range(enc_date, my_start, my_end):
            continue
        if resource_has_code(enc, HOSPICE_ENCOUNTER_SNOMED, "http://snomed.info/sct"):
            evaluated.append(f"Encounter/{enc.get('id')}")
            return True, evaluated

    # Exclusion: Palliative care
    conditions = get_resources_by_type(bundle, "Condition")
    for cond in conditions:
        onset = parse_date(cond.get("onsetDateTime"))
        if is_date_in_range(onset, my_start, my_end):
            if resource_has_code(
                cond, PALLIATIVE_CARE_ICD10, "http://hl7.org/fhir/sid/icd-10-cm"
            ):
                evaluated.append(f"Condition/{cond.get('id')}")
                return True, evaluated

    # Exclusion: Pregnancy
    for cond in conditions:
        onset = parse_date(cond.get("onsetDateTime"))
        if is_date_in_range(onset, my_start, my_end):
            code_val = cond.get("code", {})
            for coding in code_val.get("coding", []):
                if coding.get("system") == "http://hl7.org/fhir/sid/icd-10-cm":
                    c = coding.get("code", "")
                    if any(c.startswith(prefix) for prefix in PREGNANCY_ICD10_PREFIXES):
                        evaluated.append(f"Condition/{cond.get('id')}")
                        return True, evaluated

    # Exclusion: ESRD
    for cond in conditions:
        if resource_has_code(
            cond, ESRD_DIAGNOSIS_ICD10, "http://hl7.org/fhir/sid/icd-10-cm"
        ):
            onset = parse_date(cond.get("onsetDateTime"))
            if onset and onset <= my_end:
                evaluated.append(f"Condition/{cond.get('id')}")
                return True, evaluated

    # Exclusion: Dialysis procedure
    procedures = get_resources_by_type(bundle, "Procedure")
    for proc in procedures:
        if resource_has_code(proc, DIALYSIS_CPT, "http://www.ama-assn.org/go/cpt"):
            proc_date = parse_date(proc.get("performedDateTime"))
            if proc_date and proc_date <= my_end:
                evaluated.append(f"Procedure/{proc.get('id')}")
                return True, evaluated

    return False, evaluated


# ---------------------------------------------------------------------------
# Numerator
# ---------------------------------------------------------------------------


def check_numerator(bundle: dict, measurement_year: int) -> tuple[bool, list[str]]:
    """
    Check if the patient's most recent BP reading is adequately controlled
    (<140/90 mm Hg) during the measurement year.

    Returns (is_compliant, list_of_evaluated_resource_references).
    """
    evaluated = []
    my_start = date(measurement_year, 1, 1)
    my_end = date(measurement_year, 12, 31)

    observations = get_resources_by_type(bundle, "Observation")
    encounters = get_resources_by_type(bundle, "Encounter")

    # Build set of dates that are in acute inpatient or ED settings (excluded)
    excluded_dates: set[date] = set()
    for enc in encounters:
        enc_class = enc.get("class", {}).get("code", "")
        if enc_class in (ACUTE_INPATIENT_CLASS, ED_CLASS):
            period = enc.get("period", {})
            start = parse_date(period.get("start"))
            end = parse_date(period.get("end"))
            if start:
                d = start
                while d <= (end or start):
                    excluded_dates.add(d)
                    d = (
                        date(d.year, d.month, d.day + 1) if d.day < 28 else d
                    )  # simplified
                    break  # just mark start date for simplicity

    # Find BP observations during measurement year
    bp_readings: list[dict] = []  # {date, systolic, diastolic, obs_id}

    for obs in observations:
        obs_date = parse_date(
            obs.get("effectiveDateTime")
            or (obs.get("effectivePeriod", {}) or {}).get("start")
        )
        if not is_date_in_range(obs_date, my_start, my_end):
            continue

        # Skip if in excluded setting
        if obs_date in excluded_dates:
            continue

        # Check for BP panel or individual systolic/diastolic
        obs_code = obs.get("code", {})
        codings = obs_code.get("coding", [])
        loinc_codes = [
            c.get("code") for c in codings if c.get("system") == "http://loinc.org"
        ]

        systolic = None
        diastolic = None

        if LOINC_BP_PANEL in loinc_codes:
            # BP panel - extract components
            for component in obs.get("component", []):
                comp_codes = [
                    c.get("code")
                    for c in component.get("code", {}).get("coding", [])
                    if c.get("system") == "http://loinc.org"
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

    if not bp_readings:
        return False, evaluated

    # Group by date, use lowest systolic and lowest diastolic per date
    from collections import defaultdict

    by_date: dict[date, list[dict]] = defaultdict(list)
    for bp in bp_readings:
        by_date[bp["date"]].append(bp)

    # Find most recent date
    most_recent_date = max(by_date.keys())
    readings_on_date = by_date[most_recent_date]

    # Get lowest systolic and diastolic from that date
    systolics = [r["systolic"] for r in readings_on_date if r["systolic"] is not None]
    diastolics = [
        r["diastolic"] for r in readings_on_date if r["diastolic"] is not None
    ]

    if not systolics or not diastolics:
        return False, evaluated

    representative_systolic = min(systolics)
    representative_diastolic = min(diastolics)

    # Track evaluated resources
    for r in readings_on_date:
        if r["obs_id"]:
            evaluated.append(f"Observation/{r['obs_id']}")

    # Check adequate control: systolic < 140 AND diastolic < 90
    is_controlled = representative_systolic < 140 and representative_diastolic < 90

    return is_controlled, evaluated


# ---------------------------------------------------------------------------
# MeasureReport Builder
# ---------------------------------------------------------------------------


def build_measure_report(
    patient_id: str,
    measurement_year: int,
    initial_population: bool,
    denominator_exclusion: bool,
    numerator: bool,
    evaluated_resources: list[str],
) -> dict[str, Any]:
    """Build a FHIR MeasureReport for CBP."""
    denominator_count = 1 if (initial_population and not denominator_exclusion) else 0
    numerator_count = 1 if (denominator_count == 1 and numerator) else 0

    measure_score = None
    if denominator_count > 0:
        measure_score = float(numerator_count) / float(denominator_count)

    report: dict[str, Any] = {
        "resourceType": "MeasureReport",
        "id": str(uuid.uuid4()),
        "status": "complete",
        "type": "individual",
        "measure": "http://ncqa.org/fhir/Measure/CBP",
        "subject": {"reference": f"Patient/{patient_id}"},
        "date": datetime.now().isoformat(),
        "period": {
            "start": f"{measurement_year}-01-01",
            "end": f"{measurement_year}-12-31",
        },
        "group": [
            {
                "code": {
                    "coding": [
                        {
                            "system": "http://ncqa.org/fhir/CodeSystem/measure-group",
                            "code": "CBP",
                            "display": "Controlling High Blood Pressure",
                        }
                    ]
                },
                "population": [
                    {
                        "code": {
                            "coding": [
                                {
                                    "system": "http://terminology.hl7.org/CodeSystem/measure-population",
                                    "code": "initial-population",
                                    "display": "Initial Population",
                                }
                            ]
                        },
                        "count": 1 if initial_population else 0,
                    },
                    {
                        "code": {
                            "coding": [
                                {
                                    "system": "http://terminology.hl7.org/CodeSystem/measure-population",
                                    "code": "denominator",
                                    "display": "Denominator",
                                }
                            ]
                        },
                        "count": denominator_count,
                    },
                    {
                        "code": {
                            "coding": [
                                {
                                    "system": "http://terminology.hl7.org/CodeSystem/measure-population",
                                    "code": "denominator-exclusion",
                                    "display": "Denominator Exclusion",
                                }
                            ]
                        },
                        "count": 1 if denominator_exclusion else 0,
                    },
                    {
                        "code": {
                            "coding": [
                                {
                                    "system": "http://terminology.hl7.org/CodeSystem/measure-population",
                                    "code": "numerator",
                                    "display": "Numerator",
                                }
                            ]
                        },
                        "count": numerator_count,
                    },
                ],
            }
        ],
        "evaluatedResource": [{"reference": ref} for ref in evaluated_resources],
    }

    if measure_score is not None:
        report["group"][0]["measureScore"] = {"value": measure_score}

    return report


# ---------------------------------------------------------------------------
# Main Entry Point
# ---------------------------------------------------------------------------


def calculate_cbp_measure(bundle: dict, measurement_year: int = 2025) -> dict[str, Any]:
    """
    Calculate the Controlling High Blood Pressure (CBP) measure for a patient.

    Args:
        bundle: FHIR R4 Bundle containing all resources for one patient.
        measurement_year: The HEDIS measurement year (default: 2025).

    Returns:
        FHIR R4 MeasureReport resource as a dictionary.
    """
    all_evaluated: list[str] = []

    # Step 1: Check eligible population
    is_eligible, eligible_refs = check_eligible_population(bundle, measurement_year)
    all_evaluated.extend(eligible_refs)

    if not is_eligible:
        patient = get_patient(bundle)
        patient_id = patient.get("id", "unknown") if patient else "unknown"
        return build_measure_report(
            patient_id=patient_id,
            measurement_year=measurement_year,
            initial_population=False,
            denominator_exclusion=False,
            numerator=False,
            evaluated_resources=all_evaluated,
        )

    # Step 2: Check required exclusions
    is_excluded, exclusion_refs = check_exclusions(bundle, measurement_year)
    all_evaluated.extend(exclusion_refs)

    # Step 3: Check numerator (even if excluded, for reporting)
    is_compliant, numerator_refs = check_numerator(bundle, measurement_year)
    all_evaluated.extend(numerator_refs)

    patient = get_patient(bundle)
    patient_id = patient.get("id", "unknown") if patient else "unknown"

    return build_measure_report(
        patient_id=patient_id,
        measurement_year=measurement_year,
        initial_population=True,
        denominator_exclusion=is_excluded,
        numerator=is_compliant,
        evaluated_resources=list(
            dict.fromkeys(all_evaluated)
        ),  # deduplicate preserving order
    )


# ---------------------------------------------------------------------------
# Example Usage
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import json

    # Example FHIR Bundle for a 55-year-old patient with controlled hypertension
    example_bundle: dict[str, Any] = {
        "resourceType": "Bundle",
        "type": "collection",
        "entry": [
            {
                "resource": {
                    "resourceType": "Patient",
                    "id": "patient-001",
                    "birthDate": "1970-03-15",
                }
            },
            {
                "resource": {
                    "resourceType": "Condition",
                    "id": "condition-htn-001",
                    "code": {
                        "coding": [
                            {
                                "system": "http://hl7.org/fhir/sid/icd-10-cm",
                                "code": "I10",
                                "display": "Essential (primary) hypertension",
                            }
                        ]
                    },
                    "onsetDateTime": "2023-06-01",
                    "clinicalStatus": {
                        "coding": [
                            {
                                "system": "http://terminology.hl7.org/CodeSystem/condition-clinical",
                                "code": "active",
                            }
                        ]
                    },
                }
            },
            {
                "resource": {
                    "resourceType": "Encounter",
                    "id": "encounter-001",
                    "class": {
                        "system": "http://terminology.hl7.org/CodeSystem/v3-ActCode",
                        "code": "AMB",
                    },
                    "type": [
                        {
                            "coding": [
                                {
                                    "system": "http://www.ama-assn.org/go/cpt",
                                    "code": "99213",
                                }
                            ]
                        }
                    ],
                    "period": {"start": "2024-03-15", "end": "2024-03-15"},
                    "reasonCode": [
                        {
                            "coding": [
                                {
                                    "system": "http://hl7.org/fhir/sid/icd-10-cm",
                                    "code": "I10",
                                }
                            ]
                        }
                    ],
                }
            },
            {
                "resource": {
                    "resourceType": "Encounter",
                    "id": "encounter-002",
                    "class": {
                        "system": "http://terminology.hl7.org/CodeSystem/v3-ActCode",
                        "code": "AMB",
                    },
                    "type": [
                        {
                            "coding": [
                                {
                                    "system": "http://www.ama-assn.org/go/cpt",
                                    "code": "99214",
                                }
                            ]
                        }
                    ],
                    "period": {"start": "2025-02-10", "end": "2025-02-10"},
                    "reasonCode": [
                        {
                            "coding": [
                                {
                                    "system": "http://hl7.org/fhir/sid/icd-10-cm",
                                    "code": "I10",
                                }
                            ]
                        }
                    ],
                }
            },
            {
                "resource": {
                    "resourceType": "Observation",
                    "id": "bp-obs-001",
                    "status": "final",
                    "code": {
                        "coding": [
                            {
                                "system": "http://loinc.org",
                                "code": "85354-9",
                                "display": "Blood pressure panel",
                            }
                        ]
                    },
                    "effectiveDateTime": "2025-09-20",
                    "component": [
                        {
                            "code": {
                                "coding": [
                                    {
                                        "system": "http://loinc.org",
                                        "code": "8480-6",
                                        "display": "Systolic blood pressure",
                                    }
                                ]
                            },
                            "valueQuantity": {
                                "value": 132,
                                "unit": "mmHg",
                                "system": "http://unitsofmeasure.org",
                                "code": "mm[Hg]",
                            },
                        },
                        {
                            "code": {
                                "coding": [
                                    {
                                        "system": "http://loinc.org",
                                        "code": "8462-4",
                                        "display": "Diastolic blood pressure",
                                    }
                                ]
                            },
                            "valueQuantity": {
                                "value": 82,
                                "unit": "mmHg",
                                "system": "http://unitsofmeasure.org",
                                "code": "mm[Hg]",
                            },
                        },
                    ],
                }
            },
        ],
    }

    result = calculate_cbp_measure(example_bundle, measurement_year=2025)
    print(json.dumps(result, indent=2))
