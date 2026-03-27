## <a id="Blood_Pressure_Control_Diabetes_BPD"></a><a id="_Toc74816296"></a><a id="_Toc171402986"></a>Blood Pressure Control for Patients With Diabetes \(BPD\)

Summary of Changes to HEDIS MY 2025

- No changes to this measure\.

Description

The percentage of members 18–75 years of age with diabetes \(types 1 and 2\) whose blood pressure \(BP\) was adequately controlled \(<140/90 mm Hg\) during the measurement year\.

Eligible Population 

Product lines

Commercial, Medicaid, Medicare \(report each product line separately\)\.

Ages

18–75 years as of December 31 of the measurement year\.

Continuous enrollment

The measurement year\. 

Allowable gap

No more than one gap in enrollment of up to 45 days during the measurement year\. To determine continuous enrollment for a Medicaid beneficiary for whom enrollment is verified monthly, the member may not have more than a 1\-month gap in coverage \(e\.g\., a member whose coverage lapses for 2 months \[60 days\] is not considered continuously enrolled\)\. 

Anchor date

December 31 of the measurement year\. 

Benefit

Medical\.

Event/diagnosis

There are two ways to identify members with diabetes: by claim/encounter data and by pharmacy data\. The organization must use both methods to identify the eligible population, but a member only needs to be identified by one method to be included in the measure\. Members may be identified as having diabetes during the measurement year or the year prior to the measurement year\.

*Claim/encounter data\.* Members who had at least two diagnoses of diabetes \(Diabetes Value Set\) on different dates of service during the measurement year or the year prior to the measurement year\. Do not include laboratory claims \(claims with POS code 81\)\.  

*Pharmacy data\.* Members who were dispensed insulin or hypoglycemics/ antihyperglycemics during the measurement year or the year prior to the measurement year \(Diabetes Medications List\) and have at least one diagnosis of diabetes \(Diabetes Value Set\) during the measurement year or the year prior to the measurement year\. Do not include laboratory claims \(claims with POS code 81\)\. 

Diabetes Medications

Description

Prescription

Alpha\-glucosidase inhibitors

- Acarbose

- Miglitol

Amylin analogs

- Pramlintide 

Antidiabetic combinations

- Alogliptin\-metformin 
- Alogliptin\-pioglitazone
- Canagliflozin\-metformin
- Dapagliflozin\-metformin
- Dapagliflozin\-saxagliptin
- Empagliflozin\-linagliptin
- Empagliflozin\-linagliptin\-metformin

- Empagliflozin\-metformin
- Ertugliflozin\-metformin
- Ertugliflozin\-sitagliptin
- Glimepiride\-pioglitazone
- Glipizide\-metformin
- Glyburide\-metformin
- Linagliptin\-metformin

- Metformin\-pioglitazone
- Metformin\-repaglinide
- Metformin\-rosiglitazone
- Metformin\-saxagliptin
- Metformin\-sitagliptin

Insulin

- Insulin aspart 
- Insulin aspart\-insulin aspart protamine
- Insulin degludec 
- Insulin degludec\-liraglutide
- Insulin detemir
- Insulin glargine
- Insulin glargine\-lixisenatide

- Insulin glulisine
- Insulin isophane human
- Insulin isophane\-insulin regular
- Insulin lispro
- Insulin lispro\-insulin lispro protamine 
- Insulin regular human
- Insulin human inhaled

Meglitinides

- Nateglinide

- Repaglinide

Biguanides

- Metformin

Glucagon\-like peptide\-1 \(GLP1\) agonists 

- Albiglutide
- Dulaglutide
- Exenatide

- Liraglutide
- Lixisenatide
- Semaglutide

- Tirzepatide

Sodium glucose cotransporter 2 \(SGLT2\) inhibitor

- Canagliflozin
- Dapagliflozin

- Empagliflozin
- Ertugliflozin

Sulfonylureas

- Chlorpropamide
- Glimepiride

- Glipizide 
- Glyburide

- Tolazamide 
- Tolbutamide

Thiazolidinediones

- Pioglitazone

- Rosiglitazone

Dipeptidyl peptidase\-4   
\(DDP\-4\) inhibitors

- Alogliptin
- Linagliptin

- Saxagliptin 
- Sitagliptin

Required exclusions

Exclude members who meet any of the following criteria:

- Members who use hospice services \(Hospice Encounter Value Set; Hospice Intervention Value Set\) or elect to use a hospice benefit any time during the measurement year\. Organizations that use the Monthly Membership Detail Data File to identify these members must use only the run date of the file to determine if the member elected to use a hospice benefit during the measurement year\. 
- Members who die any time during the measurement year\. 
- Members receiving palliative care \(Palliative Care Assessment Value Set; Palliative Care Encounter Value Set; Palliative Care Intervention Value Set;\) any time during the measurement year\.
- Members who had an encounter for palliative care \(ICD\-10\-CM code Z51\.5\) any time during the measurement year\. Do not include laboratory claims \(claims with POS code 81\)\.
- Medicare members 66 years of age and older as of December 31 of the measurement year who meet either of the following:
- Enrolled in an Institutional SNP \(I\-SNP\) any time during the measurement year\.
- Living long\-term in an institution any time during the measurement year as identified by the LTI flag in the Monthly Membership Detail Data File\. Use the run date of the file to determine if a member had an LTI flag during the measurement year\.
- Members 66 years of age and older as of December 31 of the measurement year \(all product lines\) with frailty __and__ advanced illness\. Members must meet __both__ frailty and advanced illness criteria to be excluded: 

1\.	__Frailty\.__ At least two indications of frailty \(Frailty Device Value Set; Frailty Diagnosis Value Set; Frailty Encounter Value Set; Frailty Symptom Value Set\) with different dates of service during the measurement year\. Do not include laboratory claims \(claims with POS code 81\)\.

2\.	__Advanced Illness\.__ Either of the following during the measurement year or the year prior to the measurement year:

- Advanced illness \(Advanced Illness Value Set\) on at least two different dates of service\. Do not include laboratory claims \(claims with POS code 81\)\.
- Dispensed dementia medication \(Dementia Medications List\)\.

__*Dementia Medications*__

Description

Prescription

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

The member is numerator compliant if the BP is <140/90 mm Hg\. The member is not compliant if the BP is ≥140/90 mm Hg, if there is no BP reading during the measurement year or if the reading is incomplete \(e\.g\., the systolic or diastolic level is missing\)\. If there are multiple BPs on the same date of service, use the lowest systolic and lowest diastolic BP on that date as the representative BP\. 

If the most recent BP was identified based on a CPT Category II code \(Systolic and Diastolic Result Value Set\), use the following to determine compliance:

- Systolic Compliant: Systolic Less Than 140 Value Set\.
- Systolic Not Compliant: CPT\-CAT\-II code 3077F\.
- Diastolic Compliant: Diastolic Less Than 90 Value Set\.
- Diastolic Not Compliant: CPT\-CAT\-II code 3080F\.

Hybrid Specification

Denominator

A systematic sample drawn from the eligible population\. 

Organizations that use the Hybrid Method to report the Glycemic Status Assessment for Patients With Diabetes \(GSD\) and Blood Pressure Control for Patients With Diabetes \(BPD\) measures may use the same sample for both measures\. If the same sample is used for both measures, the organization must first take the inverse of the Glycemic Status >9\.0% rate \(100 minus the Glycemic Status >9\.0% rate\) before reducing the sample\. 

Organizations may reduce the sample size based on the current year’s administrative rate or the prior year’s audited, product line\-specific rate for the lowest rate of all GSD indicators and the BPD measure\.

If separate samples are used for the GSD and BPD measures, organizations may reduce the sample based on the product line\-specific current measurement year’s administrative rate or the prior year’s audited, product line\-specific rate for the measure\. 

Refer to the *Guidelines for Calculations and Sampling* for information on reducing sample size\.

Numerator

The *most recent* BP level \(taken during the measurement year\) is <140/90 mm Hg, as documented through administrative data or medical record review\.

*Administrative*

Refer to *Administrative Specification* to identify positive numerator hits from administrative data\.

*Medical record*

Organizations that use the same sample for the GSD and BPD measures may use the medical record from which it abstracts data for the GSD measure\. If the organization uses separate samples for the GSD and BPD measures, it should use the medical record of the provider that manages the member’s diabetes\. If that medical record does not contain a BP, the organization may use the medical record of another PCP or specialist from whom the member receives care\.

Identify the most recent BP reading noted during the measurement year\. 

Do not include BP readings:

- Taken during an acute inpatient stay or an ED visit\.
- Taken on the same day as a diagnostic test or diagnostic or therapeutic procedure that requires a change in diet or change in medication on or one day before the day of the test or procedure, with the exception of fasting blood tests\.
- Taken by the member using a non\-digital device such as with a manual blood pressure cuff and a stethoscope\.

Identify the lowest systolic and lowest diastolic BP reading from the most recent BP notation in the medical record\. If multiple readings were recorded for a single date, use the lowest systolic and lowest diastolic BP on that date as the representative BP\. The systolic and diastolic results do not need to be from the same reading\.

BP readings taken by the member and documented in the member’s medical record are eligible for use in reporting \(provided the BP does not meet any exclusion criteria\)\. There is no requirement that there be evidence the BP was collected by a PCP or specialist\. 

The member is not compliant if the BP reading is ≥140/90 mm Hg or is missing, if there is no BP reading during the measurement year or if the reading is incomplete \(i\.e\., the systolic or diastolic level is missing\)\. “Unknown” is not considered a result/finding\.

Ranges and thresholds do not meet criteria for this measure\. A distinct numeric result for both the systolic and diastolic BP reading is required for numerator compliance\. A BP documented as an “average BP” \(e\.g\., “average BP: 139/70”\) is eligible for use\.

*Note *

- *If a combination of administrative, supplemental or hybrid data are used, the most recent BP result must be used, regardless of data source\.*
- *When excluding BP readings from the numerator, the intent is to identify diagnostic or therapeutic procedures that require a medication regimen, a change in diet or a change in medication\. For example \(this list is for reference only and is not exhaustive\):*
- *A colonoscopy requires a change in diet \(NPO on the day of procedure\) and a medication change \(a medication is taken to prep the colon\)\. *
- *Dialysis, infusions and chemotherapy \(including oral chemotherapy\) are all therapeutic procedures that require a medication regimen\. *
- *A nebulizer treatment with albuterol is considered a therapeutic procedure that requires a medication regimen \(the albuterol\)\. *
- *A patient forgetting to take regular medications on the day of the procedure is not considered a required change in medication, and therefore the BP reading is eligible\.*
- *BP readings taken on the same day that the patient receives a common low\-intensity or preventive procedure are eligible for use\. For example, the following procedures are considered common low\-intensity or preventive procedures \(this list is for reference only and is not exhaustive\):*
- *Vaccinations\.*
- *Injections \(e\.g\., allergy, vitamin B\-12, insulin, steroid, Toradol, Depo\-Provera, testosterone, lidocaine\)\.*
- *TB test\.*
- *IUD insertion\.*
- *Eye exam with dilating agents\.*
- *Wart or mole removal\.*

__Data Elements for Reporting__

Organizations that submit HEDIS data to NCQA must provide the following data elements\.

__*Table BPD\-1/2/3: Data Elements for Blood Pressure Control for Patients With Diabetes*__

__Metric__

__Data Element __

__Reporting Instructions__

__A__

BPUnder140Over90

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

Rules for Allowable Adjustments of HEDIS

The “Rules for Allowable Adjustments of HEDIS” \(the “Rules”\) describe how NCQA’s HEDIS measure specifications can be adjusted for other populations, if applicable\. The Rules, reviewed and approved by NCQA measure experts, provide for expanded use of HEDIS measures without changing their clinical intent\.

__Adjusted HEDIS measures may not be used for HEDIS health plan reporting\. __

### Rules for Allowable Adjustments of Blood Pressure Control for Patients With Diabetes

__NONCLINICAL COMPONENTS__

__Eligible Population__

__Adjustments Allowed \(Yes/No\)__

__Notes__

Product lines

Yes

Organizations are not required to use product line criteria; product lines may be combined and all \(or no\) product line criteria may be used\.

Ages

Yes, with limits

Age determination dates may be changed \(e\.g\., select, “age as of June 30”\)\.

Changing denominator age range is allowed within a specified age range \(ages 18–75 years\)\. 

The denominator age may not be expanded\.

Continuous enrollment, allowable gap, anchor date

Yes

Organizations are not required to use enrollment criteria; adjustments are allowed\.

Benefits

Yes

Organizations are not required to use a benefit; adjustments are allowed\.

Other

Yes

Organizations may use additional eligible population criteria to focus on an area of interest defined by gender, race, ethnicity, socioeconomic or sociodemographic characteristics, geographic region or another characteristic\. 

__CLINICAL COMPONENTS__

__Eligible Population__

__Adjustments Allowed \(Yes/No\)__

__Notes__

Event/diagnosis

No

Only events or diagnoses that contain \(or map to\) codes in the medication lists and value sets may be used to identify visits\. Medication lists, value sets and logic may not be changed\.

__Denominator Exclusions__

__Adjustments Allowed \(Yes/No\)__

__Notes__

Required exclusions

Yes

The hospice, deceased member, palliative care, I\-SNP, LTI, frailty and advanced illness exclusions are not required\. Refer to *Exclusions* in the *Guidelines for the Rules for Allowable Adjustments*\.

__Numerator Criteria__

__Adjustments Allowed \(Yes/No\)__

__Notes__

Blood Pressure Control

No

Value sets and logic may not be changed\.

