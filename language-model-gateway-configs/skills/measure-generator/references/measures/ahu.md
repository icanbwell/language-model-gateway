## <a id="_Acute_Hospital_Utilization"></a><a id="Acute_Hospitalization_Utilization_AHU"></a><a id="_Toc74828974"></a><a id="_Toc171403050"></a>Acute Hospital Utilization \(AHU\)

Summary of Changes to HEDIS MY 2025

- Added the Medicaid product line\. 
- Removed gender from the Reporting instructions and from the Data Elements tables\. Gender remains included in the measure’s risk weight models\.
- Expanded the age and outlier criteria in the Observed Measurement in the *Rules for Allowable Adjustments*\.

Description 

For members 18 years of age and older, the risk\-adjusted ratio of observed\-to\-expected acute inpatient and observation stay discharges during the measurement year\. 

__Note:__ For Medicaid, report only members 18–64 years of age\.

Definitions 

Outlier

Medicare members with four or more inpatient or observation stay discharges during the measurement year\.

Medicaid members with six or more inpatient or observation stay discharges during the measurement year\.

Commercial members with three or more inpatient or observation stay discharges during the measurement year\.

Nonoutlier

Medicare members with three or less inpatient or observation stay discharges during the measurement year\.

Medicaid members with five or less inpatient or observation stay discharges during the measurement year\.

Commercial members with two or less inpatient or observation stay discharges during the measurement year\.

Classification period 

The year prior to the measurement year\.

Planned hospital stay

A hospital stay is considered planned if it meets criteria as described in step 3 of calculation of observed events\.

PPD

Predicted probability of discharge\. The predicted probability of a member having any discharge in the measurement year\. 

PUCD

Predicted unconditional count of discharge\. The predicted unconditional count of discharges for members during the measurement year\.

Eligible Population 

Product lines

Commercial, Medicare, Medicaid \(report each product line separately\)\.

Ages

18 years and older as of December 31 of the measurement year\.

Continuous enrollment

The measurement year and the year prior to the measurement year\.

Allowable gap

No more than one gap in enrollment of up to 45 days during each year of continuous enrollment\. 

Anchor date

December 31 of the measurement year\.

Benefit

Medical\.

Event/diagnosis

None\.

Required exclusion

Members who use hospice services \(Hospice Encounter Value Set; Hospice Intervention Value Set\) or elect to use a hospice benefit any time during the measurement year\. Organizations that use the Monthly Membership Detail Data File to identify these members must use only the run date of the file to determine if the member elected to use a hospice benefit during the measurement year\. 

Calculation of Observed Events

Use the following steps to identify and categorize acute inpatient and observation stay discharges\.

*Step 1*

Identify all acute inpatient and observation discharges during the measurement year\. To identify acute inpatient and observation discharges: 

1\.	Identify all acute and nonacute inpatient stays \(Inpatient Stay Value Set\) and observation stays \(Observation Stay Value Set\)\. 

2\.	Exclude nonacute inpatient stays \(Nonacute Inpatient Stay Value Set\)\.

3\.	Identify the discharge date for the stay\.

*Step 2*

*Direct transfers:* For discharges with one or more direct transfers, use the last discharge\. 

Using the discharges identified in step 1, identify direct transfers between acute inpatient and observation, or between observation and acute inpatient, using the definition in the *Guidelines for Risk Adjusted Utilization Measures\. *

*Step 3*

For the remaining observation and inpatient discharges, exclude inpatient and observation discharges with any of the following on the discharge claim: 

- A principal diagnosis of mental health or chemical dependency \(Mental and Behavioral Disorders Value Set\)\. 
- A principal diagnosis of live\-born infant \(Deliveries Infant Record Value Set\)\.
- A maternity\-related principal diagnosis \(Maternity Diagnosis Value Set\)\.
- A maternity\-related stay \(Maternity Value Set\)\. 
- A planned hospital stay using any of the following:

- A principal diagnosis of maintenance chemotherapy \(Chemotherapy Encounter Value Set\)\. 
- A principal diagnosis of rehabilitation \(Rehabilitation Value Set\)\. 
- An organ transplant \(Kidney Transplant Value Set, Bone Marrow Transplant Value Set, Organ Transplant Other Than Kidney Value Set, Introduction of Autologous Pancreatic Cells Value Set\)\.
- A potentially planned procedure \(Potentially Planned Procedures Value Set\) without a principal acute diagnosis \(Acute Condition Value Set\)\.
- Inpatient and observation stays with a discharge for death\.

__Note:__ For hospital stays where there was a direct transfer \(identified in step 2\), use the original stay and any direct transfer stays to identify exclusions in this step\.

*Step 4*

For the remaining observation and inpatient discharges, remove discharges for outlier members and report these members as outliers\.

__Note:__ Count discharges with one or more direct transfers \(identified in step 2\) as one discharge when identifying outlier members\. 

*Step 5*

Calculate the total using all discharges identified after completing steps 1–4\. 

Risk Adjustment Determination

For each nonoutlier member in the eligible population, use the steps in the *Risk Adjustment Comorbidity Category Determination *section in the *Guidelines for Risk Adjusted Utilization Measures* to identify risk adjustment categories based on presence of comorbidities\.

Risk Adjustment Weighting and Calculation of Expected Events

Calculation of risk\-adjusted outcomes \(counts of discharges\) uses predetermined risk weights generated by two separate regression models\. Weights from each model are combined to predict how many discharges each member might have during the measurement year, given age, gender and presence or absence of a comorbid condition\. Weights are specific to product line \(Medicare Under 65, Medicare 65 Plus, commercial, Medicaid\)\. Refer to the reporting indicator column in the risk adjustment tables to ensure that weights are linked appropriately\.

For each nonoutlier member in the eligible population, assign PPD risk weights\. Calculate the PPD\. 

*Step 1*

For each member with a comorbidity HCC category, link the PPD weights\. 

*Step 2*

Link the age\-gender PPD weights for each member\.

*Step 3*

Sum all PPD weights \(HCC, age and gender\) associated with the member\.

*Step 4*

Calculate the predicted probability of having at least one discharge in the measurement year based on the sum of the weights for each member using the formula below\.

PPD = 

<a id="_Hlk515878003"></a>Truncate the final PPD *for each member* to 10 decimal places\. Do not truncate or round in previous steps\.

For each nonoutlier member in the eligible population assign PUCD risk weights\.

*Step 1*

For each member with a comorbidity HCC Category, link the PUCD weights\. If a member does not have any comorbidities to which a weight could be linked, assign a weight of 1\.

*Step 2*

Link the age\-gender PUCD weights for each member\.

*Step 3*

Calculate the predicted unconditional count of discharges in the measurement year, by multiplying all PUCD weights \(HCC, age and gender\) associated with the member\. Use the following formula:

PUCD = Age/Gender Weight \* HCC Weight

__Note:__ Multiply by each HCC associated with the member\. For example, assume a member with HCC\-2, HCC\-10, HCC\-47\. The formula would be:

PUCD = Age/Gender Weight \* HCC\-2 \* HCC\-10 \* HCC\-47

Truncate the final PUCD *for each member* to 10 decimal places\. Do not truncate or round in previous steps\.

*Expected *  
*count of hospitalization*

Calculate the final member\-level expected count of discharges using the formula below\. 

Expected Count of Discharges = PPD x PUCD

Round the member\-level results to 4 decimal places using the \.5 rule and sum over all members in the category\.

__Step 4__

Use the formula below to calculate the covariance of the predicted outcomes for each category\. For categories with a single member \(*n*c=1\), set the covariance to zero\. Do not round the covariance before using it in step 5\.

Where:

* 	*denotes an individual category

 	is the number of members in the category indicated by 

 	is an individual member within the category indicated by 

 	is the truncated PPD for the member denoted by 

	is the unrounded/untruncated mean PPD in the category indicated by 

 	is the truncated PUCD for the member denoted by 

 	is the unrounded/untruncated mean PUCD in the category indicated by 

__Step 5__

Once the covariance between PPD and PUCD for a given category is calculated, it can be used as indicated in the formula below to calculate the variance for that category\.

Where:

* 	*denotes an individual category

 	is the number of members in the category indicated by 

 	is an individual member within the category indicated by 

 	is the truncated PPD for the member denoted by 

 	is the truncated PUCD for the member denoted by 

Round the variance for reporting to 4 decimal places using the \.5 rule\.

*Reporting:* Number of Nonoutliers

The number of nonoutlier members for each age group, reported as the NonOutlierMemberCount\.

*Reporting:* Number of Outliers

The number of outlier members for each age group, reported as the OutlierMemberCount\.

<a id="_Hlk513211646"></a>*Calculated: *Number of Members in the Eligible Population

The number of members in the eligible population \(including outliers\) for each age group and totals\. Calculated by IDSS as the MemberCount\.

*Calculated:* Outlier Rate

The number of outlier members \(OutlierMemberCount\) divided by the number of members in the eligible population \(MemberCount\), displayed as a permillage \(multiplied by 1,000\), for each age group and totals\. Calculated by IDSS as the OutlierRate\.

*Reporting:* Number of Observed Events Among Nonoutlier Members

The number of observed discharges within each age group, reported as the ObservedCount\.

*Calculated:* Observed Discharges per 1,000 Nonoutlier Members

The number of observed discharges \(ObservedCount\) divided by the number of nonoutlier members in the eligible population \(NonOutlierMemberCount\), multiplied by 1,000 within each age group and totals\. Calculated by IDSS as the ObservedRate\.

*Reporting:* Number of Expected Events Among Nonoutlier Members 

The number of expected discharges within each age group, reported as the ExpectedCount\.

*Calculated:* Expected Discharges per 1,000 Nonoutlier Members

The number of expected discharges \(ExpectedCount\) divided by the number of nonoutlier members in the eligible population \(NonOutlierMemberCount\), multiplied by 1,000 within each age group and totals\. Calculated by IDSS as the ExpectedRate\.

*Reporting:* Variance Among Nonoutlier Members

The variance \(from Risk Adjustment Weighting and Calculation of Expected Events, PUCD, step 5\) within each age group, reported as the CountVariance\.

*Calculated:* O/E Ratio

The number of Observed Discharges Among Nonoutlier Members \(ObservedCount\) divided by Number of Expected Discharges Among Nonoutlier Members \(ExpectedCount\) for each age group and totals\. Calculated by IDSS as the OE\.

*Note*

- *Supplemental data may not be used for this measure, except for required exclusions\.*

### Table AHU\-1: Data Elements for Acute Hospital Utilization

__Metric__

__Age__

__Data Element __

__Reporting Instructions__

AcuteHospitalUtilization

18\-21

NonOutlierMemberCount

For each Stratification

22\-34

OutlierMemberCount

For each Stratification

35\-44

MemberCount

NonOutlierMemberCount \+ OutlierMemberCount

18\-44

OutlierRate

OutlierMemberCount / MemberCount \(Permille\)

45\-54

ObservedCount

For each Stratification

55\-64

ObservedRate

1000 \* ObservedCount / NonOutlierMemberCount

18\-64

ExpectedCount

For each Stratification

ExpectedRate

1000 \* ExpectedCount / NonOutlierMemberCount

CountVariance

For each Stratification

OE

ObservedCount / ExpectedCount

### Table AHU\-2/3: Data Elements for Acute Hospital Utilization

__Metric__

__Age__

__Data Element __

__Reporting Instructions__

AcuteHospitalUtilization

18\-44

NonOutlierMemberCount

For each Stratification

45\-54

OutlierMemberCount

For each Stratification

55\-64

MemberCount

NonOutlierMemberCount \+ OutlierMemberCount

18\-64

OutlierRate

OutlierMemberCount / MemberCount \(Permille\)

65\-74

ObservedCount

For each Stratification

75\-84

ObservedRate

1000 \* ObservedCount / NonOutlierMemberCount

85\+

ExpectedCount

For each Stratification

65\+

ExpectedRate

1000 \* ExpectedCount / NonOutlierMemberCount

Total

CountVariance

For each Stratification

OE

ObservedCount / ExpectedCount

###  

Rules for Allowable Adjustments of HEDIS

The “Rules for Allowable Adjustments of HEDIS” \(the “Rules”\) describe how NCQA’s HEDIS measure specifications can be adjusted for other populations, if applicable\. The Rules, reviewed and approved by NCQA measure experts, provide for expanded use of HEDIS measures without changing their clinical intent\. 

__Adjusted HEDIS measures may not be used for HEDIS health plan reporting\. __

Rules for Allowable Adjustments for __Risk\-Adjusted Measurement__ of the Acute Hospital Utilization Measure \(Observed Discharges, Expected Discharges, Risk Adjustment Determination, Risk Adjustment Weighting, Observed to Expected, Variance\)

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

For risk adjusted rates, organizations are required to use enrollment criteria; adjustments are not allowed\.

Benefits

Yes

Organizations are not required to use a benefit; adjustments are allowed\.

Other

Yes, with limits

Organizations may only adjust the eligible population criteria to focus on an area of interest defined by gender, sociodemographic characteristics or geographical region\.

__*Note:*__* NCQA recommends evaluating risk model performance and validity within adjusted populations\.* 

Organizations may not adjust for a clinical subpopulation \(e\.g\., members with a diabetes diagnosis\)\.

__CLINICAL COMPONENTS__

Calculations of Observed Events

Adjustments Allowed \(Yes/No\)

Notes

Discharges

Yes, with limits

Only events or diagnoses that contain \(or map to\) codes in value sets may be used to identify visits\. The value sets and logic may not be changed\.

__*Note:*__* Organizations may include denied claims to calculate observed events\. *

Outlier

Yes, with limits

Organizations may not adjust the outlier logic\.

__*Note:*__* Organizations may include denied claims to calculate these events\. *

Exclusions

Adjustments Allowed \(Yes/No\)

Notes

Required exclusions

No

The hospice exclusion is required\. The value sets and logic may not be changed\.

Risk Adjustment and Calculation of Expected Events

Adjustments Allowed \(Yes/No\)

Notes

- Risk Adjustment Determination
- Risk Adjustment Weighting
- Expected Count of Discharges
- Variance

Yes, with limits

Risk adjustment determinations, weighting and calculations \(including PPD and PUCD\) of expected events logic may not be changed\. 

__*Note:*__* Organizations may include denied claims to calculate these events\. *

Rules for Allowable Adjustments of HEDIS

The “Rules for Allowable Adjustments of HEDIS” \(the “Rules”\) describe how NCQA’s HEDIS measure specifications can be adjusted for other populations, if applicable\. The Rules, reviewed and approved by NCQA measure experts, provide for expanded use of HEDIS measures without changing their clinical intent\. 

__Adjusted HEDIS measures may not be used for HEDIS health plan reporting\. __

Rules for Allowable Adjustments for __Observed Measurement__ of Acute Hospital Utilization Observed Events Measure \(Observed Discharges\)

<a id="_Rules_for_Allowable_6"></a>__NONCLINICAL COMPONENTS__

Eligible Population

Adjustments Allowed \(Yes/No\)

Notes

Product lines

Yes

When adjusting this measure to assess for observed events only, organizations are not required to use product line criteria; product lines may be combined and all \(or no\) product line criteria may be used\.

Ages

Yes

The denominator age range may be expanded\. The age determination dates may be changed \(e\.g\., select, “age 50 months as of June 30”\)\.

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

Calculations of Observed Events

Adjustments Allowed \(Yes/No\)

Notes

Discharges

Yes, with limits

Only events or diagnoses that contain \(or map to\) codes in value sets may be used to identify visits\. The value sets and logic may not be changed\.

__*Note:*__* Organizations may include denied claims to calculate the observed events\. *

Outlier

Yes

Organizations may adjust the outlier logic\.

Organizations may choose not to apply the outlier logic\. 

Organizations may expand or reduce the outlier threshold\. 

__*Note:*__* Organizations may include denied claims to calculate these events\. *

Exclusions

Adjustments Allowed \(Yes/No\)

Notes

Required exclusions

Yes

The hospice exclusion is not required\. Refer to *Exclusions* in the *Guidelines for the Rules for Allowable Adjustments*\.

