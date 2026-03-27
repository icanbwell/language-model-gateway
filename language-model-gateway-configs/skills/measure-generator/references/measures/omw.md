## <a id="Osteoporosis_Management_Fracture_OMW"></a><a id="_Toc400546132"></a><a id="_Toc74816301"></a><a id="_Toc171402991"></a><a id="OMW"></a>Osteoporosis Management in Women Who Had a Fracture \(OMW\)

Summary of Changes to HEDIS MY 2025

- No changes to this measure\.
- *Technical Update:* Revised the event/diagnosis\. 

Description

The percentage of women 67–85 years of age who suffered a fracture and who had either a bone mineral density \(BMD\) test or prescription for a drug to treat osteoporosis in the 180 days \(6 months\) after the fracture\. 

Definitions

Intake period

July 1 of the year prior to the measurement year to June 30 of the measurement year\. The intake period is used to capture the first fracture\.

Episode date

The date of service for an eligible encounter during the intake period with a diagnosis of fracture\. 

For an outpatient or ED visit, *the episode date is the date of service\.*

For an inpatient stay, *the episode date is the date of discharge\. *

For direct transfers, *the episode date is the discharge date from the last admission\.*

IESD

Index episode start date\. The earliest episode date during the intake period that meets all eligible population criteria\. 

Direct transfer

A __direct transfer__ is when the discharge date from the first inpatient setting precedes the admission date to a second inpatient setting by one calendar day or less\. For example:

- An inpatient discharge on June 1, followed by an admission to another inpatient setting on June 1, *is a direct transfer\.*
- An inpatient discharge on June 1, followed by an admission to an inpatient setting on June 2, *is a direct transfer\.*
- An inpatient discharge on June 1, followed by an admission to another inpatient setting on June 3, *is not a direct transfer;* these are two distinct inpatient stays\.

Use the following method to identify admissions to and discharges from inpatient settings\.

1\.	Identify all acute and nonacute inpatient stays \(Inpatient Stay Value Set\)\.

2\.	Identify the admission and discharge dates for the stay\.

__Note: __The direct transfer does not require a fracture diagnosis\.

Active prescription

A prescription is considered active if the “days supply” indicated on the date when the member was dispensed the prescription is the number of days or more between that date and the relevant service date\.

Eligible Population

Product line

Medicare\.

Age

Women 67–85 years as of December 31 of the measurement year\. 

Continuous enrollment

365 days before the episode date through 180 days after the episode date\.

Allowable gap

No more than one gap in enrollment of up to 45 days during the continuous enrollment period\.

Anchor date

Episode date\.

Benefits

Medical and pharmacy\. 

Event/diagnosis

Follow the steps below to identify the eligible population\.

*Step 1*

Identify all members who had either of the following during the intake period\.

- An outpatient visit or ED visit \(Outpatient and ED Value Set\) for a fracture \(Fractures Value Set\)\. 
- Do not include visits that result in an inpatient stay \(Inpatient Stay Value Set\)\. 
- An acute or nonacute inpatient discharge with a fracture \(Fractures Value Set\) on the discharge claim\. To identify acute and nonacute inpatient discharges:

1\.	Identify all acute and nonacute inpatient stays \(Inpatient Stay Value Set\)\.

2\.	Identify the discharge date for the stay\.

If the member had more than one fracture, identify all fractures and assess eligibility in steps 2–4\.

*Step 2*

Test for negative diagnosis history\. Remove episodes where the member had a fracture \(Fractures Value Set\) during the 60\-day period prior to the episode date\. Do not include laboratory claims \(claims with POS code 81\)\.

Test for negative diagnosis history\. Remove episodes where either of the following occurred during the 60\-day period prior to the episode date:

- An outpatient visit, ED visit, telephone visit, e\-visit or virtual check\-in \(Outpatient, ED and Telehealth Value Set\) for a fracture \(Fractures Value Set\)\.
- Do not include visits that result in an inpatient stay \(Inpatient Stay Value Set\)\.
- An acute or nonacute inpatient discharge with a fracture \(Fractures Value Set\) on the discharge claim\. To identify acute and nonacute inpatient discharges: 

1\.	Identify all acute and nonacute inpatient stays \(Inpatient Stay Value Set\)\. 

2\.	Identify the discharge date for the stay\. 

*For an acute or nonacute inpatient episode, *use the date of admission to determine the 60\-day period\. 

*For episodes that were direct transfers, *use the first admission to determine the negative diagnosis history\.

*For inpatient stay episodes* that were a result of an outpatient or ED visit, use the date of the outpatient or ED visit to determine negative diagnosis history\.

*Step 3*

Calculate continuous enrollment\. Members must be continuously enrolled during the 365 days prior to the episode date through 180 days post\-episode date\.

*Step 4*

Remove episode dates where any of the following are met:

- Members who had a BMD test \(Bone Mineral Density Tests Value Set\) during the 730 days prior to the episode date\. 
- Members who had a claim/encounter for osteoporosis therapy \(Osteoporosis Medication Therapy Value Set\) during the 365 days prior to the episode date\.
- Members who received a dispensed prescription or had an active prescription to treat osteoporosis \(Osteoporosis Medications List\) during the 365 days prior to the episode date\. 

*For an acute or nonacute inpatient event,* use the date of admission to identify the days prior to the episode date\. 

*For direct transfers*, use the first admission date to identify the days prior to the episode date\.

*For outpatient and ED visits that result in an inpatient stay*, use the date of the outpatient or ED visit to identify the days prior to the episode date\. 

*Step 5*

Select the IESD\. The measure examines the earliest eligible episode per member that meets the criteria above\.

Required exclusions

- Members who use hospice services \(Hospice Encounter Value Set; Hospice Intervention Value Set\) or elect to use a hospice benefit any time during the measurement year\. Organizations that use the Monthly Membership Detail Data File to identify these members must use only the run date of the file to determine if the member elected to use a hospice benefit during the measurement year\. 
- Members who die any time during the measurement year\. 
- Members who received palliative care \(Palliative Care Assessment Value Set; Palliative Care Encounter Value Set; Palliative Care Intervention Value Set\) any time during the intake period through the end of the measurement year\.
- Members who had an encounter for palliative care \(ICD\-10\-CM code Z51\.5\) any time during the intake period through the end of the measurement year\. Do not include laboratory claims \(claims with   
POS code 81\)\.
- Members 67 years of age and older as of December 31 of the measurement year who meet either of the following:
- Enrolled in an Institutional SNP \(I\-SNP\) any time during the intake period through the end of the measurement year\.
- Living long\-term in an institution any time during the intake period through the end of the measurement year as identified by the LTI flag in the Monthly Membership Detail Data File\. Use the run date of the file to determine if a member had an LTI flag during the intake period through the end of the measurement year\.
- Members 67–80 years of age as of December 31 of the measurement year \(all product lines\) with frailty __and__ advanced illness\. Members must meet __both__ frailty and advanced illness criteria to be excluded: 

1\.	__Frailty\.__ At least two indications of frailty \(Frailty Device Value Set; Frailty Diagnosis Value Set; Frailty Encounter Value Set; Frailty Symptom Value Set\) with different dates of service during the intake period through the end of the measurement year\. Do not include laboratory claims \(claims with POS code 81\)\. 

2\.	__Advanced Illness\.__ Either of the following during the measurement year or the year prior to the measurement year: 

- Advanced illness \(Advanced Illness Value Set\) on at least two different dates of service\. Do not include laboratory claims \(claims with POS code 81\)\.
- Dispensed dementia medication \(Dementia Medications List\)\.
- Members 81 years of age and older as of December 31 of the measurement year \(all product lines\) with at least two indications of frailty \(Frailty Device Value Set; Frailty Diagnosis Value Set; Frailty Encounter Value Set; Frailty Symptom Value Set\) with different dates of service during the intake period through the end of the measurement year\. Do not include laboratory claims \(claims with POS code 81\)\.

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

Appropriate testing or treatment for osteoporosis after the fracture defined by any of the following criteria: 

- A BMD test \(Bone Mineral Density Tests Value Set\), in any setting, on the IESD or in the 180\-day period after the IESD\. 
- If the IESD was an inpatient stay, a BMD test \(Bone Mineral Density Tests Value Set\) during the inpatient stay\. 
- Osteoporosis therapy \(Osteoporosis Medication Therapy Value Set\) on the IESD or in the 180\-day period after the IESD\.
- If the IESD was an inpatient stay, long\-acting osteoporosis therapy \(Long Acting Osteoporosis Medications Value Set\) during the inpatient stay\.
- A dispensed prescription to treat osteoporosis \(Osteoporosis Medications List\) on the IESD or in the 180\-day period after the IESD\.

Osteoporosis Medications

Description

Prescription

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

*Note *

- *Fractures of finger, toe, face and skull are not included in this measure\.*

Data Elements for Reporting 

Organizations that submit HEDIS data to NCQA must provide the following data elements\. 

__*Table OMW\-3: Data Elements for Osteoporosis Management in Women Who Had a Fracture*__

__Metric__

__Data Element__

__Reporting Instructions__

OsteoporosisManagementWomen

Benefit

Metadata

EligiblePopulation

Report once

ExclusionAdminRequired

Report once

NumeratorByAdmin

Report once

NumeratorBySupplemental

Report once

Rate

\(Percent\)

Rules for Allowable Adjustments of HEDIS

The “Rules for Allowable Adjustments of HEDIS” \(the “Rules”\) describe how NCQA’s HEDIS measure specifications can be adjusted for other populations, if applicable\. The Rules, reviewed and approved by NCQA measure experts, provide for expanded use of HEDIS measures without changing their clinical intent\. 

__Adjusted HEDIS measures may not be used for HEDIS health plan reporting\. __

### Rules for Allowable Adjustments of Osteoporosis Management in Women Who Had a Fracture

__NONCLINICAL COMPONENTS__

__Eligible Population__

__Adjustments Allowed \(Yes/No\)__

__Notes__

Product lines

Yes

Organizations are not required to use product line criteria; product lines may be combined and all \(or no\) product line criteria may be used\.

Ages

Yes, with limits

The age determination dates may be changed \(e\.g\., select, “age as of June 30”\)\.

Changing the denominator age range is allowed between 50\-85 years of age\.

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

Only events or diagnoses that contain \(or map to\) codes in the value sets may be used to identify visits\. Value sets and logic may not be changed\. 

__Denominator Exclusions__

__Adjustments Allowed \(Yes/No\)__

__Notes__

Required exclusions

Yes

The palliative care, deceased member, hospice, I\-SNP, LTI, frailty and advanced illness exclusions are not required\. Refer to *Exclusions *in the *Guidelines for the Rules for Allowable Adjustments\.* 

__Numerator Criteria__

__Adjustments Allowed \(Yes/No\)__

__Notes__

Appropriate Testing or Treatment for Osteoporosis

No

Medication lists, value sets and logic may not be changed\.

