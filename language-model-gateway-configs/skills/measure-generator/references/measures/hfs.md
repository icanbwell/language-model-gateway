## <a id="Hospitalization_Following_Discharge_HFS"></a><a id="_Hlk5735086"></a><a id="_Toc74828973"></a><a id="_Toc171403049"></a><a id="IHU"></a>Hospitalization Following Discharge From   
a Skilled Nursing Facility \(HFS\)

Summary of Changes to HEDIS* *MY 2025

- No changes to this measure\.

Description 

For members 65 years of age and older, the percentage of skilled nursing facility discharges to the community that were followed by an unplanned acute hospitalization for any diagnosis within 30 days and within 60 days\. 

Definitions

SND

Skilled nursing facility discharge\. A skilled nursing facility discharge on or between January 1 and November 1 of the measurement year\. 

Planned hospital stay

A hospital stay is considered planned if it meets criteria as described in step 3 \(required exclusions\) of the numerator\.

Classification period

365 days prior to and including an SND\. 

Eligible Population

Product line

Medicare\.

Ages

65 years and older as of the SND\.

Continuous enrollment

365 days prior to the SND date through 60 days after the SND date\. 

Allowable gap

No more than one gap in enrollment of up to 45 days during the 365 days prior to the SND date and no gap during the 60 days following the SND date\.

Anchor date

SND date\.

Benefit

Medical\.

Event/diagnosis

An SND to the community on or between January 1 and November 1 of the measurement year\.

The denominator for this measure is based on discharges, not on members\. Include all SNDs for members who had one or more discharges on or between January 1 and November 1 of the measurement year\.

Follow the steps below to identify SNDs\.

Required exclusions

Exclude members who meet any of the following criteria:

- Members who use hospice services \(Hospice Encounter Value Set; Hospice Intervention Value Set\) or elect to use a hospice benefit any time during the measurement year\. Organizations that use the Monthly Membership Detail Data File to identify these members must use only the run date of the file to determine if the member elected to use a hospice benefit during the measurement year\.
- Members living long\-term in an institution any time during the measurement year as identified by the LTI flag in the Monthly Member Detail Data File\. Use the run date of the file to determine if the member had an LTI flag during the measurement year\.

Administrative Specification

Denominator

The eligible population\.

*Step 1*

Identify all SNDs on or between January 1 and November 1 of the measurement year\. To identify SNDs: 

1\.	Identify all skilled nursing facility stays \(Skilled Nursing Stay Value Set\)\.

2\.	Identify the discharge date for the skilled nursing facility stay\.

*Step 2 *

__*Skilled nursing\-to\-skilled nursing direct transfers:* __For skilled nursing facility stays with one more direct transfers, use the last discharge\. 

*Step 3 *

Exclude SNDs where the skilled nursing facility admission date is the same as the SND date\. 

*Step 4*

Exclude SNDs due to an acute hospital transfer\. To identify acute hospital transfers from skilled nursing facilities: 

1\.	Identify all acute and nonacute inpatient stays \(Inpatient Stay Value Set\) and observation stays \(Observation Stay Value Set\)\.

2\.	Exclude nonacute inpatient stays \(Nonacute Inpatient Stay Value Set\)\.

3\.	Identify the admission date for the hospitalization\.

4\.	Exclude SNDs with an acute hospital admission date within 1 calendar day or less after the SND date\. For example:

- An SND on June 1, followed by a hospitalization on June 1,  
*is excluded\. *
- An SND on June 1, followed by a hospitalization on June 2,*   
is excluded\.*
- An SND on June 1, followed by a hospitalization on June 3,   
*is included\.*

*Step 5*

Calculate continuous enrollment\.

*Step 6*

Assign each SND to an age stratification using the *Reporting: Denominator *section\. Refer to Tables HFS\-A\-3 and HFS\-B\-3\. 

<a id="_Toc169866788"></a>Risk Adjustment Determination

For each SND, use the following steps to identify risk adjustment categories based on discharge condition, comorbidity, age and gender\.

Discharge condition

Assign a Clinical Condition \(CC\) category code or codes to the SND based on its principal discharge diagnosis, using Table CC\-Mapping\. For direct transfers, use the principal discharge diagnosis from the last discharge\. 

Exclude diagnoses that cannot be mapped to Table CC\-Mapping\.

COVID\-19 discharge

Assign a COVID\-19 discharge code to the SND if its principal discharge diagnosis was COVID\-19 \(ICD\-10\-CM code U07\.1\)\. For direct transfers, use the principal discharge diagnosis from the last discharge\.

Comorbidities

Refer to the *Risk Adjustment Comorbidity Category Determination *in the *Guidelines for Risk Adjusted Utilization Measures\.*

<a id="_Toc169866789"></a>Risk Adjustment Weighting

For each SND, use the following steps to identify the 30\-day and 60\-day hospitalization risk adjustment weights based on discharge condition, comorbidity, age and gender\. Weights are specific to reporting rate \(30\-day and 60\-day\)\. Refer to the reporting indicator column in the risk adjustment tables to ensure that weights are linked appropriately\.

*Step 1*

For each SND with a Discharge CC Category, link the 30\-day and 60\-day primary discharge weights\. 

*Step 2*

For each SND with a Comorbidity HCC Category, link the 30\-day and 60\-day weights\. 

*Step 3*

For each SND with a COVID\-19 discharge, link the 30\-day and 60\-day weights\. 

*Step 4*

Link the 30\-day and 60\-day age and gender weights for each SND\.

*Step 5*

Sum all weights \(discharge CC, comorbidities, age and gender\) associated with each SND for each category \(30\-day hospitalization, 60\-day hospitalization\)\. 

*Step 6*

Use the formula below to calculate the Estimated Hospitalization Risk for each SND, for each category \(30\-day hospitalization, 60\-day hospitalization\)\. 

Estimated Hospitalization Risk =

__*OR*__

Estimated Hospitalization Risk = \[exp \(sum of weights for SND\)\] / \[ 1 \+ exp \(sum of weights for SNDs\)\]

__Note: __“Exp” refers to the exponential or antilog function\.

Truncate the estimated hospitalization risk *for each SND* to 10 decimal places\. Do not truncate or round in previous steps\.

*Step 7*

Calculate the Count of Expected Hospitalizations for each age, for each category \(30\-day hospitalization and 60\-day hospitalization\)\. The Count of Expected Hospitalizations is the sum of the Estimated Hospitalizations Risk calculated in step 6 for each SND for each age, for each category \(30\-day hospitalization and 60\-day hospitalization\)\. 

*Step 8*

Use the formula below and the Estimated Hospitalization Risk calculated in   
step 6 to calculate the variance for each SND, for each category \(30\-day hospitalization and 60\-day hospitalization\)\.

Variance = Estimated Hospitalization Risk x \(1 – Estimated Hospitalization Risk\)

Truncate the variance *for each SND* to 10 decimal places\.

*For example:* If the Estimated 30\-Day Hospitalization Risk is 0\.1518450741 for an SND, then the 30\-day hospitalization variance for this SND is 0\.1518450741 x 0\.8481549259 = 0\.1287881475\.

__Note: __Organizations must sum the variances for each age when populating the variance cells in the reporting tables\. When reporting, round the variance to 4 decimal places using the \.5 rule\. 

Numerator

At least one acute inpatient admission or observation stay for any diagnosis within 30 days and within 60 days of the SND date\.

*Step 1*

For each SND, identify all acute inpatient admissions and observation stay hospitalizations with an admission date within 30 days and within 60 days after the SND date\. To identify acute hospitalizations: 

1\.	Identify all acute and nonacute inpatient stays \(Inpatient Stay Value Set\) and observation stays \(Observation Stay Value Set\)\.

2\.	Exclude nonacute inpatient stays \(Nonacute Inpatient Stay Value Set\)\.

3\.	Identify the admission date for the hospitalization\.

*Step 2*

*Direct transfers:* For hospitalizations with one or more direct transfers, use the last discharge\. 

Using the acute inpatient admissions or observation stays identified in step 1, identify direct transfers between acute inpatient and observation or between observation and acute inpatient using the definition found in the *Guidelines for Risk Adjusted Utilization Measures\. *

*Step 3*

Exclude acute hospitalizations with any of the following on the discharge claim: 

- Members with a principal diagnosis of pregnancy \(Pregnancy Value Set\)\.
- A principal diagnosis for a condition originating in the perinatal period \(Perinatal Conditions Value Set\)\. 
- A planned hospital stay using any of the following:
- A principal diagnosis of maintenance chemotherapy \(Chemotherapy Encounter Value Set\)\. 
- A principal diagnosis of rehabilitation \(Rehabilitation Value Set\)\. 
- An organ transplant \(Kidney Transplant Value Set, Bone Marrow Transplant Value Set, Organ Transplant Other Than Kidney Value Set, Introduction of Autologous Pancreatic Cells Value Set\)\.
- A potentially planned procedure \(Potentially Planned Procedures Value Set, Potentially Planned Post Acute Care Hospitalization Value Set\) without a principal acute diagnosis \(Acute Condition Value Set\)\.

__Note: __

- For hospital stays where there was a direct transfer \(identified in step 2\), use the original stay and any direct transfer stays to identify exclusions in this step\.
- Count each unique acute inpatient admission or observation stay hospitalization only once toward the numerator for the last denominator event\. If a single numerator event meets criteria for multiple denominator events, only count the last denominator event\. For example, consider the following events:
- *SNF stay 1: May 1–10\.*
- *SNF stay 2: May 15–25\.*
- *Acute inpatient stay: May 30–June 5\.*

*The SNDs of May 10 and May 25 are included as denominator events\. The acute inpatient stay counts as a numerator event only toward the last denominator event \(stay 2, May 15–25\)\.*

- Only one inpatient admission or observation stay hospitalization may be included in the numerator for each unique skilled nursing facility stay discharge\. If there are multiple numerator events that meet criteria for a singular denominator event, only count the numerator event closest to the SND\. For example, consider the following events: 
- *SNF stay: May 1–10\.*
- *Observation stay: May 15–25\.*
- *Acute inpatient stay: May 30–June 5\.*

Both the observation stay of May 15–25 and the acute inpatient stay of May 30–June 5 are within 30 days of the SNF discharge on May 10\. Only the observation stay is included in the numerator, because it is the hospitalization event closest to the SND\.

- *The specifications in the second and third bullets may be applied simultaneously\. For example, consider the following events: *
- *SNF stay 1: May 1–10\.*
- *SNF stay 2: May 15–25\.*
- *Acute inpatient stay 1: May 30–June 1\.*
- *Acute inpatient stay 2: June 5–June 8\.*

*The SND of May 10 and May 25 are included as denominator events\. Acute inpatient stay 1 of May 30–June 1 counts as a numerator event only toward the last denominator event \(SNF stay 2, May 15–25\)\. *

- Acute inpatient stay 2 of June 5–8 does not count toward the numerator, because the last denominator event \(SNF stay 2, May 15–25\) applies only toward the closest numerator event \(acute inpatient stay 1, May 30–June 1\)\.

*Reporting:* Denominator 

The number of SNDs for each age group, for each category \(30\-day hospitalization, 60\-day hospitalization\), reported as the Denominator\.

*Reporting:* Numerator 

The number of observed acute inpatient admission or observation stay hospitalizations for each age group, for each category \(30\-day hospitalization, 60\-day hospitalization\), reported as the ObservedCount\.

*Calculated:* Observed Hospitalization Rate

The number of observed acute inpatient admission or observation stay hospitalizations \(ObservedCount\) divided by the number of SNDs to the community \(Denominator\) for each age group and total, for each category \(30\-day hospitalization, 60\-day hospitalization\)\. Calculated by IDSS as the ObservedRate\.

*Reporting:* Count of Expected Hospitalizations

*Step 1*

Calculate the number of expected inpatient admission or observation stay hospitalizations for each age group, for each category \(30\-day hospitalization, 60\-day hospitalization\)\.

*Step 2*

Round to 4 decimal places using the \.5 rule and report these values as the ExpectedCount\.

*Calculated:* Expected Hospitalization Rate

The number of expected acute inpatient admission or observation stay hospitalizations \(ExpectedCount\) divided by the number of SNDs to the community \(Denominator\) for each age group and total, for each category \(30\-day hospitalization, 60\-day hospitalization\)\. Calculated by IDSS as the ExpectedRate\.

*Reporting: *Variance

*Step 1*

Calculate the variance \(from Risk Adjustment Weighting, step 8\) for each group, for each category \(30\-day hospitalization, 60\-day hospitalization\)\.

*Step 2*

Round to 4 decimal places using the \.5 rule and report these values as the CountVariance\.

*Calculated:* O/E Ratio

The number of observed acute inpatient admission or observation stay hospitalizations \(ObservedCount\) divided by the number of expected acute inpatient admissions or observation stay hospitalizations \(ExpectedCount\) for each age group and total, for each category \(30\-day hospitalization, 60\-day hospitalization\)\. Calculated by IDSS as the OE\.

*Note*

- *Supplemental data may not be used for this measure, except for required exclusions\.*

__*Table HFS\-3: Data Elements for Hospitalization Following Discharge From a Skilled Nursing Facility*__

Metric

Age

Data Element 

HospitalizationWithin30Days

65\-74

Denominator

For each Stratification, repeat per Metric

HospitalizationWithin60Days

75\-84

ObservedCount

For each Metric and Stratification

85\+

ObservedRate

ObservedCount / Denominator \(Percent\)

Total

ExpectedCount

For each Metric and Stratification

ExpectedRate

ExpectedCount / Denominator \(Percent\)

CountVariance

For each Metric and Stratification

OE

ObservedCount / ExpectedCount

Rules for Allowable Adjustments of HEDIS

The “Rules for Allowable Adjustments of HEDIS” \(the “Rules”\) describe how NCQA’s HEDIS measure specifications can be adjusted for other populations, if applicable\. The Rules, reviewed and approved by NCQA measure experts, provide for expanded use of HEDIS measures without changing their clinical intent\. 

__Adjusted HEDIS measures may not be used for HEDIS health plan reporting\.__ 

<a id="_Hlk67033708"></a>The following table is for the Rules for Allowable Adjustments for __Risk\-Adjusted Measurement__ of the Hospitalization Following Discharge From a Skilled Nursing Facility measure \(Count of Skilled Nursing Facility Discharges, Count of Observed Hospitalizations, Risk Adjustment Determination, Count of Expected Hospitalizations Risk Adjustment Weighting, Observed to Expected Ratio, Variance\)\.

<a id="_Rules_for_Allowable_3"></a>

__NONCLINICAL COMPONENTS__

Eligible Population

Adjustments Allowed \(Yes/No\)

Notes

Product lines

No

Organizations may not adjust product lines\. 

Ages

No

The age determination dates may not be changed\.

__*Note:*__* The denominator age may not be expanded\. The ages for the risk weights may not be changed\.*

Continuous enrollment, allowable gap, anchor date

No

For risk adjusted rates organizations are required to use enrollment criteria; adjustments are not allowed\.

Benefits

Yes

Organizations are not required to use a benefit; adjustments are allowed\.

Other

Yes, with limits

Organizations may only adjust the eligible population criteria to focus on an area of interest defined by gender, sociodemographic characteristics or geographical region\.

__*Note:*__* NCQA recommends evaluating risk model performance and validity within adjusted populations\.* 

Organizations may not adjust for a clinical subpopulation \(e\.g\., members with a diabetes diagnosis\)\.

__CLINICAL COMPONENTS__

Eligible Population

Adjustments Allowed \(Yes/No\)

Notes

Event/diagnosis

Yes, with limits

Only events or diagnoses that contain \(or map to\) codes in value sets may be used to identify visits\. The value sets and logic may not be changed\.

__*Note:*__* Organizations may include denied claims to calculate the denominator\. *

Outlier

NA

There are no outliers for this measure\.

Exclusions

Adjustments Allowed \(Yes/No\)

Notes

Required exclusions

Yes, with limits

The hospice exclusion is required\. The value sets and logic may not be changed\.

The LTI exclusion is not required\. 

Risk Adjustment and Calculation of Expected Events

Adjust Adjustments Allowed \(Yes/No\)

Notes

- Risk Adjustment Determination
- Risk Adjustment Weighting
- Expected Hospitalizations
- Variance

Yes, with limits

Risk adjustment determinations, weighting and calculations of expected events logic may not be changed\. 

__*Note:*__* Organizations may include denied claims to calculate these events\. *

Numerator Criteria

Adjustments Allowed \(Yes/No\)

Notes

- Unplanned Acute Hospitalization 30 Days
- Unplanned Acute Hospitalization 60 Days

Yes, with limits

Value sets and logic may not be changed\. 

__*Note: *__*Organizations may include denied claims to calculate the numerator\.* 

Rules for Allowable Adjustments of HEDIS

The “Rules for Allowable Adjustments of HEDIS” \(the “Rules”\) describe how NCQA’s HEDIS measure specifications can be adjusted for other populations, if applicable\. The Rules, reviewed and approved by NCQA measure experts, provide for expanded use of HEDIS measures without changing their clinical intent\.

__Adjusted HEDIS measures may not be used for HEDIS health plan reporting\. __

The following table is for the Rules for Allowable Adjustments for __Observed Measurement__ of the Hospitalization Following Discharge From a Skilled Nursing Facility Observed Events measure \(Count of Skilled Nursing Facility Discharges, Count of Observed Hospitalizations\)\.

<a id="_Rules_for_Allowable_4"></a>__NONCLINICAL COMPONENTS__

__Eligible Population__

Adjustments Allowed \(Yes/No\)

Notes

Product lines

Yes

When adjusting this measure to assess for observed events only, organizations are not required to use product line criteria; product lines may be combined and all \(or no\) product line criteria may be used\.

Ages

Yes, with limits

The age determination dates may be changed \(e\.g\., select, “age 70 months as of June 30”\)\.

__*Note:*__* The denominator age may not be expanded\.*

Continuous enrollment, allowable gap, anchor date

Yes

Organizations are not required to use enrollment criteria; adjustments are allowed\.

Benefits

Yes

Organizations are not required to use a benefit; adjustments are allowed\.

Other

Yes

Organizations may adjust the eligible population criteria to focus on an area of interest defined by gender, race, ethnicity, socioeconomic or sociodemographic characteristics, geographic region or another characteristic\.

__CLINICAL COMPONENTS__

Eligible Population

Adjustments Allowed \(Yes/No\)

Notes

Event/diagnosis

Yes, with limits

Only events or diagnoses that contain \(or map to\) codes in value sets may be used to identify visits\. The value sets and logic may not be changed\.

__*Note:*__* Organizations may include denied claims to calculate the denominator\. *

Outlier

NA

There are no outliers for this measure\. 

Exclusions

Adjustments Allowed \(Yes/No\)

Notes

Required exclusions

Yes

The hospice and LTI exclusions are not required\. Refer to *Exclusions* in the *Guidelines for the Rules for Allowable Adjustments*\.

Numerator Criteria

Adjustments Allowed \(Yes/No\)

Notes

- Unplanned Acute Hospitalization 30 Days
- Unplanned Acute Hospitalization 60 Days

Yes, with limits

Value sets and logic may not be changed\. 

__*Note:*__* Organizations may include denied claims to calculate the numerator\. *

