# HEDIS Measure Specification Pattern

Every HEDIS measure follows a consistent structure. When generating code, map each section to the corresponding logic in the Python output.

## Standard Measure Structure

### 1. Description
A brief statement of what the measure calculates (e.g., "The percentage of members 18–85 years of age who had a diagnosis of hypertension and whose BP was adequately controlled").

**Maps to**: The docstring of the main measure function and the `Measure.description` field.

### 2. Definitions
Key terms used in the measure (e.g., "Adequate control", "Representative BP").

**Maps to**: Constants, helper functions, or inline comments that define thresholds and logic.

### 3. Eligible Population
Determines who is in the denominator. Always includes:

- **Product lines**: Which insurance types (Commercial, Medicaid, Medicare).
- **Ages**: Age range as of December 31 of the measurement year.
- **Continuous enrollment**: Required enrollment period and allowable gaps.
- **Anchor date**: Usually December 31 of the measurement year.
- **Benefit**: Required benefit type (Medical, Pharmacy, etc.).
- **Event/diagnosis**: Clinical criteria for inclusion (diagnoses, visits, procedures).

**Maps to**: `check_eligible_population(bundle, measurement_year)` function that returns True/False.

### 4. Required Exclusions
Members who meet the eligible population but must be removed. Common exclusions:

- Hospice use during measurement year
- Death during measurement year
- Palliative care during measurement year
- Pregnancy (for some measures)
- ESRD / dialysis / kidney transplant (for some measures)
- Institutional SNP enrollment (Medicare 66+)
- Frailty + Advanced Illness (ages 66-80)
- Frailty alone (ages 81+)

**Maps to**: `check_exclusions(bundle, measurement_year)` function that returns True/False.

### 5. Administrative Specification

#### Denominator
Usually "The eligible population" (after exclusions).

#### Numerator
The clinical criteria that determine if the member received the desired care. This is the core logic and varies by measure. Examples:
- BP reading < 140/90 mm Hg (CBP)
- HbA1c test performed (GSD)
- Statin dispensed (SPC)
- Follow-up visit within 7/30 days (FUH)

**Maps to**: `check_numerator(bundle, measurement_year)` function that returns True/False.

### 6. Value Sets Referenced
Measures reference HEDIS Value Sets by name (e.g., "Essential Hypertension Value Set", "Outpatient and Telehealth Without UBREV Value Set"). In FHIR, these map to code systems and value sets.

**Maps to**: Dictionary constants mapping value set names to lists of codes (ICD-10, CPT, SNOMED, LOINC, etc.).

## FHIR Resource Mapping

When processing a FHIR Bundle, each HEDIS concept maps to FHIR resources:

| HEDIS Concept | FHIR Resource(s) | Key Fields |
|---|---|---|
| Member demographics | Patient | birthDate, gender, deceasedDateTime |
| Enrollment/coverage | Coverage | period, type, status |
| Diagnoses | Condition | code, onsetDateTime, clinicalStatus |
| Outpatient visits | Encounter | type, class, period, reasonCode |
| Procedures | Procedure | code, performedDateTime, status |
| Lab results | Observation | code, valueQuantity, effectiveDateTime |
| Medications dispensed | MedicationDispense / MedicationRequest | medicationCodeableConcept, authoredOn, whenHandedOver |
| BP readings | Observation | code (LOINC 85354-9 panel, 8480-6 systolic, 8462-4 diastolic), component.valueQuantity |
| Inpatient stays | Encounter (class=IMP) | type, class, period, hospitalization.dischargeDisposition |
| ED visits | Encounter (class=EMER) | type, class, period |
| Hospice | Encounter or Procedure | type with hospice codes |
| Pharmacy benefit | Coverage | type with pharmacy benefit |

## Common FHIR Code Systems

| System | URI | Used For |
|---|---|---|
| ICD-10-CM | `http://hl7.org/fhir/sid/icd-10-cm` | Diagnoses |
| CPT | `http://www.ama-assn.org/go/cpt` | Procedures, visits |
| HCPCS | `https://www.cms.gov/Medicare/Coding/HCPCSReleaseCodeSets` | Procedures |
| SNOMED CT | `http://snomed.info/sct` | Diagnoses, procedures |
| LOINC | `http://loinc.org` | Lab tests, observations |
| RxNorm | `http://www.nlm.nih.gov/research/umls/rxnorm` | Medications |
| NDC | `http://hl7.org/fhir/sid/ndc` | Medications |
| CVX | `http://hl7.org/fhir/sid/cvx` | Vaccines |

## Age Calculation Pattern

Age is always calculated as of December 31 of the measurement year:

```python
from datetime import date

def calculate_age(birth_date: date, as_of: date) -> int:
    age = as_of.year - birth_date.year
    if (as_of.month, as_of.day) < (birth_date.month, birth_date.day):
        age -= 1
    return age
```

## Date Range Patterns

- **Measurement year**: January 1 through December 31 of the year.
- **Year prior**: January 1 through December 31 of the year before.
- **Lookback periods**: Some measures look back 1-2 years before the measurement year.
- **Intake period**: Some measures define a specific window (e.g., first 10 months).

## Multiple Numerator Events

Some measures require multiple events (e.g., two visits on different dates). Events must be on different dates of service. For measures listed in the "Collecting Data for Measures With Multiple Numerator Events" guideline, events must be at least 14 days apart.
