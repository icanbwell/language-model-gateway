## <a id="Appropriate_Testing_Pharyngitis_CWP"></a><a id="_Toc400546117"></a><a id="_Toc74815059"></a><a id="_Toc171402976"></a><a id="CWP"></a>Appropriate Testing for Pharyngitis \(CWP\)

Summary of Changes to HEDIS MY 2025

- No changes to this measure\. 

Description

The percentage of episodes for members 3 years and older where the member was diagnosed with pharyngitis, dispensed an antibiotic and received a group A streptococcus \(strep\) test for the episode\. 

Definitions

Intake period

July 1 of the year prior to the measurement year to June 30 of the measurement year\. The intake period captures eligible episodes of treatment\.

Episode date

The date of service for any outpatient, telephone or ED visit, e\-visit or virtual check\-in during the intake period with a diagnosis of pharyngitis\. 

Negative medication history

To qualify for negative medication history, the following criteria must be met:

- A period of 30 days prior to the episode date when the member had no pharmacy claims for either new or refill prescriptions for a listed antibiotic drug\.
- No prescriptions dispensed more than 30 days prior to the episode date that are active on the episode date\.

A prescription is considered active if the “days supply” indicated on the date when the member was dispensed the prescription is the number of days or more between that date and the relevant service date\. The 30\-day look\-back period for pharmacy data includes the 30 days prior to the intake period\.

Negative comorbid condition history

A period of 365 days prior to and including the episode date when the member had no claims/encounters with any diagnosis for a comorbid condition \(366 days total\)\.

Negative competing diagnosis

The episode date and 3 days following the episode date when the member had no claims/encounters with a competing diagnosis\.

Eligible Population

Product lines

Commercial, Medicaid, Medicare \(report each product line separately\)\.

Ages

Members who were 3 years or older as of the episode date\. 

Report three age stratifications and a total rate: 

- 3–17 years\.
- 18–64 years\.

- 65 years and older\.
- Total\.

The total is the sum of the age stratifications\.

Continuous enrollment

30 days prior to the episode date through 3 days after the episode date \(34 total days\)\.

Allowable gap

None\.

Anchor date

None\.

Benefits

Medical and pharmacy\.

Event/ diagnosis

Follow the steps below to identify the eligible population\.

*Step 1*

Identify all members who had an outpatient visit, ED visit, telephone visit, e\-visit or virtual check\-in \(Outpatient, ED and Telehealth Value Set\) during the intake period, with a diagnosis of pharyngitis \(Pharyngitis Value Set\)\.

*Step 2*

Determine all pharyngitis episode dates\. For each member identified in   
step 1, determine all outpatient, telephone or ED visits, e\-visits and virtual check\-ins with a diagnosis of pharyngitis\.

Exclude visits that result in an inpatient stay \(Inpatient Stay Value Set\)\.

*Step 3*

Determine if antibiotics \(CWP Antibiotic Medications List\) were dispensed for any of the episode dates\. For each episode date with a qualifying diagnosis, determine if antibiotics were dispensed on or up to 3 days after\. 

Remove episode dates if the member did not receive antibiotics on or up to   
3 days after the episode date\.

### CWP Antibiotic Medications

Description

Prescription

Aminopenicillins

- Amoxicillin

- Ampicillin

Beta\-lactamase inhibitors

- Amoxicillin\-clavulanate

First generation cephalosporins

- Cefadroxil

- Cefazolin

- Cephalexin

Folate antagonist

- Trimethoprim

Lincomycin derivatives

- Clindamycin

Macrolides

- Azithromycin

- Clarithromycin 

- Erythromycin

Natural penicillins

- Penicillin G benzathine
- Penicillin G potassium

- Penicillin G sodium
- Penicillin V potassium 

Quinolones

- Ciprofloxacin
- Levofloxacin

- Moxifloxacin
- Ofloxacin

Second generation cephalosporins

- Cefaclor
- Cefprozil

- Cefuroxime

Sulfonamides

- Sulfamethoxazole\-trimethoprim

Tetracyclines

- Doxycycline
- Minocycline

- Tetracycline

Third generation cephalosporins

- Cefdinir
- Cefixime

- Cefpodoxime
- Ceftriaxone

*Step 4*  


Test for negative comorbid condition history\. Remove episode dates where the member had a claim/encounter with any diagnosis for a comorbid condition \(Comorbid Conditions Value Set\) during the 365 days prior to or on the episode date \(366 days total\)\. Do not include laboratory claims \(claims with POS   
code 81\)\. 

*Step* *5*

Test for negative medication history\. Remove episode dates where a new or refill prescription for an antibiotic medication \(CWP Antibiotic Medications List\) was dispensed 30 days prior to the episode date or was active on the episode date\. 

*Step 6*

Test for negative competing diagnosis\. Remove episode dates where the member had a claim/encounter with a competing diagnosis \(Competing Diagnosis Value Set\) on or 3 days after the episode date\. Do not include laboratory claims \(claims with POS code 81\)\.

*Step* *7*

Calculate continuous enrollment\. The member must be continuously enrolled without a gap in coverage from 30 days prior to the episode date through   
3 days after the episode date \(34 total days\)\.

*Step 8*

Deduplicate eligible episodes\. If a member has more than one eligible episode in a 31\-day period, include only the first eligible episode\. For example, if a member has an eligible episode on January 1, include the January 1 visit and do not include eligible episodes that occur on or between January 2 and January 31; then, if applicable, include the next eligible episode that occurs on or after February 1\. Identify visits chronologically including only one per 31\-day period\.

Required exclusions

Exclude members who meet either of the following criteria:

- Members who use hospice services \(Hospice Encounter Value Set; Hospice Intervention Value Set\) or elect to use a hospice benefit any time during the measurement year\. Organizations that use the Monthly Membership Detail Data File to identify these members must use only the run date of the file to determine if the member elected to use a hospice benefit during the measurement year\. 
- Members who die any time during the measurement year\. 

Administrative Specification

Denominator

The eligible population\.

Numerator

A group A streptococcus test \(Group A Strep Tests Value Set\) in the 7\-day period from 3 days prior to the episode date through 3 days after the episode date\.

__Data Elements for Reporting __

Organizations that submit HEDIS data to NCQA must provide the following data elements\.

__*Table CWP\-1/2/3: Data Elements for Appropriate Testing for Pharyngitis*__

__Metric__

__Age__

__Data Element__

__Reporting Instructions__

AppropriatePharyngitisTesting

3\-17

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

NumeratorBySupplemental

For each Stratification

Rate

\(Percent\)

Rules for Allowable Adjustments of HEDIS

The “Rules for Allowable Adjustments of HEDIS” \(the “Rules”\) describe how NCQA’s HEDIS measure specifications can be adjusted for other populations, if applicable\. The Rules, reviewed and approved by NCQA measure experts, provide for expanded use of HEDIS measures without changing their clinical intent\. 

__Adjusted HEDIS measures may not be used for HEDIS health plan reporting\. __

### Rules for Allowable Adjustments of Appropriate Testing for Pharyngitis

__NONCLINICAL COMPONENTS__

__Eligible Population__

__Adjustments Allowed \(Yes/No\)__

__Notes__

Product lines

Yes

Organizations are not required to use product line criteria; product lines may be combined and all \(or no\) product line criteria may be used\.

Ages

Yes, with limits

Age determination dates may be changed \(e\.g\., select “age as of January 1”\)\. 

The denominator age may be changed if the range is within the specified age range\. 

The denominator age may not be expanded\.

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

Only events or diagnoses that contain \(or map to\) codes in the medication lists and value sets may be used to identify visits\. Medication lists and value sets and logic may not be changed\.

__Denominator Exclusions__

__Adjustments Allowed \(Yes/No\)__

__Notes__

Required exclusions

Yes 

The hospice and deceased member exclusions are not required\. Refer to *Exclusions* in the *Guidelines for the Rules for Allowable Adjustments*\.

__Numerator Criteria__

__Adjustments Allowed \(Yes/No\)__

__Notes__

Group A Streptococcus Test

No

Value sets and logic may not be changed\.

