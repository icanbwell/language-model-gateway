"""
HEDIS MY 2025 - Colorectal Cancer Screening (COL-E)

The percentage of members 45-75 years of age who had appropriate
screening for colorectal cancer.

Screening methods and lookback periods:
- FOBT: during MY
- sDNA FIT: MY or 2 years prior
- Flexible sigmoidoscopy: MY or 4 years prior
- CT colonography: MY or 4 years prior
- Colonoscopy: MY or 9 years prior
"""

from __future__ import annotations

from datetime import date

from .hedis_common import (
    load_value_sets_from_csv,
    run_measure,
    check_common_exclusions,
    get_patient_birth_date,
    get_resources_by_type,
    calculate_age,
    parse_date,
    is_date_in_range,
    measurement_year_dates,
    resource_has_any_code,
    find_conditions_with_codes,
    find_procedures_with_codes,
    find_observations_with_codes,
    all_codes,
    SNOMED,
)

VALUE_SETS = load_value_sets_from_csv("COL-E")


# ---------------------------------------------------------------------------
# Eligible population
# ---------------------------------------------------------------------------


def check_eligible_population(
    bundle: dict,
    measurement_year: int,
) -> tuple[bool, list[str]]:
    """Members 46-75 by end of MY."""
    birth_date = get_patient_birth_date(bundle)
    if not birth_date:
        return False, []
    _, my_end = measurement_year_dates(measurement_year)
    age = calculate_age(birth_date, my_end)
    if 46 <= age <= 75:
        return True, []
    return False, []


# ---------------------------------------------------------------------------
# Exclusions
# ---------------------------------------------------------------------------


def check_exclusions(
    bundle: dict,
    measurement_year: int,
) -> tuple[bool, list[str]]:
    """Hospice, death, palliative care, frailty/advanced illness,
    colorectal cancer history, total colectomy."""
    excluded, refs = check_common_exclusions(
        bundle,
        VALUE_SETS,
        measurement_year,
        check_frailty=True,
    )
    if excluded:
        return True, refs

    far_past = date(1900, 1, 1)
    _, my_end = measurement_year_dates(measurement_year)

    # Colorectal cancer history
    crc_codes = all_codes(VALUE_SETS, "Colorectal Cancer")
    if crc_codes:
        found = find_conditions_with_codes(bundle, crc_codes, far_past, my_end)
        if found:
            return True, refs + [f"Condition/{c.get('id')}" for c, _ in found]

    # Total colectomy
    colectomy_codes = all_codes(VALUE_SETS, "Total Colectomy")
    if colectomy_codes:
        found = find_procedures_with_codes(bundle, colectomy_codes, far_past, my_end)
        if found:
            return True, refs + [f"Procedure/{p.get('id')}" for p, _ in found]
        found_cond = find_conditions_with_codes(
            bundle, colectomy_codes, far_past, my_end
        )
        if found_cond:
            return True, refs + [f"Condition/{c.get('id')}" for c, _ in found_cond]

    # SNOMED direct reference code for total colectomy
    snomed_colectomy = {SNOMED: {"119771000119101"}}
    found = find_conditions_with_codes(bundle, snomed_colectomy, far_past, my_end)
    if found:
        return True, refs + [f"Condition/{c.get('id')}" for c, _ in found]
    found_proc = find_procedures_with_codes(bundle, snomed_colectomy, far_past, my_end)
    if found_proc:
        return True, refs + [f"Procedure/{p.get('id')}" for p, _ in found_proc]

    return False, refs


# ---------------------------------------------------------------------------
# Numerator
# ---------------------------------------------------------------------------


def _find_any_screening(
    bundle: dict,
    vs_names: list[str],
    start: date,
    end: date,
) -> tuple[bool, list[str]]:
    """Search for screening in observations, procedures, diagnostic reports."""
    for vs_name in vs_names:
        vs_codes = all_codes(VALUE_SETS, vs_name)
        if not vs_codes:
            continue
        found_obs = find_observations_with_codes(bundle, vs_codes, start, end)
        if found_obs:
            return True, [f"Observation/{found_obs[0][0].get('id')}"]
        found_proc = find_procedures_with_codes(bundle, vs_codes, start, end)
        if found_proc:
            return True, [f"Procedure/{found_proc[0][0].get('id')}"]
        # DiagnosticReport
        for dr in get_resources_by_type(bundle, "DiagnosticReport"):
            dr_date = parse_date(
                dr.get("effectiveDateTime")
                or (dr.get("effectivePeriod") or {}).get("start")
            )
            if dr_date and is_date_in_range(dr_date, start, end):
                if resource_has_any_code(dr, vs_codes):
                    return True, [f"DiagnosticReport/{dr.get('id')}"]
    return False, []


def check_numerator(
    bundle: dict,
    measurement_year: int,
) -> tuple[bool, list[str]]:
    """Check for any qualifying colorectal cancer screening."""
    my_start, my_end = measurement_year_dates(measurement_year)

    # FOBT during MY
    found, refs = _find_any_screening(
        bundle,
        ["FOBT Lab Test", "FOBT Test Result or Finding"],
        my_start,
        my_end,
    )
    if found:
        return True, refs

    # sDNA FIT during MY or 2 years prior
    sdna_start = date(measurement_year - 2, 1, 1)
    found, refs = _find_any_screening(
        bundle,
        ["sDNA FIT Lab Test"],
        sdna_start,
        my_end,
    )
    if found:
        return True, refs
    # SNOMED direct reference 708699002
    snomed_sdna = {SNOMED: {"708699002"}}
    found_obs = find_observations_with_codes(bundle, snomed_sdna, sdna_start, my_end)
    if found_obs:
        return True, [f"Observation/{found_obs[0][0].get('id')}"]

    # Flexible sigmoidoscopy during MY or 4 years prior
    sig_start = date(measurement_year - 4, 1, 1)
    found, refs = _find_any_screening(
        bundle,
        ["Flexible Sigmoidoscopy"],
        sig_start,
        my_end,
    )
    if found:
        return True, refs
    # SNOMED direct ref 841000119107
    snomed_sig = {SNOMED: {"841000119107"}}
    found_proc = find_procedures_with_codes(bundle, snomed_sig, sig_start, my_end)
    if found_proc:
        return True, [f"Procedure/{found_proc[0][0].get('id')}"]

    # CT colonography during MY or 4 years prior
    found, refs = _find_any_screening(
        bundle,
        ["CT Colonography"],
        sig_start,
        my_end,
    )
    if found:
        return True, refs

    # Colonoscopy during MY or 9 years prior
    colon_start = date(measurement_year - 9, 1, 1)
    found, refs = _find_any_screening(
        bundle,
        ["Colonoscopy"],
        colon_start,
        my_end,
    )
    if found:
        return True, refs
    # SNOMED direct ref 851000119109
    snomed_colon = {SNOMED: {"851000119109"}}
    found_proc = find_procedures_with_codes(bundle, snomed_colon, colon_start, my_end)
    if found_proc:
        return True, [f"Procedure/{found_proc[0][0].get('id')}"]

    return False, []


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------


def calculate_col_e_measure(
    bundle: dict,
    measurement_year: int = 2025,
) -> dict:
    """Calculate COL-E measure."""
    return run_measure(
        bundle=bundle,
        measure_abbreviation="COL-E",
        measure_name="Colorectal Cancer Screening",
        measurement_year=measurement_year,
        check_eligible_population_fn=check_eligible_population,
        check_exclusions_fn=check_exclusions,
        check_numerator_fn=check_numerator,
    )
