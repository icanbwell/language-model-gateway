## <a id="Initiation_Engagement_SUD_Treat_IET"></a><a id="_Toc400546164"></a><a id="_Toc74826750"></a><a id="_Toc171403033"></a><a id="IET"></a>Initiation and Engagement of Substance Use Disorder Treatment \(IET\)

Summary of Changes to HEDIS MY 2025

- Added a laboratory claim exclusion to a value set for which laboratory claims should not be used\.
- Removed the data source reporting requirement from the race and ethnicity stratification\. 

__Description__

The percentage of new substance use disorder \(SUD\) episodes that result in treatment initiation and engagement\. Two rates are reported: 

- *Initiation of SUD Treatment\. *The percentage of new SUD episodes that result in treatment initiation through an inpatient SUD admission, outpatient visit, intensive outpatient encounter, partial hospitalization, telehealth visit or medication treatment within 14 days\.
- *Engagement of SUD Treatment\.* The percentage of new SUD episodes that have evidence of treatment engagement within 34 days of initiation\.

__Definitions__

Intake period

November 15 of the year prior to the measurement year–November 14 of the measurement year\. The intake period is used to capture new SUD episodes\. 

SUD episode

An encounter during the intake period with a diagnosis of SUD\. 

*For visits that result in an inpatient stay*, the inpatient discharge is the SUD episode \(an SUD diagnosis is not required for the inpatient stay; use the diagnosis from the visit that resulted in the inpatient stay to determine the diagnosis cohort\)\.

SUD episode date

The date of service for an encounter during the intake period with a diagnosis   
of SUD\. 

For a visit \(not resulting in an inpatient stay\), *the SUD episode date is the date of service\. *

For an inpatient stay or for withdrawal management \(i\.e\., detoxification\) that occurred during an inpatient stay, *the SUD episode date is the date of discharge\.*

For withdrawal management \(i\.e\., detoxification\), other than those that occurred during an inpatient stay, *the SUD episode date is the date of service\.*

For direct transfers, *the SUD episode date is the discharge date from the last admission* \(an SUD diagnosis is not required for the transfer; use the diagnosis from the initial admission to determine the diagnosis cohort\)\.

Date of service for services billed weekly or monthly

For an opioid treatment service that bills monthly or weekly \(OUD Weekly Non Drug Service Value Set; OUD Monthly Office Based Treatment Value Set; OUD Weekly Drug Treatment Service Value Set\), if the service includes a range of dates, then use the earliest date as the date of service\. Use this date for all relevant events \(the SUD episode date, negative diagnosis history and numerator events\)\.

Direct transfer

A __direct transfer__ is when the discharge date from the first inpatient setting precedes the admission date to a second inpatient setting by one calendar day or less\. For example: 

- An inpatient discharge on June 1, followed by an admission to another inpatient setting on June 1,* is a direct transfer\.*
- An inpatient discharge on June 1, followed by an admission to an inpatient setting on June 2, *is a direct transfer\.*
- An inpatient discharge on June 1, followed by an admission to another inpatient setting on June 3,* is not a direct transfer;* these are two distinct inpatient stays\.

Use the following method to identify admissions to and discharges from inpatient settings\.

1. Identify all acute and nonacute inpatient stays \(Inpatient Stay Value Set\)\.
2. Identify the admission and discharge dates for the stay\.

__Eligible Population__

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

Age

13 years and older as of the SUD episode date\. Report three age stratifications and a total:

- 13–17 years\.
- 18–64 years\.

- 65\+ years\.
- Total\.

The total is the sum of the age stratifications\.

SUD diagnosis cohort stratification 

Report the following SUD diagnosis cohort stratifications and a total: 

- Alcohol use disorder\.
- Opioid use disorder\.
- Other substance use disorder\.
- Total\.

The total is the sum of the SUD diagnosis cohort stratifications\.

Continuous enrollment

194 days prior to the SUD episode date through 47 days after the SUD episode date \(242 total days\)\. 

Allowable gap

None\.

Anchor date

None\.

Benefits

Medical, pharmacy and chemical dependency \(inpatient and outpatient\)\.

__Note: __Members with withdrawal management/detoxification\-only chemical dependency benefits do not meet these criteria\.

Event/diagnosis

New episode of SUD during the intake period\. 

Follow the steps below to identify the denominator for both rates\. 

__*Step 1 *__

Identify all SUD episodes\. Any of the following meet criteria:

- An outpatient visit \(Visit Setting Unspecified Value Set\) __*with*__ \(Outpatient POS Value Set\) __*with*__ one of the following: Alcohol Abuse and Dependence Value Set, Opioid Abuse and Dependence Value Set, Other Drug Abuse and Dependence Value Set\.
- An outpatient visit \(BH Outpatient Value Set\)__* with*__ one of the following: Alcohol Abuse and Dependence Value Set, Opioid Abuse and Dependence Value Set, Other Drug Abuse and Dependence Value Set\.
- An intensive outpatient encounter or partial hospitalization \(Visit Setting Unspecified Value Set\) __*with*__ POS code 52 __*with*__ one of the following: Alcohol Abuse and Dependence Value Set, Opioid Abuse and Dependence Value Set, Other Drug Abuse and Dependence Value Set\.
- An intensive outpatient encounter or partial hospitalization \(Partial Hospitalization or Intensive Outpatient Value Set\)__* with*__ one of the following: Alcohol Abuse and Dependence Value Set, Opioid Abuse and Dependence Value Set, Other Drug Abuse and Dependence Value Set\.
- A non\-residential substance abuse treatment facility visit \(Visit Setting Unspecified Value Set\) __*with*__ \(Nonresidential Substance Abuse Treatment Facility POS Value Set\) __*with*__ one of the following: Alcohol Abuse and Dependence Value Set, Opioid Abuse and Dependence Value Set, Other Drug Abuse and Dependence Value Set\.
- A community mental health center visit \(Visit Setting Unspecified Value Set\) __*with*__ POS code 53 __*with*__ one of the following: Alcohol Abuse and Dependence Value Set, Opioid Abuse and Dependence Value Set, Other Drug Abuse and Dependence Value Set\.

- A telehealth visit \(Visit Setting Unspecified Value Set\) __*with*__ \(Telehealth POS Value Set\) __*with*__ one of the following: Alcohol Abuse and Dependence Value Set, Opioid Abuse and Dependence Value Set, Other Drug Abuse and Dependence Value Set\.
- A substance use disorder service \(Substance Use Disorder Services Value Set\) __*with*__ one of the following: Alcohol Abuse and Dependence Value Set, Opioid Abuse and Dependence Value Set, Other Drug Abuse and Dependence Value Set\.
- Substance use disorder counseling and surveillance \(Substance Abuse Counseling and Surveillance Value Set\) __*with*__ one of the following: Alcohol Abuse and Dependence Value Set, Opioid Abuse and Dependence Value Set, Other Drug Abuse and Dependence Value Set\. Do not include laboratory claims \(claims with POS code 81\)\.
- A withdrawal management event \(Detoxification Value Set\) __*with*__ one of the following: Alcohol Abuse and Dependence Value Set, Opioid Abuse and Dependence Value Set, Other Drug Abuse and Dependence Value Set\.
- An ED visit \(ED Value Set\) __*with *__one of the following: Alcohol Abuse and Dependence Value Set, Opioid Abuse and Dependence Value Set, Other Drug Abuse and Dependence Value Set\. 
- An acute or nonacute inpatient discharge __*with *__one of the following on the discharge claim: Alcohol Abuse and Dependence Value Set, Opioid Abuse and Dependence Value Set, Other Drug Abuse and Dependence Value Set\. To identify acute and nonacute inpatient discharges:

1\.	Identify all acute and nonacute inpatient stays \(Inpatient Stay Value Set\)\.

2\.	Identify the discharge date for the stay\.

- A telephone visit \(Telephone Visits Value Set\) __*with *__one of the following: Alcohol Abuse and Dependence Value Set, Opioid Abuse and Dependence Value Set, Other Drug Abuse and Dependence Value Set\. 
- An e\-visit or virtual check\-in \(Online Assessments Value Set\) __*with*__ one of the following: Alcohol Abuse and Dependence Value Set, Opioid Abuse and Dependence Value Set, Other Drug Abuse and Dependence Value Set\.
- An opioid treatment service \(OUD Weekly Non Drug Service Value Set; OUD Monthly Office Based Treatment Value Set; OUD Weekly Drug Treatment Service Value Set\) __*with*__ a diagnosis of opioid abuse or dependence \(Opioid Abuse and Dependence Value Set\)\. 

__*Step 2*__

Test for negative SUD diagnosis history\. Remove SUD episodes if the member had a SUD diagnosis \(Alcohol Abuse and Dependence Value Set, Opioid Abuse and Dependence Value Set, Other Drug Abuse and Dependence Value Set\) during the 194 days prior to the SUD episode date\. Do not include ED visits \(ED Value Set\), withdrawal management events \(Detoxification Value Set\) or lab claims \(claims with POS code 81\)\.

If the SUD episode was an inpatient stay, use the admission date to determine negative SUD history\. 

*For visits with an SUD diagnosis that resulted in an inpatient stay *\(where the inpatient stay becomes the SUD episode\)*,* use the earliest date of service to determine the negative SUD diagnosis history \(so that the visit that resulted in the inpatient stay is not considered a positive diagnosis history\)\. 

*For direct transfers,* use the first admission date to determine the negative SUD diagnosis history\.

__*Step 3*__

Test for negative SUD medication history\. Remove SUD episodes if any of the following occurred during the 194 days prior to the SUD episode date:

- An SUD medication treatment dispensing event \(Alcohol Use Disorder Treatment Medications List; Naltrexone Injection Medications List; Buprenorphine Oral Medications List; Buprenorphine Injection Medications List; Buprenorphine Implant Medications List; Buprenorphine Naloxone Medications List\)\. 
- An SUD medication administration event \(Naltrexone Injection Value Set, Buprenorphine Oral Value Set; Buprenorphine Oral Weekly Value Set; Buprenorphine Injection Value Set; Buprenorphine Naloxone Value Set; Buprenorphine Implant Value Set; Methadone Oral Value Set; Methadone Oral Weekly Value Set\)\. 

__*Step 4*__

Remove SUD episodes that do not meet continuous enrollment criteria\. Members must be continuously enrolled from 194 days before the SUD episode date through 47 days after the SUD episode date \(242 total days\), with no gaps\. 

__*Step 5*__

Deduplicate eligible episodes\. If a member has more than one eligible episode on the same day, include only one eligible episode\. For example, if a member has two eligible episodes on January 1, only one eligible episode would be included; then, if applicable, include the next eligible episode that occurs after January 1\. 

__Note:__ The denominator for this measure is based on episodes, not on members\. All eligible episodes that were not removed or deduplicated remain in the denominator\.

__*Step 6*__

Identify the SUD diagnosis cohort for each SUD episode\.

- If the SUD episode has a diagnosis of alcohol use disorder \(Alcohol Abuse and Dependence Value Set\), include the episode in the alcohol use disorder cohort\. 
- If the SUD episode has a diagnosis of opioid use disorder \(Opioid Abuse and Dependence Value Set\), include the episode in the opioid use disorder cohort\. 
- If the SUD episode has a diagnosis of SUD that is neither for opioid nor alcohol \(Other Drug Abuse and Dependence Value Set\), place the member in the other substance use disorder cohort\. 

Include SUD episodes in all SUD diagnosis cohorts for which they meet criteria\. For example, if the SUD episode has a diagnosis of alcohol use disorder and opioid use disorder, include the episode in the alcohol use disorder and opioid use disorder cohorts\. 

Required exclusions

Exclude members who meet either of the following criteria: 

- Members who use hospice services \(Hospice Encounter Value Set; Hospice Intervention Value Set\) or elect to use a hospice benefit any time during the measurement year\. Organizations that use the Monthly Membership Detail Data File to identify these members must use only the run date of the file to determine if the member elected to use a hospice benefit during the measurement year\. 
- Members who die any time during the measurement year\.

__Administrative Specification__

Denominator

The eligible population\.

Numerator

__*Initiation of SUD Treatment*__

Initiation of SUD treatment within 14 days of the SUD episode date\. Follow the steps below to identify numerator compliance\. 

__*Step 1*__

*If the SUD episode was an inpatient discharge*, the inpatient stay is considered initiation of treatment and the SUD episode is compliant\.

__*Step 2*__

*If the SUD episode was an opioid treatment service that bills monthly *\(OUD Monthly Office Based Treatment Value Set\), the opioid treatment service is considered initiation of treatment and the SUD episode is compliant\.

__*Step 3*__

For remaining SUD episodes \(those not compliant after steps 1–2\), identify episodes with at least one of the following on the SUD episode date or during the 13 days after the SUD episode date \(14 total days\)\. 

- An acute or nonacute inpatient admission __*with*__ a diagnosis \(on the discharge claim\) of one of the following: Alcohol Abuse and Dependence Value Set, Opioid Abuse and Dependence Value Set, Other Drug Abuse and Dependence Value Set\. To identify acute and nonacute inpatient admissions:

1. Identify all acute and nonacute inpatient stays \(Inpatient Stay Value Set\)\.
2. Identify the admission date for the stay\.

- An outpatient visit \(Visit Setting Unspecified Value Set\) __*with*__ \(Outpatient POS Value Set\) __*with *__one of the following: Alcohol Abuse and Dependence Value Set, Opioid Abuse and Dependence Value Set, Other Drug Abuse and Dependence Value Set\.
- An outpatient visit \(BH Outpatient Value Set\)__* with *__one of the following: Alcohol Abuse and Dependence Value Set, Opioid Abuse and Dependence Value Set, Other Drug Abuse and Dependence Value Set\.
- An intensive outpatient encounter or partial hospitalization \(Visit Setting Unspecified Value Set\) __*with*__ POS code 52__* with *__one of the following: Alcohol Abuse and Dependence Value Set, Opioid Abuse and Dependence Value Set, Other Drug Abuse and Dependence Value Set\.
- An intensive outpatient encounter or partial hospitalization \(Partial Hospitalization or Intensive Outpatient Value Set\)__* with *__one of the following: Alcohol Abuse and Dependence Value Set, Opioid Abuse and Dependence Value Set, Other Drug Abuse and Dependence Value Set\.
- A non\-residential substance abuse treatment facility visit \(Visit Setting Unspecified Value Set\) __*with*__ \(Nonresidential Substance Abuse Treatment Facility POS Value Set\)__* with *__one of the following: Alcohol Abuse and 

Dependence Value Set, Opioid Abuse and Dependence Value Set, Other Drug Abuse and Dependence Value Set\.

- A community mental health center visit \(Visit Setting Unspecified Value Set\) __*with*__ POS code 53__* with *__one of the following: Alcohol Abuse and Dependence Value Set, Opioid Abuse and Dependence Value Set, Other Drug Abuse and Dependence Value Set\.
- A telehealth visit \(Visit Setting Unspecified Value Set\) __*with*__ \(Telehealth POS Value Set\)__* with *__one of the following: Alcohol Abuse and Dependence Value Set, Opioid Abuse and Dependence Value Set, Other Drug Abuse and Dependence Value Set\.
- A substance use disorder service \(Substance Use Disorder Services Value Set\) __*with *__one of the following: Alcohol Abuse and Dependence Value Set, Opioid Abuse and Dependence Value Set, Other Drug Abuse and Dependence Value Set\.
- Substance use disorder counseling and surveillance \(Substance Abuse Counseling and Surveillance Value Set\) __*with *__one of the following: Alcohol Abuse and Dependence Value Set, Opioid Abuse and Dependence Value Set, Other Drug Abuse and Dependence Value Set\)\. Do not include laboratory claims \(claims with POS code 81\)\.
- A telephone visit \(Telephone Visits Value Set\) __*with *__one of the following: Alcohol Abuse and Dependence Value Set, Opioid Abuse and Dependence Value Set, Other Drug Abuse and Dependence Value Set\.
- An e\-visit or virtual check\-in \(Online Assessments Value Set\) __*with *__one of the following: Alcohol Abuse and Dependence Value Set, Opioid Abuse and Dependence Value Set, Other Drug Abuse and Dependence Value Set\.
- A weekly or monthly opioid treatment service \(OUD Weekly Non Drug Service Value Set; OUD Monthly Office Based Treatment Value Set; OUD Weekly Drug Treatment Service Value Set\)\.
- For SUD episodes in the alcohol use disorder cohort, an alcohol use disorder medication treatment dispensing event \(Alcohol Use Disorder Treatment Medications List\) or a medication administration event \(Naltrexone Injection Value Set\)\. 
- For SUD episodes in the opioid use disorder cohort, an opioid use disorder medication treatment dispensing event \(Naltrexone Oral Medications List; Naltrexone Injection Medications List; Buprenorphine Oral Medications List; Buprenorphine Injection Medications List; Buprenorphine Implant Medications List; Buprenorphine Naloxone Medications List\) or a medication administration event \(Naltrexone Injection Value Set, Buprenorphine Oral Value Set, Buprenorphine Oral Weekly Value Set, Buprenorphine Injection Value Set, Buprenorphine Implant Value Set, Buprenorphine Naloxone Value Set, Methadone Oral Value Set, Methadone Oral Weekly Value Set\)\.

For all initiation events except medication treatment dispensing events and medication administration events, initiation on the same day as the SUD episode date must be with different providers in order to count\.

Remove the member from the denominator for both indicators *\(*Initiation of SUD Treatment and Engagement of SUD Treatment\) if the initiation of treatment event is an inpatient stay with a discharge date after November 27 of the measurement year\.

__*Engagement of SUD Treatment*__

Follow the steps below to identify numerator compliance\.

If Initiation of SUD Treatment was an inpatient admission, the 34\-day period for engagement begins the day after discharge\.

__*Step 1*__

Identify all SUD episodes compliant for the Initiation of SUD Treatment numerator\. SUD episodes that are not compliant for Initiation of SUD Treatment are not compliant for Engagement of SUD Treatment\. 

__*Step 2*__

Identify SUD episodes that had at least one weekly or monthly opioid treatment service with medication administration \(OUD Monthly Office Based Treatment Value Set; OUD Weekly Drug Treatment Service Value Set\) on the day after the initiation encounter through 34 days after the initiation event\. The opioid treatment service is considered engagement of treatment and the SUD episode is compliant\. 

__*Step 3*__

Identify SUD episodes with long\-acting SUD medication administration events on the day after the initiation encounter through 34 days after the initiation event\. The long\-acting SUD medication administration event is considered engagement of treatment and the SUD episode is compliant\. Any of the following meet criteria:

- For SUD episodes in the alcohol use disorder cohort, an alcohol use disorder medication treatment dispensing event \(Naltrexone Injection Medications List\) or a medication administration event \(Naltrexone Injection Value Set\)\.
- For SUD episodes in the opioid use disorder cohort, an opioid use disorder medication treatment dispensing event \(Naltrexone Injection Medications List; Buprenorphine Injection Medications List; Buprenorphine Implant Medications List\) or a medication administration event \(Naltrexone Injection Value Set; Buprenorphine Injection Value Set; Buprenorphine Implant Value Set\)\.

__*Step 4*__

For remaining SUD episodes, identify episodes with at least two of the following \(any combination\) on the day after the initiation encounter through 34 days after the initiation event:

- Engagement visit\.
- Engagement medication treatment event\.

Two engagement visits may be on the same date of service, but they must be with different providers to count as two events\. An engagement visit on the same date of service as an engagement medication treatment event meets criteria \(there is no requirement that they be with different providers\)\.

Refer to the descriptions below to identify engagement visits and engagement medication treatment events\. 

__*Engagement visits*__

Any of the following meet criteria for an engagement visit:

- An acute or nonacute inpatient admission __*with*__ a diagnosis \(on the discharge claim\) of one of the following: Alcohol Abuse and Dependence Value Set, Opioid Abuse and Dependence Value Set, Other Drug Abuse and Dependence Value Set\. To identify acute or nonacute inpatient admissions:

1. Identify all acute and nonacute inpatient stays \(Inpatient Stay Value Set\)\.
2. Identify the admission date for the stay\. 

- An outpatient visit \(Visit Setting Unspecified Value Set\) __*with*__ \(Outpatient POS Value Set\) __*with *__one of the following: Alcohol Abuse and Dependence Value Set, Opioid Abuse and Dependence Value Set, Other Drug Abuse and Dependence Value Set\.
- An outpatient visit \(BH Outpatient Value Set\)__* with *__one of the following: Alcohol Abuse and Dependence Value Set, Opioid Abuse and Dependence Value Set, Other Drug Abuse and Dependence Value Set\.
- An intensive outpatient encounter or partial hospitalization \(Visit Setting Unspecified Value Set\) __*with*__ POS code 52 __*with *__one of the following: Alcohol Abuse and Dependence Value Set, Opioid Abuse and Dependence Value Set, Other Drug Abuse and Dependence Value Set\.
- An intensive outpatient encounter or partial hospitalization \(Partial Hospitalization or Intensive Outpatient Value Set\)__* with *__one of the following: Alcohol Abuse and Dependence Value Set, Opioid Abuse and Dependence Value Set, Other Drug Abuse and Dependence Value Set\.
- A non\-residential substance abuse treatment facility visit \(Visit Setting Unspecified Value Set\) __*with*__ \(Nonresidential Substance Abuse Treatment Facility POS Value Set\)__* with *__one of the following: Alcohol Abuse and Dependence Value Set, Opioid Abuse and Dependence Value Set, Other Drug Abuse and Dependence Value Set\.
- A community mental health center visit \(Visit Setting Unspecified Value Set\) __*with*__ POS code 53 __*with *__one of the following: Alcohol Abuse and Dependence Value Set, Opioid Abuse and Dependence Value Set, Other Drug Abuse and Dependence Value Set\.
- A telehealth visit: \(Visit Setting Unspecified Value Set\) __*with*__ \(Telehealth POS Value Set\)__* with *__one of the following: Alcohol Abuse and Dependence Value Set, Opioid Abuse and Dependence Value Set, Other Drug Abuse and Dependence Value Set\.
- A substance use disorder service \(Substance Use Disorder Services Value Set\) __*with *__one of the following: Alcohol Abuse and Dependence Value Set, Opioid Abuse and Dependence Value Set, Other Drug Abuse and Dependence Value Set\.
- Substance use disorder counseling and surveillance \(Substance Abuse Counseling and Surveillance Value Set\) __*with *__one of the following: Alcohol Abuse and Dependence Value Set, Opioid Abuse and Dependence Value Set, Other Drug Abuse and Dependence Value Set\)\. Do not include laboratory claims \(claims with POS code 81\)\.
- A telephone visit \(Telephone Visits Value Set\) __*with *__one of the following: Alcohol Abuse and Dependence Value Set, Opioid Abuse and Dependence Value Set, Other Drug Abuse and Dependence Value Set\. 
- An e\-visit or virtual check\-in \(Online Assessments Value Set\) __*with *__one   
of the following: Alcohol Abuse and Dependence Value Set, Opioid   
Abuse and Dependence Value Set, Other Drug Abuse and Dependence Value Set\. 
- An opioid treatment service \(OUD Weekly Non Drug Service Value Set\)\.

*Engagement medication treatment events*

Either of the following meets criteria for a medication treatment event:

- For SUD episodes in the alcohol use disorder cohort, an alcohol use disorder medication treatment dispensing event \(Alcohol Use Disorder Treatment Medications List\)\. 
- For SUD episodes in the opioid use disorder cohort, an opioid use disorder medication treatment dispensing event \(Naltrexone Oral Medications List; Buprenorphine Oral Medications List; Buprenorphine Naloxone Medications List\) or a medication administration event \(Buprenorphine Oral Value Set; Buprenorphine Oral Weekly Value Set; Buprenorphine Naloxone Value Set; Methadone Oral Value Set; Methadone Oral Weekly Value Set\)\.

__*Alcohol Use Disorder Treatment Medications*__

__Description__

__Prescription__

Aldehyde dehydrogenase inhibitor

- Disulfiram \(oral\)

Antagonist

- Naltrexone \(oral and injectable\)

Other

- Acamprosate \(oral; delayed\-release tablet\)

__*Opioid Use Disorder Treatment Medications *__

Description

Prescription

Medication Lists

Antagonist 

- Naltrexone \(oral\) 

Naltrexone Oral Medications List

Antagonist

- Naltrexone \(injectable\)

Naltrexone Injection Medications List

Partial agonist

- Buprenorphine \(sublingual tablet\) 

Buprenorphine Oral Medications List

Partial agonist

- Buprenorphine \(injection\)

Buprenorphine Injection Medications List

Partial agonist

- Buprenorphine \(implant\) 

Buprenorphine Implant Medications List

Partial agonist

- Buprenorphine/naloxone \(sublingual tablet, buccal film, sublingual film\)

Buprenorphine Naloxone Medications List

*Note*

- *Organizations may have different methods for billing intensive outpatient encounters and partial hospitalizations\. Some organizations may bill comparable to outpatient billing, with separate claims for each date of service; others may bill comparable to inpatient billing, with an admission date, a discharge date and units of service\. Organizations whose billing is comparable to inpatient billing may count each unit of service as an individual visit\. The unit of service must have occurred during the required time frame for the rate\.*
- *Methadone is not included on the medication lists for this measure\. Methadone for opioid use disorder \(OUD\) administered or dispensed by federally certified opioid treatment programs \(OTP\) is billed on  
a medical claim\. A pharmacy claim for methadone would be indicative of treatment for pain rather   
than OUD\.*

__Data Elements for Reporting__

Organizations that submit HEDIS data to NCQA must provide the following data elements\.

__*Table IET\-A\-1/2/3: Data Elements for Initiation and Engagement of Substance Use Disorder Treatment*__

__Metric__

__Diagnosis__

__Age__

__Data Element __

__Reporting Instructions__

Initiation

Alcohol

13\-17

Benefit

Metadata

Engagement

Opioid

18\-64

EligiblePopulation

For each Stratification, repeat per Metric

Other

65\+

ExclusionAdminRequired

For each Stratification, repeat per Metric

Total

Total

NumeratorByAdmin

For each Metric and Stratification

Rate

\(Percent\)

__*Table IET\-B\-1/2/3: Data Elements for Initiation and Engagement of Substance Use Disorder Treatment: Stratifications by Race*__

Metric

Race

Data Element

Reporting Instructions

Initiation

AmericanIndianOrAlaskaNative

EligiblePopulation

For each Stratification, repeat per Metric

Engagement

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

__*Table IET\-C\-1/2/3: Data Elements for Initiation and Engagement of Substance Use Disorder Treatment: Stratifications by Ethnicity*__

__Metric__

__Ethnicity__

__Data Element__

__Reporting Instructions__

Initiation

HispanicOrLatino

EligiblePopulation

For each Stratification, repeat per Metric

Engagement

NotHispanicOrLatino

Numerator

For each Metric and Stratification

AskedButNoAnswer

Rate

\(Percent\)

Unknown

__Rules for Allowable Adjustments of HEDIS__

The “Rules for Allowable Adjustments of HEDIS” \(the “Rules”\) describe how NCQA’s HEDIS measure specifications can be adjusted for other populations, if applicable\. The Rules, reviewed and approved by NCQA measure experts, provide for expanded use of HEDIS measures without changing their clinical intent\. 

__Adjusted HEDIS measures may not be used for HEDIS health plan reporting\. __

__*Rules for Allowable Adjustments of Initiation and Engagement of Substance Use Disorder Treatment*__

<a id="_Hlk4502537"></a>__NONCLINICAL COMPONENTS__

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

SUD diagnosis cohorts 

Yes, with limits

Reporting each stratum or combined strata is allowed\.

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

Only events that contain \(or map to\) codes in the medication lists and value sets may be used to identify visits\. Medication lists and value sets and logic may not be changed\.* *

__Denominator Exclusions__

__Adjustments Allowed \(Yes/No\)__

__Notes__

Required exclusions

Yes

The hospice and deceased member exclusions are not required\. Refer to *Exclusions* in the *Guidelines for the Rules for Allowable Adjustments*\.

Numerator Criteria

Adjustments Allowed \(Yes/No\)

Notes

- Initiation of SUD Treatment
- Engagement of SUD Treatment

No

Medication lists, value sets and logic may not be changed\.

