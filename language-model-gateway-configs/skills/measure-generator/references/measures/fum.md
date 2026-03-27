## <a id="FollowUp_ED_Visit_FUM"></a><a id="_Toc74816308"></a><a id="_Toc171402996"></a>Follow\-Up After Emergency Department Visit for Mental Illness \(FUM\)\*

__\*Adapted from an NCQA measure with financial support from the Office of the Assistant Secretary for Planning and Evaluation \(ASPE\) under Prime Contract No\. HHSP23320100019WI/HHSP23337001T, in which NCQA was a subcontractor to Mathematica\. Additional financial support was provided by the   
Substance Abuse and Mental Health Services Administration \(SAMHSA\)\.__

Summary of changes to HEDIS MY 2025

- Modified the denominator criteria to allow intentional self\-harm diagnoses to take any position on the claim\.
- Added phobia, anxiety and additional intentional self\-harm diagnoses to the denominator in the event/ diagnosis\. 
- Modified the numerator criteria to allow a mental health diagnosis to take any position on the claim\. 
- Deleted visits that required both a mental health diagnosis and self\-harm diagnosis from the numerator\. 
- Added peer support services and residential treatment to the numerator\. 
- Added visits in a behavioral healthcare setting and psychiatric collaborative care management services to the numerator\. 
- Deleted the mental health diagnosis requirement for partial hospitalization/ intensive outpatient visits, community mental health center visits and electroconvulsive therapy\.
- Deleted the *Note* regarding billing methods for intensive outpatient encounters and partial hospitalizations\.
- Removed the data source reporting requirement from the race and ethnicity stratification\.
- *Technical Update:* Revised the numerator\. 

Description

The percentage of emergency department \(ED\) visits for members 6 years of age and older with a principal diagnosis of mental illness, or any diagnosis of intentional self\-harm, and had a mental health follow\-up service\. Two rates are reported:

1\.	The percentage of ED visits for which the member received follow\-up within 30 days of the ED visit \(31 total days\)\.

2\.	The percentage of ED visits for which the member received follow\-up within 7 days of the ED visit \(8 total days\)\. 

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

6 years and older as of the date of the ED visit\. Report three age stratifications and a total rate:

- 6–17 years\.
- 18–64 years\.

- 65 years and older\.
- Total\.

The total is the sum of the age stratifications\. 

Continuous enrollment

Date of the ED visit through 30 days after the ED visit \(31 total days\)\.

Allowable gap

None\. 

Anchor date

None\.

Benefit

Medical and mental health\. 

Event/diagnosis

An ED visit \(ED Value Set\) with a principal diagnosis of mental illness \(Mental Illness Value Set\), or any diagnosis of intentional self\-harm \(Intentional Self Harm Value Set\), on or between January 1 and December 1 of the measurement year where the member was 6 years or older on the date of the visit\. 

The denominator for this measure is based on ED visits, not on members\. If a member has more than one ED visit, identify all eligible ED visits between January 1 and December 1 of the measurement year and do not include more than one visit per 31\-day period as described below\.

*Multiple visits in a 31\-day period*

If a member has more than one ED visit in a 31\-day period, include only the   
first eligible ED visit\. For example, if a member has an ED visit on January 1, include the January 1 visit and do not include ED visits that occur on or between January 2 and January 31; then, if applicable, include the next ED visit that occurs on or after February 1\. Identify visits chronologically, including only one per 31\-day period\. 

__Note:__ Removal of multiple visits in a 31\-day period is based on __eligible__ visits\. Assess each ED visit for exclusions before removing multiple visits in a 31\-day period\.

*ED visits followed by inpatient admission*

Exclude ED visits that result in an inpatient stay\. Exclude ED visits followed by admission to an acute or nonacute inpatient care setting on the date of the ED visit or within the 30 days after the ED visit \(31 total days\), regardless of the principal diagnosis for the admission\. To identify admissions to an acute or nonacute inpatient care setting: 

1. Identify all acute and nonacute inpatient stays except for residential psychiatric treatment \(Inpatient Stay Except Psychiatric Residential Value Set\)\.
2. Identify the admission date for the stay\. 

These events are excluded from the measure because admission to an acute or nonacute inpatient setting may prevent an outpatient follow\-up visit from taking place\.

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

A follow\-up service for mental health within 30 days after the ED visit \(31 total days\)\. Include services that occur on the date of the ED visit\.

*7\-Day *

*Follow\-Up*

A follow\-up service for mental health within 7 days after the ED visit \(8 total days\)\. Include services that occur on the date of the ED visit\.

For both indicators, any of the following meet criteria for a follow\-up service\.

- An outpatient visit \(Visit Setting Unspecified Value Set __*with*__ Outpatient POS Value Set\)__* with*__ any diagnosis of a mental health disorder \(Mental Health Diagnosis Value Set\)\.
- An outpatient visit \(BH Outpatient Value Set\) __*with*__ any diagnosis of a mental health disorder \(Mental Health Diagnosis Value Set\)\.
- An intensive outpatient encounter or partial hospitalization \(Visit Setting Unspecified Value Set\) __*with*__ POS code 52\.
- An intensive outpatient encounter or partial hospitalization \(Partial Hospitalization or Intensive Outpatient Value Set\) __*with*__ any diagnosis of a mental health disorder \(Mental Health Diagnosis Value Set\)\.
- A community mental health center visit \(Visit Setting Unspecified Value Set\) __*with*__ POS code 53\.
- Electroconvulsive therapy \(Electroconvulsive Therapy Value Set\) __*with*__ \(Outpatient POS Value Set; POS code 24; POS code 52; POS code 53\)\.
- A telehealth visit \(Visit Setting Unspecified Value Set __*with*__ Telehealth POS Value Set\)__* with *__any diagnosis of a mental health disorder \(Mental Health Diagnosis Value Set\)\.
- A telephone visit \(Telephone Visits Value Set\) __*with *__any diagnosis of a mental health disorder \(Mental Health Diagnosis Value Set\)\.
- An e\-visit or virtual check\-in \(Online Assessments Value Set\) __*with *__any diagnosis of a mental health disorder \(Mental Health Diagnosis Value Set\)\.
- Psychiatric collaborative care management \(Psychiatric Collaborative Care Management Value Set\)\.
- Peer support services \(Peer Support Services Value Set\) __*with *__any diagnosis of mental health disorder \(Mental Health Diagnosis Value Set\)\.
- Psychiatric residential treatment \(Residential Behavioral Health Treatment Value Set\)\.
- Psychiatric residential treatment \(Visit Setting Unspecified Value Set __*with*__ POS code 56\)\.
- A visit in a behavioral healthcare setting \(Behavioral Healthcare Setting Value Set\)\.

__*Note*__*: Events that meet both eligible population and numerator criteria should not be included in the numerator\.*

__Data Elements for Reporting __

Organizations that submit HEDIS data to NCQA must provide the following data elements\.

__*Table FUM\-A\-1/2/3: Data Elements for Follow\-Up After Emergency Department Visit for Mental Illness*__

Metric

Age

Data Element

Reporting Instructions

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

### Table FUM\-B\-1/2/3: Data Elements for Follow\-Up After Emergency Department Visit for Mental Illness: Stratifications by Race 

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

 

 

### Table FUM\-C\-1/2/3: Data Elements for Follow\-Up After Emergency Department Visit for Mental Illness: Stratifications by Ethnicity 

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

### Rules for Allowable Adjustments of Follow\-Up After Emergency Department Visit for Mental Illness

<a id="_Hlk4488996"></a>__NONCLINICAL COMPONENTS__

__Eligible Population__

__Adjustments Allowed \(Yes/No\)__

__Notes__

Product lines

Yes

Organizations are not required to use product line criteria; product lines may be combined and all \(or no\) product line criteria may be used\.

Ages

Yes

Age determination dates may be changed \(6 years as of the date of the ED visit\)\. 

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

Only events or diagnoses that contain \(or map to\) codes in the value sets may be used to identify visits with a diagnosis\. Value sets and logic may not be changed\. 

__*Note:*__* Organizations may assess at the member level by applying measure logic appropriately \(i\.e\., percentage of members with documentation of an ED visit with a principal diagnosis of mental illness or intentional self\-harm, who had a follow\-up visit for mental illness\)\.*

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

