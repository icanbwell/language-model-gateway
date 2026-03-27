## <a id="Cardiac_Rehabilitation_CRE"></a><a id="_Toc74815067"></a><a id="_Toc171402983"></a>Cardiac Rehabilitation \(CRE\)

<a id="CDC"></a>Summary of Changes to HEDIS MY 2025

- No changes to this measure\.

Description

The percentage of members 18 years and older who attended cardiac rehabilitation following a qualifying cardiac event, including myocardial infarction, percutaneous coronary intervention, coronary artery bypass grafting, heart and heart/lung transplantation or heart valve repair/replacement\. Four rates are reported:

- *Initiation*\. The percentage of members who attended 2 or more sessions of cardiac rehabilitation within 30 days after a qualifying event\.
- *Engagement 1*\. The percentage of members who attended 12 or more sessions of cardiac rehabilitation within 90 days after a qualifying event\.
- *Engagement 2*\. The percentage of members who attended 24 or more sessions of cardiac rehabilitation within 180 days after a qualifying event\.
- *Achievement*\. <a id="_Hlk38872465"></a>The percentage of members who attended 36 or more sessions of cardiac rehabilitation within 180 days after a qualifying event\.

Definitions

Intake period

July 1 of the year prior to the measurement year to June 30 of the measurement year\. 

Episode date

The most recent cardiac event during the intake period, including myocardial infarction \(MI\), coronary artery bypass graft \(CABG\), percutaneous coronary intervention \(PCI\), heart or heart/lung transplant or heart valve repair/ replacement\.

For MI, CABG, heart or heart/lung transplant or heart valve repair/replacement, the episode date is the *date of discharge\.*

For PCI, the episode date is the *date of service*\. 

For inpatient claims, the episode date is the *date of discharge*\.

For direct transfers, the episode date is the *discharge date from the last admission\.*

Eligible Population

Product lines

Commercial, Medicaid, Medicare \(report each product line separately\)\.

Ages

18 years and older as of the episode date\. Report the following age stratifications and a total rate:

- 18–64 years\.
- 65 and older\.
- Total\.

The total is the sum of the age stratifications for each product line\.

Continuous enrollment

Episode date through the following 180 days\.

Allowable gap

None\.

Anchor date

Episode date\.

Benefits

Medical\.

Event/diagnosis

Follow the steps below to identify the eligible population\.

*Step 1*

Identify all members who had any of the following cardiac events during the intake period: 

- Discharged from an inpatient setting with any of the following on the discharge claim:
- MI \(MI Value Set\)\.
- CABG \(CABG Value Set; Percutaneous CABG Value Set\)\.
- Heart or heart/lung transplant \(Heart Transplant Value Set\)\. 
- Heart valve repair or replacement \(Heart Valve Repair or Replacement Value Set\)\. 

To identify discharges:

1\.	Identify all acute and nonacute inpatient stays \(Inpatient Stay Value Set\)\.

2\.	Identify the discharge date for the stay\.

- PCI\.* *Members who had PCI \(PCI Value Set; Other PCI Value Set\) in any setting\.

__*Step 2 *__

For each member identified in step 1, the episode date is the date of the most recent cardiac event\. If a member has more than one cardiac event that meets the event/diagnosis criteria, include only the most recent during the intake period\.

__*Step 3*__

Test for direct transfers\. For episodes with a direct transfer to an acute or nonacute setting for any diagnosis, the episode date is the discharge date from the last admission\.

A __direct transfer__ is when the discharge date from the first inpatient setting precedes the admission date to a second inpatient setting by 1 calendar day or less\. For example:

- An inpatient discharge on June 1, followed by an admission to another inpatient setting on June 1, *is a direct transfer\.*
- An inpatient discharge on June 1, followed by an admission to an inpatient setting on June 2, *is a direct transfer\.*
- An inpatient discharge on June 1, followed by an admission to another inpatient setting on June 3,* is not a direct transfer;* these are two distinct inpatient stays\.

Use the following method to identify admissions to and discharges from inpatient settings\.

1\.	Identify all acute and nonacute inpatient stays \(Inpatient Stay Value Set\)\.

2\.	Identify the admission and discharge dates for the stay\.

Exclude both the initial discharge and the direct transfer discharge if the last discharge occurs after June 30 of the measurement year\.

__Note: __The direct transfer does not require a cardiac event diagnosis\.

Required exclusions

Exclude members who meet any of the following criteria: 

- Discharged from an inpatient setting with any of the following on the discharge claim during the 180 days after the episode date:
- MI \(MI Value Set\)\.
- CABG \(CABG Value Set; Percutaneous CABG Value Set\)\.
- Heart or heart/lung transplant \(Heart Transplant Value Set\)\. 
- Heart valve repair or replacement \(Heart Valve Repair or Replacement Value Set\)\. 

To identify discharges:

1\.	Identify all acute and nonacute inpatient stays \(Inpatient Stay Value Set\)\.

2\.	Identify the discharge date for the stay\.

- PCI\.* *Members who had PCI \(PCI Value Set; Other PCI Value Set\), in any setting, during the 180 days after the episode date\.
- Members who use hospice services \(Hospice Encounter Value Set; Hospice Intervention Value Set\) or elect to use a hospice benefit any time during the measurement year\. Organizations that use the Monthly Membership Detail Data File to identify these members must use only the run date of the file to determine if the member elected to use a hospice benefit during the measurement year\. 
- Members who die any time during the measurement year\. 
- Members receiving palliative care \(Palliative Care Assessment Value Set; Palliative Care Encounter Value Set; Palliative Care Intervention Value Set\) any time during the intake period through the end of the measurement year\. 
- Members who had an encounter for palliative care \(ICD\-10\-CM code Z51\.5\) any time during the intake period through the end of the measurement year\. Do not include laboratory claims \(claims with   
POS code 81\)\.
- Medicare members 66 years of age and older as of December 31 of the measurement year who meet either of the following:
- Enrolled in an Institutional SNP \(I\-SNP\) any time during the intake period through the end of the measurement year\.

- Living long\-term in an institution any time during the intake period through the end of the measurement year as identified by the LTI flag in the Monthly Membership Detail Data File\. Use the run date of the file to determine if a member had an LTI flag during the intake period through the end of the measurement year\.
- Members 66–80 years of age as of December 31 of the measurement year \(all product lines\) with frailty __and__ advanced illness\. Members must meet __both__ frailty and advanced illness criteria to be excluded: 

1\.	__Frailty\.__ At least two indications of frailty \(Frailty Device Value Set; Frailty Diagnosis Value Set; Frailty Encounter Value Set; Frailty Symptom Value Set\) with different dates of service during the intake period through the end of the measurement year\. Do not include laboratory claims \(claims with POS code 81\)\.

2\.	__Advanced Illness\.__ Either of the following during the measurement year or the year prior to the measurement year: 

- Advanced illness \(Advanced Illness Value Set\) on at least two different dates of service\. Do not include laboratory claims \(claims with POS code 81\)\.
- Dispensed dementia medication \(Dementia Medications List\)\.
- Members 81 years of age and older as of December 31 of the measurement year \(all product lines\) with at least two indications of frailty \(Frailty Device Value Set; Frailty Diagnosis Value Set; Frailty Encounter Value Set; Frailty Symptom Value Set\) with different dates of service any time during the intake period through the end of the measurement year\. Do not include laboratory claims \(claims with POS code 81\)\.

### Dementia Medications

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

Numerators

*Initiation*

At least 2 sessions of cardiac rehabilitation \(Cardiac Rehabilitation Value Set\)__* *__on the episode date through 30 days after the episode date \(31 total days\) \(on the same or different dates of service\)\.

*Engagement 1*

At least 12 sessions of cardiac rehabilitation \(Cardiac Rehabilitation Value Set\) on the episode date through 90 days after the episode date \(91 total days\) \(on the same or different dates of service\)\. 

*Engagement 2*

At least 24 sessions of cardiac rehabilitation \(Cardiac Rehabilitation Value Set\) on the episode date through 180 days after the episode date \(181 total days\) \(on the same or different dates of service\)\.

*Achievement*

At least 36 sessions of cardiac rehabilitation \(Cardiac Rehabilitation Value Set\) on the episode date through 180 days after the episode date \(181 total days\) \(on the same or different dates of service\)\.

__Note:__ Count multiple cardiac rehabilitation sessions on the same date of service as multiple sessions\. For example, if a member has two different codes for cardiac rehabilitation on the same date of service \(or one code billed as two units\), count this as two sessions of cardiac rehabilitation\.

__Data Elements for Reporting __

Organizations that submit HEDIS data to NCQA must provide the following data elements\.

__*Table CRE\-1/2/3: Data Elements for Cardiac Rehabilitation*__

Metric

Age

Data Element

Reporting Instructions

Initiation

18\-64

EligiblePopulation 

For each Stratification, repeat per Metric

Engagement1

65\+

ExclusionAdminRequired

For each Stratification, repeat per Metric

Engagement2

Total

NumeratorByAdmin

For each Metric and Stratification

Achievement

NumeratorBySupplemental

For each Metric and Stratification

Rate

\(Percent\)

Rules for Allowable Adjustments of HEDIS

The “Rules for Allowable Adjustments of HEDIS” \(the “Rules”\) describe how NCQA’s HEDIS measure specifications can be adjusted for other populations, if applicable\. The Rules, reviewed and approved by NCQA measure experts, provide for expanded use of HEDIS measures without changing their clinical intent\. 

__Adjusted HEDIS measures may not be used for HEDIS health plan reporting\.__

### Rules for Allowable Adjustments of Cardiac Rehabilitation

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

The denominator age may be changed if the range is within the specified age range \(e\.g\., ages 18–30 years\)\. 

Continuous enrollment, allowable gap, anchor date

Yes

Organizations are not required to use enrollment criteria; adjustments are allowed\.

Benefits

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

Only events that contain \(or map to\) codes in the value sets may be used to identify cardiac events\. Value sets and logic may not be changed\.

__Denominator Exclusions__

__Adjustments Allowed \(Yes/No\)__

__Notes__

Required exclusions

Yes, with limits

Apply required exclusions according to specified value sets and medication lists\. 

The hospice, deceased member, palliative care, I\-SNP, LTI, frailty and advanced illness exclusions are not required\. Refer to *Exclusions* in the *Guidelines for the Rules for Allowable Adjustments\.* 

__Numerator Criteria__

__Adjustments Allowed \(Yes/No\)__

__Notes__

- Initiation
- Engagement 1
- Engagement 2
- Achievement

No

Value sets and logic may not be changed\.

<a id="_Toc74816294"></a><a id="_Toc171402984"></a>Diabetes

