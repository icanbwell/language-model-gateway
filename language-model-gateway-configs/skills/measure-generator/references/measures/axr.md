## <a id="Antibiotic_Utilization_Respiratory_AXR"></a><a id="_Toc74828967"></a><a id="_Toc171403043"></a><a id="_Toc400546184"></a><a id="ABX"></a>Antibiotic Utilization for Respiratory Conditions \(AXR\) 

Summary of Changes to HEDIS MY 2025

- No changes to this measure\. 

<a id="_Toc169867009"></a>Description 

The percentage of episodes for members 3 months of age and older with a diagnosis of a respiratory condition that resulted in an antibiotic dispensing event\.

__Note:__ This measure is designed to capture the frequency of antibiotic utilization for respiratory conditions\. Organizations should use this information for internal evaluation only\. NCQA does not view higher or lower service counts as indicating better or worse performance\.

Definitions

Intake period 

July 1 of the year prior to the measurement year to June 30 of the measurement year\. The intake period captures eligible episodes of treatment\.

Episode date 

The date of service for any outpatient, telephone or ED visit, e\-visit or virtual check\-in during the intake period with a diagnosis of a respiratory condition\. 

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

Members who were 3 months of age or older as of the episode date\. Report three age stratifications and a total rate: 

- 3 months–17 years\.
- 18\-64 years\.

- 65 years and older\.
- Total\.

The total is the sum of the age stratifications\.

Continuous enrollment

30 days prior to the episode date through 3 days after the episode date \(34 total days\)\. 

Allowable gap

No gaps in enrollment during the continuous enrollment period\.

Anchor date

None\.

Benefit

Medical and pharmacy\.

Event/diagnosis

Follow the steps below to identify the eligible population:

*Step 1*

Identify all members who had an outpatient visit, ED visit, telephone visit, e\-visit or virtual check\-in \(Outpatient, ED and Telehealth Value Set\) during the intake period, with a diagnosis of a respiratory condition \(Respiratory Conditions and Symptoms Value Set\)\. 

*Step 2*

Determine all respiratory condition episode dates\. For each member identified in step 1, determine all outpatient, telephone or ED visits, e\-visits and virtual check\-ins with a diagnosis of a respiratory condition\. 

Do not include visits that result in an inpatient stay \(Inpatient Stay Value Set\)\.

*Step 3*

Test for negative comorbid condition history\. Remove episode dates when the member had a claim/encounter with any diagnosis for a comorbid condition \(Comorbid Conditions Value Set\) during the 365 days prior to or on the episode date\. Do not include laboratory claims \(claims with POS code 81\)\.

*Step 4*

Test for negative medication history\. Remove episode dates where a new or refill prescription for an antibiotic medication \(AXR Antibiotic Medications List\) was dispensed 30 days prior to the episode date or was active on the episode date\.

*Step 5*

Test for negative competing diagnosis\.* *Remove episode dates where the member had a claim/encounter with a competing diagnosis \(AXR Competing Diagnosis Value Set\) on or 3 days after the episode date\. Do not include laboratory claims \(claims with POS code 81\)\.

*Step 6*

Calculate continuous enrollment\. The member must be continuously enrolled without a gap in coverage from 30 days prior to the episode date through   
3 days after the episode date \(34 total days\)\.

*Step 7*

Deduplicate eligible episodes\. If a member has more than one eligible episode in a 31\-day period, include only the first eligible episode\. For example, if a member has an eligible episode on January 1, include the January 1 visit and do not include eligible episodes that occur on or between January 2 and January 31; then, if applicable, include the next eligible episode that occurs on or after February 1\. Identify visits chronologically, including only one per 31\-day period\. 

__Note:__ The denominator for this measure is based on episodes, not on members\. All eligible episodes that were not removed or deduplicated remain in the denominator\.

Required exclusion

Members who use hospice services \(Hospice Encounter Value Set; Hospice Intervention Value Set\) or elect to use a hospice benefit any time during the measurement year\. Organizations that use the Monthly Membership Detail Data File to identify these members must use only the run date of the file to determine if the member elected to use a hospice benefit during the measurement year\. 

Administrative Specification

Denominator 

The eligible population\. 

Numerator 

Dispensed prescription for an antibiotic medication from the <a id="_Hlk51153109"></a>AXR Antibiotic Medications List on or 3 days after the episode date\.

### AXR Antibiotic Medications

Description

Prescriptions

Absorbable sulfonamides

- Sulfadiazine

- Sulfamethoxazole\-trimethoprim

Aminoglycoside

- Amikacin
- Gentamicin

- Streptomycin
- Tobramycin

Amoxicillin/clavulanate

- Amoxicillin\-clavulanate

Azithromycin and clarithromycin

- Azithromycin

- Clarithromycin

Cephalosporin \(first generation\)

- Cefadroxil

- Cefazolin

- Cephalexin

Cephalosporin \(second, third, fourth generation\)

- Cefaclor
- Cefdinir
- Cefepime 
- Cefixime

- Cefotaxime
- Cefotetan
- Cefoxitin
- Cefpodoxime

- Cefprozil
- Ceftriaxone
- Cefuroxime
- Ceftazidime

Clindamycin 

- Clindamycin

Lincosamide \(other than clindamycin\)

- Lincomycin

Macrolide \(other than azithromycin and clarithromycin\)

- Erythromycin

Penicillin \(other than amoxicillin/clavulanate\)

- Ampicillin
- Ampicillin\-sulbactam
- Amoxicillin
- Dicloxacillin
- Nafcillin

- Oxacillin
- Penicillin G benzathine
- Penicillin G benzathine\-procaine
- Penicillin G potassium

- Penicillin G procaine
- Penicillin G sodium
- Penicillin V potassium
- Piperacillin\-tazobactam

Tetracyclines

- Doxycycline

- Minocycline

- Tetracycline

Quinolones

- Ciprofloxacin
- Gemifloxacin

- Levofloxacin
- Moxifloxacin

- Ofloxacin

Miscellaneous antibiotics

- Aztreonam
- Chloramphenicol
- Dalfopristin\-quinupristin 
- Daptomycin
- Fosfomycin 

- Linezolid
- Metronidazole
- Nitrofurantoin
- Nitrofurantoin macrocrystals\-monohydrate

- Rifampin
- Telavancin
- Trimethoprim 
- Vancomycin

*Note*

- *Supplemental data may not be used for this measure, except for required exclusions\.*
- __*Which services count?*__* Report all services the organization paid for or expects to pay for \(i\.e\., claims incurred but not paid\)\. Do not include services and days denied for any reason\. If a member is enrolled retroactively, count all services for which the organization paid or expects to pay\.*

*The organization may have:*

- *Covered the full amount\.*
- *Paid only a portion of the amount \(e\.g\., 80%\)\.*
- *Paid nothing because the member covered the entire amount to meet a deductible\. *
- *Paid nothing because the service was covered as part of a per member per month \(PMPM\) payment\.*
- *Denied the service\.*

*Count the service if:*

- *The organization paid the full amount or a portion of the amount \(e\.g\., 80%\)\.*
- *The member paid for the service as part of the benefit offering \(e\.g\., to meet a deductible\), *__*or *__
- *The service was covered under a PMPM payment\.*

*Do not count the service if: *

- *The organization denied the service for any reason, unless the member paid for the service as part of the benefit offering \(e\.g\., to meet a deductible\), *__*or*__
- *The claim for the service was rejected because it was missing information or was invalid for another reason\.*

__Data Elements for Reporting __

Organizations that submit HEDIS data to NCQA must provide the following data elements\.

__*Table AXR\-1/2/3: Data Elements for Antibiotic Utilization for Respiratory Conditions*__

__Metric__

__Age__

__Data Element__

__Reporting Instructions__

AntibioticUtilizationRespiratoryConditions

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

__Adjusted HEDIS measures may not be used for HEDIS health plan reporting\.__

__*Rules for Allowable Adjustments of Antibiotic Utilization for Respiratory Conditions*__

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

__*Note: *__*Changes to these criteria can affect how the event/diagnosis will be calculated using the intake period, episode date, negative comorbid condition, negative medication history, negative competing diagnosis\.*

Benefits

Yes

Organizations are not required to use a benefit; adjustments are allowed\.

Other

Yes

Organizations may use additional eligible population criteria to focus on an area of interest defined by gender, race, ethnicity, socioeconomic or sociodemographic characteristics, geographic region or another characteristic\. 

__CLINICAL COMPONENTS__

__Exclusions__

__Adjustments Allowed \(Yes/No\)__

__Notes__

Event/diagnosis

Yes, with limits

Only events that contain \(or map to\) codes in the medication lists and value sets may be used to identify visits, diagnoses and medication history\. Medication lists, value sets and logic may not be changed\. 

Organizations may include denied claims to calculate the denominator\.

__Exclusions__

__Adjustments Allowed \(Yes/No\)__

__Notes__

Required exclusions

Yes

The hospice exclusion is not required\. Refer to *Exclusions* in the *Guidelines for the Rules for Allowable Adjustments*\.

__Calculations Criteria__

__Adjustments Allowed \(Yes/No\)__

__Notes__

Dispensed prescription for antibiotic medication

Yes, with limits

Medications lists and logic may not be changed\. 

Organizations may include denied claims to calculate inpatient services\.

<a id="_Toc74828968"></a><a id="_Toc171403044"></a>Risk Adjusted Utilization 

# <a id="_Toc74828969"></a><a id="_Toc171403045"></a><a id="RiskAdjustedGuidelines"></a><a id="_Toc400546185"></a>Guidelines for   
Risk Adjusted Utilization Measures

Summary of Changes to HEDIS MY 2025

- No changes to these guidelines\.

<a id="_Toc74828970"></a><a id="_Toc171403046"></a>Guidelines

__*1\.*__

__Which services count? __Include all services, whether or not the organization paid for them or expects to pay for them \(include denied claims\) when applying risk adjustment in the Risk Adjusted Utilization measures\. *Do not include* denied services \(only include paid services and services expected to be paid\) when identifying all other events \(e\.g\., the IHS in the PCR measure or observed events in the other risk adjusted utilization measures\)\.

When confirming that an ED visit does not result in an inpatient or observation stay, all inpatient and observation stays must be considered, regardless of payment status \(paid, suspended, pending, denied\)\. For example, if an ED visit is paid but an inpatient stay is denied, the ED visit resulted in an inpatient stay and is not included in the Emergency Department Utilization measure when identifying observed ED visits\.

The organization may have:

- Covered the full amount\.
- Paid only a portion of the amount \(e\.g\., 80%\)\.
- Paid nothing because the member covered the entire amount to meet a deductible\. 
- Paid nothing because the service was covered as part of a PMPM payment\.
- Denied the service\.

*Count the service as paid or expected to be paid if:*

- The organization paid the full amount __*or*__ a portion of the amount \(e\.g\., 80%\)\.
- The member paid for the service as part of the benefit offering \(e\.g\., to meet a deductible\), __*or*__ 
- The service was covered under a PMPM payment\.

*Count the service as denied if: *

- The organization denied the service for any reason, unless the member paid for the service as part of the benefit offering \(e\.g\., to meet a deductible\), __*or*__
- The claim for the service was rejected because it was missing information or was invalid for another reason\.

__*2\. *__

__Risk adjustment\. __Organizations may not use supplemental data sources when applying the risk adjustment methodology\.

Organizations may not use risk assessment protocols to supplement diagnoses for calculation of the risk adjustment scores for these measures\. The measurement model was developed and tested using only claims\-based diagnoses and diagnoses from additional data sources would affect the validity of the models as they are current implemented in the specification\.

__*3\.*__

__Counting transfers\.__ Unless otherwise specified in the measure, treat transfers *between *institutions as separate admissions\. Base transfer reports *within* an institution on the type and level of services provided\. Report separate admissions when the transfer is between acute and nonacute levels of service or between mental health/chemical dependency services and non\-mental health/chemical dependency services\.

Count only one admission when the transfer takes place within the same service category but to a different level of care; for example, from intensive care to a lesser level of care or from a lesser level of care to intensive care\.

__*4\.*__

__Mental health and chemical dependency transfers\. __Unless otherwise specified in the measure, count as a separate admission a transfer within the same institution but to a different level of care \(e\.g\., a transfer between inpatient and residential care\)\. Each level must appropriately include discharges and length of stay \(count inpatient days under inpatient; count residential days under residential\)\.

__*5\. *__

__Observation stays without an admission and/or__ __discharge date\.__ For observation stays \(Observation Stay Value Set\) that do not have a recorded admission or discharge date, set the admission date to the earliest date of service on the claim and set the discharge date to the last date of service on the claim\.

__*6\.*__

__Direct transfers\.__ A direct transfer is when the discharge date from the initial stay precedes the admission date to a subsequent stay by one calendar day or less\. For example:

- A discharge on June 1, followed by a subsequent admission on June 1, *is a direct transfer\.*
- A discharge on June 1, followed by a subsequent admission on June 2, *is a direct transfer\.*
- A discharge on June 1, followed by a subsequent admission on June 3, *is not a direct transfer;* these are two distinct stays\.
- A discharge on June 1, followed by a subsequent admission on June 2 \(with discharge on June 3\), followed by a subsequent admission on June 4, *is a direct transfer\.*

Direct transfers may occur from and between different facilities and/or different service levels\. Refer to individual measure specifications for details\.

<a id="_Toc74828971"></a><a id="_Toc171403047"></a>Risk Adjustment Comorbidity Category Determination 

*Step 1*

Identify all diagnoses for encounters during the classification period for each denominator unit of the measure \(i\.e\., denominator event or member\)\. Include the following when identifying encounters:

- Outpatient visits, ED visits, telephone visits, nonacute inpatient encounters and acute inpatient encounters \(Outpatient, ED, Telephone, Acute Inpatient and Nonacute Inpatient Value Set\) with a date of service during the classification period\.
- Acute and nonacute inpatient discharges \(Inpatient Stay Value Set\) with a discharge date during the classification period\. 

For PCR, exclude the principal discharge diagnosis on the IHS\. For the HFS measure, exclude the primary discharge diagnosis on the skilled nursing facility discharge \(SND\) to the community\.

*Step 2*

Assign each diagnosis to a comorbid Clinical Condition \(CC\) category using Table CC—Mapping\. If the code appears more than once in Table CC—Mapping, it is assigned to multiple CCs\.

Exclude all diagnoses that cannot be assigned to a comorbid CC category\. For members with no qualifying diagnoses from face\-to\-face encounters, skip to the *Risk Adjustment Weighting* section\.

All digits must match exactly when mapping diagnosis codes to the comorbid CCs\.

*Step 3*

Determine HCCs for each comorbid CC identified\. Refer to Table HCC—Rank\.

For each denominator unit’s comorbid CC list, match the comorbid CC code to the comorbid CC code in the table, and assign:

- The ranking group\.
- The rank\.
- The HCC\.

For comorbid CCs that do not match to Table HCC—Rank, use the comorbid CC as the HCC and assign a rank of 1\.

__Note: __One comorbid CC can map to multiple HCCs; each HCC can have one or more comorbid CCs\.

*Step 4*

Assess each ranking group separately and select only the highest ranked HCC in each ranking group using the “Rank” column \(1 is the highest rank possible\)\. 

Drop all other HCCs in each ranking group, and de\-duplicate the HCC list if necessary\.

Example

*Assume a denominator unit with the following comorbid CCs*: CC\-85, CC\-17 and CC\-19 \(assume no other CCs\)\. 

- CC\-85 does not have a map to the ranking table and becomes HCC\-85\.
- HCC\-17 and HCC\-19 are part of Diabetes Ranking Group 1\. Because CC\-17 is ranked higher than CC\-19 in Ranking Group Diabetes 1, the comorbidity is assigned as HCC\-17 for Ranking Group 1\. 
- The final comorbidities for this denominator unit are HCC\-17 and HCC\-85\.

Example: Table HCC—Rank

Ranking Group

CC

Description

Rank

HCC

NA

CC\-85

Congestive Heart Failure

NA

HCC\-85

Diabetes 1 

CC\-17

Diabetes With Acute Complications 

1

HCC\-17

CC\-18

Diabetes With Chronic Complications 

2

HCC\-18

CC\-19

Diabetes Without Complications 

3

HCC\-19

*Step 5*

Identify combination HCCs listed in Table HCC—Comb\. 

Some combinations suggest a greater amount of risk when observed together\. For example, when diabetes *and *CHF are present, an increased amount of risk is evident\. Additional HCCs are selected to account for these relationships\. 

Compare each denominator unit’s list of unique HCCs to those in the *Comorbid HCC* columns in Table HCC—Comb and assign any additional HCC conditions\.

*If there are fully nested combinations, use only the more comprehensive pattern\. *For example, if the diabetes/CHF combination is nested in the diabetes/CHF/renal combination, count only the diabetes/CHF/renal combination\.

*If there are overlapping combinations, use both sets of combinations\. *Based on the combinations, a denominator unit can have none, one or more of these added HCCs\.

Example

For a denominator unit with comorbidities HCC\-17 and HCC\-85 \(assume no other HCCs\), assign HCC\-901 in addition to HCC\-17 and HCC\-85\. This *does not* replace HCC\-17 and HCC\-85\.

Example: Table HCC—Comb

Comorbid   
HCC 1

Comorbid   
HCC 2

Comorbid   
HCC 3

HCC\-  
Combination 

HCC\-Comb Description

HCC\-17

HCC\-85

NA

HCC\-901

Combination: Diabetes and CHF

HCC\-18

HCC\-85

NA

HCC\-901

Combination: Diabetes and CHF

HCC\-19

HCC\-85

NA

HCC\-901

Combination: Diabetes and CHF

