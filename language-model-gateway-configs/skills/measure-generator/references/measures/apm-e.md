## <a id="_Toc74830499"></a><a id="_Hlk512942590"></a>

## <a id="Metabolic_Monitoring_APME"></a><a id="_Toc74830495"></a><a id="_Toc171403071"></a>Metabolic Monitoring for Children and Adolescents on Antipsychotics \(APM\-E\)\*

__\*Developed with financial support from the Agency for Healthcare Research and Quality \(AHRQ\) and   
the Centers for Medicare & Medicaid Services \(CMS\) under the CHIPRA Pediatric Quality Measures Program   
Centers of Excellence grant number U18 HS020503\.__

Summary of Changes to HEDIS MY 2025

- Removed “Programming Guidance” from the *Characteristics* section\. 
- Removed the *Data criteria \(element level\)* section\. 

Description

The percentage of children and adolescents 1–17 years of age who had two or more antipsychotic prescriptions and had metabolic testing\. Three rates are reported:

- The percentage of children and adolescents on antipsychotics who received blood glucose testing\.
- The percentage of children and adolescents on antipsychotics who received cholesterol testing\.
- The percentage of children and adolescents on antipsychotics who received blood glucose and cholesterol testing\.

Measurement period

January 1–December 31\.

Clinical recommendation statement

The American Academy of Child & Adolescent Psychiatry \(AACAP\) practice parameters endorse the American Psychiatric Association and American Diabetes Association recommendations for laboratory monitoring, including a fasting glucose and fasting lipid profile at baseline, 3 and 12 months \(Findling, 2011\)\.

The Canadian Alliance for Monitoring Effectiveness and Safety of Antipsychotics in Children calls for more frequent monitoring in youth at baseline, 3, 6 and 12 months, and additional monitoring of fasting insulin \(Pringsheim, 2011\)\.

Citations

Findling, R\.L\., S\.S\. Drury, P\.S\. Jensen, J\.L\. Rapoport, O\.G\. Bukstein, H\.J\. Walter, S\. Benson, et al\. 2011\. “Practice Parameter for the Use Of Atypical Antipsychotic Medications in Children and Adolescents\.” *J Am Acad Child Adolesc Psychiatry*\.

Pringsheim, T\., C\. Panagiotopoulos, J\. Davidson, J\. Ho, and Canadian Alliance for Monitoring Effectiveness and Safety of Antipsychotics in Children \(CAMESA\) guideline group\. 2011\. “Evidence\-Based Recommendations for Monitoring Safety of Second\-Generation Antipsychotics in Children and Youth\.” *Paediatrics & Child Health* 16, no\. 9: 581–9\.

Characteristics

Scoring

Proportion\.

Type 

Process\.

Stratification

- Blood Glucose\.
- Product line:
- Commercial\.
- Medicaid\.
- Age \(for each product line\):
- 1–11 years\.
- 12–17 years\.
- Cholesterol\.
- Product line:
- Commercial\.
- Medicaid\.
- Age \(for each product line\):
- 1–11 years\.
- 12–17 years\.
- Blood Glucose and Cholesterol\.
- Product line:
- Commercial\.
- Medicaid\.
- Age \(for each product line\):
- 1–11 years\.
- 12–17 years\.

Risk adjustment

None\.

Improvement notation

A higher rate indicates better performance\.

Guidance

__General Rules:__  
If an organization uses both pharmacy data \(NDC codes\) and clinical data \(RxNorm codes\) for reporting, to avoid double counting, if there are both NDC codes and RxNorm codes on the same date of service, use only one data source for that date of service \(use only NDC codes or only RxNorm codes\) for reporting\. This rule is not included in the measure calculation logic and must be programmed manually\.

__Allocation:__  
The member was enrolled with a medical and pharmacy benefit throughout the measurement period\.

No more than one gap in enrollment of up to 45 days during the measurement period\.

The member must be enrolled on the last day of the measurement period\.

__Reporting:__  
The total is the sum of the age stratifications\.

Definitions

Participation

The identifiers and descriptors for each organization’s coverage used to define members’ eligibility for measure reporting\. Allocation for reporting is based on eligibility during the participation period\.

Participation period

The measurement period\.

Initial population

__Initial population 1  
__Members 1–17 years by the end of the measurement period with at least two antipsychotic medication dispensing events \(APM Antipsychotic Medications List\) of the same or different medications on different dates of service during the measurement period, and who also meet criteria for participation\.

__Initial population 2  
__Same as the initial population 1\.

__Initial population 3  
__Same as the initial population 1\.

Exclusions

__Exclusions 1__

- Members who use hospice services \(Hospice Encounter Value Set; Hospice Intervention Value Set\) or elect to use a hospice benefit any time during the measurement period\. Organizations that use the Monthly Membership Detail Data File to identify these members must use only the run date of the file to determine if the member elected to use a hospice benefit during the measurement period\.
- Members who die any time during the measurement period\.

__Exclusions 2  
__Same as exclusions 1\.

__Exclusions 3  
__Same as exclusions 1\.

Denominator

__Denominator 1  
__The initial population, minus exclusions\.

__Denominator 2  
__Same as denominator 1\.

__Denominator 3  
__Same as denominator 1\.

Numerator

__Numerator 1—Blood Glucose  
__Members who received at least one test for blood glucose or HbA1c during the measurement period\. Any of the following meet criteria:

- Glucose Lab Test Value Set\.
- Glucose Test Result or Finding Value Set\.
- HbA1c Lab Test Value Set\.
- HbA1c Test Result or Finding Value Set\. Do not include codes with a modifier \(CPT CAT II Modifier Value Set\) or from laboratory claims \(claims with POS code 81\)\.

__Numerator 2—Cholesterol  
__Members who received at least one test for LDL\-C or cholesterol during the measurement period\. Any of the following meet criteria:

- Cholesterol Lab Test Value Set\.
- Cholesterol Test Result or Finding Value Set\.
- LDL C Lab Test Value Set\.
- LDL C Test Result or Finding Value Set\. Do not include codes with a modifier \(CPT CAT II Modifier Value Set\) or from laboratory claims \(claims with POS code 81\)\.

__Numerator 3—Blood Glucose and Cholesterol  
__Members who were compliant for both the blood glucose and cholesterol indicators \(numerator 1 and numerator 2\)\.

__Data Elements for Reporting __

Organizations that submit data to NCQA must provide the following data elements in a specified file\. 

__*Table APM\-E\-1/2: Data Elements for Metabolic Monitoring for Children and Adolescents on Antipsychotics*__

__Metric__

__Age__

__Data Element__

__Reporting Instructions__

BloodGlucoseTesting

1\-11

Benefit

Metadata

CholesterolTesting

12\-17

InitialPopulationByEHR

For each Stratification, repeat per Metric

BloodGlucoseCholesterolTesting

Total

InitialPopulationByCaseManagement

For each Stratification, repeat per Metric

 

InitialPopulationByHIERegistry

For each Stratification, repeat per Metric

InitialPopulationByAdmin

For each Stratification, repeat per Metric

 

InitialPopulation

\(Sum over SSoRs\)

 

Exclusions

For each Stratification, repeat per Metric

 

Denominator

For each Stratification, repeat per Metric

 

NumeratorByEHR

For each Metric and Stratification

NumeratorByCaseManagement

For each Metric and Stratification

NumeratorByHIERegistry

For each Metric and Stratification

NumeratorByAdmin

For each Metric and Stratification

Numerator

\(Sum over SSoRs\)

Rate

\(Percent\)

__Rules for Allowable Adjustments of HEDIS__

The “Rules for Allowable Adjustments of HEDIS” \(the “Rules”\) describe how NCQA’s HEDIS measure specifications can be adjusted for other populations, if applicable\. The Rules, reviewed and approved by NCQA measure experts, provide for expanded use of HEDIS measures without changing their clinical intent\.

__Adjusted HEDIS measures may not be used for HEDIS health plan reporting\. __

__*Allowable Adjustments of Metabolic Monitoring of Children and Adolescents on Antipsychotics—ECDS*__

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

Changing the denominator age range is allowed within a specified age range \(ages 1–17\+ years\)\. Additionally, the upper age range may be expanded or no upper age limit may be used\.

Allocation 

Yes 

Organizations are not required to use enrollment criteria; adjustments are allowed\.

Benefit

Yes 

Organizations are not required to use a benefit; adjustments are allowed\.

Other

Yes 

Organizations may use additional eligible population criteria to focus on an area of interest defined by gender, race, ethnicity, socioeconomic or sociodemographic characteristics, geographic region or another characteristic\.

__CLINICAL COMPONENTS__

__Initial Population__

__Adjustments Allowed \(Yes/No\)__

__Notes__

Event/diagnosis 

No

Only dispensing events that contain \(or map to\) codes in the medication lists and value sets may be used to identify antipsychotic medication events\. Medication lists, value sets and logic may not be changed\.

__Exclusions__

__Adjustments Allowed \(Yes/No\)__

__Notes__

Exclusions: Hospice and deceased member

Yes

These exclusions are not required\. Refer to* Exclusions* in the *Guidelines for the* *Rules for Allowable Adjustments\.*

__Denominator__

__Adjustments Allowed \(Yes/No\)__

__Notes__

Denominators

No

The logic may not be changed\. 

__Numerator Criteria__

__Adjustments Allowed \(Yes/No\)__

__Notes__

Metabolic Monitoring

No

Value sets, direct reference codes and logic may not be changed\.

