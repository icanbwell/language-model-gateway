## <a id="Pharmacotherapy_OUD_POD"></a><a id="_Toc74816312"></a><a id="_Toc171403000"></a><a id="SSD"></a>Pharmacotherapy for Opioid Use Disorder \(POD\)\*

__\*Adapted with permission by NCQA from the “Continuity of Pharmacotherapy for Opioid Use Disorder” measure owned by The RAND Corporation\.__

Summary of Changes to HEDIS MY 2025

- Removed the data source reporting requirement from the race and ethnicity stratification\.

Description

The percentage of opioid use disorder \(OUD\) pharmacotherapy events that lasted at least 180 days among members 16 years of age and older with a diagnosis of OUD and a new OUD pharmacotherapy event\. 

Definitions

Intake period

July 1 of the year prior to the measurement year to June 30 of the measurement year\. 

OUD dispensing event

OUD pharmacotherapy identified using pharmacy data \(medication lists\)\.

OUD medication administration event

OUD pharmacotherapy identified using medical claims data \(value sets\)\.

Treatment period start date

The date of an OUD dispensing event or OUD medication administration event with a negative medication history during the intake period\.

Negative medication history

To qualify for negative medication history, the following criteria must be met:

- A period of 31 days prior to the OUD dispensing event or OUD medication administration event when the member had no OUD dispensing events or OUD medication administration events\.
- A period of 31 days prior to the OUD dispensing event or OUD medication administration event when the member was not already receiving OUD pharmacotherapy\. For example, if an OUD dispensing event has a date of service of January 1, the 31 days prior includes December 1–31\. If the member had received a buprenorphine implant \(180 days supply\) any time during the 179 days prior to December 1, the member is already receiving OUD pharmacotherapy on December 1 and does not have a negative medication history\.

Treatment period

A period of 180 calendar days, beginning on the treatment period start date through 179 days after the treatment period start date\.

__Note:__ Members can have multiple treatment period start dates and treatment periods during the measurement year\. Treatment periods can overlap\.

Determining same or different medications 

Medication lists and value sets that are in the same row of the Opioid Use Disorder Treatment Medications table are the “same medication\.” For example, if a member has a dispensing event from the Buprenorphine Oral Medications List and an encounter with a code from the Buprenorphine Oral Value Set, this is considered two dispensing events for the same medication\. 

Medication lists and value sets that are in different rows of the Opioid Use Disorder Treatment Medications table are “different medications\.” For example, if a member has a dispensing event from the Buprenorphine Oral Medications List and a dispensing event from the Buprenorphine Injection Medications List, this is considered two dispensing events for different medications\.

Direct transfer

A __direct transfer__ is when the discharge date from the first inpatient setting precedes the admission date to a second inpatient setting by one calendar day or less\. For example:

- An inpatient discharge on June 1, followed by an admission to another inpatient setting on June 1, *is a direct transfer\.*
- An inpatient discharge on June 1, followed by an admission to an inpatient setting on June 2, *is a direct transfer\.*
- An inpatient discharge on June 1, followed by an admission to another inpatient setting on June 3, *is not a direct transfer;* these are two distinct inpatient stays\.

Use the following method to identify admissions to and discharges from inpatient settings\.

1\.	Identify all acute and nonacute inpatient stays \(Inpatient Stay Value Set\)\.

2\.	Identify the admission and discharge dates for the stay\.

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

16 years and older as of the treatment period start date\. Report two age stratifications and total rate: 

- 16–64 years\.
- 65 years and older\.
- Total\.

The total is the sum of the age stratifications\.

Continuous enrollment

31 days prior to the treatment period start date through 179 days after the treatment period start date \(211 total days\)\.

Allowable gap 

None\.

Anchor date

None\.

Benefits

Medical and pharmacy\.

Event/diagnosis

Follow the steps below to identify eligible events\. 

*Step 1*

Identify members with any diagnosis of OUD \(Opioid Abuse and Dependence Value Set\) during the intake period\. Do not include laboratory claims \(claims with POS code 81\)\.

__*Step 2 *__

For each member identified in step 1, identify all OUD dispensing events or OUD medication administration events during the intake period\. Use all medication lists and value sets in the Opioid Use Disorder Treatment Medications table below to identify OUD dispensing events and OUD administration events\.

__*Step 3 *__

Test for negative medication history\. For each OUD dispensing event or OUD medication administration event in step 2, test for a negative medication history\. Remove events that do not have a negative medication history\. All remaining events with a negative medication history are considered treatment period start dates\. 

Identify start and end dates for OUD dispensing events and OUD medication administration events\. The start date is the event date and the end date is the start date plus the days supply minus one\. 

For OUD dispensing events and OUD medication administration events with overlapping days supply, apply the following rules:

- For multiple OUD dispensing events or OUD medication administration events for different medications on the same or different dates of service with overlapping days supply, calculate the start and end dates for each medication individually\. For example, if there is a 7\-days supply of oral buprenorphine on January 1 and a 31\-days supply of buprenorphine injection on January 5:

- The oral buprenorphine start date is January 1 and the end date is January 7\.
- The buprenorphine injection start date is January 5 and the end date is February 4\.
- For multiple OUD dispensing events or OUD medication administration events for the same medication on the same date of service or on different dates of service with overlapping days supply, sum the days supply and then calculate start and end dates\. For example: 
- If a 7\-days supply and a 14\-days supply of buprenorphine are dispensed on January 1, the start date is January 1 and the end date is January 21\. 
- If a 7\-days supply of buprenorphine is dispensed on January 1 and January 5, the start date is January 1 and the end date is January 14\. 
- If a member has three codes \(or one code billed as three units\) from the Buprenorphine Oral Weekly Value Set on January 1, the start date is January 1 and the end date is January 21\.
- If a member has four codes \(or one code billed as four units\) from the Methadone Oral Weekly Value Set on January 1, the start date is January 1 and the end date is January 28\.

For OUD medication administration events identified using a value set, use the days supply listed in the Opioid Use Disorder Treatment Medications table\. 

For OUD dispensing events identified using a medication list, use days supply in the pharmacy data\. If days supply is not available in the pharmacy data then use the days supply listed for the corresponding value set\. If the pharmacy data for a buprenorphine oral medication does not contain days supply, count as a 7\-days supply\.

__*Step 4*__

Remove any treatment period start dates where the member had an acute or nonacute inpatient stay of 8 or more days during the treatment period:

1\.	Identify all acute and nonacute inpatient stays \(Inpatient Stay Value Set\)\.

2\.	Identify the admission and discharge dates for the stay\. 

3\.	Calculate length of stay \(LOS\) as the admission date through and including the discharge date\. If there are direct transfers between stays, add the LOS from any subsequent direct transfers to the initial LOS to calculate a total LOS\. If direct transfer days overlap, count each day only once\.

For example:

- Remove a July 1 treatment period start date where a member was admitted for an inpatient hospital stay on August 1 and discharged on August 8 \(LOS = 8 days\)\.
- Remove a July 1 treatment period start date where a member had an acute inpatient stay \(admission date August 1; discharge date August 4; LOS = 4 days\), followed by a direct transfer to a nonacute inpatient facility \(admission date August 5; discharge date August 8; LOS = 4 days\)\.   
Total LOS = 8 days\.

Do not remove a July 1 treatment period start date where a member   
had an acute inpatient stay \(admission date August 1; discharge date August 4; LOS = 4 days\), followed by a direct transfer to a nonacute inpatient facility \(admission date August 4; discharge date August 7,   
LOS = 4 days\)\. Total LOS = 7 days \(do not double count August 4\)\.

__*Step 5*__

Calculate continuous enrollment\. Members must be continuously enrolled from 31 days prior to the treatment period start date through 179 days after the treatment period start date \(211 total days\)\.

__Note:__ All treatment period start dates \(OUD dispensing events or OUD medication administration events\) that were not removed remain in the denominator\. The denominator for this measure is based on events, not members\.

__Required exclusions__

Exclude members who meet either of the following criteria:

- Members who use hospice services \(Hospice Encounter Value Set; Hospice Intervention Value Set\) or elect to use a hospice benefit any time during the measurement year\. Organizations that use the Monthly Membership Detail Data File to identify these members must use only the run date of the file to determine if the member elected to use a hospice benefit during the measurement year\. 
- Members who die any time during the measurement year\. 

Administrative Specification

Denominator

The eligible population\.

Numerator

New OUD pharmacotherapy events with OUD pharmacotherapy for 180 or more days without a gap in treatment of 8 or more consecutive days\. Use the steps below to identify the numerator\. 

*Step 1*

Identify the treatment period for each treatment period start date in the denominator\. Follow the steps below for each treatment period in the denominator\.

*Step 2*

Identify all OUD dispensing events and OUD medication administration events during the treatment period\. Use all the medication lists and value sets in the Opioid Use Disorder Treatment Medications table to identify OUD dispensing events and OUD medication administration events\.

*Step 3*

Identify start and end dates for OUD dispensing events and OUD medication administration events\. The start date is the event date and the end date is the start date plus the days supply minus one\. 

For OUD dispensing events and OUD medication administration events with overlapping days supply, apply the following rules:

- For multiple OUD dispensing events or OUD medication administration events for different medications on the same or different dates of service with overlapping days supply, calculate the start and end dates for each medication individually\. For example, if there is a 7\-days supply of oral buprenorphine on January 1 and a 31\-days supply of buprenorphine injection on January 5:
- The oral buprenorphine start date is January 1 and the end date is January 7\.

- The buprenorphine injection start date is January 5 and the end date is February 4\.
- For multiple OUD dispensing events or OUD medication administration events for the same medication on the same date of service or on different dates of service with overlapping days supply, sum the days supply and then calculate start and end dates\. For example: 
- If a 7\-days supply and a 14\-days supply of buprenorphine are dispensed on January 1, the start date is January 1 and the end date is January 21\. 
- If a 7\-days supply of buprenorphine is dispensed on January 1 and January 5, the start date is January 1 and the end date is January 14\. 
- If a member has three codes \(or one code billed as three units\) from the Buprenorphine Oral Weekly Value Set on January 1, the start date is January 1 and the end date is January 21\.
- If a member has four codes \(or one code billed as four units\) from the Methadone Oral Weekly Value Set on January 1, the start date is January 1 and the end date is January 28\.

For OUD medication administration events identified using a value set, use the days supply listed in the Opioid Use Disorder Treatment Medications table\. 

For OUD dispensing events identified using a medication list, use the days supply in the pharmacy data\. If days supply is not available in the pharmacy data, then use the days supply listed for the corresponding value set\. If the pharmacy data for a buprenorphine oral medication does not contain days supply, count as a 7\-days supply\.

*Step 4*

For each treatment period, using the start and end dates identified in step 3, determine calendar days covered by an OUD dispensing event or OUD medication administration event\. These covered days are referred to as “treatment days\.”

*Step 5*

Identify gaps in treatment days of 8 or more consecutive days\. 

*Step 6*

Determine numerator compliance\. 

If the treatment period does not contain any gaps in treatment of 8 or more consecutive calendar days, *the event is numerator compliant\. *

If the treatment period contains at least one gap in treatment of 8 or more consecutive calendar days, *the event is not numerator compliant\.* 

### Opioid Use Disorder Treatment Medications 

Description

Prescription

Medication Lists

Value Sets and Days Supply

Antagonist 

- Naltrexone \(oral\) 

Naltrexone Oral Medications List

NA—Codes do not exist

Antagonist

- Naltrexone \(injectable\)

Naltrexone Injection Medications List

Naltrexone Injection Value Set   
\(31 days supply\)

Partial agonist

- Buprenorphine \(sublingual tablet\) 

Buprenorphine Oral Medications List

Buprenorphine Oral Value Set   
\(1 day supply\)

Buprenorphine Oral Weekly Value Set \(7 days supply\)

Partial agonist

- Buprenorphine \(injection\)

Buprenorphine Injection Medications List

Buprenorphine Injection Value Set \(31 days supply\)

Partial agonist

- Buprenorphine \(implant\) 

Buprenorphine Implant Medications List

Buprenorphine Implant Value Set \(180 days supply\)

Partial agonist

- Buprenorphine/ naloxone \(sublingual tablet, buccal film, sublingual film\)

Buprenorphine Naloxone Medications List

Buprenorphine Naloxone Value Set \(1 day supply\)

Agonist

- Methadone \(oral\)

NA \(refer to *Note *below\)

Methadone Oral Value Set   
\(1 day supply\)

Methadone Oral Weekly Value Set   
\(7 days supply\)

*Note*

- *Methadone is not included on the medication lists for this measure\. Methadone for OUD administered or dispensed by federally certified opioid treatment programs \(OTP\) is billed on a medical claim\. A pharmacy claim for methadone would be indicative of treatment for pain rather than OUD\. *
- *The allowable gaps in the measure numerator of 7 or fewer consecutive days are used to account for weekly billing and other variations in billing practices and do not necessarily indicate that OUD pharmacotherapy ended\. For example, members receiving daily methadone treatment over their *  
*180\-day treatment period meet numerator criteria if their treatment is billed weekly\.*

__Data Elements for Reporting __

Organizations that submit HEDIS data to NCQA must provide the following data elements\. 

__*Table POD\-A\-1/2/3: Data Elements for Pharmacotherapy for Opioid Use Disorder*__

Metric

Age

Data Element

Reporting Instructions

PharmacotherapyOpioidUseDisorder

16\-64

Benefit

Metadata

65\+

EligiblePopulation 

For each Stratification

Total

ExclusionAdminRequired

For each Stratification

NumeratorByAdmin

For each Stratification

NumeratorBySupplemental

For each Stratification

Rate

\(Percent\)

### Table POD\-B\-1/2/3: Data Elements for Pharmacotherapy for Opioid Use: Stratifications by Race

Metric

Race

Data Element

Reporting Instructions

PharmacotherapyOpioidUseDisorder

AmericanIndianOrAlaskaNative

EligiblePopulation

For each Stratification

Asian

Numerator

For each Stratification

BlackOrAfricanAmerican 

Rate

\(Percent\)

NativeHawaiianOrOtherPacificIslander

White

SomeOtherRace

TwoOrMoreRaces

AskedButNoAnswer

Unknown

__*Table POD\-C\-1/2/3: Data Elements for Pharmacotherapy for Opioid Use: Stratifications by Ethnicity*__

Metric

Ethnicity

Data Element

Reporting Instructions

PharmacotherapyOpioidUseDisorder

HispanicOrLatino

EligiblePopulation

For each Stratification

NotHispanicOrLatino

Numerator

For each Stratification

AskedButNoAnswer

Rate

\(Percent\)

Unknown

Rules for Allowable Adjustments of HEDIS

The “Rules for Allowable Adjustments of HEDIS” \(the “Rules”\) describe how NCQA’s HEDIS measure specifications can be adjusted for other populations, if applicable\. The Rules, reviewed and approved by NCQA measure experts, provide for expanded use of HEDIS measures without changing their clinical intent\.

__Adjusted HEDIS measures may not be used for HEDIS health plan reporting\. __

### Rules for Allowable Adjustments of Pharmacotherapy for Opioid Use Disorder

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

Changing the denominator age range is allowed if the limits are within the specified age range\. The denominator age may not be expanded\.

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

Only events and diagnoses that contain \(or map to\) codes in the value sets and medication lists may be used to identify visits with a diagnosis\. Value sets, medication lists and logic may not be changed\. 

__*Note:*__* Organizations may assess at the member level by applying measure logic appropriately \(i\.e\.,* *percentage of pharmacotherapy events with OUD pharmacotherapy for 180 or more days with a diagnosis of OUD\)\.*

__Denominator Exclusions__

__Adjustments Allowed \(Yes/No\)__

__Notes__

Required exclusions

Yes

The hospice and deceased member exclusions are not required\. Refer to *Exclusions* in the *Guidelines for the Rules for Allowable Adjustments*\.

__Numerator Criteria__

__Adjustments Allowed \(Yes/No\)__

__Notes__

Pharmacotherapy Events

No

Medication lists, value sets and logic may not be changed\.

