## <a id="FollowUp_High_Intensity_SUD_FUI"></a><a id="_Toc171402998"></a><a id="FUA"></a>Follow\-Up After High\-Intensity Care for Substance Use Disorder \(FUI\)

Summary of Changes to HEDIS MY 2025

- Added a laboratory claim exclusion to a value set for which laboratory claims should not be used\.
- Deleted the *Note* regarding billing methods for intensive outpatient encounters and partial hospitalizations\.

Description

The percentage of acute inpatient hospitalizations, residential treatment or withdrawal management visits for a diagnosis of substance use disorder among members 13 years of age and older that result in a follow\-up visit or service for substance use disorder\. Two rates are reported:

1. The percentage of visits or discharges for which the member received follow\-up for substance use disorder within the 30 days after the visit or discharge\. 
2. The percentage of visits or discharges for which the member received follow\-up for substance use disorder within the 7 days after the visit or discharge\. 

Definitions

Episode date

The date of service for any acute inpatient discharge, residential treatment discharge or withdrawal management visit with a principal diagnosis of substance use disorder\. 

For an acute inpatient discharge or residential treatment discharge or for withdrawal management that occurred during an acute inpatient stay or residential treatment stay, *the episode date is the date of discharge\. *

For direct transfers, *the episode date is the discharge date from the transfer admission\. *

For withdrawal management \(other than withdrawal management that occurred during an acute inpatient stay or residential treatment stay\), *the episode date is the date of service\.*

Eligible Population 

Product lines

Commercial, Medicaid, Medicare \(report each product line separately\)\.

Ages

13 years and older as of the date of discharge, stay or event\. Report three age stratifications and total rate:

- 13–17 years\.
- 18–64 years\.

- 65 years and older\.
- Total\.

The total is the sum of the age stratifications\.

Continuous enrollment

Date of episode through 30 days after the episode \(31 total days\)\.

Allowable gap 

None\.

Anchor date

None\.

Benefits

Medical, chemical dependency and pharmacy\.

__Note: __Members with withdrawal management/detoxification\-only chemical dependency benefits do not meet these criteria\.

Event/diagnosis

An acute inpatient discharge, residential treatment or withdrawal management event for a principal diagnosis of substance use disorder on or between January 1 and December 1 of the measurement year\. Any of the following combinations meet criteria:

- An acute inpatient discharge or a residential behavioral health stay __*with*__ a principal diagnosis of substance use disorder \(AOD Abuse and Dependence Value Set\) on the discharge claim\. To identify acute inpatient discharges:
	1. Identify all acute and nonacute inpatient stays \(Inpatient Stay Value Set\)\.
	2. Exclude nonacute inpatient stays other than behavioral health \(Nonacute Inpatient Stay Other Than Behavioral Health Accommodations Value Set\)\.
	3. Identify the discharge date for the stay\.
- A withdrawal management visit \(Detoxification Value Set\) __*with*__ a principal diagnosis of substance use disorder \(AOD Abuse and Dependence Value Set\)\.

The denominator for this measure is based on episodes, not on members\. If members have more than episode, include all that fall on or between January 1 and December 1 of the measurement year\.

*Direct transfers*

Identify direct transfers to an acute inpatient care or residential setting\. If the direct transfer to the acute inpatient or residential care setting was for a principal diagnosis of substance use disorder \(AOD Abuse and Dependence Value Set\), use the date of last discharge\. 

A __direct transfer__ is when the discharge date from the first acute inpatient or residential care setting precedes the admission date to a second acute inpatient or residential care setting by one calendar day or less\. For example: 

- An inpatient discharge on June 1, followed by an admission to another inpatient setting on June 1, *is a direct transfer\. *
- An inpatient discharge on June 1, followed by an admission to an inpatient setting on June 2, *is a direct transfer\. *
- An inpatient discharge on June 1, followed by an admission to another inpatient setting on June 3, *is not a direct transfer; *these are two distinct inpatient stays\. 

Use the following method to identify direct transfers:

1. Identify all acute and nonacute inpatient stays \(Inpatient Stay Value Set\)\. 
2. Exclude nonacute inpatient stays other than behavioral health \(Nonacute Inpatient Stay Other Than Behavioral Health Accommodations Value Set\)\. 
3. Identify the admission date for the stay\. 

Exclude both the initial discharge and the direct transfer discharge if the last discharge occurs after December 1 of the measurement year\. 

If the direct transfer to the acute inpatient or residential behavioral health care setting was for any other principal diagnosis, exclude both the original and the direct transfer discharge\.

*Multiple discharges, visits or events in a 31\-day period*

After evaluating for direct transfers, if a member has more than one episode in   
a 31\-day period, include only the first eligible episode\. For example, if a member is discharged from a residential treatment stay on January 1, include the   
January 1 discharge and do not include subsequent episodes that occur on or between January 2 and January 31; then, if applicable, include the next episode that occurs on or after February 1\. Identify episodes chronologically, including only the first episode per 31\-day period\. 

__Note:__ Removal of multiple episodes in a 31\-day period is based on eligibility\. Assess each episode for eligibility before removing multiple episodes in a 31\-day period\.

Required exclusions

Exclude members who meet either of the following criteria:

- Members who use hospice services \(Hospice Encounter Value Set; Hospice Intervention Value Set\) or elect to use a hospice benefit any time during the measurement year\. Organizations that use the Monthly Membership Detail Data File to identify these members must use only the run date of the file to determine if the member elected to use a hospice benefit during the measurement year\. 
- Members who die any time during the measurement year\. 

Administrative Specification

Denominator

The eligible population\.

Numerators

*30\-Day Follow\-Up*

A follow\-up visit or event with any practitioner for a principal diagnosis of substance use disorder within the 30 days after an episode for substance use disorder\. Do not include visits that occur on the date of the denominator episode\.

*7\-Day Follow\-Up*

A follow\-up visit or event with any practitioner for a principal diagnosis of substance use disorder within the 7 days after an episode for substance use disorder\. Do not include visits that occur on the date of the denominator episode\.

For both indicators, any of the following meet criteria for a follow\-up visit\.

- An acute or nonacute inpatient admission or residential behavioral health stay __*with*__ a principal diagnosis of substance use disorder \(AOD Abuse and Dependence Value Set\) on the discharge claim\. To identify acute and nonacute inpatient admissions: 

1\.	Identify all acute and nonacute inpatient stays \(Inpatient Stay Value Set\)\. 

2\.	Identify the admission date for the stay\.

- An outpatient visit \(Visit Setting Unspecified Value Set\) __*with*__ \(Outpatient POS Value Set\)__* with*__ a principal diagnosis of substance use disorder \(AOD Abuse and Dependence Value Set\)\.
- An outpatient visit \(BH Outpatient Value Set\)__* with*__ a principal diagnosis of substance use disorder \(AOD Abuse and Dependence Value Set\)\.
- An intensive outpatient encounter or partial hospitalization \(Visit Setting Unspecified Value Set\) __*with*__ POS code 52__* with*__ a principal diagnosis of substance use disorder \(AOD Abuse and Dependence Value Set\)\.
- An intensive outpatient encounter or partial hospitalization \(Partial Hospitalization or Intensive Outpatient Value Set\)__* with*__ a principal diagnosis of substance use disorder \(AOD Abuse and Dependence Value Set\)\.
- A non\-residential substance abuse treatment facility visit \(Visit Setting Unspecified Value Set\) __*with*__ \(Nonresidential Substance Abuse Treatment Facility POS Value Set\)__* with*__ a principal diagnosis of substance use disorder \(AOD Abuse and Dependence Value Set\)\.
- A community mental health center visit \(Visit Setting Unspecified Value Set\) __*with*__ POS code 53 __*with*__ a principal diagnosis of substance use disorder \(AOD Abuse and Dependence Value Set\)\.
- A telehealth visit \(Visit Setting Unspecified Value Set\) __*with*__ \(Telehealth POS Value Set\)__* with*__ a principal diagnosis of substance use disorder \(AOD Abuse and Dependence Value Set\)\.
- A substance use disorder service \(Substance Use Disorder Services Value Set\) __*with*__ a principal diagnosis of substance use disorder \(AOD Abuse and Dependence Value Set\)\.
- Substance use disorder counseling and surveillance \(Substance Abuse Counseling and Surveillance Value Set\) __*with*__ a principal diagnosis of substance use disorder \(AOD Abuse and Dependence Value Set\)\. Do not include laboratory claims \(claims with POS code 81\)\.
- An opioid treatment service that bills monthly or weekly \(OUD Weekly Non Drug Service Value Set; OUD Monthly Office Based Treatment Value Set\) __*with*__ a principal diagnosis of substance use disorder \(AOD Abuse and Dependence Value Set\)\.
- Residential behavioral health treatment \(Residential Behavioral Health Treatment Value Set\) __*with*__ a principal diagnosis of substance use disorder \(AOD Abuse and Dependence Value Set\)\.
- A telephone visit \(Telephone Visits Value Set\) __*with*__ a principal diagnosis of substance use disorder \(AOD Abuse and Dependence Value Set\)\. 
- An e\-visit or virtual check\-in \(Online Assessments Value Set\) __*with*__ a principal diagnosis of substance use disorder \(AOD Abuse and Dependence Value Set\)\.
- A pharmacotherapy dispensing event \(Alcohol Use Disorder Treatment Medications List; Opioid Use Disorder Treatment Medications List\) or medication treatment event \(AOD Medication Treatment Value Set; OUD Weekly Drug Treatment Service Value Set\)\. 

__*Note:*__* Follow\-up does not include withdrawal management\. Exclude all withdrawal management events \(Detoxification Value Set\) when identifying follow\-up care for numerator compliance\. Detoxification does not need to be excluded from pharmacotherapy dispensing events identified using pharmacy claims \(Alcohol Use Disorder Treatment Medications List; Opioid Use Disorder Treatment Medications List\), because detoxification codes are not used on pharmacy claims\.*

### Opioid Use Disorder Treatment Medications

Description

Prescription

Antagonist 

- Naltrexone \(oral and injectable\) 

Partial agonist

- Buprenorphine \(sublingual tablet, injection, implant\)__\*__
- Buprenorphine/naloxone \(sublingual tablet, buccal film, sublingual film\)

__\*__Buprenorphine administered via transdermal patch or buccal film is not included because it is FDA\-approved for the treatment of pain, not for opioid use disorder\.

### Alcohol Use Disorder Treatment Medications

Description

Prescription

Aldehyde dehydrogenase inhibitor

- Disulfiram \(oral\)

Antagonist 

- Naltrexone \(oral and injectable\) 

Other

- Acamprosate \(oral and delayed\-release tablet\)

*Note*

- *Methadone is not included on the medication lists for this measure\. Methadone for opioid use disorder is only administered or dispensed by federally certified opioid treatment programs and does not show up in pharmacy claims data\. A pharmacy claim for methadone would be more indicative of treatment for pain than for an opioid use disorder and therefore is not included on medication lists\. The AOD Medication Treatment Value Set and OUD Weekly Drug Treatment Service Value Set include codes that identify methadone treatment for opioid use disorder because these codes are used on medical claims, not on pharmacy claims\.*

__Data Elements for Reporting __

Organizations that submit HEDIS data to NCQA must provide the following data elements\.

__*Table FUI\-1/2/3: Data Elements for Follow\-Up After High Intensity Care for Substance Use Disorder*__

Metric

Age

Data Element

Reporting Instructions

FollowUp30Day

13\-17

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

Rules for Allowable Adjustments of HEDIS

The “Rules for Allowable Adjustments of HEDIS” \(the “Rules”\) describe how NCQA’s HEDIS measure specifications can be adjusted for other populations, if applicable\. The Rules, reviewed and approved by NCQA measure experts, provide for expanded use of HEDIS measures without changing their clinical intent\.

__Adjusted HEDIS measures may not be used for HEDIS health plan reporting\. __

### Rules for Allowable Adjustments of Follow\-Up After High Intensity Care for Substance Use Disorder

__NONCLINICAL COMPONENTS__

__Eligible Population__

__Adjustments Allowed \(Yes/No\)__

__Notes__

Product lines

Yes

Organizations are not required to use product line criteria; product lines may be combined and all \(or no\) product line criteria may be used\.

Ages

Yes

The age determination date\(s\) may be changed \(13 years as of discharge date\)\. 

Changing denominator age range is allowed\.

Continuous enrollment, allowable gap

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

__*Note:*__* Organizations may assess at the member level by applying measure logic appropriately \(i\.e\.,* *percentage of acute inpatient hospitalizations, residential treatment or withdrawal management visits for a diagnosis of substance use disorder that result in a follow\-up visit or service for substance use disorder\)\.*

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

Medication lists, value sets and logic may not be changed\.

<a id="_Toc74816311"></a><a id="_Toc171402999"></a>

