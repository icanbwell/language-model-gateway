## <a id="FollowUp_Hosp_Mental_FUH"></a><a id="_Toc400546137"></a><a id="_Toc74816307"></a><a id="_Toc171402995"></a><a id="FUH"></a><a id="FUM"></a><a id="_Toc441634930"></a><a id="_Toc400546138"></a>Follow\-Up After Hospitalization for Mental Illness \(FUH\)

Summary of Changes to HEDIS MY 2025

- Modified the denominator criteria to allow intentional self\-harm diagnoses to take any position on the acute inpatient discharge claim\.
- Added phobia, anxiety and additional intentional self\-harm diagnoses to the denominator in the event/ diagnosis\. 
- Added visits with any diagnosis of a mental health disorder to the numerator\. 
- Added peer support and residential treatment services to the numerator\. 
- Deleted the *Note* regarding billing methods for intensive outpatient encounters and partial hospitalizations\. 
- Removed the data source reporting requirement from the race and ethnicity stratification\.

Description

The percentage of discharges for members 6 years of age and older who were hospitalized for a principal diagnosis of mental illness, or any diagnosis of intentional self\-harm, and had a mental health follow\-up service\. Two rates are reported:

1. The percentage of discharges for which the member received follow\-up within 30 days after discharge\.
2. The percentage of discharges for which the member received follow\-up within 7 days after discharge\.

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

6 years and older as of the date of discharge\. Report three age stratifications and a total rate:

- 6–17 years\.
- 18–64 years\.

- 65 years and older\.
- Total\.

The total is the sum of the age stratifications\.

Continuous enrollment

Date of discharge through 30 days after discharge\.

Allowable gap

None\. 

Anchor date

None\. 

Benefits

Medical and mental health \(inpatient and outpatient\)\.

Event/diagnosis

An acute inpatient discharge with a principal diagnosis of mental illness \(Mental Illness Value Set\), or any diagnosis of intentional self\-harm \(Intentional Self Harm Value Set\), on the discharge claim on or between January 1 and December 1 of the measurement year\. To identify acute inpatient discharges:

1\.	Identify all acute and nonacute inpatient stays \(Inpatient Stay Value Set\)\.

2\.	Exclude nonacute inpatient stays \(Nonacute Inpatient Stay Value Set\)\.

3\.	Identify the discharge date for the stay\.

The denominator for this measure is based on discharges, not on members\. If members have more than one discharge, include all discharges on or between January 1 and December 1 of the measurement year\.

*Acute readmission or direct transfer*

Identify readmissions and direct transfers to an acute inpatient care setting during the 30\-day follow\-up period:

1\.	Identify all acute and nonacute inpatient stays \(Inpatient Stay Value Set\)\. 

2\.	Exclude nonacute inpatient stays \(Nonacute Inpatient Stay Value Set\)\.

3\.	Identify the admission date for the stay \(the admission date must occur during the 30\-day follow\-up period\)\.

4\.	Identify the discharge date for the stay\.

Exclude both the initial discharge and the readmission/direct transfer discharge if the last discharge occurs after December 1 of the measurement year\.

If the readmission/direct transfer to the acute inpatient care setting was for a principal diagnosis of mental health disorder, or any diagnosis of intentional self\-harm \(Mental Health Diagnosis Value Set; Intentional Self Harm Value Set\), count only the last discharge \(use only the discharge claim\)\.

If the readmission/direct transfer to the acute inpatient care setting was for any other principal diagnosis, and intentional self\-harm was not on the claim in any diagnosis position, exclude both the original and the readmission/direct transfer discharge \(use only the discharge claim\)\. 

*Nonacute readmission or direct transfer*

Exclude discharges followed by readmission or direct transfer to a nonacute inpatient care setting \(except for psychiatric residential treatment\) within the 30\-day follow\-up period, regardless of the diagnosis for the readmission\. To identify readmissions and direct transfers to a nonacute inpatient care setting:

1\.	Identify all acute and nonacute inpatient stays except for residential psychiatric treatment \(Inpatient Stay Except Psychiatric Residential Value Set\)\.

2\.	Confirm the stay was for nonacute care based on the presence of a nonacute code \(Nonacute Inpatient Stay Value Set\) on the claim\. 

3\.	Identify the admission date for the stay\.

These discharges are excluded from the measure because rehospitalization or direct transfer may prevent an outpatient follow\-up visit from taking place\. 

Required exclusions

Exclude members who meet either of the following criteria:

- Members who use hospice services \(Hospice Encounter Value Set; Hospice Intervention Value Set\) or elect to use a hospice benefit any time during the measurement year\. Organizations that use the Monthly Membership Detail Data File to identify these members must use only the run date of the file to determine if the member elected to use a hospice benefit during the measurement year\. 
- Members who die any time during the measurement year\. 

Administrative Specification

Denominator

The eligible population\. 

Numerators

*30\-Day   
Follow\-Up*

A follow\-up service for mental health within 30 days after discharge\. Do not include services that occur on the date of discharge\.

*7\-Day   
Follow\-Up*

A follow\-up service for mental health within 7 days after discharge\. Do not include services that occur on the date of discharge\.

For both indicators, any of the following meet criteria for a follow\-up service\. 

- An outpatient visit \(Visit Setting Unspecified Value Set\) __*with*__ \(Outpatient POS Value Set\)__* with*__ a mental health provider\.
- An outpatient visit \(Visit Setting Unspecified Value Set\) __*with*__ \(Outpatient POS Value Set\)__* with*__ any diagnosis of mental health disorder \(Mental Health Diagnosis Value Set\)\.
- An outpatient visit \(BH Outpatient Value Set\) __*with*__ a mental health provider\.
- An outpatient visit \(BH Outpatient Value Set\) __*with*__ any diagnosis of mental health disorder \(Mental Health Diagnosis Value Set\)\.
- An intensive outpatient encounter or partial hospitalization \(Visit Setting Unspecified Value Set __*with*__ POS code 52\)\.
- An intensive outpatient encounter or partial hospitalization \(Partial Hospitalization or Intensive Outpatient Value Set\)\.
- A community mental health center visit \(Visit Setting Unspecified Value Set; BH Outpatient Value Set; Transitional Care Management Services Value Set\) __*with*__ POS code 53\.
- Electroconvulsive therapy \(Electroconvulsive Therapy Value Set\) __*with*__ \(Outpatient POS Value Set; POS code 24; POS code 52; POS code 53\)\.
- A telehealth visit: \(Visit Setting Unspecified Value Set\) __*with*__ \(Telehealth POS Value Set\)__* with *__a mental health provider\.
- A telehealth visit: \(Visit Setting Unspecified Value Set\) __*with*__ \(Telehealth POS Value Set\)__* with *__any diagnosis of mental health disorder \(Mental Health Diagnosis Value Set\)\.
- Transitional care management services \(Transitional Care Management Services Value Set\) __*with*__ a mental health provider\.
- Transitional care management services \(Transitional Care Management Services Value Set\) __*with*__ any diagnosis of mental health disorder \(Mental Health Diagnosis Value Set\)\.
- A visit in a behavioral healthcare setting \(Behavioral Healthcare Setting Value Set\)\.
- A telephone visit \(Telephone Visits Value Set\) __*with *__a mental health provider\.
- A telephone visit \(Telephone Visits Value Set\) __*with *__any diagnosis of mental health disorder \(Mental Health Diagnosis Value Set\)\.
- Psychiatric collaborative care management \(Psychiatric Collaborative Care Management Value Set\)\. 
- Peer support services \(Peer Support Services Value Set\) __*with *__any diagnosis of mental health disorder \(Mental Health Diagnosis Value Set\)\.
- Psychiatric residential treatment \(Residential Behavioral Health Treatment Value Set\)\.
- Psychiatric residential treatment \(Visit Setting Unspecified Value Set __*with*__ POS code 56\)\.

*Note*

- *Refer to Appendix 3 for the definition of *mental health provider\.* Organizations must develop their own methods to identify mental health providers\. Methods are subject to review by the HEDIS auditor\. *

__Data Elements for Reporting __

Organizations that submit HEDIS data to NCQA must provide the following data elements\.

__*Table FUH\-A\-1/2/3: Data Elements for Follow\-Up After Hospitalization for Mental Illness*__

__Metric__

__Age__

__Data Element__

__Reporting Instructions__

FollowUp30Day

6\-17

Benefit

Metadata

FollowUp7Day

18\-64

EligiblePopulation 

For each Stratification, repeat per Metric

65\+

ExclusionAdminRequired

For each Stratification, repeat per Metric

Total

NumeratorByAdmin

For each Metric and Stratification

NumeratorBySupplemental

For each Metric and Stratification

Rate

\(Percent\)

### Table FUH\-B\-1/2/3: Data Elements for Follow\-Up After Hospitalization for Mental Illness: Stratifications by Race 

Metric

Race

Data Element

Reporting Instructions

FollowUp30Day 

AmericanIndianOrAlaskaNative 

EligiblePopulation 

For each Stratification, repeat per Metric 

FollowUp7Day 

Asian

Numerator 

For each Metric and Stratification 

 

BlackOrAfricanAmerican 

Rate 

\(Percent\) 

 

NativeHawaiianOrOtherPacificIslander

 

 

 

White 

 

 

 

SomeOtherRace 

 

 

TwoOrMoreRaces 

 

 

AskedButNoAnswer 

 

 

Unknown

 

### Table FUH\-C\-1/2/3: Data Elements for Follow\-Up After Hospitalization for Mental Illness: Stratifications   
by Ethnicity 

__Metric__ 

__Ethnicity__ 

__Data Element__ 

__Reporting Instructions__ 

FollowUp30Day 

HispanicOrLatino 

EligiblePopulation 

For each Stratification, repeat per Metric 

FollowUp7Day 

NotHispanicOrLatino 

Numerator 

For each Metric and Stratification 

 

AskedButNoAnswer

Rate 

\(Percent\) 

 

Unknown 

 

 

 

Rules for Allowable Adjustments of HEDIS

The “Rules for Allowable Adjustments of HEDIS” \(the “Rules”\) describe how NCQA’s HEDIS measure specifications can be adjusted for other populations, if applicable\. The Rules, reviewed and approved by NCQA measure experts, provide for expanded use of HEDIS measures without changing their clinical intent\.

__Adjusted HEDIS measures may not be used for HEDIS health plan reporting\. __

### Rules for Allowable Adjustments of Follow\-Up After Hospitalization for Mental Illness

__NONCLINICAL COMPONENTS__

__Eligible Population__

__Adjustments Allowed \(Yes/No\)__

__Notes__

Product lines

Yes

Organizations are not required to use product line criteria; product lines may be combined and all \(or no\) product line criteria may be used\.

Ages

Yes

The age determination dates may be changed \(e\.g\., select, “age as of June 30”\)\.

Changing the denominator age range is allowed\.

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

Yes, with limits

Only events or diagnoses that contain \(or map to\) codes in the value sets may be used to identify inpatient stays and diagnoses\. Value sets and logic may not be changed\. 

__*Note:*__* Organizations may assess at the member level \(vs\. discharge level\) by applying measure logic appropriately \(i\.e\., percentage of members who were hospitalized for treatment of selected mental illness or intentional self\-harm diagnoses who had a follow\-up visit with a mental health practitioner\)\.*

__Denominator Exclusions__

__Adjustments Allowed \(Yes/No\)__

__Notes__

Required exclusions

Yes

The hospice and deceased member exclusions are not required\. Refer to *Exclusions* in the *Guidelines for the Rules for Allowable Adjustments*\.

__Numerator Criteria__

__Adjustments Allowed \(Yes/No\)__

__Notes__

- 30\-Day Follow\-Up
- 7\-Day Follow\-Up

No

Value sets and logic may not be changed\.

