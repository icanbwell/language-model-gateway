## <a id="Avoidance_Of_Antibiotic_Bronchitis_AAB"></a><a id="_Toc400546119"></a><a id="_Toc74825576"></a><a id="_Toc171403012"></a><a id="AAB"></a>Avoidance of Antibiotic Treatment for Acute Bronchitis/Bronchiolitis \(AAB\)

Summary of Changes to HEDIS MY 2025

- No changes to this measure\.

Description

The percentage of episodes for members ages 3 months and older with a diagnosis of acute bronchitis/ bronchiolitis that did not result in an antibiotic dispensing event\.

Calculation

The measure is reported as an inverted rate \[1–\(numerator/eligible population\)\]\. A higher rate indicates appropriate acute bronchitis/bronchiolitis treatment \(i\.e\., the proportion for episodes that *did not* result in an antibiotic dispensing event\)\. 

Definitions

Intake period

July 1 of the year prior to the measurement year to June 30 of the measurement year\. The intake period captures eligible episodes of treatment\.

Episode date

The date of service for any outpatient, telephone, or ED visit, e\-visit or virtual check\-in during the intake period with a diagnosis of acute bronchitis/ bronchiolitis\.

Negative medication history

To qualify for negative medication history, the following criteria must be met:

- A period of 30 days prior to the episode date, when the member had no pharmacy claims for either new or refill prescriptions for a listed antibiotic drug\.
- No prescriptions were dispensed more than 30 days prior to the episode date and are active on the episode date\.

A prescription is considered active if the “days supply” indicated on the date when the member was dispensed the prescription is the number of days or more between that date and the relevant service date\. The 30\-day look\-back period for pharmacy data includes the 30 days prior to the intake period\.

Negative comorbid condition history

A period of 365 days prior to and including the episode date when the member had no claims/encounters with any diagnosis for a comorbid condition \(366 days total\)\.

Negative competing diagnosis

The episode date and 3 days following the episode date when the member had no claims/encounters with any competing diagnosis\. 

Eligible Population

Product lines

Commercial, Medicaid, Medicare \(report each product line separately\)\.

Ages

Members who were 3 months or older as of the episode date\. 

Report three age stratifications and a total rate: 

- 3 months–17 years\.
- 18–64 years\.

- 65 years and older\.
- Total\.

The total is the sum of the age stratifications\.

Continuous enrollment

30 days prior to the episode date through 3 days after the episode date   
\(34 total days\)\. 

Allowable gap

None\. 

Anchor date

None\. 

Benefits

Medical and pharmacy\.

Event/diagnosis

Follow the steps below to identify the eligible population:

*Step 1*

Identify all members who had an outpatient visit, ED visit, telephone visit, e\-visit or virtual check\-in \(Outpatient, ED and Telehealth Value Set\) during the intake period, with a diagnosis of acute bronchitis/bronchiolitis \(Acute Bronchitis Value Set\)\.

*Step 2*

Determine all acute bronchitis/bronchiolitis episode dates\. For each member identified in step 1, determine all outpatient, telephone or ED visits, e\-visits and virtual check\-ins with a diagnosis of acute bronchitis/bronchiolitis\. 

Exclude visits that result in an inpatient stay \(Inpatient Stay Value Set\)\.

*Step 3*

Test for negative comorbid condition history\. Remove episode dates where the member had a claim/encounter with any diagnosis for a comorbid condition \(Comorbid Conditions Value Set\) during the 365 days prior to or on the episode date\. Do not include laboratory claims \(claims with POS code 81\)\.

*Step 4*

Test for negative medication history\. Remove episode dates where a new or refill prescription for an antibiotic medication \(AAB Antibiotic Medications List\) was dispensed 30 days prior to the episode date or was active on the episode date\.

*Step 5*

Test for Negative Competing Diagnosis\.* *Remove episode dates where the member had a claim/encounter with a competing diagnosis on or 3 days after the episode date\. Either of the following meets criteria for a competing diagnosis\. Do not include laboratory claims \(claims with POS code 81\)\.

- Pharyngitis Value Set\.
- Competing Diagnosis Value Set\.

*Step 6*

Calculate continuous enrollment\. The member must be continuously enrolled without a gap in coverage from 30 days prior to the episode date through 3 days after the episode date \(34 total days\)\.

*Step 7*

Deduplicate eligible episodes\. If a member has more than one eligible episode in a 31\-day period, include only the first eligible episode\. For example, if a member has an eligible episode on January 1, include the January 1 visit and do not include eligible episodes that occur on or between January 2 and January 31; then, if applicable, include the next eligible episode that occurs on or after February 1\. Identify visits chronologically, including only one per 31\-day period\. 

__Note:__ The denominator for this measure is based on episodes, not on members\. All eligible episodes that were not removed or deduplicated remain in the denominator\.

Required exclusions

Exclude members who meet either of the following criteria:

- Members who use hospice services \(Hospice Encounter Value Set; Hospice Intervention Value Set\) or elect to use a hospice benefit any time during the measurement year\. Organizations that use the Monthly Membership Detail Data File to identify these members must use only the run date of the file to determine if the member elected to use a hospice benefit during the measurement year\. 
- Members who die any time during the measurement year\. 

Administrative Specification

Denominator

The eligible population\.

Numerator

Dispensed prescription for an antibiotic medication \(AAB Antibiotic Medications List\) on or 3 days after the episode date\.

### AAB Antibiotic Medications

Description

Prescription

Aminoglycosides

- Amikacin
- Gentamicin

- Streptomycin
- Tobramycin

Aminopenicillins

- Amoxicillin

- Ampicillin

Beta\-lactamase inhibitors

- Amoxicillin\-clavulanate
- Ampicillin\-sulbactam

- Piperacillin\-tazobactam

First\-generation cephalosporins

- Cefadroxil

- Cefazolin

- Cephalexin

Fourth\-generation cephalosporins

- Cefepime

Lincomycin derivatives

- Clindamycin

- Lincomycin

Macrolides

- Azithromycin

- Clarithromycin

- Erythromycin

Miscellaneous antibiotics

- Aztreonam
- Chloramphenicol
- Dalfopristin\-quinupristin

- Daptomycin
- Linezolid
- Metronidazole

- Vancomycin

Natural penicillins

- Penicillin G benzathine\-procaine 
- Penicillin G potassium

- Penicillin G procaine
- Penicillin G sodium

- Penicillin V potassium
- Penicillin G benzathine

Penicillinase resistant penicillins

- Dicloxacillin

- Nafcillin

- Oxacillin

Quinolones

- Ciprofloxacin
- Gemifloxacin

- Levofloxacin
- Moxifloxacin

- Ofloxacin

Rifamycin derivatives

- Rifampin

Second\-generation cephalosporin

- Cefaclor
- Cefotetan

- Cefoxitin
- Cefprozil

- Cefuroxime

Sulfonamides

- Sulfadiazine

- Sulfamethoxazole\-trimethoprim

Tetracyclines

- Doxycycline

- Minocycline

- Tetracycline

Third\-generation cephalosporins

- Cefdinir
- Cefixime
- Cefotaxime

- Cefpodoxime
- Ceftazidime
- Ceftriaxone

Urinary anti\-infectives

- Fosfomycin
- Nitrofurantoin

- Nitrofurantoin macrocrystals\-monohydrate
- Trimethoprim

*Note*

- *Although denied claims are not included when assessing the numerator, all claims \(paid, suspended, pending and denied\) must be included when identifying the eligible population\.*
- *Supplemental data may not be used for this measure, except for required exclusions\. *

__Data Elements for Reporting __

Organizations that submit HEDIS data to NCQA must provide the following data elements\. 

__*Table AAB\-1/2/3: Data Elements for Avoidance of Antibiotic Treatment for Acute Bronchitis/Bronchiolitis*__

__Metric__

__Age__

__Data Element__

__Reporting Instructions__

AvoidanceAntibioticTreatment

3m\-17

Benefit

Metadata

18\-64

EligiblePopulation 

For each Stratification

65\+

ExclusionAdminRequired

For each Stratification

Total

NumeratorByAdmin

For each Stratification

Rate

\(Percent\)

Rules for Allowable Adjustments of HEDIS

The “Rules for Allowable Adjustments of HEDIS” \(the “Rules”\) describe how NCQA’s HEDIS measure specifications can be adjusted for other populations, if applicable\. The Rules, reviewed and approved by NCQA measure experts, provide for expanded use of HEDIS measures without changing their clinical intent\.

__Adjusted HEDIS measures may not be used for HEDIS health plan reporting\. __

### Rules for Allowable Adjustments of Avoidance of Antibiotic Treatment for Acute Bronchitis/Bronchiolitis

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

Changing the denominator age range is* *allowed if the limits are within the specified age range\. 

The denominator age may not be expanded\.

Continuous enrollment, allowable gap, anchor date

Yes

Organizations are not required to use enrollment criteria; adjustments are allowed\. 

__*Note:*__* Changes to these criteria can affect how the event/diagnosis will be calculated using the intake period, episode date, IESD, negative medication history, negative competing diagnosis, negative comorbid condition history\.*

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

Only events that contain \(or map to\) codes in the medication lists and value sets may be used to identify visits, diagnoses and medication history\. Medication lists, value sets and logic may not be changed\.

__Denominator Exclusions__

__Adjustments Allowed \(Yes/No\)__

__Notes__

Required exclusions

Yes

The hospice and deceased member exclusions are not required\. Refer to *Exclusions* in the *Guidelines for the Rules for Allowable Adjustments*\.

Numerator Criteria

Adjustments Allowed \(Yes/No\)

Notes

Dispensed Prescription for Antibiotic Medication

Yes, with limits

Medication lists, value sets and logic may not be changed\.

Organizations may include denied claims to calculate the numerator\.

