## <a id="FollowUp_ED_Visit_MultipleChronic_FMC"></a><a id="_Toc74817960"></a><a id="_Toc171403008"></a>Follow\-Up After Emergency Department Visit for People With Multiple High\-Risk Chronic Conditions \(FMC\)

Summary of Changes to HEDIS MY 2025

- Added a laboratory claim exclusion to a value set for which laboratory claims should not be used\.
- Deleted the *Note* regarding billing methods for intensive outpatient encounters and partial hospitalizations\.
- *Technical Update: *Revised the event/diagnosis and Data Elements for Reporting table\. 

Description

The percentage of emergency department \(ED\) visits for members 18 years of age and older who have multiple high\-risk chronic conditions who had a follow\-up service within 7 days of the ED visit\.

Eligible Population

Product lines

Medicare\. 

Ages

18 years and older as of the ED visit\. Report two age stratifications and a total rate:

- 18–64 years\. 
- 65 years and older\. 
- Total\. 

Continuous enrollment

365 days prior to the ED visit through 7 days after the ED visit\.

Allowable gap

No more than one gap in enrollment of up to 45 days during the 365 days prior to the ED visit and no gap during the 7 days following the ED visit\. 

Anchor date

None\. 

Benefits

Medical\. 

Event/diagnosis

Follow the steps below to identify the eligible population\.

__*Step 1*__

An ED visit \(ED Value Set\) on or between January 1 and December 24 of the measurement year where the member was 18 years or older on the date of the visit\. 

The denominator for this measure is based on ED visits, not on members\. If a member has more than one ED visit, identify all ED visits between January 1 and December 24 of the measurement year\.

__*Step 2:*__  
__* ED visits resulting in inpatient stay*__

Exclude ED visits that result in an inpatient stay\. Exclude ED visits followed by admission to an acute or nonacute inpatient care setting on the date of the ED visit or within 7 days after the ED visit, regardless of the principal diagnosis for admission\. To identify admissions to an acute or nonacute inpatient care setting:

1\.	Identify all acute and nonacute inpatient stays \(Inpatient Stay Value Set\)\.

2\.	Identify the admission date for the stay\.

These events are excluded from the measure because admission to an acute or nonacute setting may prevent an outpatient follow\-up visit from taking place\.

__*Step 3: *__  
__*Eligible chronic condition diagnoses*__

Identify ED visits where the member had a chronic condition prior to the ED visit\. 

The following are eligible chronic condition diagnoses\. Each bullet indicates an eligible chronic condition \(for example, COPD and asthma are considered the same chronic condition\):

- COPD, asthma or unspecified bronchitis \(COPD Diagnosis Value Set; Asthma Diagnosis Value Set; ICD\-10\-CM code J40\)\.
- Alzheimer’s disease and related disorders \(Dementia Value Set; Frontotemporal Dementia Value Set\)\.
- Chronic kidney disease \(Chronic Kidney Disease Value Set\)\.
- Depression \(Major Depression Value Set; Dysthymic Disorder Value Set\)\.
- Heart failure \(Chronic Heart Failure and Cardiomyopathy Value Set; Heart Failure Diagnosis Value Set\)\.
- Acute myocardial infarction \(MI Value Set; Old Myocardial Infarction Value Set\)\.
- Atrial fibrillation \(Atrial Fibrillation Value Set\)\.
- Stroke and transient ischemic attack \(Stroke Value Set\)\.
- Remove any visit with a principal diagnosis of encounter for other specified aftercare \(ICD\-10\-CM code Z51\.89\)\. 
- Remove any visit with any diagnosis of concussion with loss of consciousness or fracture of vault of skull, initial encounter \(Other Stroke Exclusions Value Set\)\.

Using the eligible chronic condition diagnoses above, identify members who had any of the following during the measurement year or the year prior to the measurement year, but prior to the ED visit \(count services that occur over both years\): 

- At least two outpatient visits, ED visits, telephone visits, e\-visits, virtual check\-ins or nonacute inpatient encounters \(Outpatient, ED, Telehealth and Nonacute Inpatient Value Set\) or nonacute inpatient discharges \(instructions below; the diagnosis must be on the discharge claim\) on different dates of service, with an eligible chronic condition\. Visit type need not be the same for the two visits, but the visits must be for the same eligible chronic condition*\.* To identity a nonacute inpatient discharge:

1\.	Identify all acute and nonacute inpatient stays \(Inpatient Stay Value Set\)\.

2\.	Confirm the stay was for nonacute care based on the presence of a nonacute code \(Nonacute Inpatient Stay Value Set\) on the claim\. 

3\.	Identify the discharge date for the stay\.

- At least one acute inpatient encounter \(Acute Inpatient Value Set\) with an eligible chronic condition\.
- At least one acute inpatient discharge with an eligible chronic condition on the discharge claim\. To identify an acute inpatient discharge:

1\.	Identify all acute and nonacute inpatient stays \(Inpatient Stay Value Set\)\.

2\.	Confirm the stay was for nonacute care based on the presence of a nonacute code \(Nonacute Inpatient Stay Value Set\) on the claim\. Exclude nonacute inpatient stays \(Nonacute Inpatient Stay Value Set\)\.

3\.	Identify the discharge date for the stay\.

For each ED visit, identify the total number of chronic conditions the member had prior to the ED visit\. 

__*Step 4: *  
*Identifying members with multiple chronic conditions*__

Identify ED visits where the member had two or more different chronic conditions prior to the ED visit, that meet the criteria included in step 3\. These are eligible ED visits\. 

__*Step 5:  
Multiple visits in 8\-day period*__

If a member has more than one ED visit in an 8\-day period, include only the first eligible ED visit\. For example, if a member has an eligible ED visit on January 1, include the January 1 visit and do not include ED visits that occur on or between January 2 and January 8\. Then, if applicable, include the next eligible ED visit that occurs on or after January 9\. Identify visits chronologically, including only one visit per 8\-day period\.

Required exclusions

Exclude members who meet either of the following criteria: 

- Members who use hospice services \(Hospice Encounter Value Set; Hospice Intervention Value Set\) or elect to use a hospice benefit any time during the measurement year\. Organizations that use the Monthly Membership Detail Data File to identify these members must use only the run date of the file to determine if the member elected to use a hospice benefit during the measurement year\. 
- Members who die any time during the measurement year\. 

Administrative Specification

Denominator

The eligible population\. 

Numerator

__*7\-Day *__  
__*Follow\-Up*__

A follow\-up service within 7 days after the ED visit \(8 total days\)\. Include visits that occur on the date of the ED visit\. The following meet criteria for follow\-up:

- An outpatient visit, telephone visit, e\-visit or virtual check\-in \(Outpatient and Telehealth Value Set\)\.
- Transitional care management services \(Transitional Care Management Services Value Set\)\.
- Case management visits \(Case Management Encounter Value Set\)\. 
- Complex Care Management Services \(Complex Care Management Services Value Set\)\.
- An outpatient or telehealth behavioral health visit \(Visit Setting Unspecified Value Set __*with*__ Outpatient POS Value Set\)\.
- An outpatient or telehealth behavioral health visit \(BH Outpatient Value Set\)\.

- An intensive outpatient encounter or partial hospitalization \(Visit Setting Unspecified Value Set __*with*__ POS code 52\)\.
- An intensive outpatient encounter or partial hospitalization \(Partial Hospitalization or Intensive Outpatient Value Set\)\.
- A community mental health center visit \(Visit Setting Unspecified Value Set __*with*__ POS code 53\)\.
- Electroconvulsive therapy \(Electroconvulsive Therapy Value Set\) __*with*__ \(Outpatient POS Value Set; POS code 24; POS code 52; POS code 53\)\.
- A telehealth visit \(Visit Setting Unspecified Value Set __*with*__ Telehealth POS Value Set\)\.
- A substance use disorder service \(Substance Use Disorder Services Value Set\)\.
- Substance use disorder counseling and surveillance \(Substance Abuse Counseling and Surveillance Value Set\)\. Do not include laboratory claims \(claims with POS code 81\)\.

__Data Elements for Reporting__

Organizations that submit HEDIS data to NCQA must provide the following data elements\.

__*Table FMC\-3: 	Data Elements for Follow\-Up After Emergency Department Visit for People   
With High\-Risk Multiple Chronic Conditions*__

Metric

Age

Data Element

Reporting Instructions

FollowUp7Day

18\-64 16\-64

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

### Rules for Allowable Adjustments of Follow\-Up After Emergency Department Visit for People With High\-Risk Multiple Chronic Conditions

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

Expanding the denominator age range is allowed\.

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

Only events or diagnoses that contain \(or map to\) codes in the value sets may be used to identify visits with a diagnosis\. The value sets and logic may not be changed\.

__*Note:*__* Organizations may assess at the member level by applying measure logic appropriately \(i\.e\., percentage of members with documentation of an emergency department visit with multiple high\-risk chronic conditions, who had a follow\-up visit within 7 days\)\.*

__Denominator Exclusions__

__Adjustments Allowed \(Yes/No\)__

__Notes__

Required exclusions

Yes

The hospice and deceased member exclusions are not required\. Refer to *Exclusions* in the *Guidelines for the Rules for Allowable Adjustments*\.

__Numerator Criteria__

__Adjustments Allowed \(Yes/No\)__

__Notes__

7\-Day Follow\-Up

No

Value sets and logic may not be changed\.

<a id="_Toc400546111"></a>

<a id="_Toc74825572"></a><a id="_Toc171403009"></a>Overuse/Appropriateness

