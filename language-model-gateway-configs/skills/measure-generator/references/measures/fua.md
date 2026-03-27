## <a id="FollowUp_ED_Visit_Substance_Use_FUA"></a>Follow\-Up After Emergency Department Visit for   
Substance Use \(FUA\)\* 

__\*Adapted from an NCQA measure with financial support from the Office of the Assistant Secretary for Planning and Evaluation \(ASPE\) under Prime Contract No\. HHSP23320100019WI/HHSP23337001T, in which NCQA was a subcontractor to Mathematica\. Additional financial support was provided by the   
Substance Abuse and Mental Health Services Administration \(SAMHSA\)\.__

Summary of Changes to HEDIS MY 2025

- Added a laboratory claim exclusion to a value set for which laboratory claims should not be used\.
- Deleted the *Note* regarding billing methods for intensive outpatient encounters and partial hospitalizations\.
- Removed the data source reporting requirement from the race and ethnicity stratification\.

Description

The percentage of emergency department \(ED\) visits among members age 13 years and older with a principal diagnosis of substance use disorder \(SUD\), or any diagnosis of drug overdose, for which there was follow\-up\. Two rates are reported:

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

13 years and older as of the ED visit\. Report two age stratifications and a total rate:

- 13–17 years\.
- 18 years and older\.
- Total\.

The total is the sum of the age stratifications\. 

Continuous enrollment

The date of the ED visit through 30 days after the ED visit \(31 total days\)\. 

Allowable gap

None\. 

Anchor date

None\.

Benefit

Medical, chemical dependency and pharmacy\.

__Note:__ Members with withdrawal management/detoxification\-only chemical dependency benefits do not meet these criteria\. 

Event/diagnosis

An ED visit \(ED Value Set\) with a principal diagnosis of SUD \(AOD Abuse and Dependence Value Set\) __*or*__ any diagnosis of drug overdose \(Unintentional Drug Overdose Value Set\) on or between January 1 and December 1 of the measurement year, where the member was 13 years or older on the date of   
the visit\. 

The denominator for this measure is based on ED visits, not on members\. If a member has more than one ED visit, identify all eligible ED visits between January 1 and December 1 of the measurement year and do not include more than one visit per 31\-day period, as described below\.

*Multiple visits in a 31\-day period*

If a member has more than one ED visit in a 31\-day period, include only the first eligible ED visit\. For example, if a member has an ED visit on January 1, include the January 1 visit and do not include ED visits that occur on or between January 2 and January 31; then, if applicable, include the next ED visit that occurs on or after February 1\. Identify visits chronologically, including only one per 31\-day period\. 

__Note:__ Removal of multiple visits in a 31\-day period is based on __eligible__ visits\. Assess each ED visit for exclusions before removing multiple visits in a 31\-day period\.

*ED visits followed by inpatient admission*

Exclude ED visits that result in an inpatient stay\. Exclude ED visits followed by an admission to an acute or nonacute inpatient care setting on the date of the ED visit or within the 30 days after the ED visit, regardless of the principal diagnosis for the admission\. To identify admissions to an acute or nonacute inpatient care setting:

1. Identify all acute and nonacute inpatient stays \(Inpatient Stay Value Set\)\.
2. Identify the admission date for the stay\.

*ED visits followed by residential treatment*

Exclude ED visits followed by residential treatment on the date of the ED visit or within the 30 days after the ED visit\. Any of the following meets criteria for residential treatment:

- Residential Behavioral Health Treatment Value Set\.
- Psychiatric Residential Treatment Center \(POS code 56\)\.
- Residential Substance Abuse Treatment Facility \(POS code 55\)\.
- Residential Program Detoxification Value Set\.

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

A follow\-up visit or a pharmacotherapy dispensing event within 30 days after the ED visit \(31 total days\)\. Include visits and pharmacotherapy events that occur on the date of the ED visit\. 

*7\-Day   
Follow\-Up*

A follow\-up visit or a pharmacotherapy dispensing event within 7 days after the ED visit \(8 total days\)\. Include visits and pharmacotherapy events that occur on the date of the ED visit\.

For both indicators, any of the following meet criteria for a follow\-up visit:

- An outpatient visit \(Visit Setting Unspecified Value Set\) __*with*__ \(Outpatient POS Value Set\)__* with*__ any diagnosis of SUD \(AOD Abuse and Dependence Value Set\), substance use \(Substance Induced Disorders Value Set\) or drug overdose \(Unintentional Drug Overdose Value Set\)\.
- An outpatient visit \(Visit Setting Unspecified Value Set\) __*with*__ \(Outpatient POS Value Set\)__* with*__ a mental health provider\.
- An outpatient visit \(BH Outpatient Value Set\)__* with*__ any diagnosis of SUD \(AOD Abuse and Dependence Value Set\), substance use \(Substance Induced Disorders Value Set\) or drug overdose \(Unintentional Drug Overdose Value Set\)\.
- An outpatient visit \(BH Outpatient Value Set\)__* with *__a mental health provider\. 

- An intensive outpatient encounter or partial hospitalization \(Visit Setting Unspecified Value Set\) __*with*__ POS code 52__* with*__ any diagnosis of SUD \(AOD Abuse and Dependence Value Set\), substance use \(Substance Induced Disorders Value Set\) or drug overdose \(Unintentional Drug Overdose Value Set\)\.
- An intensive outpatient encounter or partial hospitalization \(Visit Setting Unspecified Value Set\) __*with*__ POS code 52__* with*__ a mental health provider\.
- An intensive outpatient encounter or partial hospitalization \(Partial Hospitalization or Intensive Outpatient Value Set\)__* with*__ any diagnosis of SUD \(AOD Abuse and Dependence Value Set\), substance use \(Substance Induced Disorders Value Set\) or drug overdose \(Unintentional Drug Overdose Value Set\)\.
- An intensive outpatient encounter or partial hospitalization \(Partial Hospitalization or Intensive Outpatient Value Set\)__* with*__ a mental health provider\.
- A non\-residential substance abuse treatment facility visit \(Visit Setting Unspecified Value Set\) __*with*__ \(Nonresidential Substance Abuse Treatment Facility POS Value Set\)__* with*__ any diagnosis of SUD \(AOD Abuse and Dependence Value Set\), substance use \(Substance Induced Disorders Value Set\) or drug overdose \(Unintentional Drug Overdose Value Set\)\.
- A non\-residential substance abuse treatment facility visit \(Visit Setting Unspecified Value Set\) __*with*__ \(Nonresidential Substance Abuse Treatment Facility POS Value Set\)__* with*__ a mental health provider\. 
- A community mental health center visit \(Visit Setting Unspecified Value Set\) __*with*__ POS code 53 __*with*__ any diagnosis of SUD \(AOD Abuse and Dependence Value Set\), substance use \(Substance Induced Disorders Value Set\) or drug overdose \(Unintentional Drug Overdose Value Set\)\.
- A community mental health center visit \(Visit Setting Unspecified Value Set\) __*with*__ POS code 53, __*with*__ a mental health provider\.
- A peer support service \(Peer Support Services Value Set\) __*with*__ any diagnosis of SUD \(AOD Abuse and Dependence Value Set\), substance use \(Substance Induced Disorders Value Set\) or drug overdose \(Unintentional Drug Overdose Value Set\)\.
- An opioid treatment service that bills monthly or weekly \(OUD Weekly Non Drug Service Value Set; OUD Monthly Office Based Treatment Value Set\) __*with*__ any diagnosis of SUD \(AOD Abuse and Dependence Value Set\), substance use \(Substance Induced Disorders Value Set\) or drug overdose \(Unintentional Drug Overdose Value Set\)\.
- A telehealth visit \(Visit Setting Unspecified Value Set\) __*with*__ \(Telehealth POS Value Set\)__* with*__ any diagnosis of SUD \(AOD Abuse and Dependence Value Set\), substance use \(Substance Induced Disorders Value Set\) or drug overdose \(Unintentional Drug Overdose Value Set\)\.
- A telehealth visit \(Visit Setting Unspecified Value Set\) __*with*__ \(Telehealth POS Value Set\)__* with*__ a mental health provider\.
- A telephone visit \(Telephone Visits Value Set\) __*with*__ any diagnosis of SUD \(AOD Abuse and Dependence Value Set\), substance use \(Substance Induced Disorders Value Set\) or drug overdose \(Unintentional Drug Overdose Value Set\)\. 

- A telephone visit \(Telephone Visits Value Set\) __*with*__ a mental health provider\. 
- An e\-visit or virtual check\-in \(Online Assessments Value Set\) __*with*__ any diagnosis of SUD \(AOD Abuse and Dependence Value Set\), substance use \(Substance Induced Disorders Value Set\) or drug overdose \(Unintentional Drug Overdose Value Set\)\.
- An e\-visit or virtual check\-in \(Online Assessments Value Set\) __*with*__ a mental health provider\.
- A substance use disorder service \(Substance Use Disorder Services Value Set\)\.
- Substance use disorder counseling and surveillance \(Substance Abuse Counseling and Surveillance Value Set\)\. Do not include laboratory claims \(claims with POS code 81\)\.
- A behavioral health screening or assessment for SUD or mental health disorders \(Behavioral Health Assessment Value Set\)\.
- A substance use service \(Substance Use Services Value Set\)\.
- A pharmacotherapy dispensing event \(Alcohol Use Disorder Treatment Medications List; Opioid Use Disorder Treatment Medications List\) or medication treatment event \(AOD Medication Treatment Value Set; OUD Weekly Drug Treatment Service Value Set\)\.

### Alcohol Use Disorder Treatment Medications

Description

Prescription

Aldehyde dehydrogenase inhibitor

- Disulfiram \(oral\)

Antagonist

- Naltrexone \(oral and injectable\)

Other

- Acamprosate \(oral; delayed\-release tablet\)

### Opioid Use Disorder Treatment Medications

Description

Prescription

Antagonist 

- Naltrexone \(oral and injectable\) 

Partial agonist

- Buprenorphine \(sublingual tablet, injection, implant\)__\*__
- Buprenorphine/naloxone \(sublingual tablet, buccal film, sublingual film\)

__\*__	Buprenorphine administered via transdermal patch or buccal film is not included because it is FDA\-approved for the treatment of pain, not for opioid use disorder\.

*Note*

- *Refer to Appendix 3 for the definition of *mental health provider\.* Organizations must develop their own methods to identify mental health providers\. Methods are subject to review by the HEDIS auditor\.*

<a id="_Toc169866964"></a>Data Elements for Reporting 

Organizations that submit HEDIS data to NCQA must provide the following data elements\.

__*Table FUA\-A\-1/2/3: Data Elements for Follow\-Up After Emergency Department Visit for Substance Use*__

Metric

Age

Data Element

Reporting Instructions

FollowUp30Day

13\-17

Benefit

Metadata

FollowUp7Day

18\+

EligiblePopulation 

For each Stratification, repeat per Metric

Total

ExclusionAdminRequired

For each Stratification, repeat per Metric

NumeratorByAdmin

For each Metric and Stratification

NumeratorBySupplemental

For each Metric and Stratification

Rate

\(Percent\)

__*Table FUA\-B\-1/2/3: Data Elements for Follow\-Up After Emergency Department Visit for Substance Use: Stratifications by Race*__

__Metric__

__Race__

__Data Element__

__Reporting Instructions__

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

__*Table FUA\-C\-1/2/3: Data Elements for Follow\-Up After Emergency Department Visit for Substance Use: Stratifications by Ethnicity*__

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

### Rules for Allowable Adjustments of Follow\-Up After Emergency Department Visit for Substance Use

__NONCLINICAL COMPONENTS__

__Eligible Population__

__Adjustments Allowed \(Yes/No\)__

__Notes__

Product lines

Yes

Organizations are not required to use product line criteria; product lines may be combined and all \(or no\) product line criteria may be used\.

Ages

Yes

The age determination date\(s\) may be changed \(i\.e\., age 13 as of ED visit\)\. 

Changing denominator age range is allowed\.

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

Only events and diagnoses that contain \(or map to\) codes in the value sets may be used to identify visits with a diagnosis\. Value sets and logic may not be changed\. 

__*Note:*__* Organizations may assess at the member level by applying measure logic appropriately \(i\.e\., percentage of members with documentation of an emergency department visit with a principal diagnosis of SUD or any diagnosis of unintentional drug overdose, who had a follow\-up visit\)\.*

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

