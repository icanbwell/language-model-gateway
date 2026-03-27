## <a id="Controlling_HB_CBP"></a><a id="_Toc74815064"></a><a id="_Toc171402980"></a><a id="_Toc400546127"></a><a id="PBH"></a>Controlling High Blood Pressure \(CBP\)

Summary of Changes to HEDIS MY 2025

- Removed the data source reporting requirement from the race and ethnicity stratification\. 
- *Technical Update:* Revised the required exclusions\. 

Description

The percentage of members 18–85 years of age who had a diagnosis of hypertension \(HTN\) and whose blood pressure \(BP\) was adequately controlled \(<140/90 mm Hg\) during the measurement year\. 

Definitions

Adequate control

Both a representative systolic BP <140 mm Hg and a representative diastolic BP of <90 mm Hg\. 

Representative BP

The most recent BP reading during the measurement year on or after the second diagnosis of hypertension\. If multiple BP measurements occur on the same date, or are noted in the chart on the same date, use the lowest systolic and lowest diastolic BP reading\. If no BP is recorded during the measurement year, assume that the member is “not controlled\.”

Eligible Population 

Product lines

Commercial, Medicaid, Medicare \(report each product line separately\)\.

Stratifications

For each product line, report the following stratifications by race and total, and stratifications by ethnicity and total: 

- *Race:*
- American Indian or Alaska Native\.
- Asian\.
- Black or African American\.
- Native Hawaiian or Other Pacific Islander\.
- White\.
- Some Other Race\.
- Two or More Races\.
- Asked But No Answer\.
- Unknown\.
- Total\. 
- *Ethnicity:*
- Hispanic or Latino\.
- Not Hispanic or Latino\.
- Asked But No Answer\.
- Unknown\.
- Total\.

__Note: __Stratifications are mutually exclusive, and the sum of all categories in each stratification is the total population\.

Ages

18–85 years as of December 31 of the measurement year\.

Continuous enrollment

The measurement year\. 

__Allowable gap__

No more than one gap in continuous enrollment of up to 45 days during the measurement year\. To determine continuous enrollment for a Medicaid beneficiary for whom enrollment is verified monthly, the member may not have more than a 1\-month gap in coverage \(e\.g\., a member whose coverage lapses for 2 months \[60 days\] is not considered continuously enrolled\)\. 

Anchor date

December 31 of the measurement year\.

Benefit

Medical\.

Event/diagnosis

Follow the steps below to identify the eligible population\.

*Step 1*

Identify members who had at least two outpatient visits, telephone visits, e\-visits or virtual check\-ins \(Outpatient and Telehealth Without UBREV Value Set\) on different dates of service with a diagnosis of hypertension \(Essential Hypertension Value Set\) on or between January 1 of the year prior to the measurement year and June 30 of the measurement year\. 

*Step 2*

Remove members who had a nonacute inpatient admission during the measurement year\. To identify nonacute inpatient admissions:

1\.	Identify all acute and nonacute inpatient stays \(Inpatient Stay Value Set\)\. 

2\.	Confirm the stay was for nonacute care based on the presence of a nonacute code \(Nonacute Inpatient Stay Value Set\) on the claim\. 

3\.	Identify the admission date for the stay\.

Required exclusions

<a id="_Hlk37948636"></a>Exclude members who meet any of the following criteria:

- Members who use hospice services \(Hospice Encounter Value Set; Hospice Intervention Value Set\) or elect to use a hospice benefit any time during the measurement year\. Organizations that use the Monthly Membership Detail Data File to identify these members must use only the run date of the file to determine if the member elected to use a hospice benefit during the measurement year\. 
- Members who die any time during the measurement year\. 
- Members receiving palliative care \(Palliative Care Assessment Value Set; Palliative Care Encounter Value Set; Palliative Care Intervention Value Set\) any time during the measurement year\. 
- Members who had an encounter for palliative care \(ICD\-10\-CM code Z51\.5\) any time during the measurement year\. Do not include laboratory claims \(claims with POS code 81\)\.
- Members with a diagnosis that indicates end\-stage renal disease \(ESRD\) \(ESRD Diagnosis Value Set; History of Nephrectomy or Kidney Transplant Value Set\), any time during the member’s history on or prior to December 31 of the measurement year\. Do not include laboratory claims \(claims with POS code 81\)\.
- Members with a procedure that indicates ESRD: dialysis \(Dialysis Procedure Value Set\), nephrectomy \(Total Nephrectomy Value Set; Partial Nephrectomy Value Set\) or kidney transplant \(Kidney Transplant Value Set\) any time during the member’s history on or prior to December 31 of the measurement year\. 
- Members with a diagnosis of pregnancy \(Pregnancy Value Set\) any time during the measurement year\. Do not include laboratory claims \(claims with POS code 81\)\.
- Medicare members 66 years of age and older as of December 31 of the measurement year who meet either of the following:
- Enrolled in an Institutional SNP \(I\-SNP\) any time during the measurement year\.
- Living long\-term in an institution any time during the measurement year as identified by the LTI flag in the Monthly Membership Detail Data File\. Use the run date of the file to determine if a member had an LTI flag during the measurement year\.
- Members 66–80 years of age as of December 31 of the measurement year \(all product lines\) with frailty __*and*__ advanced illness\. Members must meet __*both*__ frailty and advanced illness criteria to be excluded: 

1\.	__Frailty\.__ At least two indications of frailty \(Frailty Device Value Set; Frailty Diagnosis Value Set; Frailty Encounter Value Set; Frailty Symptom Value Set\) with different dates of service during the measurement year\. Do not include laboratory claims \(claims with POS code 81\)\. 

2\.	__Advanced Illness\.__ Either of the following during the measurement year or the year prior to the measurement year: 

- Advanced illness \(Advanced Illness Value Set\) on at least two different dates of service\. Do not include laboratory claims \(claims with POS code 81\)\.
- Dispensed dementia medication \(Dementia Medications List\)\.
- Members 81 years of age and older as of December 31 of the measurement year \(all product lines\) with at least two indications of frailty \(Frailty Device Value Set; Frailty Diagnosis Value Set; Frailty Encounter Value Set; Frailty Symptom Value Set\) with different dates of service during the measurement year\. Do not include laboratory claims \(claims with POS code 81\)\.

__*Dementia Medications*__

__Description__

__Prescription__

Cholinesterase inhibitors

- Donepezil

- Galantamine

- Rivastigmine 

Miscellaneous central nervous system agents

- Memantine

Dementia combinations

- Donepezil\-memantine

Administrative Specification

Denominator

The eligible population\. 

Numerator

Identify the most recent BP reading \(Systolic Blood Pressure Value Set; Diastolic Blood Pressure Value Set\) taken during the measurement year\. Do not include CPT Category II codes \(Systolic and Diastolic Result Value Set\) with a modifier \(CPT CAT II Modifier Value Set\)\. Do not include BPs taken in an acute inpatient setting \(Acute Inpatient Value Set; Acute Inpatient POS Value Set\) or during an ED visit \(ED Value Set; POS code 23\)\. 

The BP reading must occur *on or after* the date of the second diagnosis of hypertension \(identified using the event/diagnosis criteria\)\.

The member is numerator compliant if the BP is <140/90 mm Hg\. The member is not compliant if the BP is ≥140/90 mm Hg, if there is no BP reading during the measurement year or if the reading is incomplete \(e\.g\., the systolic or diastolic level is missing\)\. If there are multiple BPs on the same date of service, use the lowest systolic and lowest diastolic BP on that date as the representative BP\. 

If the most recent blood pressure was identified based on a CPT Category II code \(Systolic and Diastolic Result Value Set\) use the following to determine compliance:

- Systolic Compliant: Systolic Less Than 140 Value Set\.
- Systolic Not Compliant: CPT\-CAT\-II code 3077F\.
- Diastolic Compliant: Diastolic Less Than 90 Value Set\.
- Diastolic Not Compliant: CPT\-CAT\-II code 3080F\.

Hybrid Specification

Denominator

A systematic sample drawn from the eligible population\. 

The organization may reduce the sample size using the current year’s administrative rate or the prior year’s audited, product line specific rate\. Refer to the *Guidelines for Calculations and Sampling* for information on reducing the sample size\.

Identifying   
the medical record

All eligible BP measurements recorded in the record must be considered\. If an organization cannot find the medical record, the member remains in the measure denominator and is considered noncompliant for the numerator\.

Use the following guidance to find the appropriate medical record to review\.

- Identify the member’s PCP\.
- If the member had more than one PCP for the time period, identify the PCP who most recently provided care to the member\.
- If the member did not visit a PCP for the time period or does not have a PCP, identify the practitioner who most recently provided care to the member\.
- If a practitioner other than the member’s PCP manages the hypertension, the organization may use the medical record of that practitioner\.

Numerator

The number of members in the denominator whose most recent BP \(both systolic and diastolic\) is adequately controlled during the measurement year\. For a member’s BP to be controlled, the systolic and diastolic BP must be <140/90 mm Hg \(adequate control\)\. To determine if a member’s BP is adequately controlled, the representative BP must be identified\.

Administrative

Refer to *Administrative Specification* to identify positive numerator hits from administrative data\.

Medical record

Identify the most recent BP reading noted during the measurement year\. 

The BP reading must occur on or after the date when the second diagnosis of hypertension \(identified using the event/diagnosis criteria\) occurred\.

Do not include BP readings:

- Taken during an acute inpatient stay or an ED visit\.
- Taken on the same day as a diagnostic test or diagnostic or therapeutic procedure that requires a change in diet or change in medication on or one day before the day of the test or procedure, with the exception of fasting blood tests\.
- Taken by the member using a non\-digital device such as with a manual blood pressure cuff and a stethoscope\.

Identify the lowest systolic and lowest diastolic BP reading from the most recent BP notation in the medical record\. If multiple readings were recorded for a single date, use the lowest systolic and lowest diastolic BP on that date as the representative BP\. The systolic and diastolic results do not need to be from the same reading\. 

BP readings taken by the member and documented in the member’s medical record are eligible for use in reporting \(provided the BP does not meet any exclusion criteria\)\. There is no requirement that there be evidence the BP was collected by a PCP or specialist\. 

The member is not compliant if the BP reading is ≥140/90 mm Hg or is missing, or if there is no BP reading during the measurement year or if the reading is incomplete \(e\.g\., the systolic or diastolic level is missing\)\.

Ranges and thresholds do not meet criteria for this measure\. A distinct numeric result for both the systolic and diastolic BP reading is required for numerator compliance\. A BP documented as an “average BP” \(e\.g\., “average BP: 139/70”\) is eligible for use\.

*Note*

- *When identifying the most recent BP reading, all eligible BP readings in the appropriate medical record should be considered, regardless of practitioner type and setting \(excluding acute inpatient and ED visit settings\)\.*
- *An EMR can be used to identify the most recent BP reading if it meets the criteria for appropriate medical record\.*
- *When excluding BP readings from the numerator, the intent is to identify diagnostic or therapeutic procedures that require a medication regimen, a change in diet or a change in medication\. For example \(this list is for reference only and is not exhaustive\):*
- *A colonoscopy requires a change in diet \(NPO on the day of the procedure\) and a medication change \(a medication is taken to prep the colon\)\. *
- *Dialysis, infusions and chemotherapy \(including oral chemotherapy\) are all therapeutic procedures that require a medication regimen\. *
- *A nebulizer treatment with albuterol is considered a therapeutic procedure that requires a medication regimen \(the albuterol\)\. *
- *A patient forgetting to take regular medications on the day of the procedure is not considered a required change in medication and therefore the BP reading is eligible\.*
- *BP readings taken on the same day that the member receives a common low\-intensity or preventive procedure are eligible for use\. For example, the following procedures are considered common low\-intensity or preventive \(this list is for reference only and is not exhaustive\): *
- *Vaccinations\.*
- *Injections \(e\.g\., allergy, vitamin B\-12, insulin, steroid, Toradol, Depo\-Provera, testosterone, lidocaine\)\.*
- *TB test\.*
- *IUD insertion\.*
- *Eye exam with dilating agents\.*
- *Wart or mole removal\.*

__Data Elements for Reporting __

Organizations that submit HEDIS data to NCQA must provide the following data elements\.

__*Table CBP\-A\-1/2/3: Data Elements for Controlling High Blood Pressure*__

__Metric__

__Data Element __

__Reporting Instructions__

__A__

ControlHighBP

CollectionMethod

Report once

ü

EligiblePopulation

Report once

ü

ExclusionAdminRequired

Report once

ü

NumeratorByAdminElig

Report once

CYAR

\(Percent\)

MinReqSampleSize

Report once

OversampleRate

Report once

OversampleRecordsNumber

\(Count\)

ExclusionValidDataErrors

Report once

ExclusionEmployeeOrDep

Report once

OversampleRecsAdded

Report once

Denominator

Report once

NumeratorByAdmin

Report once

ü

NumeratorByMedicalRecords

Report once

NumeratorBySupplemental

Report once

ü

Rate

\(Percent\)

ü

__*Table CBP\-B\-1/2/3: Data Elements for Controlling High Blood Pressure: Stratifications by Race*__

Metric

Race

Data Element

Reporting Instructions

A

ControlHighBP

AmericanIndianOrAlaskaNative

CollectionMethod

Repeat per Stratification

ü

Asian

EligiblePopulation

For each Stratification

ü

BlackOrAfricanAmerican

Denominator

For each Stratification

NativeHawaiianOrOtherPacificIslander 

Numerator

For each Stratification

ü

White

Rate

\(Percent\)

ü

SomeOtherRace

TwoOrMoreRaces

AskedButNoAnswer

Unknown

__*Table CBP\-C\-1/2/3: Data Elements for Controlling High Blood Pressure: Stratifications by Ethnicity*__

Metric

Ethnicity

Data Element

Reporting Instructions

A

ControlHighBP

HispanicOrLatino

CollectionMethod

Repeat per Stratification

ü

NotHispanicOrLatino

EligiblePopulation

For each Stratification

ü

AskedButNoAnswer

Denominator

For each Stratification

Unknown

Numerator

For each Stratification

ü

Rate

\(Percent\)

ü

Rules for Allowable Adjustments of HEDIS

The “Rules for Allowable Adjustments of HEDIS” \(the “Rules”\) describe how NCQA’s HEDIS measure specifications can be adjusted for other populations, if applicable\. The Rules, reviewed and approved by NCQA measure experts, provide for expanded use of HEDIS measures without changing their clinical intent\. 

__Adjusted HEDIS measures may not be used for HEDIS health plan reporting*\. *__

### Rules for Allowable Adjustments of Controlling High Blood Pressure

__NONCLINICAL COMPONENTS__

__Eligible Population__

__Adjustments Allowed \(Yes/No\)__

__Notes__

Product lines

Yes

Using product line criteria is not required\. Including any product line, combining product lines or not including product line criteria is allowed\.

Ages

Yes, with limits

Age determination dates may be changed \(e\.g\., select, “age as of June 30”\)\. 

The denominator age may be changed if the range is within the specified age range \(ages 18–85 years\)\. 

The denominator age may not be expanded\.

Continuous enrollment, allowable gap, anchor date

Yes

Organizations are not required to use enrollment criteria; adjustments are allowed\.

Benefit

Yes

Organizations are not required to use enrollment criteria; adjustments are allowed\.

Other

Yes

Organizations may use additional eligible population criteria to focus on an area of interest defined by gender, race, ethnicity, socioeconomic or sociodemographic characteristics, geographic region or another characteristic\. 

__CLINICAL COMPONENTS__

__Eligible Population__

__Adjustments Allowed \(Yes/No\)__

__Notes__

Event/diagnosis

No

Only events that contain \(or map to\) codes in the value sets may be used to identify visits\. Value sets and logic may not be changed\.

__Denominator Exclusions__

__Adjustments Allowed \(Yes/No\)__

__Notes__

Required exclusions

Yes, with limits

Apply required exclusions according to specified value sets\.

The hospice, deceased member, palliative care, I\-SNP, LTI, frailty and advanced illness exclusions are not required\. Refer to *Exclusions* in the *Guidelines for the Rules for Allowable Adjustments\.*

__Numerator Criteria__

__Adjustments Allowed \(Yes/No\)__

__Notes__

Adequate Control of Blood Pressure

No

Value sets and logic may not be changed\.

