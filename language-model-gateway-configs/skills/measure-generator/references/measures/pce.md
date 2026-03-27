## <a id="Pharmacotherapy_Management_COPD_PCE"></a><a id="_Toc400546121"></a><a id="_Toc74815061"></a><a id="_Toc171402977"></a><a id="PCE"></a>Pharmacotherapy Management of COPD Exacerbation \(PCE\)

Summary of Changes to HEDIS MY 2025

- No changes to this measure\.

Description

The percentage of COPD exacerbations for members 40 years of age and older who had an acute inpatient discharge or ED visit on or between January 1–November 30 of the measurement year and who were dispensed appropriate medications\. Two rates are reported:

1. Dispensed a Systemic Corticosteroid \(or there was evidence of an active prescription\) within   
14 days of the event\.
2. Dispensed a Bronchodilator \(or there was evidence of an active prescription\) within 30 days of the event\.

__Note:__ The eligible population for this measure is based on acute inpatient discharges and ED visits, not on members\. It is possible for the denominator to include multiple events for the same individual\. 

Definitions

Intake period

January 1 of the measurement year to November 30 of the measurement year\. The intake period captures eligible episodes of treatment\. 

Episode date

The date of service for any acute inpatient discharge or ED visit during the intake period with a principal diagnosis of COPD\. 

*For an acute inpatient discharge,* the episode date is the date of discharge\.

*For direct transfers \(to acute or nonacute settings\), *the episode date is the discharge date from the transfer admission\. 

*For an ED visit,* the episode date is the date of service\. 

Active prescription

A prescription is considered active if the “days supply” indicated on the date when the member was dispensed the prescription is the number of days or more between that date and the relevant date\.

*For an acute inpatient stay,* the relevant date is the date of admission\.

*For an ED visit,* the relevant date is the date of service\.

Eligible Population

Product lines

Commercial, Medicaid, Medicare \(report each product line separately\)\. 

Ages

40 years or older as of January 1 of the measurement year\.

Continuous enrollment

Episode date through 30 days after the episode date\.

Allowable gap

None\.

Anchor date

Episode date\.

Benefits

Medical and pharmacy\.

Event/diagnosis

A COPD exacerbation as indicated by an acute inpatient discharge or ED encounter with a principal diagnosis of COPD\. 

Follow the steps below to identify the eligible population\.

*Step 1*

Identify all members who had either of the following during the intake period:

- An ED visit \(ED Value Set\) with a principal diagnosis of COPD, emphysema or chronic bronchitis \(Chronic Obstructive Pulmonary Diseases Value Set\)\. 
- An acute inpatient discharge with a principal diagnosis of COPD, emphysema or chronic bronchitis \(Chronic Obstructive Pulmonary Diseases Value Set\) on the discharge claim\. To identify acute inpatient discharges:

1. Identify all acute and nonacute inpatient stays \(Inpatient Stay Value Set\)\.
2. Exclude nonacute inpatient stays \(Nonacute Inpatient Stay Value Set\)\.
3. Identify the discharge date for the stay\.

*Step 2*

Identify all COPD episodes\. For each member identified in step 1, identify all acute inpatient discharges and ED visits\. An acute inpatient discharge and ED visit on the same date are counted as one COPD episode\. Multiple ED visits on the same date are counted as one COPD episode\. Do not include ED visits that result in an inpatient stay \(Inpatient Stay Value Set\)\.

*Step 3*

Test for direct transfers\. For episodes with a direct transfer to an acute or nonacute setting for any diagnosis, the episode date is the discharge date from the last admission\. 

A __direct transfer__ is when the discharge date from the first inpatient setting precedes the admission date to a second inpatient setting by one calendar day or less\. For example:

- An inpatient discharge on June 1, followed by an admission to another inpatient setting on June 1, *is a direct transfer\.*
- An inpatient discharge on June 1, followed by an admission to an inpatient setting on June 2, *is a direct transfer\.*
- An inpatient discharge on June 1, followed by an admission to another inpatient setting on June 3, *is not a direct transfer;* these are two distinct inpatient stays\.

Use the following method to identify admissions to and discharges from inpatient settings\.

1. Identify all acute and nonacute inpatient stays \(Inpatient Stay Value Set\)\.
2. Identify the admission and discharge dates for the stay\.

*Step 4*

Calculate continuous enrollment\. The member must be continuously enrolled without a gap in coverage from the episode date through 30 days after the episode date\. 

__Note: __All episodes that were not excluded remain in the denominator\. The denominator for this measure is based on acute inpatient discharges and ED visits, not on members\.

Required exclusions

Exclude members who meet either of the following criteria:

- Members who use hospice services \(Hospice Encounter Value Set; Hospice Intervention Value Set\) or elect to use a hospice benefit any time during the measurement year\. Organizations that use the Monthly Membership Detail Data File to identify these members must use only the run date of the file to determine if the member elected to use a hospice benefit during the measurement year\. 
- Members who die any time during the measurement year\. 

Administrative Specification

Denominator

The eligible population\.

Numerators

*Systemic Corticosteroid*

Dispensed prescription for systemic corticosteroid \(Systemic Corticosteroid Medications List\) on or 14 days after the episode date\. Count systemic corticosteroids that are active on the relevant date\.

Systemic Corticosteroid Medications

Description

Prescription

Glucocorticoids

- Cortisone
- Dexamethasone

- Hydrocortisone
- Methylprednisolone

- Prednisolone
- Prednisone

*Bronchodilator*

Dispensed prescription for a bronchodilator \(Bronchodilator Medications List\) on or 30 days after the episode date\. Count bronchodilators that are active on the relevant date\.

Bronchodilator Medications

Description

Prescription

Anticholinergic agents

- Aclidinium bromide
- Ipratropium

- Tiotropium
- Umeclidinium

Beta 2\-agonists

- Albuterol
- Arformoterol
- Formoterol

- Indacaterol 
- Levalbuterol
- Metaproterenol

- Olodaterol 
- Salmeterol

Bronchodilator combinations

- Albuterol\-ipratropium
- Budesonide\-formoterol
- Fluticasone\-salmeterol
- Fluticasone\-vilanterol

- Formoterol\-aclidinium
- Formoterol\-glycopyrrolate
- Formoterol\-mometasone
- Glycopyrrolate\-indacaterol

- Olodaterol\-tiotropium
- Umeclidinium\-vilanterol

- Fluticasone furoate\-umeclidinium\-vilanterol

Data Elements for Reporting 

Organizations that submit HEDIS data to NCQA must provide the following data elements\.

__*Table PCE\-1/2/3:	Data Elements for Pharmacotherapy Management of COPD Exacerbation*__

__Metric__

__Data Element__

__Reporting Instructions__

SystemicCorticosteroid

Benefit

Metadata

Bronchodilator

EligiblePopulation 

Repeat per Metric

ExclusionAdminRequired

Repeat per Metric

NumeratorByAdmin

For each Metric

NumeratorBySupplemental

For each Metric

Rate

\(Percent\)

Rules for Allowable Adjustments of HEDIS

The “Rules for Allowable Adjustments of HEDIS” \(the “Rules”\) describe how NCQA’s HEDIS measure specifications can be adjusted for other populations, if applicable\. The Rules, reviewed and approved by NCQA measure experts, provide for expanded use of HEDIS measures without changing their clinical intent\. 

__Adjusted HEDIS measures may not be used for HEDIS health plan reporting\. __

### <a id="_Hlk1050695"></a>Rules for Allowable Adjustments of Pharmacotherapy Management of COPD Exacerbation

__NONCLINICAL COMPONENTS__

__Eligible Population__

__Adjustments Allowed \(Yes/No\)__

__Notes__

Product lines

Yes

Using product line criteria is not required\. Including any product line, combining product lines, or not including product line criteria is allowed\.

Ages

Yes, with limits

The age determination dates may be changed \(e\.g\., select “age as of June 30”\)\. 

The denominator age may be changed if the range is within the specified age range \(40 years and older\)\. 

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

Yes, with limits

Only events or diagnoses that contain \(or map to\) codes in the value sets may be used to identify visits\. Value sets and logic may not be changed\.

__*Note:*__* Organizations may assess at the member level \(vs\. event level\) by applying measure logic appropriately \(i\.e\., percentage of members with COPD exacerbations\)\.*

__Denominator Exclusions__

__Adjustments Allowed \(Yes/No\)__

__Notes__

Required exclusions

Yes

The hospice and deceased member exclusions are not required\. Refer to *Exclusions* in the *Guidelines for the Rules for Allowable Adjustments*\.

__Numerator Criteria__

__Adjustments Allowed \(Yes/No\)__

__Notes__

- Systemic Corticosteroid
- Bronchodilator

No

Medication lists, value sets and logic may not be changed\.

