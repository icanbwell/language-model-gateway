## <a id="Hospitalization_Potentially_Prev_HPC"></a><a id="_Hlk500497946"></a><a id="_Toc74828976"></a><a id="_Toc171403052"></a><a id="HPC"></a>Hospitalization for Potentially Preventable Complications \(HPC\)\*

__\*Adapted with financial support from CMS and with permission from the measure developer,   
the Agency for Healthcare Research and Quality \(AHRQ\)\.__

Summary of Changes to HEDIS MY 2025

- Removed gender from the *Reporting* and *Calculated* instructions and from the Data Elements tables\. Gender will still be included in the measure’s risk weight models\.
- Expanded the age and outlier criteria in the Observed Measurement in the *Rules for Allowable Adjustments*\.
- *Technical Update:* Revised the ACSC definition and Calculation of Observed Events\.

Description 

For members 67 years of age and older, the rate of discharges for ambulatory care sensitive conditions \(ACSC\) per 1,000 members and the risk\-adjusted ratio of observed\-to\-expected discharges for ACSC by chronic and acute conditions\.

Definitions 

ACSC

Ambulatory care sensitive condition\. An acute or chronic health condition that can be managed or treated in an outpatient setting\. The ambulatory care conditions included in this measure are:

- *Chronic ACSC:*
- Diabetes short\-term complications\. 
- Diabetes long\-term complications\.
- Uncontrolled diabetes\.
- Lower\-extremity amputation among patients with diabetes\.
- COPD\.
- Asthma\.
- Hypertension\.
- Heart failure\.
- *Acute ACSC:*
- Bacterial pneumonia\.
- Urinary tract infection\.
- Cellulitis\.
- Severe pressure ulcers Pressure ulcer\.

Chronic ACSC outlier

Members with three or more inpatient or observation stay chronic ACSCs during the measurement year\.

Chronic ACSC nonoutlier

Members with two or fewer inpatient or observation stay chronic ACSCs during the measurement year\.

Acute ACSC outlier

Members with three or more inpatient or observation stay acute ACSCs during the measurement year\. 

Acute ACSC nonoutlier

Members with two or fewer inpatient or observation stay acute ACSCs during the measurement year\. 

Total ACSC outlier

Members classified as either a chronic ACSC outlier or an acute ACSC outlier\.

Total ACSC nonoutlier

Members who are not classified as a chronic ACSC outlier and an acute ACSC outlier\.

Classification period

The year prior to the measurement year\. 

PPD

Predicted probability of discharge\. The predicted probability of a member having any discharge in the measurement year\. 

PUCD

Predicted unconditional count of discharge\. The predicted unconditional count of discharges for members during the measurement year\.

Eligible Population 

Product lines

Medicare\. 

Ages

67 years and older as of December 31 of the measurement year\. 

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

Required exclusions

Exclude members who meet any of the following criteria:

- Members who use hospice services \(Hospice Encounter Value Set; Hospice Intervention Value Set\) or elect to use a hospice benefit any time during the measurement year\. Organizations that use the Monthly Membership Detail Data File to identify these members must use only the run date of the file to determine if the member elected to use a hospice benefit during the measurement year\.
- Members enrolled in an Institutional SNP \(I\-SNP\) any time during the measurement year\. 
- Members living long\-term in an institution any time during the measurement year, as identified by the LTI flag in the Monthly Membership Detail Data File\. Use the run date of the file to determine if a member had an LTI flag during the measurement year\.

Calculation of Observed Events

Report each ACSC category separately and as a combined total\. 

Chronic ACSC

Follow the steps below to identify the number of chronic ACSC acute inpatient and observation stay discharges\.

*Step 1*

Identify all acute inpatient and observation stay discharges during the measurement year\. To identify acute inpatient and observation stay discharges:

1\.	Identify all acute and nonacute inpatient stays \(Inpatient Stay Value Set\) and observation stays \(Observation Stay Value Set\)\. 

2\.	Exclude nonacute inpatient stays \(Nonacute Inpatient Stay Value Set\)\.

3\.	Identify the discharge date for the stay\.

*Step 2*

*Direct transfers\.* For discharges with one or more direct transfers, use the last discharge\. 

Using the discharges identified in step 1, identify direct transfers between acute inpatient and observation or between observation and acute inpatient using the definition found in the *Guidelines for Risk Adjusted Utilization Measures\.*

*Step 3 *

For the remaining acute inpatient and observation stay discharges, identify discharges with any of the following on the discharge claim:

- Principal diagnosis of diabetes short\-term complications \(ketoacidosis, hyperosmolarity or coma; Diabetes Short Term Complications Value Set\)\.
- Principal diagnosis of diabetes with long\-term complications \(renal, eye, neurological, circulatory or unspecified complications; Diabetes Long Term Complications Value Set\)\.
- Principal diagnosis of uncontrolled diabetes \(Uncontrolled Diabetes Value Set\)\.
- A procedure code for lower extremity amputation \(Lower Extremity Amputation Procedures Value Set\) __*with*__ any diagnosis of diabetes \(Diabetes Diagnosis Value Set\)\. 
- Exclude any discharge with a diagnosis of traumatic amputation of the lower extremity \(Traumatic Amputation of Lower Extremity Value Set\)\. 
- Principal diagnosis of COPD \(COPD Diagnosis Value Set\)\.
- Exclude any discharge with a diagnosis of cystic fibrosis or anomaly of the respiratory system \(Cystic Fibrosis and Respiratory System Anomalies Value Set\)\.
- Principal diagnosis of asthma \(Asthma Diagnosis Value Set\)\. 
- Exclude any discharge with a diagnosis of cystic fibrosis or anomaly of the respiratory system \(Cystic Fibrosis and Respiratory System Anomalies Value Set\)\.
- Principal diagnosis of heart failure \(Heart Failure Diagnosis Value Set\)\.
- Exclude any discharges with a cardiac procedure \(Cardiac Procedure Value Set\)\.
- Principal diagnosis of hypertension \(Hypertension Value Set\)\.
- Exclude any discharge with a cardiac procedure \(Cardiac Procedure Value Set\)\.
- Exclude any discharge with a diagnosis of Stage I\-IV kidney disease \(Stage I Through IV Kidney Disease Value Set\) __*with*__ a dialysis procedure \(Dialysis Value Set\)\.

__Note: __For direct transfers, use all discharges to identify principal diagnoses and exclusions in this step\. 

*Step 4*

Remove discharges for members with any three or more chronic ACSC discharges during the measurement year and report these members as chronic ACSC outliers\. 

__Note:__ Count discharges with one or more direct transfers \(identified in step 2\) as one discharge when identifying outlier members\. 

Acute ACSC

Follow the steps below to identify the number of acute ACSC acute inpatient and observation stay discharges\.

*Step 1*

Identify all acute inpatient and observation stay discharges during the measurement year\. To identify acute inpatient and observation stay discharges:

1\.	Identify all acute and nonacute inpatient stays \(Inpatient Stay Value Set\) and observation stays \(Observation Stay Value Set\)\. 

2\.	Exclude nonacute inpatient stays \(Nonacute Inpatient Stay Value Set\)\.

3\.	Identify the discharge date for the stay\.

*Step 2*

*Direct transfers:* For discharges with one or more direct transfers, use the last discharge\. 

Using the discharges identified in step 1, identify direct transfers between acute inpatient and observation or between observation and acute inpatient using the definition found in the *Guidelines for Risk Adjusted Utilization Measures\.* 

*Step 3*

For the remaining acute inpatient and observation stay discharges, identify discharges with any of the following on the discharge claim:

- Principal diagnosis of bacterial pneumonia \(Bacterial Pneumonia Value Set\)\.
- Exclude any discharge with a diagnosis of sickle cell anemia HB S disease \(Sickle Cell Anemia and HB S Disease Value Set\)\. 
- Exclude any discharge with a procedure or diagnosis for immunocompromised state \(Immunocompromised State Value Set\)\.
- Principal diagnosis of urinary tract infection \(Urinary Tract Infection Value Set\)\.
- Exclude any discharge with a diagnosis of kidney/urinary tract disorder \(Kidney and Urinary Tract Disorders Value Set\)\. 
- Exclude any discharge with a procedure or diagnosis for immunocompromised state \(Immunocompromised State Value Set\)\. 
- Principal diagnosis of cellulitis \(Cellulitis Value Set\)\.
- Principal diagnosis of severe pressure ulcers \(Severe Pressure Ulcers Value Set\)\. 

__Note:__ For direct transfers, use all discharges to identify principal diagnoses and exclusions in this step\.

*Step 4*

Remove discharges for members with any three or more acute ACSC discharges during the measurement year and report these members as acute ACSC outliers\. 

__Note: __Count discharges with one or more direct transfers \(identified in step 2\) as one discharge when identifying outlier members\. 

Total ACSC

Follow the steps below to identify the number of total ACSC acute inpatient and observation stay discharges\.

*Step 1*

Sum the discharges from the Chronic ACSC and Acute ACSC categories\.

*Step 2*

Remove discharges for acute ACSC outliers or chronic ACSC outliers\. Report these members as total ACSC outliers\.

__Note:__ Count discharges with one or more direct transfers \(identified in step 2\) as one discharge when identifying outlier members\.

Risk Adjustment Determination

For each nonoutlier member in the eligible population, use the steps in the *Risk Adjustment Comorbidity Category Determination *section in the *Guidelines for Risk Adjusted Utilization Measures* to identify risk adjustment categories based on presence of comorbidities\.

Risk Adjustment Weighting and Calculation of Expected Events

Calculation of risk\-adjusted outcomes \(counts of discharges\) uses predetermined risk weights generated by two separate regression models\. Weights from each model are combined to predict how many discharges each member might have during the measurement year, given their age, gender and the presence or absence of a comorbid condition\. Weights are specific to reporting indicator \(Chronic ACSC, Acute ACSC and Total ACSC\)\. Refer to the reporting indicator in the risk adjustment tables to ensure that weights are linked appropriately\.

For each nonoutlier member in the eligible population, assign PPD risk weights\. Calculate the PPD for each ACSC category \(Chronic ACSC, Acute ACSC, Total ACSC\)\.

*Step 1*

For each member with a comorbidity HCC Category, link the PPD weights\.

*Step 2*

Link the age and gender PPD weights for each member\.

*Step 3*

Sum all PPD weights associated with the member \(HCC, age and gender\) for each category \(Chronic ACSC, Acute ACSC, Total ACSC\)\.

*Step 4*

Calculate the predicted probability of having at least one discharge in the measurement year, based on the sum of the weights for each member, for each category \(Chronic ACSC, Acute ACSC, Total ACSC\), using the formula below\.

PPD = 

Truncate the final PPD *for each member* to 10 decimal places\. Do not truncate or round in previous steps\.

For each nonoutlier member in the eligible population, assign PUCD risk weights\. Calculate the PUCD for each ACSC category \(Chronic ACSC, Acute ACSC, Total ACSC\)\.

*Step 1*

For each member with a comorbidity HCC Category, link the PUCD weights\. If a member does not have any comorbidities to which weights can be linked, assign a weight of 1\.

*Step 2*

Link the age and gender PUCD weights for each member\.

*Step 3*

Calculate the predicted unconditional count of discharges in the measurement year by multiplying all PUCD weights \(HCC, age and gender\) associated with the member for each ACSC category \(Chronic ACSC, Acute ACSC, Total ACSC\)\. Use the following formula:

PUCD = Age/Gender Weight \* HCC Weight

__Note:__ Multiply by each HCC associated with the member\. For example, assume a member with HCC\-2, HCC\-10, HCC\-47\. The formula would be:

PUCD = Age/Gender Weight \* HCC\-2 \* HCC\-10 \* HCC\-47

Truncate the final PUCD *for each member* to 10 decimal places\. Do not truncate or round in prior steps\.

*Expected count of hospitalization*

Calculate the final member\-level expected count of discharges for each category using the formula below\.

Expected Count of ACSC Discharges = PPD x PUCD 

Round the member\-level results to 4 decimal places using the \.5 rule and sum over all members in the category\.

*Step 4 *

Use the formula below to calculate to calculate the covariance of the predicted outcomes for each category \(age group and type of ACSC\)\. For categories with a single member \(*n*c=1\), set the covariance to zero\. Do not round the covariance before using it in step 5\.

Where:

* 	*denotes an individual category

 	is the number of members in the category indicated by 

 	is an individual member within the category indicated by 

 	is the truncated PPD for the member denoted by 

 	is the unrounded/untruncated mean PPD in the category indicated by 

 	is the truncated PUCD for the member denoted by 

 	is the unrounded/untruncated mean PUCD in the category indicated by 

*Step 5 *

Once the covariance between PPD and PUCD for a given category is calculated, it can be used as indicated in the formula below to calculate the variance for that category\.

Where:

* 	*denotes an individual category

 	is the number of members in the category indicated by 

 	is an individual member within the category indicated by 

 	is the truncated PPD for the member denoted by 

 	is the truncated PUCD for the member denoted by 

 	is the number of members in the category indicated by 

Round the variance for reporting to 4 decimal places using the \.5 rule\.

*Reporting:* Number of Chronic ACSC Nonoutliers, Acute ACSC Nonoutliers and Total ACSC Nonoutliers

The number of Chronic ACSC nonoutlier members, Acute ACSC nonoutliers and Total ACSC nonoutliers for each age group, reported as the NonOutlierMemberCount\.

*Reporting:* Number of Chronic ACSC Outliers, Acute ACSC Outliers and Total ACSC Outliers

The number of Chronic ACSC outlier members, Acute ACSC outliers and Total ACSC outliers for each age group, reported as the OutlierMemberCount\.

<a id="_Hlk513211715"></a>*Calculated:* Number of Members in the Eligible Population

The number of members in the eligible population \(including all outliers\) for each age group and totals\. Calculated by IDSS as the MemberCount\.

*Calculated:* Chronic ACSC Outlier Rate, Acute ACSC Outlier Rate and Total ACSC   
Outlier Rate

The number of Chronic ACSC outlier members \(OutlierMemberCount\) divided by the number of members in the eligible population \(MemberCount\), displayed as a permillage \(multiplied by 1,000\) for each age group and totals\. Calculated by IDSS as the OutlierRate\.

The number of Acute ACSC outlier members \(OutlierMemberCount\) divided by the number of members in the eligible population \(MemberCount\), displayed as a permillage \(multiplied by 1,000\) for each age group and totals\. Calculated by IDSS as the OutlierRate\.

The number of Total ACSC outlier members \(OutlierMemberCount\) divided by the number of members in the eligible population \(MemberCount\), displayed as a permillage \(multiplied by 1,000\) for each age group and totals\. Calculated by IDSS as the OutlierRate\.

*Reporting:* Number of Observed Events Among Nonoutlier Members

The number of observed discharges within each age group for each ACSC category and Total ACSC, reported as the ObservedCount\.

*Calculated:* Observed Discharges per 1,000 Nonoutlier Members

The number of observed discharges \(ObservedCount\) divided by the number of nonoutlier members in the eligible population \(NonOutlierMemberCount\), multiplied by 1,000 for each age group and totals for each ACSC category and Total ACSC\. Calculated by IDSS as the ObservedRate\.

*Reporting:* Number of Expected Events Among Nonoutlier Members

The number of expected discharges for each age group for each ACSC category and Total ACSC, reported as the ExpectedCount\.

*Calculated:* Expected Discharges per 1,000 Nonoutlier Members

The number of expected discharges \(ExpectedCount\) divided by the number of nonoutlier members in the eligible population \(NonOutlierMemberCount\), multiplied by 1,000 for each age group and totals for each ACSC category and Total ACSC\. Calculated by IDSS as the ExpectedRate\.

*Reporting:* Variance Among Nonoutlier Members

The variance \(from Risk Adjustment Weighting and Calculation of Expected Events, PUCD, step 5\) for each age group for each ACSC category and Total ACSC, reported as the CountVariance\.

*Calculated:* O/E Ratio

The number of observed discharges \(ObservedCount\) divided by the number of expected discharges \(ExpectedCount\) for each age group and totals for each ACSC category and Total ACSC\. Calculated by IDSS as the OE\.

*Note*

- Supplemental data may not be used for this measure, except for required exclusions\.

### Table HPC\-3: Data Elements for Hospitalization for Potentially Preventable Complications

Metric

Age

Data Element 

Reporting Instructions

Chronic

67\-74

NonOutlierMemberCount

For each Metric and Stratification

Acute

75\-84

OutlierMemberCount

For each Metric and Stratification

Total

85\+

MemberCount

NonOutlierMemberCount \+ OutlierMemberCount

Total

OutlierRate

OutlierMemberCount / MemberCount \(Permille\)

ObservedCount

For each Metric and Stratification

ObservedRate

1,000 \* ObservedCount / NonOutlierMemberCount

ExpectedCount

For each Metric and Stratification

ExpectedRate

1,000 \* ExpectedCount / NonOutlierMemberCount

CountVariance

For each Metric and Stratification

OE

ObservedCount / ExpectedCount

Rules for Allowable Adjustments of HEDIS

The “Rules for Allowable Adjustments of HEDIS” \(the “Rules”\) describe how NCQA’s HEDIS measure specifications can be adjusted for other populations, if applicable\. The Rules, reviewed and approved by NCQA measure experts, provide for expanded use of HEDIS measures without changing their clinical intent\.

__Adjusted HEDIS measures may not be used for HEDIS health plan reporting\. __

The following table is for the Rules for Allowable Adjustments for __Risk\-Adjusted Measurement__ of the Hospitalization for Potentially Preventable Complications measure \(Observed Discharges, Risk Adjustment Determination, Risk Adjustment Weighting, Count of Expected Discharges, Variance, Observed to Expected\)\.

<a id="_Rules_for_Allowable"></a>__NONCLINICAL COMPONENTS__

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

Calculation of Observed Events

Adjustments Allowed \(Yes/No\)

Notes

- Chronic ACSC
- Acute ACSC
- Total ACSC

Yes, with limits

Only events or diagnoses that contain \(or map to\) codes in value sets may be used to identify visits\. The value sets and logic may not be changed\.

__*Note:*__* Organizations may include denied claims to calculate observed events\. *

- Chronic ACSC Outliers
- Acute ACSC Outliers
- Total ACSC Outliers

Yes, with limits

Organizations may not adjust the outlier logic\.

__*Note:*__* Organizations may include denied claims to calculate these events\. *

Exclusions

Adjustments Allowed \(Yes/No\)

Notes

Exclusions: I\-SNP, LTI

Yes

These exclusions are not required\. Refer to *Exclusions* in the *Guidelines for the Rules for Allowable Adjustments\.*

Required exclusions

No

The hospice exclusion is required\. The value sets and logic may not be changed\.

Risk Adjustment and Calculation of Expected Events

Adjustments Allowed \(Yes/No\)

Notes

- Risk Adjustment Determination
- Risk Adjustment Weighting
- Expected Count of Hospitalization
- Variance

Yes, with limits

Risk adjustment determinations, weighting and calculations \(including PPD and PUCD\) of expected events logic may not be changed\. 

__*Note:*__* Organizations may include denied claims to calculate these events\. *

Rules for Allowable Adjustments of HEDIS

The “Rules for Allowable Adjustments of HEDIS” \(the “Rules”\) describe how NCQA’s HEDIS measure specifications can be adjusted for other populations, if applicable\. The Rules, reviewed and approved by NCQA measure experts, provide for expanded use of HEDIS measures without changing their clinical intent\.

__Adjusted HEDIS measures may not be used for HEDIS health plan reporting\. __

<a id="_Rules_for_Allowable_9"></a>The following table is for the Rules for Allowable Adjustments for __Observed Measurement__ of the Hospitalization for Potentially Preventable Complications measure, Observed Events \(Observed Discharges\)\.

__NONCLINICAL COMPONENTS__

Eligible Population

Adjustments Allowed \(Yes/No\)

Notes

Product lines

Yes

When adjusting this measure to assess for observed events only, organizations are not required to use product line criteria; product lines may be combined and all \(or no\) product line criteria may be used\.

Ages

Yes, with limits

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

__CLINICAL COMPONENTS__

Calculation of Observed Events

Adjustments Allowed \(Yes/No\)

Notes

- Chronic ACSC
- Acute ACSC
- Total ACSC

Yes, with limits

Only events or diagnoses that contain \(or map to\) codes in value sets may be used to identify visits\. The value sets and logic may not be changed\.

__*Note:*__* Organizations may include denied claims to calculate observed events\. *

Outlier

Yes

Organizations may adjust the outlier logic\.

Organizations may choose not to apply the outlier logic\. 

Organizations may expand or reduce the outlier threshold\. 

__*Note:*__* Organizations may include denied claims to calculate these events\.*

Exclusions

Adjustments Allowed \(Yes/No\)

Notes

Exclusions: I\-SNP, LTI

Yes

These exclusions are not required\. Refer to *Exclusions* in the *Guidelines for the Rules for Allowable Adjustments*\.

Required exclusions

Yes

The hospice exclusion is not required\. Refer to *Exclusions* in the *Guidelines for the Rules for Allowable Adjustments*\.

