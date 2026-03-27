## <a id="Chlamydia_Screening_CHL"></a><a id="_Toc171402971"></a><a id="_Toc400546113"></a><a id="_Toc74750486"></a><a id="CHL"></a>Chlamydia Screening \(CHL\)

Summary of Changes to HEDIS MY 2025

- Updated the measure title from *Chlamydia Screening in Women *to *Chlamydia Screening*\. 
- Replaced references to “women” with “members recommended for routine chlamydia screening\.” 
- Added criteria for “members recommended for routine chlamydia screening” to the eligible population\. 
- Added an exclusion for members who were assigned male at birth\. 
- Added a note to clarify that supplemental data can be used to identify members recommended for routine chlamydia screening\.

Description

The percentage of members 16–24 years of age who were recommended for routine chlamydia screening, were identified as sexually active and had at least one test for chlamydia during the measurement year\. 

Eligible Population 

Product lines

Commercial, Medicaid \(report each product line separately\)\.

Ages

Members 16–24 years as of December 31 of the measurement year\. Report two age stratifications and a total rate:

- 16–20 years\.
- 21–24 years\.
- Total\.

The total is the sum of the age stratifications\.

Continuous enrollment

The measurement year\. 

Allowable gap

No more than one gap in enrollment of up to 45 days during the measurement year\. To determine continuous enrollment for a Medicaid beneficiary for whom enrollment is verified monthly, the member may not have more than a 1\-month gap in coverage \(e\.g\., a member whose coverage lapses for 2 months \[60 days\] is not considered continuously enrolled\)\. 

Anchor date

December 31 of the measurement year\. 

Benefit

Medical\.

Members recommended for routine chlamydia screening

Include members recommended for routine chlamydia screening with any of the following criteria:

- Administrative Gender: Female \(AdministrativeGender code female\) any time in the member’s history\.
- Sex Assigned at Birth: \(LOINC code 76689\-9\) Female \(LOINC code   
LA3\-6\) any time in the member’s history\.
- Sex Parameter for Clinical Use of Female \(SexParameterForClinicalUse code female\-typical\) during the measurement year\. 

Event/diagnosis

Follow the steps below to identify the eligible population\.

*Step 1*

Identify members who were recommended for routine chlamydia screening and are sexually active\. Two methods identify sexually active members: pharmacy data and claim/encounter data\. The organization must use both methods to identify the eligible population, but a member only needs to be identified by one method to be eligible for the measure\.

*Claim/encounter data\.* Members who had a claim or encounter indicating sexual activity during the measurement year\. Any of the following meets criteria\. 

- Diagnoses Indicating Sexual Activity Value Set\. Do not include laboratory claims \(claims with POS code 81\)\.
- Procedures Indicating Sexual Activity Value Set\.
- Pregnancy Tests Value Set\.

*Pharmacy data\. *At least one contraceptive medication dispensing event during the measurement year \(Contraceptive Medications List\)\.

### Contraceptive Medications

Description

Prescription

Contraceptives

- Desogestrel\-ethinyl estradiol
- Dienogest\-estradiol \(multiphasic\)
- Drospirenone\-ethinyl estradiol
- Drospirenone\-ethinyl estradiol\-levomefolate \(biphasic\)
- Ethinyl estradiol\-ethynodiol
- Ethinyl estradiol\-etonogestrel
- Ethinyl estradiol\-levonorgestrel
- Ethinyl estradiol\-norelgestromin

- Ethinyl estradiol\-norethindrone
- Ethinyl estradiol\-norgestimate
- Ethinyl estradiol\-norgestrel
- Etonogestrel
- Levonorgestrel
- Medroxyprogesterone
- Norethindrone

Diaphragm

- Diaphragm

Spermicide

- Nonoxynol 9

*Step 2*

For the members identified in step 1 based on a pregnancy test alone, remove members with either of the following:

- A pregnancy test \(Pregnancy Tests Value Set\) during the measurement year and a prescription for isotretinoin \(Retinoid Medications List\) on the date of the pregnancy test through 6 days after the pregnancy test\. 
- A pregnancy test \(Pregnancy Tests Value Set\) during the measurement year and an x\-ray \(Diagnostic Radiology Value Set\) on the date of the pregnancy test through 6 days after the pregnancy test\.

__*Retinoid Medications*__

__Description__

__Prescription__

Retinoid

Isotretinoin

Required exclusions

Exclude members who meet any of the following criteria:

- Sex Assigned at Birth: \(LOINC code 76689\-9\) Male \(LOINC code LA2\-8\) any time in the member’s history\. 
- Members who use hospice services \(Hospice Encounter Value Set; Hospice Intervention Value Set\) or elect to use a hospice benefit any time during the measurement year\. Organizations that use the Monthly Membership Detail Data File to identify these members must use only the run date of the file to determine if the member elected to use a hospice benefit during the measurement year\. 
- Members who die any time during the measurement year\. 

Administrative Specification

Denominator

The eligible population\.

Numerator

At least one chlamydia test \(Chlamydia Tests Value Set\) during the measurement year\. 

*Note*

- *Do not include supplemental data when identifying the eligible population, except when identifying members recommended for routine chlamydia screening criteria and required exclusions\.*

Data Elements for Reporting 

Organizations that submit HEDIS data to NCQA must provide the following data elements\.

__*Table CHL\-1/2: Data Elements for Chlamydia Screening *__

Metric

Age

Data Element

Reporting Instructions

ChlamydiaScreening

16\-20

EligiblePopulation 

For each Stratification

21\-24

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

__Adjusted HEDIS measures may not be used for HEDIS health plan reporting__

### Rules for Allowable Adjustments of Chlamydia Screening 

__NONCLINICAL COMPONENTS__

Eligible Population

Adjustments Allowed \(Yes/No\)

Notes

Product lines

Yes

Organizations are not required to use product line criteria; product lines may be combined and all \(or no\) product line criteria may be used\.

Ages

Yes, with limits

The age determination dates may be changed \(e\.g\., select, “age as of June 30”\)\.

The denominator age may not be expanded\.

Continuous enrollment, allowable gap, anchor date

Yes

Organizations are not required to use enrollment criteria; adjustments are acceptable\.

Benefit

Yes

Organizations are not required to use a benefit; adjustments are acceptable\.

Other

Yes

Organizations may use additional eligible population criteria to focus on an area of interest defined by gender, race, ethnicity, socio\-economic or sociodemographic characteristics, geographic region or another characteristic\. 

__CLINICAL COMPONENTS__

Eligible Population

Adjustments Allowed \(Yes/No\)

Notes

Event/diagnosis

Yes, with limits

Only events that contain \(or map to\) codes in medication lists and value sets may be used to identify sexual activity\. Medication lists, value sets and logic may not be changed\. Claims/encounter data or pharmacy data may be used to identify sexual activity\.

Denominator Exclusions

Adjustments Allowed \(Yes/No\)

Notes

Required exclusions

Yes, with limits

Apply required exclusions according to specified value sets\.

The hospice and deceased member exclusions are not required\. Refer to *Exclusions* in the *Guidelines for the Rules for Allowable Adjustments*\.

Numerator Criteria

Adjustments Allowed \(Yes/No\)

Notes

Chlamydia Test

No 

Value sets and logic may not be changed\.

