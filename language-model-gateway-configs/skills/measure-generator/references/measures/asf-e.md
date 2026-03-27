## <a id="Unhealthy_Alcohol_Use_ASFE"></a><a id="_Toc171403075"></a>Unhealthy Alcohol Use Screening and Follow\-Up \(ASF\-E\)\*

__\*Adapted with financial support from the Substance Abuse and Mental Health Services Administration \(SAMHSA\) and with permission from the measure developer, the American Medical Association \(AMA\)\.__

Summary of Changes to HEDIS MY 2025

- Removed “Programming Guidance” from the *Characteristics* section\. 
- Removed the *Data criteria \(element level\)* section\.
- Added a laboratory claim exclusion to a direct reference code\.

Description

The percentage of members 18 years of age and older who were screened for unhealthy alcohol use using a standardized instrument and, if screened positive, received appropriate follow\-up care\.

- *Unhealthy Alcohol Use Screening*\. The percentage of members who had a systematic screening for unhealthy alcohol use\.
- *Follow\-Up Care on Positive Screen*\. The percentage of members receiving brief counseling or other follow\-up care within 60 days   
\(2 months\) of screening positive for unhealthy alcohol use\.

Measurement period

January 1–December 31\.

Clinical recommendation statement

The U\.S\. Preventive Services Task Force recommends that clinicians screen adults aged 18 years or older for alcohol misuse and provide brief behavioral counseling interventions to those who misuse alcohol\. \(B recommendation\)

Citations

U\.S\. Preventive Services Task Force\. 2018\. “Unhealthy Alcohol Use in Adolescents and Adults: Screening and Behavioral Counseling Interventions\.” *JAMA* 320\(18\):1899–1909\. DOI:10\.1001/jama\.2018\.16789\.

__Characteristics__

Scoring

Proportion\.

Type 

Process\.

Stratification

- Unhealthy Alcohol Use Screening\.
- Product line:
- Commercial\.
- Medicaid\.
- Medicare\.
- Age \(as of the start of the measurement period, for each product line\):
- 18–44 years\.
- 45–64 years\.
- 65 years and older\.

- Follow\-Up on Care Positive Screen\.
- Product line:
- Commercial\.
- Medicaid\.
- Medicare\.
- Age \(as of the start of the measurement period, for each product line\):
- 18–44 years\.
- 45–64 years\.
- 65 years and older\.

Risk adjustment

None\.

Improvement notation

A higher rate indicates better performance\.

Guidance

__Allocation:  
__The member was enrolled with a medical benefit throughout the measurement period\.

No more than one gap in enrollment of up to 45 days during the measurement period\.

The member must be enrolled on the last day of the measurement period\.

__Reporting:  
__The total is the sum of the age stratifications\.

Definitions

Participation

The identifiers and descriptors for each organization’s coverage used to define members’ eligibility for measure reporting\. Allocation for reporting is based on eligibility during the participation period\.

Participation period

The measurement period\.

Unhealthy Alcohol Use Screening

A standard assessment instrument that has been normalized and validated for the adult patient population\. Eligible screening instruments with thresholds for positive findings include:

__Screening Instrument __

__Total Score   
LOINC Codes__

__Positive Finding__

Alcohol Use Disorders Identification Test \(AUDIT\) screening instrument

75624\-7

Total score ≥8

Alcohol Use Disorders Identification Test Consumption \(AUDIT\-C\) screening instrument

75626\-2

Total score ≥4 for men

Total score ≥3 for women

__Screening Instrument __

__Total Score   
LOINC Codes__

__Positive Finding__

Single\-question screen \(for men\):  
“How many times in the past year have you had 5 or more drinks in a day?”

88037\-7

Response ≥1

Single\-question screen \(for women and all adults older than 65 years\):  
“How many times in the past year have you had 4 or more drinks in a day?”

75889\-6

Response ≥1

Alcohol Counseling or Other Follow\-Up Care

Any of the following on or up to 60 days after the first positive screen:

- Feedback on alcohol use and harms\.
- Identification of high\-risk situations for drinking and coping strategies\.
- Increase the motivation to reduce drinking\.
- Development of a personal plan to reduce drinking\.
- Documentation of receiving alcohol misuse treatment\.

Initial population

__Initial population 1  
__Members 18 years and older at the start of the measurement period who also meet criteria for participation\.

__Initial population 2  
__Same as the initial population 1\.

Exclusions

__Exclusions 1__

- Members with alcohol use disorder \(Alcohol Use Disorder Value Set\) that starts during the year prior to the measurement period\. Do not include laboratory claims \(claims with POS code 81\)\.
- Members with history of dementia \(Dementia Value Set\) any time during the member’s history through the end of the measurement period\. Do not include laboratory claims \(claims with POS code 81\)\.
- Members who use hospice services \(Hospice Encounter Value Set; Hospice Intervention Value Set\) or elect to use a hospice benefit any time during the measurement period\. Organizations that use the Monthly Membership Detail Data File to identify these members must use only the run date of the file to determine if the member elected to use a hospice benefit during the measurement period\.
- Members who die any time during the measurement period\.

__Exclusions 2  
__Same as exclusions 1\.

Denominator

__Denominator 1  
__The initial population, minus exclusions\.

__Denominator 2  
__All members in numerator 1 with a positive finding for unhealthy alcohol use screening between January 1 and November 1 of the measurement period\.

Numerator

__Numerator 1—Unhealthy Alcohol Use Screening  
__Members with a documented result for unhealthy alcohol use screening performed between January 1 and November 1 of the measurement period\.

__Numerator 2—Follow\-Up Care on Positive Screen  
__Members receiving alcohol counseling or other follow\-up care\. Either of the following on or up to 60 days after the date of the first positive screen \(61 days total\) meets criteria:

- Alcohol Counseling or Other Follow Up Care Value Set\.
- A diagnosis of encounter for alcohol counseling and surveillance \(ICD\-10\-CM code Z71\.41\)\. Do not include laboratory claims \(claims with POS code 81\)\.

__Data Elements for Reporting __

Organizations that submit data to NCQA must provide the following data elements in a specified file\. 

__*Table ASF\-E\-1/2/3: Data Elements for Unhealthy Alcohol Use Screening and Follow\-Up*__

__Metric__

__Age__

__Data Element__

__Reporting Instructions__

Screening

18\-44

InitialPopulation

For each stratification, repeat per metric

FollowUp

45\-64

ExclusionsByEHR

For each stratification, repeat per metric

 

65\+

ExclusionsByCaseManagement

For each stratification, repeat per metric

 

Total

ExclusionsByHIERegistry

For each stratification, repeat per metric

ExclusionsByAdmin

For each stratification, repeat per metric

 

Exclusions

\(Sum over SSoRs\)

 

Denominator

For each Metric and Stratification

 

NumeratorByEHR

For each Metric and Stratification

 

NumeratorByCaseManagement

For each Metric and Stratification

 

NumeratorByHIERegistry

For each Metric and Stratification

NumeratorByAdmin

For each Metric and Stratification

Numerator

\(Sum over SSoRs\)

Rate

\(Percent\)

<a id="_Hlk28348874"></a>

Rules for Allowable Adjustments of HEDIS

<a id="_Hlk1053748"></a>The “Rules for Allowable Adjustments of HEDIS” \(the “Rules”\) describe how NCQA’s HEDIS measure specifications can be adjusted for other populations, if applicable\. The Rules, reviewed and approved by NCQA measure experts, provide for expanded use of HEDIS measures without changing their clinical intent\.

__Adjusted HEDIS measures may not be used for HEDIS health plan reporting\. __

### Rules for Allowable Adjustments of Unhealthy Alcohol Use Screening and Follow\-Up

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

Changing the denominator age range is allowed if the limits are within the specified age range \(18 years and older\)\.

Organizations must consult UPSTSF guidelines when considering whether to expand the age ranges outside of the current thresholds\.

Allocation

Yes

Organizations are not required to use enrollment criteria; adjustments are allowed\.

Benefits

Yes

Using a benefit is not required; adjustments are allowed\.

Other

Yes

Organizations may use additional eligible population criteria to focus on an area of interest defined by gender, race, ethnicity, socioeconomic or sociodemographic characteristics, geographic region or another characteristic\. 

__CLINICAL COMPONENTS__

__Initial Population__

__Adjustments Allowed \(Yes/No\)__

__Notes__

Event/diagnosis

No

Value sets, direct reference codes and logic may not be changed for denominator 2\.

__Exclusions__

__Adjustments Allowed \(Yes/No\)__

__Notes__

Exclusions

No

Apply exclusions according to specified direct reference codes\.

Exclusions: Hospice and deceased member

Yes

These exclusions are not required\. Refer to *Exclusions* in the *Guidelines for the Rules for Allowable Adjustments*\.

__Denominator__

__Adjustments Allowed \(Yes/No\)__

__Notes__

Denominators

No

The logic may not be changed\. 

__Numerator Criteria__

__Adjustments Allowed \(Yes/No\)__

__Notes__

- Unhealthy Alcohol Use Screening
- Counseling Or Other Follow\-Up On Positive Screen

No

Value sets, direct reference codes and logic may not be changed\.

