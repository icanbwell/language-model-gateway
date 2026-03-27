## <a id="_Toc74828972"></a><a id="PCR"></a>

## <a id="Plan_AllCause_Readmission_PCR"></a><a id="_Toc171403048"></a>Plan All\-Cause Readmissions \(PCR\)

Summary of Changes to HEDIS MY 2025

- Expanded the age and outlier criteria in the Observed Measurement in the *Rules for Allowable Adjustments*\.

Description 

For members 18 years of age and older, the number of acute inpatient and observation stays during the measurement year that were followed by an unplanned acute readmission for any diagnosis within 30 days and the predicted probability of an acute readmission\. <a id="_Hlk505332169"></a>

__Note:__ For commercial and Medicaid, report only members 18–64 years of age\.

Definitions

IHS

Index hospital stay\. An acute inpatient or observation stay with a discharge on or between January 1 and December 1 of the measurement year, as identified in the denominator\. 

Index Admission Date

The IHS admission date\. 

Index Discharge Date

The IHS discharge date\. The Index Discharge Date must occur on or between January 1 and December 1 of the measurement year\.

Index Readmission Stay

An acute inpatient or observation stay for any diagnosis with an admission date within 30 days of a previous Index Discharge Date\. 

Index Readmission Date

The admission date associated with the Index Readmission Stay\. 

Planned hospital stay

A hospital stay is considered planned if it meets criteria as described in step 3 \(required exclusions\) of the numerator\.

Plan population

Members in the eligible population prior to exclusion of outliers \(denominator steps 1–5\)\. The plan population is only used as a denominator for the Outlier Rate\.

Members must be 18 and older as of the earliest Index Discharge Date\.

The plan population is based on members, not discharges\. Count members only once in the plan population\.

Assign members to the product/product line in which they are enrolled at the start of the continuous enrollment period of their earliest IHS\. If the member has a gap at the beginning of this continuous enrollment period, assign the member to the product/product line in which they were enrolled as of their first enrollment segment during this continuous enrollment period\.

Outlier

Medicaid and Medicare members in the eligible population with four or more IHS between January 1 and December 1 of the measurement year\.

Commercial members in the eligible population with three or more IHS between January 1 and December 1 of the measurement year\. 

Assign members to the product/product line in which they are enrolled at the start of the continuous enrollment period of their earliest IHS\. If the member has a gap at the beginning of this continuous enrollment period, assign the member to the product/product line in which they were enrolled as of their first enrollment segment during the continuous enrollment period\.

Nonoutlier

Members in the eligible population who are not considered outliers\.

Classification period

365 days prior to and including Index Discharge Date\. 

Eligible Population

Product line

Commercial, Medicare, Medicaid \(report each product line separately\)\.

__Note: __Per General Guideline Members With Dual Enrollment, members with dual commercial and Medicaid enrollment may only be reported in the commercial product line\. Members with dual Medicaid/Medicare enrollment “dual eligible” and with Medicare\-Medicaid \(MMP\) enrollment may only be reported in the Medicare product line\. 

Stratification

For only Medicare IHS, report the following SES stratifications and total: 

- Non\-LIS/DE, Nondisability\.
- LIS/DE\.
- Disability\.
- LIS/DE and Disability\. 
- Other\.
- Unknown\.
- Total Medicare\.

__Note: __Stratifications are mutually exclusive, and the sum of all six stratifications is the Total population\.

Ages

*For commercial,* 18–64 years as of the Index Discharge Date\.

*For Medicare,* 18 years and older as of the Index Discharge Date\.

*For Medicaid, *18–64 years as of the Index Discharge Date*\.*

Continuous enrollment

365 days prior to the Index Discharge Date through 30 days after the Index Discharge Date\. 

Allowable gap

No more than one gap in enrollment of up to 45 days during the 365 days prior to the Index Discharge Date and no gap during the 30 days following the Index Discharge Date\.

Anchor date

Index Discharge Date\.

Benefit

Medical\.

Event/diagnosis

An acute inpatient or observation stay discharge on or between January 1 and December 1 of the measurement year\.

The denominator for this measure is based on discharges, not members\. Include all acute inpatient or observation stay discharges for nonoutlier members who had one or more discharges on or between January 1 and December 1 of the measurement year\.

Follow the steps below to identify acute inpatient and observation stays\.

Required exclusion

Members who use hospice services \(Hospice Encounter Value Set; Hospice Intervention Value Set\) or elect to use a hospice benefit any time during the measurement year\. Organizations that use the Monthly Membership Detail Data File to identify these members must use only the run date of the file to determine if the member elected to use a hospice benefit during the measurement year\.* *

Administrative Specification

Denominator

The eligible population\.

*Step 1*

Identify all acute inpatient and observation stay discharges on or between January 1 and December 1 of the measurement year\. To identify acute inpatient and observation stay discharges:

1. Identify all acute and nonacute inpatient stays \(Inpatient Stay Value Set\) and observation stays \(Observation Stay Value Set\)\.
2. Exclude nonacute inpatient stays \(Nonacute Inpatient Stay Value Set\)\.
3. Identify the discharge date for the stay\.

Inpatient and observation stays where the discharge date from the first setting and the admission date to the second setting are 2 or more calendar days apart must be considered distinct stays\. 

The measure includes acute discharges from any type of facility \(including behavioral healthcare facilities\)\. 

*Step 2*

*Direct transfers:* For discharges with one or more direct transfers, use the last discharge\. 

Using the discharges identified in step 1, identify direct transfers between acute inpatient and observation or between observation and acute inpatient using the definition found in the *Guidelines for Risk Adjusted Utilization Measures\.* 

Exclude the hospital stay if the direct transfer’s discharge date occurs after December 1 of the measurement year\.

*Step 3 *

Exclude hospital stays where the Index Admission Date is the same as the Index Discharge Date\. 

* Step 4*

Exclude hospital stays for the following reasons:

- The member died during the stay\.
- Members with a principal diagnosis of pregnancy \(Pregnancy Value Set\) on the discharge claim\. 
- A principal diagnosis of a condition originating in the perinatal period \(Perinatal Conditions Value Set\) on the discharge claim\.

__Note: __For hospital stays where there was a direct transfer \(identified in step 2\), use the original stay and any direct transfer stays to identify exclusions in this step\.

*Step 5*

Calculate continuous enrollment\.

*Step 6*

Remove hospital stays for outlier members and report these members as outliers in Tables PCR\-A\-1/2 and PCR\-A\-3\. 

__Note:__ Count discharges with one or more direct transfers \(identified in step 2\) as one discharge when identifying outlier members\. 

*Step 7*

Assign each remaining acute inpatient or observation stay to an age and stratification category using the reporting instructions below\. 

Risk Adjustment Determination

For each IHS among nonoutlier members, use the following steps to identify risk adjustment categories based on presence of observation stay status at discharge, surgeries, discharge condition, comorbidity, age and gender\.

Observation stay 

Determine if the IHS at discharge was an observation stay \(Observation Stay Value Set\)\. For direct transfers, determine the hospitalization status using the last discharge\.

Surgeries

Determine if the member underwent surgery during the stay \(Surgery Procedure Value Set\)\. Consider an IHS to include a surgery if at least one procedure code is present from any provider between the admission and discharge dates\.

Discharge condition

Assign a discharge Clinical Condition \(CC\) category code or codes to the IHS based on its principal discharge diagnosis, using Table CC\-Mapping\. For direct transfers, use the principal discharge diagnosis from the last discharge\.

Exclude diagnoses that cannot be mapped to Table CC\-Mapping\.

COVID\-19 discharge

Assign a COVID\-19 discharge code to the IHS if its principal discharge diagnosis was COVID\-19 \(ICD\-10\-CM code U07\.1\)\. For direct transfers, use the principal discharge diagnosis from the last discharge\.

Comorbidities

Refer to the *Risk Adjustment Comorbidity Category Determination *in the *Guidelines for Risk Adjusted Utilization Measures\.*

<a id="RiskAdjustmentWeighting"></a>Risk Adjustment Weighting

For each IHS among nonoutliers, use the following steps to identify risk adjustment weights based on observation stays status at discharge, surgeries, discharge condition, comorbidity, age and gender\. Weights are specific to product line \(Medicare Under 65, Medicare 65\+, commercial, Medicaid\)\. Refer to the reporting indicator column in the risk adjustment tables to ensure that weights are linked appropriately\. 

__Note:__ For Medicare product lines, IHS that are discharged or transferred to skilled nursing care should be assigned two sets of risk adjustment weights; the skilled nursing care risk weights for reporting in Table   
PCR\-C\-3 and the standard set of risk weights for reporting in Table PCR\-A\-3 and Table PCR\-B\-3\. For reporting IHS that are discharged or transferred to skilled nursing care, do not assign the skilled nursing care risk weights for the stays when reporting in Table PCR\-A\-3 and Table PCR\-B\-3 and do not assign the standard set or risk weights for the stays when reporting in Table PCR\-C\-3\.

*Step 1*

For each IHS discharge that is an observation stay, link the observation stay IHS weight\.

*Step 2*

For each IHS with a surgery, link the surgery weight\. 

*Step 3*

For each IHS with a discharge CC category, link the primary discharge weights\. 

*Step 4*

For each IHS with a comorbidity HCC category, link the comorbidity weights\. 

*Step 5*

For each IHS with a COVID\-19 discharge, link the COVID\-19 discharge weight\.

*Step 6*

Link the age and gender weights for each IHS\.

*Step 7*

Sum all weights associated with the IHS \(i\.e\., observation stay, presence of surgery, principal discharge diagnosis, comorbidities, age and gender\) and use the formula below to calculate the Estimated Readmission Risk for each IHS:

Estimated Readmission Risk = 

__*OR*__

Estimated Readmission Risk = \[exp \(sum of weights for IHS\)\] / \[ 1 \+ exp \(sum of weights for IHS\)\]

__Note: __“Exp” refers to the exponential or antilog function\.

Truncate the estimated readmission risk for each IHS to 10 decimal places\. Do not truncate or round in previous steps\.

*Step 8*

Calculate the Count of Expected Readmissions for each age and stratification category\. The Count of Expected Readmissions is the sum of the Estimated Readmission Risk calculated in step 7 for each IHS in each age and stratification category\. 

*Step 9*

Use the formula below and the Estimated Readmission Risk calculated in step 7 to calculate the variance for each IHS\.

Variance = Estimated Readmission Risk x \(1 – Estimated Readmission Risk\)

Truncate the variance *for each IHS* to 10 decimal places\.

*For example:* If the Estimated Readmission Risk is 0\.1518450741 for an IHS, then the variance for this IHS is 0\.1518450741 x 0\.8481549259 = 0\.1287881475\.

__Note: __Organizations must sum the variances for each stratification and age when populating the Variance cells in the reporting tables\. When reporting, round the variance to 4 decimal places using the \.5 rule\. 

Numerator

At least one acute readmission for any diagnosis within 30 days of the Index Discharge Date\.

*Step 1*

Identify all acute inpatient and observation stays with an admission date on or between January 3 and December 31 of the measurement year\. To identify acute inpatient and observation admissions:

1. Identify all acute and nonacute inpatient stays \(Inpatient Stay Value Set\) and observation stays \(Observation Stay Value Set\)\.
2. Exclude nonacute inpatient stays \(Nonacute Inpatient Stay Value Set\)\.
3. Identify the admission date for the stay\.

*Step 2*

*Direct transfers:* For discharges with one or more direct transfers, use the last discharge\. 

Using the discharges identified in step 1, identify direct transfers between acute inpatient and observation or between observation and acute inpatient using the definition found in the *Guidelines for Risk Adjusted Utilization Measures\.* 

*Step 3*

Exclude acute hospitalizations with any of the following criteria on the discharge claim: 

- Members with a principal diagnosis of pregnancy \(Pregnancy Value Set\)\. 
- A principal diagnosis for a condition originating in the perinatal period \(Perinatal Conditions Value Set\)\. 
- A planned hospital stay using any of the following:
- A principal diagnosis of maintenance chemotherapy \(Chemotherapy Encounter Value Set\)\. 
- A principal diagnosis of rehabilitation \(Rehabilitation Value Set\)\. 
- An organ transplant \(Kidney Transplant Value Set, Bone Marrow Transplant Value Set, Organ Transplant Other Than Kidney Value Set, Introduction of Autologous Pancreatic Cells Value Set\)\.
- A potentially planned procedure \(Potentially Planned Procedures Value Set\) without a principal acute diagnosis \(Acute Condition Value Set\)\.

__Note: __For hospital stays where there was a direct transfer \(identified in step 2\), use the original stay and any direct transfer stays to identify exclusions in this step\.

*Step 4*

For each IHS identified in the denominator, determine if any of the acute inpatient and observation stays identified in the numerator have an admission date within 30 days after the Index Discharge Date\.

__Note: __Count each acute hospitalization only once toward the numerator for the last denominator event\. 

If a single numerator event meets criteria for multiple denominator events, only count the last denominator event\. For example, consider the following events:

- *Acute inpatient stay 1: May 1–10\.*
- *Acute inpatient stay 2: May 15–25 \(principal diagnosis of maintenance chemotherapy\)\.*
- *Acute inpatient stay 3: May 30–June 5\.*

All three acute inpatient stays are included as denominator events\. Stay 2 is excluded from the numerator because it is a planned hospitalization\. Stay 3 is within 30 days of Stay 1 and Stay 2\. Count Stay 3 as a numerator event only toward the last denominator event \(Stay 2, May 15–25\)\. 

*Reporting:* Number of Members in Plan Population

*Step 1*

Determine the member’s age as of the earliest Index Discharge Date\. 

*Step 2*

Report the count of members in the plan population for each age group as the MemberCount\.

*Reporting:* Number of Outliers

*Step 1*

Determine the member’s age as of the earliest Index Discharge Date\. 

*Step 2*

Report the count of outlier members for each age group as the OutlierMemberCount\.

*Calculated:* Outlier Rate

The number of outlier members \(OutlierMemberCount\) divided by the number of members in the plan population \(MemberCount\), displayed as a permillage \(multiplied by 1,000\), for each age group and totals\. Calculated by IDSS as the OutlierRate\.

*Reporting:* Denominator

Count the number of IHS among nonoutlier members for each age group\. Report these values as the Denominator\.

<a id="_Toc169866786"></a>*Reporting*: SES Stratification \(Medicare only\)

*Step 1*

Determine the member’s SES stratifications as of the end of the continuous enrollment period for each Medicare discharge:

- *Non\-LIS/DE, Nondisability: *Member is eligible for Medicare due to age only \(does not receive LIS, is not DE for Medicaid, does not have disability status\)\.
- *LIS/DE: *Member is eligible for Medicare due to age and receives LIS \(includes members eligible for Medicare due to DE\), does not have disability status\.
- *Disability*: Member is eligible for Medicare due to disability status only\. 
- *LIS/DE and Disability:* Member is eligible for Medicare, receives LIS and has disability status\.
- *Other: *Member has ESRD\-only status or is assigned “9—none of the above\.”
- *Unknown: *Member’s SES is unknown\. 
- *Total Medicare: *Total of all categories\.

*Step 2*

Report Medicare discharges based on the SES stratification assigned for each Medicare index stay in Table PCR\-B\-3\. 

__*Reporting*: Skilled Nursing Care Stratification \(Medicare 65\+ only\)__

*Step 1*

For Medicare nonoutlier members 65 years of age and older, determine if the IHS was discharged or transferred to skilled nursing care \(Skilled Nursing Stay Value Set\)\. 

An index stay is discharged or transferred to skilled nursing care when the discharge date from the acute inpatient or observation stay precedes the admission date for skilled nursing care by one calendar day or less\. For example:

- An index stay discharge on June 1, followed by an admission to a skilled nursing setting on June 1, *is an IHS discharged or transferred to skilled nursing care\. *
- An index stay discharge on June 1, followed by an admission to a skilled nursing setting on June 2, *is an IHS discharged or transferred to skilled nursing care\.* 
- An index stay discharge on June 1, followed by an admission to a skilled nursing setting on June 3,* is not an IHS discharged or transferred to skilled nursing care*\. 

*Step 2*

Report Medicare discharges for each IHS discharged or transferred to skilled nursing care to an age group in Table PCR\-C\-3\.

*Reporting:* Numerator

Count the number of observed IHS among nonoutlier members with a readmission within 30 days of discharge for each age group and report these values as the ObservedCount\.

*Calculated:* Observed Readmission Rate

The Count of Observed 30\-Day Readmissions \(ObservedCount\) divided by the Count of Index Stays \(Denominator\) for each age group and totals\. Calculated by IDSS as the ObservedRate\.

*Reporting:* Count of Expected 30\-Day Readmissions

*Step 1*

Calculate the Count of Expected Readmissions among nonoutlier members for each age group\. 

*Step 2*

Round to 4 decimal places using the \.5 rule and report these values as the ExpectedCount\.

*Calculated:* Expected Readmission Rate

The Count of Expected 30\-Day Readmissions \(ExpectedCount\) divided by the Count of Index Stays \(Denominator\) for each age group and totals\. Calculated by IDSS as the ExpectedRate\.

*Reporting: *Variance

*Step 1*

Calculate the total \(sum\) variance for each SES stratification \(Medicare only\), skilled nursing stratification \(Medicare only\) and age group\. 

*Step 2*

Round to 4 decimal places using the \.5 rule and report these values as the CountVariance\.

*Calculated:* O/E Ratio

The Count of Observed 30\-Day Readmissions \(ObservedCount\) divided by the Count of Expected   
30\-Day Readmissions \(ExpectedCount\) for each age group and totals\. Calculated by IDSS as the OE\. The O/E Ratio is not calculated for SES stratifications\.

*Note*

- *Supplemental data may not be used for this measure, except for required exclusions\.*

__*Table PCR\-A\-1/2: Data Element for Plan All\-Cause Readmissions *__

Metric

Age

Data Element 

Reporting Instructions

PlanAllCauseReadmissions

18\-44

MemberCount

For each Stratification

45\-54

OutlierMemberCount

For each Stratification

55\-64

OutlierRate

OutlierMemberCount / MemberCount \(Permille\)

18\-64

Denominator

For each Stratification

ObservedCount

For each Stratification

ObservedRate

ObservedCount / Denominator \(Percent\)

ExpectedCount

For each Stratification

ExpectedRate

ExpectedCount / Denominator \(Percent\)

CountVariance

For each Stratification

OE

ObservedCount / ExpectedCount

__*Table PCR\-A\-3: Data Elements for Plan All\-Cause Readmissions *__

Metric

Age

Data Element 

Reporting Instructions

PlanAllCauseReadmissions

18\-44

MemberCount

For each Stratification

45\-54

OutlierMemberCount

For each Stratification

55\-64

OutlierRate

OutlierMemberCount / MemberCount \(Permille\)

18\-64

Denominator

For each Stratification

65\-74

ObservedCount

For each Stratification

75\-84

ObservedRate

ObservedCount / Denominator \(Percent\)

85\+

ExpectedCount

For each Stratification

65\+

ExpectedRate

ExpectedCount / Denominator \(Percent\)

CountVariance

For each Stratification

OE

ObservedCount / ExpectedCount

### Table PCR\-B\-3:	Data Elements for Plan All\-Cause Readmissions by SES Stratification

Metric

SES Stratification

Age

Data Element 

Reporting Instructions

PlanAllCauseReadmissions

NonLisDeNondisability

18\-64

Denominator

For each Stratification

LisDe

65\+

ObservedCount

For each Stratification

Disability

ObservedRate

ObservedCount / Denominator \(Percent\)

LisDeAndDisability

ExpectedCount

For each Stratification

Other

ExpectedRate

ExpectedCount / Denominator \(Percent\)

Unknown

CountVariance

For each Stratification

### Table PCR\-C\-3:	Data Elements for Plan All\-Cause Readmissions for Skilled Nursing Care Stratification

Metric

Age

Data Element 

Reporting Instructions

SkilledNursingCare

65\-74

Denominator

For each Stratification

75\-84

ObservedCount

For each Stratification

85\+

ObservedRate

ObservedCount / Denominator \(Percent\)

65\+

ExpectedCount

For each Stratification

ExpectedRate

ExpectedCount / Denominator \(Percent\)

CountVariance

For each Stratification

OE

ObservedCount / ExpectedCount

Rules for Allowable Adjustments of HEDIS

The “Rules for Allowable Adjustments of HEDIS” \(the “Rules”\) describe how NCQA’s HEDIS measure specifications can be adjusted for other populations, if applicable\. The Rules, reviewed and approved by NCQA measure experts, provide for expanded use of HEDIS measures without changing their clinical intent\. 

__Adjusted HEDIS measures may not be used for HEDIS health plan reporting\. __

<a id="_Hlk56083120"></a>The following table is for the Rules for Allowable Adjustments for __Risk\-Adjusted__ __Measurement__   
of the Plan All\-Cause Readmissions measure \(Count of Index Stays, Count of Observed 30\-Day Readmissions, Observed Readmission Rate, Risk Adjustment Determination, Risk Adjustment Weighting, Count of Expected 30\-Day Readmissions, Observed to Expected\)\.

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

Plan population

Yes

Organizations are not required to use plan population to identify outlier rates\.

__CLINICAL COMPONENTS__

<a id="_Hlk54697020"></a>Stratifications

Adjustments Allowed \(Yes/No\)

Notes

- SES Stratification
- Skilled Nursing Care Stratification

No, if applied

Stratifications not required, but if they are used the value sets, logic and product lines may not be changed\.

Eligible Population

Adjustments Allowed \(Yes/No\)

Notes

Event/diagnosis

Yes, with limits

Only events or diagnoses that contain \(or map to\) codes in value sets may be used to identify visits\. The value sets and logic may not be changed\.

__*Note:*__* Organizations may include denied claims to calculate the denominator\.*

Outlier

Yes, with limits

Organizations may not adjust the outlier logic\. 

__*Note:*__* Organizations may include denied claims to calculate these events\. *

Denominator Exclusions

Adjustments Allowed \(Yes/No\)

Notes

Required exclusions

No

The hospice exclusion is required\. The value sets and logic may not be changed\.

Risk Adjustment and Calculation of Expected Events

Adjust Adjustments Allowed \(Yes/No\)

Notes

- Risk Adjustment Determination
- Risk Adjustment Weighting
- Expected Readmissions
- Variance 

Yes, with limits

Risk adjustment determinations, weighting and calculations of expected events logic may not be changed\. 

__*Note:*__* Organizations may include denied claims to calculate these events\. *

<a id="_Hlk4506959"></a>Numerator Criteria

Adjustments Allowed \(Yes/No\)

Notes

Unplanned Acute Readmission

Yes, with limits

Value sets and logic may not be changed\. 

__*Note:*__* Organizations may include denied claims to calculate the numerator\. *

Rules for Allowable Adjustments of HEDIS

The “Rules for Allowable Adjustments of HEDIS” \(the “Rules”\) describe how NCQA’s HEDIS measure specifications can be adjusted for other populations, if applicable\. The Rules, reviewed and approved by NCQA measure experts, provide for expanded use of HEDIS measures without changing their clinical intent\. 

__Adjusted HEDIS measures may not be used for HEDIS health plan reporting\. __

The following table is for the Rules for Allowable Adjustments for __Observed Measurement__   
of the Plan All\-Cause Readmissions Observed Events measure \(Count of Index Stays, Count of Observed 30\-Day Readmissions, Observed Readmission Rate\)\.

__NONCLINICAL COMPONENTS__

Eligible Population

Adjustments Allowed \(Yes/No\)

Notes

Product lines

Yes

When adjusting this measure to assess for observed events only, organizations are not required to use product line criteria; product lines may be combined and all \(or no\) product line criteria may be used\.

Ages

Yes

The denominator age may be expanded\. The age determination dates may be changed \(e\.g\., select, “age 50 as of June 30”\)\.

Continuous enrollment, allowable gap, anchor date

Yes

Organizations are not required to use enrollment criteria; adjustments are allowed\.

Benefits

Yes

Organizations are not required to use a benefit; adjustments are allowed\.

Other

Yes

Organizations may adjust the eligible population criteria to focus on an area of interest defined by gender, race, ethnicity, socioeconomic or sociodemographic characteristics, geographic region or another characteristic\.

Plan population

Yes

Organizations are not required to use plan population to identify outlier rates\.

__CLINICAL COMPONENTS__

Stratifications

Adjustments Allowed \(Yes/No\)

Notes

- SES Stratification
- Skilled Nursing Care Stratification

No, if applied

Stratifications are not required, but if they are used, the value sets, logic and product lines may not be changed\.

Eligible Population

Adjustments Allowed \(Yes/No\)

Notes

Event/diagnosis

Yes, with limits

Only events or diagnoses that contain \(or map to\) codes in value sets may be used to identify visits\. The value sets and logic may not be changed\.

__*Note:*__* Organizations may include denied claims to calculate the denominator\. *

Eligible Population

Adjustments Allowed \(Yes/No\)

Notes

Outlier

Yes

Organizations may adjust the outlier logic\.

Organizations may choose not to apply the outlier logic\. 

Organizations may expand or reduce the outlier threshold\. 

__*Note:*__* Organizations may include denied claims to calculate these events\. *

Denominator Exclusions

Adjustments Allowed \(Yes/No\)

Notes

Required exclusions

Yes

The hospice exclusion is not required\. Refer to *Exclusions* in the *Guidelines for the Rules for Allowable Adjustments*\.

Numerator Criteria

Adjustments Allowed \(Yes/No\)

Notes

Unplanned Acute Readmission

Yes, with limits

Value sets and logic may not be changed\. 

__*Note:*__* Organizations may include denied claims to calculate the numerator\. *

