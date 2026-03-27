## <a id="Colorectal_Cancer_Screening_COLE"></a><a id="_Toc171403068"></a>Colorectal Cancer Screening \(COL\-E\)

Summary of Changes to HEDIS MY 2025

- Removed “Programming Guidance” from the *Characteristics* section\. 
- Removed the *Data criteria \(element level\)* section\.
- Removed the data source reporting requirement from the race and ethnicity stratification\.

Description

The percentage of members 45–75 years of age who had appropriate screening for colorectal cancer\.

Measurement period

January 1–December 31\.

Clinical recommendation statement

The U\.S\. Preventive Services Task Force “recommends screening for colorectal cancer in all adults aged 50 to 75 years \(A recommendation\) and all adults   
aged 45 to 49 years \(B recommendation\)\.” Potential screening methods include an annual guaiac\-based fecal occult blood test \(gFOBT\), annual fecal immunochemical test \(FIT\), multitargeted stool DNA with FIT test \(sDNA FIT\) every 3 years, colonoscopy every 10 years, CT colonography every 5 years, flexible sigmoidoscopy every 5 years or flexible sigmoidoscopy every 10 years, with FIT every year\.

Citations

U\.S\. Preventive Services Task Force\. 2021\. “Screening for Colorectal Cancer: U\.S\. Preventive Services Task Force Recommendation Statement\.” *JAMA *325\(19\):1965–1977\. doi:10\.1001/jama\.2021\.6238

Characteristics

Scoring

Proportion\.

Type

Process\.

Stratification

- Colorectal Cancer Screening\.
- Product line:
- Commercial\.
- Medicaid\.
- Medicare\.
- Age \(for each product line\):
- 46–50 years\.
- 51–75 years\.
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
The member was enrolled with a medical benefit during the measurement period and the year prior to the measurement period\.

No more than one gap in enrollment of up to 45 days during each calendar year \(i\.e\., the measurement period and the year prior to the measurement period\)\.

The member must be enrolled on the last day of the measurement period\.

__Reporting:__  
For Medicare plans, the SES stratifications are mutually exclusive, and the sum of all six stratifications is the total population\.

For all plans, the race and ethnicity stratifications are mutually exclusive, and the sum of all categories in each stratification is the total population\.

Definitions

Participation

The identifiers and descriptors for each organization’s coverage used to define members’ eligibility for measure reporting\. Allocation for reporting is based on eligibility during the participation period\.

Participation period

The measurement period and the year prior to the measurement period\.

Initial population

Members 46–75 years as of the end of the measurement period who also meet the criteria for participation\.

Exclusions

- Members who use hospice services \(Hospice Encounter Value Set; Hospice Intervention Value Set\) or elect to use a hospice benefit any time during the measurement period\. Organizations that use the Monthly Membership Detail Data File to identify these members must use only the run date of the file to determine if the member elected to use a hospice benefit during the measurement period\.
- Members who die any time during the measurement period\.
- Members who had colorectal cancer \(Colorectal Cancer Value Set\) any time during the member’s history through December 31 of the measurement year\. Do not include laboratory claims \(claims with POS code 81\)\.
- Members who had a total colectomy \(Total Colectomy Value Set; SNOMEDCT code 119771000119101\) any time during the member’s history through December 31 of the measurement period\.
- Medicare members 66 years of age and older by the end of the measurement period who meet either of the following:
- Enrolled in an Institutional SNP \(I\-SNP\) any time during the measurement period\.
- Living long\-term in an institution any time during the measurement period, as identified by the LTI flag in the monthly membership detail data file\. Use the run date of the file to determine if a member had an LTI flag during the measurement period\.
- Members 66 years of age and older by the end of the measurement period, with frailty __*and*__ advanced illness\. Members must meet __*both*__ frailty and advanced illness criteria to be excluded:

1\.	__Frailty\.__ At least two indications of frailty \(Frailty Device Value Set; Frailty Diagnosis Value Set; Frailty Encounter Value Set; Frailty Symptom Value Set\) with different dates of service during the measurement period\. Do not include laboratory claims \(claims with POS code 81\)\.

2\.	__Advanced Illness\.__ Either of the following during the measurement period or the year prior to the measurement period:

- Advanced illness \(Advanced Illness Value Set\) on at least two different dates of service\. Do not include laboratory claims \(claims with POS code 81\)\.
- Dispensed dementia medication \(Dementia Medications List\)\.
- Members receiving palliative care \(Palliative Care Assessment Value Set; Palliative Care Encounter Value Set; Palliative Care Intervention Value Set\) any time during the measurement period\.
- Members who had an encounter for palliative care \(ICD\-10\-CM code Z51\.5\) any time during the measurement year\. Do not include laboratory claims \(claims with POS code 81\)\.

Denominator

The initial population, minus exclusions\.

Numerator

Members with one or more screenings for colorectal cancer\. Any of the following meet criteria:

- Fecal occult blood test \(FOBT Lab Test Value Set; FOBT Test Result or Finding Value Set\) during the measurement period\. For administrative data, assume the required number of samples were returned, regardless of FOBT type\.
- Stool DNA \(sDNA\) with FIT test \(sDNA FIT Lab Test Value Set; SNOMEDCT code 708699002\) during the measurement period or the   
2 years prior to the measurement period\.
- Flexible sigmoidoscopy \(Flexible Sigmoidoscopy Value Set; SNOMEDCT code 841000119107\) during the measurement period or the 4 years prior to the measurement period\.
- CT colonography \(CT Colonography Value Set\) during the measurement period or the 4 years prior to the measurement period\.
- Colonoscopy \(Colonoscopy Value Set; SNOMEDCT code 851000119109\) during the measurement period or the 9 years prior to the measurement period\.

__Data Elements for Reporting __

Organizations that submit data to NCQA must provide the following data elements in a specified file\. 

__*Table COL\-E\-A\-1/2/3: Metadata Elements for Colorectal Cancer Screening*__

__Metric__

__Age __

__Data Element__

__Reporting Instructions__

ColorectalCancerScreening

46\-50

InitialPopulation

For each Stratification

 

51\-75

ExclusionsByEHR

For each Stratification

 

Total

ExclusionsByCaseManagement

For each Stratification

 

ExclusionsByHIERegistry

For each Stratification

ExclusionsByAdmin

For each Stratification

 

Exclusions

\(Sum over SSoRs\)

 

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

\(Sum over SSoRs\)

Rate

\(Percent\)

__*Table COL\-E\-B\-3: Data Elements for Colorectal Cancer Screening: SES Stratifications*__

__Metric__

__SES Stratification__

__Data Element__

__Reporting Instructions__

ColorectalCancerScreening

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

\(Sum over SSoRs\)

 

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

\(Sum over SSoRs\)

Rate

\(Percent\)

__*Table COL\-E\-C 1/2/3: Data Elements for Colorectal Cancer Screening: Stratifications by Race*__

__Metric__

__Race__

__Data Element__

__Reporting Instructions__

ColorectalCancerScreening

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

__*Table COL\-E\-D\-1/2/3: Data Elements for Colorectal Cancer Screening: Stratifications by Ethnicity*__

__Metric__

__Ethnicity__

__Data Element__

__Reporting Instructions__

ColorectalCancerScreening

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

Rules for Allowable Adjustments of HEDIS

<a id="_Hlk1054445"></a>The “Rules for Allowable Adjustments of HEDIS” \(the “Rules”\) describe how NCQA’s HEDIS measure specifications can be adjusted for other populations, if applicable\. The Rules, reviewed and approved by NCQA measure experts, provide for expanded use of HEDIS measures without changing their clinical intent\.

__Adjusted HEDIS measures may not be used for HEDIS health plan reporting\. __

__*Rules for Allowable Adjustments of Colorectal Cancer Screening—ECDS*__

__NONCLINICAL COMPONENTS __

__Eligible Population__

__Adjustments Allowed \(Yes/No\)__

__Notes__

Product lines

Yes

Organizations are not required to use product line criteria; product lines may be combined and all \(or no\) product line criteria may be used\.

Ages

Yes, with limits

The age determination dates may be changed \(e\.g\., select, “age as of June 30”\)\.

The denominator age may be expanded to 45\-85 years of age\. 

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

Only the specified exclusions may be applied\. Value sets may not be changed\.

Exclusions: Hospice, deceased member, palliative care, I\-SNP, LTI, frailty and advanced illness

Yes

These exclusions are not required\. Refer to *Exclusions* in the *Guidelines for the Rules for Allowable Adjustments*\. 

__Denominator__

__Adjustments Allowed \(Yes/No\)__

__Notes__

Denominator

No

The logic may not be changed\. 

__Numerator Criteria__

__Adjustments Allowed \(Yes/No\)__

__Notes__

Colorectal Cancer Screening

No 

The value sets, direct reference codes and logic may not be changed\.

