## <a id="Asthma_Medication_AMR"></a><a id="_Toc400546124"></a><a id="_Toc74815062"></a><a id="_Toc171402978"></a><a id="AMR"></a>Asthma Medication Ratio \(AMR\)

Summary of Changes to HEDIS MY 2025

- *Technical Update:* Deleted Added albuterol\-budesonide as an asthma reliever medication\. 
- Clarified in the *Note* to not use RxNorm codes when identifying required exclusions\.
- Removed the data source reporting requirement from the race and ethnicity stratification\.
- *Technical Update:* Revised the Asthma Controller Medications table\.

Description

The percentage of members 5–64 years of age who were identified as having persistent asthma and had a ratio of controller medications to total asthma medications of 0\.50 or greater during the measurement year\. 

Definitions

Oral medication dispensing event

One prescription of an amount lasting 30 days or less\. To calculate dispensing events for prescriptions longer than 30 days, divide the days supply by 30 and round down to convert\. For example, a 100\-day prescription is equal to three dispensing events \(100/30 = 3\.33, rounded down to 3\)\. Allocate the dispensing events to the appropriate year based on the date when the prescription is dispensed\.

Multiple prescriptions for different medications dispensed on the same day are counted as separate dispensing events\. If multiple prescriptions for the same medication are dispensed on the same day, sum the days supply and divide   
by 30\. 

Use the medication lists to determine if drugs are the same or different\. Drugs in different medication lists are considered different drugs\.

Inhaler dispensing event 

When identifying the eligible population, use the definition below to count inhaler dispensing events\.

All inhalers \(i\.e\., canisters\) of the same medication dispensed on the same day count as one dispensing event\. Different inhaler medications dispensed on the same day are counted as different dispensing events\. For example, if a member received three canisters of Medication A and two canisters of Medication B on the same date, it would count as two dispensing events\.

Allocate the dispensing events to the appropriate year based on the date when the prescription was dispensed\.

Use the medication lists to determine if drugs are the same or different\. Drugs in different medication lists are considered different drugs\.

Injection dispensing event

Each injection counts as one dispensing event\. Multiple dispensed injections of the same or different medications count as separate dispensing events\. For example, if a member received two injections of Medication A and one injection of Medication B on the same date, it would count as three dispensing events\.

Use the medication lists to determine if drugs are the same or different\. Drugs in different medication lists are considered different drugs\. Allocate the dispensing events to the appropriate year based on the date when the prescription was dispensed\.

Units of medication

When identifying medication units for the numerator, count each individual medication, defined as an amount lasting 30 days or less, as one medication unit\. One medication unit equals one inhaler canister, one injection, one infusion or a 30 days or less supply of an oral medication\. For example, two inhaler canisters of the same medication dispensed on the same day counts as two medication units and only one dispensing event\. 

Use the package size and units columns in the medication lists to determine the number of canisters or injections\. Divide the dispensed amount by the package size to determine the number of canisters or injections dispensed\. For example, if the package size for an inhaled medication is 10 g and pharmacy data indicate the dispensed amount is 30 g, three inhaler canisters were dispensed\.

Eligible Population 

Product lines

Commercial, Medicaid \(report each product line separately\)\.

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

Ages 5–64 as of December 31 of the measurement year\. Report the following age stratifications and a total rate:

- 5–11 years\.
- 12–18 years\.
- 19–50 years\.

- 51–64 years\.
- Total\.

The total is the sum of the age stratifications for each product line\.

Continuous enrollment

The measurement year and the year prior to the measurement year\.

Allowable gap

No more than one gap in enrollment of up to 45 days during each year of continuous enrollment\. To determine continuous enrollment for a Medicaid beneficiary for whom enrollment is verified monthly, the member may not have more than a 1\-month gap in coverage during each year of continuous enrollment\. 

Anchor date

December 31 of the measurement year\.

Benefits

Medical\. Pharmacy during the measurement year\.

Event/diagnosis

Follow the steps below to identify the eligible population\.

*Step 1*

Identify members as having persistent asthma who met at least one of the following criteria during both the measurement year and the year prior to the measurement year\. Criteria need not be the same across both years*\.*

- At least one ED visit or acute inpatient encounter \(ED and Acute Inpatient Value Set\), with a principal diagnosis of asthma \(Asthma Value Set\)\.
- At least one acute inpatient discharge with a principal diagnosis of asthma \(Asthma Value Set\) on the discharge claim\. To identify an acute inpatient discharge:

1\.	Identify all acute and nonacute inpatient stays \(Inpatient Stay Value Set\)\.

2\.	Exclude nonacute inpatient stays \(Nonacute Inpatient Stay Value Set\)\.

3\.	Identify the discharge date for the stay\.

- At least four outpatient visits, telephone visits or e\-visits or virtual check\-ins \(Outpatient and Telehealth Value Set\), on different dates of service, with any diagnosis of asthma \(Asthma Value Set\) __*and*__ at least two asthma medication dispensing events for any controller or reliever medication\. Visit type need not be the same for the four visits\. Use all the medication lists in the tables below to identify asthma controller and reliever medications\. 
- At least four asthma medication dispensing events for any controller or reliever medication\. Use all the medication lists in the tables below to identify asthma controller and reliever medications\.

*Step 2*

A member identified as having persistent asthma because of at least four asthma medication dispensing events, where leukotriene modifiers or antibody inhibitors were the sole asthma medication dispensed in that year, must also have at least one diagnosis of asthma \(Asthma Value Set\) in the same year as the leukotriene modifier or antibody inhibitor \(the measurement year or the year prior to the measurement year\)\. Do not include laboratory claims \(claims with POS code 81\)\.

Required exclusions

Exclude members who met any of the following criteria:

- Members who had a diagnosis that requires a different treatment approach than members with asthma \(Respiratory Diseases With Different Treatment Approaches Than Asthma Value Set\) any time during the member’s history through December 31 of the measurement year\. Do not include laboratory claims \(claims with POS code 81\)\.
- Members who had no asthma controller or reliever medications \(Asthma Controller and Reliever Medications List\) dispensed during the measurement year\. 
- Members who use hospice services \(Hospice Encounter Value Set; Hospice Intervention Value Set\) or elect to use a hospice benefit any time during the measurement year\. Organizations that use the Monthly Membership Detail Data File to identify these members must use only the run date of the file to determine if the member elected to use a hospice benefit during the measurement year\. 
- Members who die any time during the measurement year\. 

Administrative Specification

Denominator

The eligible population\.

Numerator

The number of members who have a medication ratio of ≥0\.50 during the measurement year\. Follow the steps below to calculate the ratio\.

Use all the medication lists in the Asthma Controller Medications table below to identify asthma controller medications\. Use all the medication lists in the Asthma Reliever Medications table below to identify asthma reliever medications\.

*Step 1*

For each member, count the units of asthma controller medications dispensed during the measurement year\. Refer to the definition of *Units of medications*\. 

*Step 2*

For each member, count the units of asthma reliever medications dispensed during the measurement year\. Refer to the definition of *Units of medications*\. 

*Step 3*

For each member, sum the units calculated in step 1 and step 2 to determine units of total asthma medications\.* *

*Step 4*

For each member, calculate the ratio of controller medications to total asthma medications using the following formula\. Round \(using the 0\.5 rule\) to the nearest whole number\.

Units of Controller Medications \(step 1\)

Units of Total Asthma Medications \(step 3\)

*Step 5*

Sum the total number of members who have a ratio of ≥0\.50 in step 4\. 

### Asthma Controller Medications

Description

Prescriptions

Medication Lists

Route

Antibody inhibitors

- Omalizumab

Omalizumab Medications List

Injection

Anti\-interleukin\-4

- Dupilumab

Dupilumab Medications List

Injection

Anti\-interleukin\-5

- Benralizumab

Benralizumab Medications List

Injection

Anti\-interleukin\-5

- Mepolizumab

Mepolizumab Medications List

Injection

Anti\-interleukin\-5

- Reslizumab

Reslizumab Medications List

Injection

Inhaled steroid combinations

- Budesonide\-formoterol

Budesonide Formoterol Medications List

Inhalation

Inhaled steroid combinations

- Fluticasone\-salmeterol

Fluticasone Salmeterol Medications List

Inhalation

Inhaled steroid combinations

- Fluticasone\-vilanterol

Fluticasone Vilanterol Medications List

Inhalation

Inhaled steroid combinations

- Formoterol\-mometasone

Formoterol Mometasone Medications List

Inhalation

Inhaled corticosteroids

- Beclomethasone

Beclomethasone Medications List

Inhalation

Inhaled corticosteroids

- Budesonide

Budesonide Medications List

Inhalation

Inhaled corticosteroids

- Ciclesonide

Ciclesonide Medications List

Inhalation

Inhaled corticosteroids

- Flunisolide

Flunisolide Medications List

Inhalation

Inhaled corticosteroids

- Fluticasone 

Fluticasone Medications List

Inhalation

Inhaled corticosteroids

- Mometasone

Mometasone Medications List

Inhalation

Leukotriene modifiers

- Montelukast

Montelukast Medications List

Oral

Leukotriene modifiers

- Zafirlukast

Zafirlukast Medications List

Oral

Leukotriene modifiers

- Zileuton

Zileuton Medications List

Oral

Long\-acting beta2\-adrenergic agonist \(LABA\)

- Fluticasone furoate\-umeclidinium\-vilanterol

Fluticasone Furoate Umeclidinium Vilanterol Medications List

Inhalation

Long\-acting beta2\-adrenergic agonist \(LABA\)

- Salmeterol

Salmeterol Medications List

Inhalation

Long\-acting muscarinic antagonists \(LAMA\)

- Tiotropium

Tiotropium Medications List

Inhalation

Methylxanthines

- Theophylline

Theophylline Medications List

Oral

__*Asthma Reliever Medications *__

__Description__

__Prescriptions__

__Medication Lists__

__Route__

Beta2 adrenergic agonist—corticosteroid combination

Albuterol\-budesonide

Albuterol Budesonide Medications List

Inhalation

Short\-acting, inhaled beta\-2 agonists

Albuterol

Albuterol Medications List

Inhalation

Short\-acting, inhaled beta\-2 agonists

Levalbuterol

Levalbuterol Medications List

Inhalation

*Note*

- *Do not use RxNorm codes when identifying required exclusions or when assessing the numerator\.*
- *When mapping NDC codes, medications described as “injection,” “prefilled syringe,” “subcutaneous,” “intramuscular” or “auto\-injector” are considered “injections” \(route\)\.*
- *When mapping NDC codes, medications described as “metered dose inhaler,” “dry powder inhaler” or “inhalation powder” are considered “inhalation” \(route\) medications\.*
- *Do not map medications described as “nasal spray” to “inhalation” medications\. *

__Data Elements for Reporting __

Organizations that submit HEDIS data to NCQA must provide the following data elements\. 

__*Table AMR\-A\-1/2: Data Elements for Asthma Medication Ratio*__

Metric

Age

Data Element

Reporting Instructions

AsthmaMedicationRatio

5\-11

Benefit

Metadata

12\-18

EligiblePopulation 

For each Stratification

19\-50

ExclusionAdminRequired

For each Stratification

51\-64

NumeratorByAdmin

For each Stratification

Total

NumeratorBySupplemental

For each Stratification

Rate

\(Percent\)

<a id="_Hlk103151018"></a>__*Table AMR\-B\-1/2: Data Elements for Asthma Medication Ratio: Stratifications by Race*__

Metric

Race

Data Element

Reporting Instructions

AsthmaMedicationRatio

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

__*Table AMR\-C\-1/2: Data Elements for Asthma Medication Ratio: Stratifications by Ethnicity*__

Metric

Ethnicity

Data Element

Reporting Instructions

AsthmaMedicationRatio

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

### Rules for Allowable Adjustments of Asthma Medication Ratio

__NONCLINICAL COMPONENTS__

__Eligible Population__

__Adjustments Allowed \(Yes/No\)__

__Notes__

Product lines

Yes

Using product line criteria is not required\. Including any product line, combining product lines, or not including product line criteria is allowed\.

Ages

Yes, with limits

Age determination dates may be changed \(e\.g\., select “age as of June 30”\)\. 

The denominator age may be changed within the specified age range \(ages 5–64 years\)\. 

The denominator age may also be expanded to 65 years of age and older\.

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

Yes, with limits

Only events or diagnoses that contain \(or map to\) codes in the medication lists and value sets may be used to identify visits\. Medication lists, value sets and logic may not be changed\.* *

__Denominator Exclusions__

__Adjustments Allowed \(Yes/No\)__

__Notes__

Required exclusions

Yes, with limits

Apply required exclusions according to specified value sets\. 

The hospice and deceased member exclusions are not required\. Refer to *Exclusions* in the *Guidelines for the Rules for Allowable Adjustments*\.

__Numerator Criteria__

__Adjustments Allowed \(Yes/No\)__

__Notes__

Medication Ratio of 0\.50 or greater

No

Medication lists and logic may not be changed\.

<a id="_Toc74815063"></a><a id="_Toc171402979"></a>Cardiovascular Conditions

