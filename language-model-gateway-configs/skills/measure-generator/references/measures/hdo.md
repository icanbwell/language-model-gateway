## <a id="Use_of_Opioids_High_Dosage_HDO"></a><a id="_Toc171403017"></a>Use of Opioids at High Dosage \(HDO\)\*

__\*Adapted with financial support from CMS and with permission from the measure developer,   
Pharmacy Quality Alliance \(PQA\)\. __

Summary of Changes to HEDIS MY 2025

- No changes to this measure\. 

Description

The percentage of members 18 years of age and older who received prescription opioids at a high dosage \(average morphine milligram equivalent dose \[MME\] ≥90\) for ≥15 days during the measurement year\.

__Note:__ A lower rate indicates better performance\. 

Definitions

Calculating number of days covered for the denominator

Use the following steps to identify and calculate covered days for the denominator\.

*Step 1*

Identify dispensing events where multiple prescriptions for the same medication are dispensed with overlapping days supply \(i\.e\., dispensed on the same day *or* dispensed on different days with overlapping days supply\)\. Sum the days supply for these dispensing events\. 

Identify the start and end dates: The start date is the date of service of the earliest dispensing event and the end date is the start date plus the summed days supply minus one\. The start date through the end date are considered covered days\. For example:

- If there are three 7\-days supply dispensing events for the same medication on January 1, the start date is January 1 and the end date is January 21\. Covered days include January 1–21\. 
- If there are two 7\-days supply dispensing events for the same medication on January 1 and January 5, the start date is January 1 and the end date is January 14\. Covered days include January 1–14\.
- If there are three 7\-days supply dispensing events for the same medication on January 1, a 7\-days supply dispensing event on January 20, and a 7\-days supply dispensing event on January 28, the start date   
is January 1 and the end date is February 4\. Covered days include January 1–February 4\.__ __

*Step 2*

For all other dispensing events \(i\.e\., multiple prescriptions for the same medication on different days without overlap, and multiple prescriptions for different medications on the same or different days, with or without overlap\), identify the start and end dates for each dispensing event individually\. The start date through the end date are considered covered days\.

*Step 3*

Count the covered days\. Consider each calendar day covered by one or more medications to be one covered day\. 

Identifying same or different drugs

To identify “same” or “different” drugs, use Table HDO\-A, which identifies the medications lists for the measure\. Dispensing events from any of the Fentanyl medication lists, even if they are on different rows, are all considered the “same” drug\. 

For all other types of opioids, the table includes a “Medication Lists” column that identifies the “same” high\-risk medications by grouping them on the same row\. For example, a dispensing event from the Codeine Sulfate 15 mg Medications List is considered the same drug as a dispensing event from the Codeine Sulfate 30 mg Medications List\. Conversely, a dispensing event from the Codeine Sulfate 15 mg Medications List is considered a different drug than a dispensing event from the Acetaminophen Codeine 15 mg Medications List because they are in different table rows\.

Treatment period

*To identify the treatment period:* For all dispensing events, identify the start and end dates for each dispensing event individually\. The treatment period start date is the start date of the earliest dispensing event during the measurement year\. The treatment period end date is the last end date during the measurement year\. 

MME

Morphine milligram equivalent\. The dose of oral morphine that is the analgesic equivalent of a given dose of another opioid analgesic \(Table HDO\-A\)\.

Opioid dosage unit

For each dispensing event, use the following calculation to determine the opioid dosage unit\. 

\# of Opioid Dosage Units per day = \(opioid quantity dispensed\) /   
\(opioid days supply\)

MME daily dose

For each dispensing event, use the following calculation to determine the MME daily dose\. Convert each medication into the MME using the appropriate MME conversion factor and strength associated with the opioid product of the dispensing event \(refer to Table HDO\-A for MME conversion factor and strength\)\. 

MME Daily Dose = \(\# of opioid dosage units per day\) X \(strength \(e\.g\., mg, mcg\)\) X \(MME conversion factor \[Table HDO\-A\]\)\.

*Example 1: *10 mg oxycodone tablets X \(120 tablets / 30 days\) X 1\.5 = 60 MME/ day 

*Example 2:* 25 mcg/hr fentanyl patch X \(10 patches / 30 days\) X 7\.2 = 60 MME/ day

Total daily MME

The total sum of the MME daily doses for all opioid dispensing events on 1 day\. 

Average MME

The average MME for all opioids dispensed during the treatment period\. 

Eligible Population 

Product lines

Commercial, Medicaid, Medicare \(report each product line separately\)\.

Age

18 years and older as of January 1 of the measurement year\. 

Continuous enrollment

The measurement year\.

Allowable gap 

None\.

Anchor date

None\.

Benefit

Medical and pharmacy\.

Event/diagnosis

Use the steps below to determine the eligible population\.

__*Step 1*__

Identify members who met both of the following criteria during the measurement year:

- Two or more opioid dispensing events on different dates of service\. Use all the medication lists in Table HDO\-A to identify opioid medication dispensing events\. 
- ≥15 total days covered by opioids\. 

__*Required exclusions*__

Exclude members who met any of the following any time during the measurement year:

- Cancer \(Malignant Neoplasms Value Set\)\. Do not include laboratory claims \(claims with POS code 81\)\.
- Sickle cell disease \(Sickle Cell Anemia and HB S Disease Value Set\)\. Do not include laboratory claims \(claims with POS code 81\)\.
- Members receiving palliative care \(Palliative Care Assessment Value Set; Palliative Care Encounter Value Set; Palliative Care Intervention Value Set\)\.
- Members who had an encounter for palliative care \(ICD\-10\-CM code Z51\.5\)\. Do not include laboratory claims \(claims with POS code 81\)\.
- Members who use hospice services \(Hospice Encounter Value Set; Hospice Intervention Value Set\) or elect to use a hospice benefit any time during the measurement year\. Organizations that use the Monthly Membership Detail Data File to identify these members must use only the run date of the file to determine if the member elected to use a hospice benefit during the measurement year\. 
- Members who die any time during the measurement year\. 

Administrative Specification

Denominator

The eligible population\.

Numerator

The number of members whose average MME was ≥90 during the treatment period\. Follow the steps below to identify numerator compliance\. 

*Step 1 *

Use all the medication lists in Table HDO\-A to identify all opioid medication dispensing events during the measurement year\.

*Step 2*

For each member, calculate the MME daily dose for each medication dispensing event\.

*Step 3*

For a single dispensing event, multiply the MME daily dose by the dispensing event’s days supply\. For example, a dispensing event with a MME daily dose of 90 and a 5 days supply would have a total MME of 450 for that dispensing event\. As multiple dispensing events can overlap on one calendar day, for each day, sum the MME daily doses for all dispensing events to determine the total daily MME for that day\.

*Step 4*

Determine the treatment period\. 

*Step 5*

Determine the average MME\. Sum the total daily MME for the treatment period and divide by the number of days in the treatment period\. Members whose average MME was ≥90 meet the numerator criteria\. 

### Table HDO\-A: Opioid Medications

<a id="_Hlk74645723"></a><a id="_Hlk11906819"></a>Type of Opioid

Medication Lists

Strength

MME Conversion Factor

Benzhydrocodone

Acetaminophen Benzhydrocodone 4\.08 mg Medications List

Acetaminophen Benzhydrocodone 6\.12 mg Medications List

Acetaminophen Benzhydrocodone 8\.16 mg Medications List

4\.08 mg

6\.12 mg

8\.16 mg

1\.2

Butorphanol 

Butorphanol 10 MGPML Medications List

10 mg

7

Codeine

Codeine Sulfate 15 mg Medications List

Codeine Sulfate 30 mg Medications List

Codeine Sulfate 60 mg Medications List

15 mg

30 mg

60 mg

0\.15

Codeine

Acetaminophen Codeine 2\.4 MGPML Medications List

Acetaminophen Codeine 15 mg Medications List

Acetaminophen Codeine 30 mg Medications List

Acetaminophen Codeine 60 mg Medications List

2\.4 mg

15 mg

30 mg

60 mg

0\.15

Codeine

Acetaminophen Butalbital Caffeine Codeine 30 mg Medications List

30 mg

0\.15

Codeine

Aspirin Butalbital Caffeine Codeine 30 mg Medications List

30 mg

0\.15

Codeine

Aspirin Carisoprodol Codeine 16 mg Medications List

16 mg

0\.15

Dihydrocodeine

Acetaminophen Caffeine Dihydrocodeine 16 mg Medications List

16 mg

0\.25

Fentanyl buccal or sublingual tablet, transmucosal lozenge \(mcg\)1

Fentanyl 100 mcg Medications List

Fentanyl 200 mcg Medications List

Fentanyl 300 mcg Medications List

Fentanyl 400 mcg Medications List

Fentanyl 600 mcg Medications List

Fentanyl 800 mcg Medications List

Fentanyl 1200 mcg Medications List

Fentanyl 1600 mcg Medications List

100 mcg

200 mcg

300 mcg

400 mcg

600 mcg

800 mcg

1200 mcg

1600 mcg

0\.13

Fentanyl oral spray \(mcg\)2

Fentanyl 100 MCGPS Oral Medications List

Fentanyl 200 MCGPS Oral Medications List

Fentanyl 400 MCGPS Oral Medications List

Fentanyl 600 MCGPS Oral Medications List

Fentanyl 800 MCGPS Oral Medications List

100 mcg

200 mcg

400 mcg

600 mcg

800 mcg

0\.18

Fentanyl nasal spray \(mcg\)3

Fentanyl 100 MCGPS Nasal Medications List

Fentanyl 300 MCGPS Nasal Medications List

Fentanyl 400 MCGPS Nasal Medications List

100 mcg

300 mcg

400 mcg

0\.16

Fentanyl transdermal film/ patch \(mcg/hr\)4

Fentanyl 12 MCGPH Medications List

Fentanyl 25 MCGPH Medications List

Fentanyl 37\.5 MCGPH Medications List

Fentanyl 50 MCGPH Medications List

Fentanyl 62\.5 MCGPH Medications List

Fentanyl 75 MCGPH Medications List

Fentanyl 87\.5 MCGPH Medications List

Fentanyl 100 MCGPH Medications List

12 mcg

25 mcg

37\.5 mcg

50 mcg

62\.5 mcg

75 mcg

87\.5 mcg

100 mcg

7\.2

Hydrocodone

Hydrocodone 10 mg Medications List

Hydrocodone 15 mg Medications List

Hydrocodone 20 mg Medications List

Hydrocodone 30 mg Medications List

Hydrocodone 40 mg Medications List

Hydrocodone 50 mg Medications List

Hydrocodone 60 mg Medications List

Hydrocodone 80 mg Medications List

Hydrocodone 100 mg Medications List

Hydrocodone 120 mg Medications List

10 mg

15 mg

20 mg

30 mg

40 mg

50 mg

60 mg

80 mg

100 mg

120 mg

1

Hydrocodone

Acetaminophen Hydrocodone \.5 MGPML Medications List

Acetaminophen Hydrocodone \.67 MGPML Medications List

Acetaminophen Hydrocodone 2\.5 mg Medications List

Acetaminophen Hydrocodone 5 mg Medications List

Acetaminophen Hydrocodone 7\.5 mg Medications List

Acetaminophen Hydrocodone 10 mg Medications List

\.5 mg

\.67 mg

2\.5 mg

5 mg

7\.5 mg 

10 mg

1

Type of Opioid

Medication Lists

Strength

MME Conversion Factor

Hydrocodone

Hydrocodone Ibuprofen 2\.5 mg Medications List

Hydrocodone Ibuprofen 5 mg Medications List

Hydrocodone Ibuprofen 7\.5 mg Medications List

Hydrocodone Ibuprofen 10 mg Medications List

2\.5 mg

5 mg

7\.5 mg

10 mg

1

Hydromorphone 

Hydromorphone 1 MGPML Medications List

Hydromorphone 2 mg Medications List

Hydromorphone 3 mg Medications List

Hydromorphone 4 mg Medications List

Hydromorphone 8 mg Medications List

Hydromorphone 12 mg Medications List

Hydromorphone 16 mg Medications List

Hydromorphone 32 mg Medications List

1 mg 

2 mg

3 mg

4 mg

8 mg

12 mg

16 mg

32 mg

4

Levorphanol

Levorphanol 2 mg Medications List

Levorphanol 3 mg Medications List

2 mg

3 mg

11

Meperidine

Meperidine 10 MGPML Medications List

Meperidine 50 mg Medications List

Meperidine 100 mg Medications List

10 mg

50 mg

100 mg

0\.1

Methadone6

Methadone 1 MGPML Medications List

Methadone 2 MGPML Medications List

Methadone 5 mg Medications List

Methadone 10 mg Medications List

Methadone 10 MGPML Medications List

Methadone 40 mg Medications List

1 mg

2 mg

5 mg

10 mg

10 mg

40 mg

3

Morphine

Morphine 2 MGPML Medications List

Morphine 4 MGPML Medications List

Morphine 5 mg Medications List

Morphine 10 mg Medications List

Morphine 15 mg Medications List

Morphine 20 MGPML Medications List

Morphine 20 mg Medications List

Morphine 30 mg Medications List

Morphine 40 mg Medications List

Morphine 45 mg Medications List

Morphine 50 mg Medications List

Morphine 60 mg Medications List

2 mg

4 mg

5 mg

10 mg

15 mg

20 mg

20 mg

30 mg

40 mg

45 mg

50 mg

60 mg

1

Morphine 75 mg Medications List

Morphine 80 mg Medications List

Morphine 90 mg Medications List

Morphine 100 mg Medications List

Morphine 120 mg Medications List

Morphine 200 mg Medications List

75 mg

80 mg

90 mg

100 mg

120 mg

200 mg

Opium

Belladonna Opium 30 mg Medications List

Belladonna Opium 60 mg Medications List

30 mg

60 mg

1

Oxycodone

Oxycodone 1 MGPML Medications List

Oxycodone 5 mg Medications List

Oxycodone 7\.5 mg Medications List

Oxycodone 9 mg Medications List

Oxycodone 10 mg Medications List

Oxycodone 13\.5 mg Medications List

Oxycodone 15 mg Medications List

Oxycodone 18 mg Medications List

Oxycodone 20 mg Medications List

Oxycodone 20 MGPML Medications List

Oxycodone 27 mg Medications List

Oxycodone 30 mg Medications List

Oxycodone 36 mg Medications List

Oxycodone 40 mg Medications List

Oxycodone 60 mg Medications List

Oxycodone 80 mg Medications List

1 mg

5 mg

7\.5 mg

9 mg

10 mg

13\.5 mg

15 mg

18 mg

20 mg

20 mg

27 mg

30 mg

36 mg

40 mg

60 mg

80 mg

1\.5

Oxycodone

Acetaminophen Oxycodone 1 MGPML Medications List

Acetaminophen Oxycodone 2 MGPML Medications List

Acetaminophen Oxycodone 2\.5 mg Medications List

Acetaminophen Oxycodone 5 mg Medications List

Acetaminophen Oxycodone 7\.5 mg Medications List

Acetaminophen Oxycodone 10 mg Medications List

1 mg

2 mg

2\.5 mg

5 mg

7\.5 mg

10 mg

1\.5

Oxycodone

Aspirin Oxycodone 4\.84 mg Medications List

4\.84 mg

1\.5

Oxycodone

Ibuprofen Oxycodone 5 mg Medications List

5 mg

1\.5

Oxymorphone

Oxymorphone 5 mg Medications List

Oxymorphone 7\.5 mg Medications List

Oxymorphone 10 mg Medications List

Oxymorphone 15 mg Medications List

Oxymorphone 20 mg Medications List

Oxymorphone 30 mg Medications List

Oxymorphone 40 mg Medications List

5 mg

7\.5 mg

10 mg

15 mg

20 mg

30 mg

40 mg

3

Pentazocine

Naloxone Pentazocine 50 mg Medications List

50 mg

0\.37

Tapentadol

Tapentadol 50 mg Medications List

Tapentadol 75 mg Medications List

Tapentadol 100 mg Medications List

Tapentadol 150 mg Medications List

Tapentadol 200 mg Medications List

Tapentadol 250 mg Medications List

50 mg

75 mg

100 mg

150 mg

200 mg

250 mg

0\.4

Tramadol

Tramadol 5 MGPML Medications List

Tramadol 50 mg Medications List

Tramadol 100 mg Medications List

Tramadol 150 mg Medications List

Tramadol 200 mg Medications List

Tramadol 300 mg Medications List

5 mg

50 mg

100 mg

150 mg

200 mg

300 mg

0\.1

Tramadol

Acetaminophen Tramadol 37\.5 mg Medications List

37\.5 mg

0\.1

1	MME conversion factor for fentanyl films and oral sprays is 0\.18\. This reflects a 40% greater bioavailability for films compared to lozenges/tablets and 38% greater bioavailability for oral sprays compared to lozenges/tablets\. 

2	MME conversion factor for fentanyl nasal spray is 0\.16, which reflects a 20% greater bioavailability for sprays compared to lozenges/tablets\. 

3	MME conversion factor for fentanyl patches is 7\.2 based on the assumption that one milligram of parenteral fentanyl is equivalent to 100 milligrams of oral morphine and that one patch delivers the dispensed micrograms per hour over a 24\-hour day and remains in place for 3 days\. Using the formula, Strength per Unit \* \(Number of Units/ Days Supply\) \* MME conversion factor = MME/Day: 25 µg/hr\. fentanyl patch \* \(10 patches/30 days\) \* 7\.2 = 60 MME/day\.

4	Adapted from Von Korff M, Saunders K, Ray GT, et al\. Clin J Pain 2008;24:521–7 and Washington State Interagency Guideline on Prescribing Opioids for Pain \([http://www\.agencymeddirectors\.wa\.gov/Files/2015AMDGOpioidGuideline\.pdf](http://www.agencymeddirectors.wa.gov/Files/2015AMDGOpioidGuideline.pdf)\)\.

*Note*

- *Do not include denied claims when identifying the eligible population \(except for required exclusions\) or assessing the numerator for this measure\. *
- *Do not include supplemental data when identifying the eligible population or assessing the numerator\. Supplemental data can be used for only required exclusions for this measure\. *
- *This measure does not include *the* following opioid medications: *
- *Injectables\. *
- *Opioid cough and cold products\.*
- *Ionsys® \(fentanyl transdermal patch\)\.*
- *This is for inpatient use only and is available only through a restricted program under a Risk Evaluation and Mitigation Strategy \(REMS\)\.*
- *Methadone for the treatment of opioid use disorder\.*

__Data Elements for Reporting __

Organizations that submit HEDIS data to NCQA must provide the following data elements\. 

__*Table HDO\-1/2/3: Data Elements for Use of Opioids at High Dosage*__

__Metric__

__Data Element__

__Reporting Instructions__

OpioidUseHighDosage

Benefit

Metadata

EligiblePopulation 

Report once

ExclusionAdminRequired

Report once

NumeratorByAdmin

Report once

Rate

\(Percent\)

Rules for Allowable Adjustments of HEDIS

The “Rules for Allowable Adjustments of HEDIS” \(the “Rules”\) describe how NCQA’s HEDIS measure specifications can be adjusted for other populations, if applicable\. The Rules, reviewed and approved by NCQA measure experts, provide for expanded use of HEDIS measures without changing their clinical intent\. 

__Adjusted HEDIS measures may not be used for HEDIS health plan reporting\. __

### Rules for Allowable Adjustments of Use of Opioids at High Dosage

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

Only medications that contain \(or map to\) codes in the medication lists may be used to identify opioid use\. The medication lists and logic may not be changed\.

Organizations may include denied claims to calculate the denominator\. 

__Denominator Exclusions__

__Adjustments Allowed \(Yes/No\)__

__Notes__

Required exclusions

Yes, with limits

Apply required exclusions according to specified value sets\.

The hospice, deceased member and palliative care exclusions are not required\. Refer to *Exclusions* in the *Guidelines for the Rules for Allowable Adjustments\.*

__Numerator Criteria__

__Adjustments Allowed \(Yes/No\)__

__Notes__

Members Receiving High\-Dosage Opioids

Yes, with limits

Medication lists and logic may not be changed\.

Organizations may include denied claims to calculate the numerator\.

