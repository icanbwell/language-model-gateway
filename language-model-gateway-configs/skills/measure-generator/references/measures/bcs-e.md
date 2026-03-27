## <a id="Breast_Cancer_Screening_BCSE"></a><a id="_Toc74830492"></a><a id="_Toc171403064"></a>Breast Cancer Screening \(BCS\-E\)

Summary of Changes to HEDIS MY 2025

- <a id="_Hlk34985466"></a>Removed “Programming Guidance” from the *Characteristics *section\. 
- Added a laboratory claim exclusion to the Absence of Left Value Set and Absence of Right Breast Value Set\.
- Removed the *Data criteria \(element level\)* section\. 
- Removed the data source reporting requirement from the race and ethnicity stratification\. 
- *Technical Update: *Revised the description, clinical recommendation statement, citations, stratification, initial population, Data Elements for Reporting tables and Rules for Allowable Adjustments of HEDIS\. 

Description

The percentage of members 40–74 50–74 years of age who were recommended for routine breast cancer screening and had a mammogram to screen for breast cancer\.

Measurement period

January 1–December 31\.

Clinical recommendation statement

The U\.S\. Preventive Services Task Force recommends screening women 50–74 years of age for breast cancer every 2 years\. \(B recommendation\)

The U\.S\. Preventive Services Task Force \(USPSTF\) recommends biennial screening mammography for women aged 40–74 years\. \(B recommendation\)

The Fenway Institute recommends that for patients assigned female at birth who have not undergone chest reconstruction \(including those who have had breast reduction\), breast/chest screening recommendations are the same as for cisgender women of a similar age and medical history\.

The University of California San Francisco Center of Excellence for Transgender Health recommends that transgender men who have not undergone bilateral mastectomy, or who have only undergone breast reduction, undergo screening according to current guidelines for non\-transgender women\.

The World Professional Association for Transgender Health recommends health care professionals follow local breast cancer screening guidelines developed for cisgender women in their care of transgender and gender diverse people with breasts from natal puberty who have not had gender\-affirming chest surgery\.

Citations

U\.S\. Preventive Services Task Force\. Nicholson, W\.K\., M\. Silverstein, J\.B\. Wong, M\.J\. Barry, D\. Chelmow, T\.R\. Coker, et al\. June 11, 2024\. “Screening for Breast Cancer: U\.S\. Preventive Services Task Force Recommendation Statement\.” JAMA 331, no\. 22: 1918\. https://doi\.org/10\.100/jama\.2024\.5534

Fenway Health\. 2021\. *Medical Care of Trans and Gender Diverse Adults*\. https://fenwayhealth\.org/wp\-content/uploads/Medical\-Care\-of\-Trans\-and\-Gender\-Diverse\-Adults\-Spring\-2021\-1\.pdf

University of California San Francisco Center of Excellence for Transgender Health\. 2016\. *Guidelines for the Primary and Gender\-Affirming Care of Transgender and Gender Nonbinary People*\. https://transcare\.ucsf\.edu/sites/transcare\.ucsf\.edu/files/Transgender\-PGACG\-6\-17\-16\.pdf

U\.S\. Preventive Services Task Force\. 2016\. “Screening for Breast Cancer: U\.S\. Preventive Services Task Force Recommendation Statement\." *Ann Intern Med* 164\(4\):279–96\.

World Professional Association for Transgender Health\. 2022\. *Standards of Care for the Health of Transgender and Gender Diverse People, Version 8\.* https://www\.tandfonline\.com/doi/pdf/10\.1080/26895269\.2022\.2100644

Characteristics

Scoring

Proportion\.

Type

Process\.

Stratification

- Breast Cancer Screening\.
- Product line:
- Commercial\.
- Medicaid\.
- Medicare\.
- Age \(for each product line\):
- 42–51 years\.
- 52–74 years\.
- SES \(for Medicare only\):
- SES—Non\-LIS/DE, Nondisability\.
- SES—LIS/DE\.
- SES—Disability\.
- SES—LIS/DE and Disability\.
- SES—Other\.
- SES—Unknown\.
- Race \(for each product line\):
- Race—American Indian or Alaska Native\.
- Race—Asian\.
- Race—Black or African American\.
- Race—Native Hawaiian or Other Pacific Islander\.
- Race—White\.
- Race—Some Other Race\.
- Race—Two or More Races\.
- Race—Asked But No Answer\.
- Race—Unknown\.
- Ethnicity \(for each product line\):
- Ethnicity—Hispanic or Latino\.
- Ethnicity—Not Hispanic or Latino\.

- Ethnicity—Asked But No Answer\.
- Ethnicity—Unknown\.

Risk adjustment

None\.

Improvement notation

A higher rate indicates better performance\.

Guidance

__Allocation:__  
The member was enrolled with a medical benefit October 1 two years prior to the measurement period through the end of the measurement period\.

No more than one gap in enrollment of up to 45 days for each full calendar year \(i\.e\., the measurement period and the year prior to the measurement period\)\.

No gaps in enrollment are allowed from October 1 two years prior to the measurement period through December 31 two years prior to the measurement period\.

The member must be enrolled on the last day of the measurement period\.

__Reporting:__  
For Medicare plans, the SES stratifications are mutually exclusive\. NCQA calculates a total rate for Medicare plans by adding all six Medicare stratifications\.

For all plans, the race and ethnicity stratifications are mutually exclusive, and the sum of all categories in each stratification is the total population\.

__Definitions__

__Participation__

The identifiers and descriptors for each organization’s coverage used to define members’ eligibility for measure reporting\. Allocation for reporting is based on eligibility during the participation period\.

Participation period

October 1 two years prior to the measurement period through the end of the measurement period\.

Initial population

Members 42–74  52–74 years of age by the end of the measurement period who were recommended for routine breast cancer screening and also meet the criteria for participation\.

Include members recommended for routine breast cancer screening with any of the following criteria:

- Administrative Gender of Female \(AdministrativeGender code female\) at any time in the member’s history\.
- Sex Assigned at Birth \(LOINC code 76689\-9\) of Female \(LOINC code LA3\-6\) at any time in the member’s history\.
- Sex Parameter for Clinical Use of Female \(SexParameterForClinicalUse code female\-typical\) during the measurement period\.

Exclusions

- Members who use hospice services \(Hospice Encounter Value Set; Hospice Intervention Value Set\) or elect to use a hospice benefit any time during the measurement period\. Organizations that use the Monthly Membership Detail Data File to identify these members must use only the run date of the file to determine if the member elected to use a hospice benefit during the measurement period\.
- Members who die any time during the measurement period\.
- Members who had a bilateral mastectomy or both right and left unilateral mastectomies any time during the member’s history through the end of the measurement period\. Any of the following meet the criteria for bilateral mastectomy:
- Bilateral mastectomy \(Bilateral Mastectomy Value Set\)\.
- Unilateral mastectomy \(Unilateral Mastectomy Value Set\) with a bilateral modifier \(CPT Modifier code 50\) \(same procedure\)\.
- Unilateral mastectomy found in clinical data \(Clinical Unilateral Mastectomy Value Set\) with a bilateral qualifier value \(SNOMED CT Modifier code 51440002\) \(same procedure\)\.

__Note: __The “clinical” mastectomy value sets identify mastectomy; the word “clinical” refers to the data source, not to the type of mastectomy\.

- History of bilateral mastectomy \(History of Bilateral Mastectomy Value Set\)\.
- Any combination of codes from the table below that indicate a mastectomy on __*both*__ the left __*and*__ right side on the same date of service or on different dates of service\.

__Left Mastectomy  
\(any of the following\)__

__Right Mastectomy  
\(any of the following\)__

Unilateral mastectomy \(Unilateral Mastectomy Value Set\) __*with *__a left\-side modifier \(CPT Modifier code LT\) \(same procedure\)

Unilateral mastectomy \(Unilateral Mastectomy Value Set\) __*with *__a right\-side modifier \(CPT Modifier code RT\) \(same procedure\)

Unilateral mastectomy found in clinical data \(Clinical Unilateral Mastectomy Value Set\) __*with *__a left\-side qualifier value \(SNOMED CT Modifier code 7771000\) \(same procedure\)

Unilateral mastectomy found in clinical data \(Clinical Unilateral Mastectomy Value Set\) __*with *__a right\-side qualifier value \(SNOMED CT Modifier code 24028007\) \(same procedure\)

Absence of the left breast \(Absence of Left Breast Value Set\)\. Do not include laboratory claims \(claims with POS code 81\)

Absence of the right breast \(Absence of Right Breast Value Set\)\. Do not include laboratory claims \(claims with POS code 81\)

Left unilateral mastectomy \(Unilateral Mastectomy Left Value Set\)

Right unilateral mastectomy \(Unilateral Mastectomy Right Value Set\)

- Members who had gender\-affirming chest surgery \(CPT code 19318\) with a diagnosis of gender dysphoria \(Gender Dysphoria Value Set\) any time during the member’s history through the end of the measurement period\.

- Medicare members 66 years of age and older by the end of the measurement period who meet either of the following:
- Enrolled in an Institutional SNP \(I\-SNP\) any time during the measurement period\.
- Living long\-term in an institution any time during the measurement period, as identified by the LTI flag in the monthly membership detail data file\. Use the run date of the file to determine if a member had an LTI flag during the measurement period\.
- Members 66 years of age and older by the end of the measurement period, with frailty __*and*__ advanced illness\. Members must meet __*both*__ frailty and advanced illness criteria to be excluded:

1\.	__Frailty\.__ At least two indications of frailty \(Frailty Device Value Set; Frailty Diagnosis Value Set; Frailty Encounter Value Set; Frailty Symptom Value Set\) with different dates of service during the measurement period\. Do not include laboratory claims \(claims with POS code 81\)\.

2\.	__Advanced Illness\.__ Either of the following during the measurement period or the year prior to the measurement period:

- Advanced illness \(Advanced Illness Value Set\) on at least two different dates of service\. Do not include laboratory claims \(claims with POS   
code 81\)\.
- Dispensed dementia medication \(Dementia Medications List\)\.
- Members receiving palliative care \(Palliative Care Assessment Value Set; Palliative Care Encounter Value Set; Palliative Care Intervention Value Set\) any time during the measurement period\.
- Members who had an encounter for palliative care \(ICD\-10\-CM code Z51\.5\) any time during the measurement period\. Do not include laboratory claims \(claims with POS code 81\)\.

Denominator

The initial population, minus exclusions\.

Numerator

One or more mammograms \(Mammography Value Set\) any time on or between October 1 two years prior to the measurement period and the end of the measurement period\.

__Data Elements for Reporting __

Organizations that submit data to NCQA must provide the following data elements in a specified file\. 

__*Table BCS\-E\-A\-1/2/3: Data Elements for Breast Cancer Screening*__

Metric

Age

Data Element

Reporting Instructions

BreastCancerScreening

42\-51

InitialPopulation

Report once For each stratification

 

52\-74

ExclusionsByEHR

Report once For each stratification

 

Total

ExclusionsByCaseManagement

Report once For each stratification

 

ExclusionsByHIERegistry

Report once For each stratification

ExclusionsByAdmin

Report once For each stratification

Exclusions

\(Sum over SsoRs\)

Denominator

Report once For each stratification

NumeratorByEHR

Report once For each stratification

NumeratorByCaseManagement

Report once For each stratification

NumeratorByHIERegistry

Report once For each stratification

NumeratorByAdmin

Report once For each stratification

Numerator

\(Sum over SsoRs\)

Rate

\(Percent\)

__*Table BCS\-E\-A\-3 BCS\-E\-B\-3: Data Elements for Breast Cancer Screening*__

Metric

SES Stratification

Data Element

Reporting Instructions

BreastCancerScreening

NonLisDeNondisability

InitialPopulation

For each Stratification

 

LisDe

ExclusionsByEHR

For each Stratification

 

Disability

ExclusionsByCaseManagement

For each Stratification

 

LisDeAndDisability

ExclusionsByHIERegistry

For each Stratification

Other

ExclusionsByAdmin

For each Stratification

 

Unknown

Exclusions

\(Sum over SsoRs\)

 

Total

Denominator

For each Stratification

 

NumeratorByEHR

For each Stratification

 

NumeratorByCaseManagement

For each Stratification

 

NumeratorByHIERegistry

For each Stratification

NumeratorByAdmin

For each Stratification

Numerator

\(Sum over SsoRs\)

Rate

\(Percent\)

__*Table BCS\-E\-B\-1/2/3 BCS\-E\-C\-1/2/3: Data Elements for Breast Cancer Screening: Stratifications by Race*__

Metric

Race

Data Element

Reporting Instructions

BreastCancerScreening

AmericanIndianOrAlaskaNative

InitialPopulation

For each Stratification

Asian

Exclusions

For each Stratification

BlackOrAfricanAmerican 

Denominator

For each Stratification

NativeHawaiianOrOtherPacificIslander 

Numerator

For each Stratification

White

Rate

\(Percent\)

SomeOtherRace

TwoOrMoreRaces

AskedButNoAnswer

Unknown

__*Table BCS\-E\-C\-1/2/3 BCS\-E\-D\-1/2/3: Data Elements for Breast Cancer Screening: Stratifications by Ethnicity*__

__Metric__

__Ethnicity__

__Data Element__

__Reporting Instructions__

BreastCancerScreening

HispanicOrLatino

InitialPopulation

For each Stratification

NotHispanicOrLatino

Exclusions

For each Stratification

AskedButNoAnswer

Denominator

For each Stratification

Unknown

Numerator

For each Stratification

Rate

\(Percent\)

<a id="_Hlk1054351"></a>Rules for Allowable Adjustments of HEDIS

The “Rules for Allowable Adjustments of HEDIS” \(the “Rules”\) describe how NCQA’s HEDIS measure specifications can be adjusted for other populations, if applicable\. The Rules, reviewed and approved by NCQA measure experts, provide for expanded use of HEDIS measures without changing their clinical intent\.

__Adjusted HEDIS measures may not be used for HEDIS health plan reporting\. __

__*Rules for Allowable Adjustments of Breast Cancer Screening—ECDS*__

__NONCLINICAL COMPONENTS __

__Eligible Population__

__Adjustments Allowed \(Yes/No\)__

__Notes__

Product lines

Yes 

Organizations are not required to use product line criteria; product lines may be combined and all \(or no\) product line criteria may be used\.

Ages

Yes, with limits 

Age determination dates may be changed \(e\.g\., select, “age as of June 30”\)\.

The denominator age range may be expanded to 40–74 years\.

Allocation 

Yes 

Organizations are not required to use enrollment criteria; adjustments are allowed\.

Benefit

Yes 

Organizations are not required to use a benefit; adjustments are allowed\.

Other

Yes 

Organizations may use additional eligible population criteria to focus on a population of interest such as gender, race and ethnicity, socioeconomic, sociodemographic characteristic or geographic region\.

__CLINICAL COMPONENTS__

__Initial Population__

__Adjustments Allowed \(Yes/No\)__

__Notes__

Event/diagnosis 

NA

There is no event/diagnosis for this measure\.

__Exclusions__

__Adjustments Allowed \(Yes/No\)__

__Notes__

Exclusions 

No

Only specified exclusions may be applied\. Value sets may not be changed\.

Exclusions: Hospice, deceased member, palliative care, I\-SNP, LTI, frailty and advanced illness

Yes

These exclusions are not required\. Refer to* Exclusions* in the *Guidelines for the* *Rules for Allowable Adjustments\.*

__Denominator__

__Adjustments Allowed \(Yes/No\)__

__Notes__

Denominator

No

The logic may not be changed\. 

__Numerator Criteria__

__Adjustments Allowed \(Yes/No\)__

__Notes__

Mammogram

No

Value sets and logic may not be changed\.

