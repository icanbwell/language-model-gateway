## <a id="Use_of_Imaging_Back_Pain_LBP"></a><a id="_Toc400546133"></a><a id="_Toc74825577"></a><a id="_Toc171403013"></a><a id="LBP"></a>Use of Imaging Studies for Low Back Pain \(LBP\)

Summary of Changes to HEDIS MY 2025

- Revised step 1 of the event/diagnosis to no longer require a diagnosis of uncomplicated low back pain to be in conjunction with a specific visit type\.
- Added a diagnosis of osteoporosis to required exclusions\.
- *Technical Update:* Revised the event/diagnosis\. 

Description

The percentage of members 18–75 years of age with a principal diagnosis of low back pain who did not have an imaging study \(plain X\-ray, MRI, CT scan\) within 28 days of the diagnosis\. 

Calculation

The measure is reported as an inverted rate \[1–\(numerator/eligible population\)\]\. A higher score indicates appropriate treatment of low back pain \(i\.e\., the proportion for whom imaging studies did not occur\)\. 

Definitions

Intake period

January 1–December 3 of the measurement year\. The intake period is used to identify the first eligible encounter with a principal diagnosis of low back pain\.

IESD

Index episode start date\. The earliest date of service for an eligible encounter during the intake period with a principal diagnosis of low back pain\.

Negative diagnosis history

A period of 180 days prior to the IESD when the member had no claims/ encounters with any diagnosis of low back pain\.

Eligible Population

Product line

Commercial, Medicaid, Medicare \(report each product line separately\)\. 

Ages

18–75 years as of December 31 of the measurement year\. 

Report two age stratifications and a total rate:

- 18–64\.
- 65–75\.
- Total\.

The total is the sum of the age stratifications\.

Continuous enrollment

180 days prior to the IESD through 28 days after the IESD\. 

Allowable gap

None\.

Anchor date

IESD\.

Benefit

Medical\. 

Event/diagnosis

Follow the steps below to identify the eligible population\. 

*Step 1*

Identify members with a principal diagnosis of uncomplicated low back pain \(Uncomplicated Low Back Pain Value Set\) during the intake period\. Do not include visits that result in an inpatient stay \(Inpatient Stay Value Set\)\. Do not include inpatient stays \(Inpatient Stay Value Set\) or visits that result in an inpatient stay \(Inpatient Stay Value Set\)\. Do not include laboratory claims \(claims with POS code 81\)\.

*Step 2*

Determine the IESD\. For each member identified in step 1, determine the earliest episode of low back pain\. If the member had more than one encounter, include only the first encounter\.

*Step 3*

Test for negative diagnosis history\. Remove members with a diagnosis of uncomplicated low back pain \(Uncomplicated Low Back Pain Value Set\) during the 180 days prior to the IESD\. Do not include laboratory claims \(claims with POS code 81\)\.

*Step 4*

Calculate continuous enrollment\. Members must be continuously enrolled for 180 days prior to the IESD through 28 days after the IESD\.

Required exclusions

Exclude members who meet any of the following criteria: 

- Cancer, HIV, history of organ transplant, osteoporosis or spondylopathy \(Diagnosis History That May Warrant Imaging Value Set\) any time during the member’s history through 28 days after the IESD\. Do not include laboratory claims \(claims with POS code 81\)\. 
- Organ transplant, lumbar surgery or medication treatment for osteoporosis \(Procedure History That May Warrant Imaging Value Set\) any time during the member’s history through 28 days after the IESD\.
- IV drug abuse, neurologic impairment or spinal infection \(Recent Diagnoses That May Warrant Imaging Value Set\) any time during the 365 days prior to the IESD through 28 days after the IESD\. Do not include laboratory claims \(claims with POS code 81\)\.
- Trauma or a fragility fracture \(Recent Injuries That May Warrant Imaging Value Set\) any time during the 90 days prior to the IESD through 28 days after the IESD\. Do not include laboratory claims \(claims with POS   
code 81\)\.
- *Prolonged use of corticosteroids\. *90 consecutive days of corticosteroid treatment any time during the 366\-day period that begins 365 days prior to the IESD and ends on the IESD\. 

To identify consecutive treatment days, identify calendar days covered by at least one dispensed corticosteroid \(Corticosteroid Medications List\)\. For overlapping prescriptions and multiple prescriptions on the same day assume the member started taking the second prescription after exhausting the first prescription\. For example, if a member had a 30\-days prescription dispensed on June 1 and a 30\-days prescription dispensed on June 26, there are 60 covered calendar days \(June 1–July 30\)\.

Count only medications dispensed during the 365 days prior to and including the IESD\. When identifying consecutive treatment days, do not count days supply that extend beyond the IESD\. For example, if a member had a 90\-days prescription dispensed on the IESD, there is one covered calendar day \(the IESD\)\.

No gaps are allowed\.

### Corticosteroid Medications

__Description__

__Prescription__

Corticosteroid

- Hydrocortisone
- Cortisone
- Prednisone
- Prednisolone

- Methylprednisolone
- Triamcinolone
- Dexamethasone
- Betamethasone/Betamethasone acetate

- A dispensed prescription to treat osteoporosis \(Osteoporosis Medications List\) any time during the member’s history through 28 days after the IESD\.

### Osteoporosis Medications

__Description__

__Prescription__

Bisphosphonates

- Alendronate
- Alendronate\-cholecalciferol
- Ibandronate

- Risedronate
- Zoledronic acid

Other agents

- Abaloparatide
- Denosumab
- Raloxifene

- Romosozumab
- Teriparatide

- Members receiving palliative care \(Palliative Care Assessment Value Set; Palliative Care Encounter Value Set; Palliative Care Intervention Value Set\) any time during the measurement year\.
- Members who had an encounter for palliative care \(ICD\-10\-CM code Z51\.5\) any time during the measurement year\. Do not include laboratory claims \(claims with POS code 81\)\.
- Members who use hospice services \(Hospice Encounter Value Set; Hospice Intervention Value Set\) or elect to use a hospice benefit any time during the measurement year\. Organizations that use the Monthly Membership Detail Data File to identify these members must use only the run date of the file to determine if the member elected to use a hospice benefit during the measurement year\. 
- Members who die any time during the measurement year\.
- Members 66 years of age and older as of December 31 of the measurement year \(all product lines\) with frailty __and __advanced illness\. Members must meet __both __frailty and advanced illness criteria to be excluded:

1. __Frailty\.__ At least two indications of frailty \(Frailty Device Value Set; Frailty Diagnosis Value Set; Frailty Encounter Value Set; Frailty Symptom Value Set\) with different dates of service during the measurement year\. Do not include laboratory claims \(claims with POS code 81\)\.

2\.	__Advanced Illness\.__ Either of the following during the measurement year or the year prior to the measurement year:

- Advanced illness \(Advanced Illness Value Set\) on at least two different dates of service\. Do not include laboratory claims \(claims with POS   
code 81\)\.
- Dispensed dementia medication \(Dementia Medication List\)\. 

### Dementia Medications

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

An imaging study \(Imaging Study Value Set\) with a diagnosis of uncomplicated low back pain \(Uncomplicated Low Back Pain Value Set\) on the IESD or in the 28 days following the IESD\. 

*Note*

- *Although denied claims are not included when assessing the numerator, all claims \(paid, suspended, pending and denied\) must be included when identifying the eligible population\.*
- *Do not include supplemental data when identifying the eligible population or assessing the numerator\. Supplemental data can be used for only required exclusions for this measure\. *

__Data Elements for Reporting __

Organizations that submit HEDIS data to NCQA must provide the following data elements\.

__*Table LBP\-1/2/3: Data Elements for Use of Imaging Studies for Low Back Pain *__

Metric

Age

Data Element

Reporting Instructions

LowBackPainImaging

18\-64

EligiblePopulation 

For each Stratification

65\-75

ExclusionAdminRequired

For each Stratification

Total

NumeratorByAdmin

For each Stratification

Rate

\(Percent\)

Rules for Allowable Adjustments of HEDIS

The “Rules for Allowable Adjustments of HEDIS” \(the “Rules”\) describe how NCQA’s HEDIS measure specifications can be adjusted for other populations, if applicable\. The Rules, reviewed and approved by NCQA measure experts, provide for expanded use of HEDIS measures without changing their clinical intent\. 

__Adjusted HEDIS measures may not be used for HEDIS health plan reporting\. __

### <a id="_Hlk1052665"></a>Rules for Allowable Adjustments of Use of Imaging Studies for Low Back Pain

__NONCLINICAL COMPONENTS__

__Eligible Population__

__Adjustments Allowed \(Yes/No\)__

__Notes__

Product lines

Yes

Organizations are not required to use product line criteria; product lines may be combined, and all \(or no\) product line criteria may be used\.

Ages

Yes, with limits

The age determination dates may be changed \(e\.g\., select, “age as of June 30”\)\.

Changing the denominator age range is allowed if the limits are within the specified age range \(18–50 years\)\. 

The denominator age may not be expanded\.

Continuous enrollment, allowable gap, anchor date

Yes

Organizations are not required to use enrollment criteria; adjustments are allowed\.

__*Note:*__* Changes to *the*se criteria can affect how *the* event/diagnosis will be calculated using *the* intake period, IESD, negative diagnosis history\.*

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

Only diagnoses that contain \(or map to\) codes in the value sets may be used\. The value sets and logic may not be changed\.

__Denominator Exclusions__

__Adjustments Allowed \(Yes/No\)__

__Notes__

Required exclusions

Yes, with limits

Apply required exclusions according to specified medication lists and value sets\.

The hospice, deceased member and palliative care exclusions are not required\. Refer to *Exclusions* in the *Guidelines for the Rules for Allowable Adjustments*\.

__Numerator Criteria__

__Adjustments Allowed \(Yes/No\)__

__Notes__

Imaging Study

Yes, with limits

Value sets and logic may not be changed\.

Organizations may include denied claims to calculate the numerator\.

