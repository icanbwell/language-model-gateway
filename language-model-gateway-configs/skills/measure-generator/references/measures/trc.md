## <a id="Transitions_of_Care_TRC"></a><a id="_Toc74817959"></a><a id="_Toc171403007"></a>Transitions of Care \(TRC\)

Summary of Changes to HEDIS MY 2025

- Added examples to the* Note *to clarify what is not considered evidence that the provider was aware of the member’s hospitalization or discharge when reporting the Medication Reconciliation Post\-Discharge indicator\. 
- Deleted the *Note* regarding billing methods for intensive outpatient encounters and partial hospitalizations\.
- *Technical Update:* Revised the hybrid specification for the Notification of Inpatient Admission and Receipt of Discharge Information indicators\.

Description

The percentage of discharges for members 18 years of age and older who had each of the following\. Four rates are reported:

- *Notification of Inpatient Admission*\. Documentation of receipt of notification of inpatient admission on the day of admission through 2 days after the admission \(3 total days\)\.
- *Receipt of Discharge Information\. *Documentation of receipt of discharge information on the day of discharge through 2 days after the discharge \(3 total days\)\.
- *Patient Engagement After Inpatient Discharge*\. Documentation of patient engagement \(e\.g\., office visits, visits to the home, telehealth\) provided within 30 days after discharge\.
- *Medication Reconciliation Post\-Discharge*\. Documentation of medication reconciliation on the date of discharge through 30 days after discharge \(31 total days\)\.

Definitions

Medication reconciliation

A type of review in which the discharge medications are reconciled with the most recent medication list in the outpatient medical record\.

Medication list

A list of medications in the medical record\. The medication list may include medication names only or may include medication names, dosages and frequency, over\-the\-counter \(OTC\) medications and herbal or supplemental therapies\. 

Eligible Population

Product lines

Medicare\.

Ages

18 years and older as of December 31 of the measurement year\. Report two age stratifications and a total rate:

- 18–64 years\.
- 65 years and older\.
- Total\.

Continuous enrollment

The date of discharge through 30 days after discharge \(31 total days\)\.

Allowable gap

None\.

Anchor date

None\.

Benefit

Medical\.

Event/diagnosis

An acute or nonacute inpatient discharge on or between January 1 and December 1 of the measurement year\. To identify acute and nonacute inpatient discharges:

1\.	Identify all acute and nonacute inpatient stays \(Inpatient Stay Value Set\)\.

2\.	Identify the discharge date for the stay\.

The denominator for this measure is based on discharges, not on members\. If members have more than one discharge, include all discharges on or between January 1 and December 1 of the measurement year\.

*Observation stays that precede the inpatient stay*

Do not adjust the admit date if the discharge is preceded by an observation stay; use the admit date from the acute or nonacute inpatient stay\. 

*Readmission or direct transfer*

If the discharge is followed by a readmission or direct transfer to an acute or nonacute inpatient care setting on the date of discharge through 30 days after discharge \(31 days total\), use the admit date from the first admission and the discharge date from the last discharge\. To identify readmissions and direct transfers during the 31\-day period:

1. Identify all acute and nonacute inpatient stays \(Inpatient Stay Value Set\)\.
2. Identify the admission date for the stay \(the admission date must occur during the 31\-day period\)\.
3. Identify the discharge date for the stay \(the discharge date is the event date\)\.

Exclude both the initial and the readmission/direct transfer discharge if the last discharge occurs after December 1 of the measurement year\.

If the admission date and the discharge date for an acute inpatient stay occur between the admission and discharge dates for a nonacute inpatient stay, include only the nonacute inpatient discharge\. To identify acute inpatient discharges:

1. Identify all acute and nonacute inpatient stays \(Inpatient Stay Value Set\)\.
2. Exclude nonacute inpatient stays \(Nonacute Inpatient Stay Value Set\)\.
3. Identify the admission date for the stay\.
4. Identify the discharge date for the stay\.

To identify nonacute inpatient discharges:

1. Identify all acute and nonacute inpatient stays \(Inpatient Stay Value Set\)\.
2. Confirm the stay was for nonacute care based on the presence of a nonacute code \(Nonacute Inpatient Stay Value Set\)\.
3. Identify the admission date for the stay\.
4. Identify the discharge date for the stay\.

__Note: __If a member remains in an acute or nonacute facility through December 1 of the measurement year, a discharge is not included in the measure for this member, but the organization must have a method for identifying the member’s status for the 

remainder of the measurement year, and may not assume the member remained admitted based only on the absence of a discharge before December 1\. 

If the organization is unable to confirm the member remained in the acute or nonacute care setting through December 1, disregard the readmission or direct transfer and use the initial discharge date\.

Required exclusions

Members who meet either of the following criteria:

- Members who use hospice services \(Hospice Encounter Value Set; Hospice Intervention Value Set\) or elect to use a hospice benefit any time during the measurement year\. Organizations that use the Monthly Membership Detail Data File to identify these members must use only the run date of the file to determine if the member elected to use a hospice benefit during the measurement year\. 
- Members who die any time during the measurement year\. 

Administrative Specification

Denominator

The eligible population\.

Numerators

*Notification of Inpatient Admission*

Administrative reporting is not available for this indicator\.

*Receipt of Discharge Information*

Administrative reporting is not available for this indicator\.

*Patient Engagement *  
*After Inpatient Discharge*

Patient engagement provided within 30 days after discharge\. Do not include patient engagement that occurs on the date of discharge\. The following meet criteria for patient engagement:

- An outpatient visit, telephone visit, e\-visit or virtual check\-in \(Outpatient and Telehealth Value Set\)\.
- Transitional care management services \(Transitional Care Management Services Value Set\)\. 

*Medication Reconciliation Post\-Discharge*

Medication reconciliation conducted by a prescribing practitioner, clinical pharmacist, physician assistant or registered nurse on the date of discharge through 30 days after discharge \(31 total days\)\. Either of the following meet criteria:

- Medication Reconciliation Encounter Value Set\.
- Medication Reconciliation Intervention Value Set\. Do not include codes with a modifier \(CPT CAT II Modifier Value Set\)\.

Hybrid Specification

Denominator

A systematic sample drawn from the eligible population\. 

The denominator is based on discharges, not on members\. Members may appear more than once in the sample\.

Organizations may reduce the sample size based only on the prior year’s audited, product line\-specific rate for the lowest rate of all TRC indicators\.

Refer to the *Guidelines for Calculations and Sampling* for information on reducing the sample size\.

Identifying the medical record

Documentation in any outpatient medical record that is accessible to the PCP or ongoing care provider is eligible for use in reporting\.

Numerators

*Notification of Inpatient Admission*

Documentation of receipt of notification of inpatient admission on the day of admission or on the day of admission through 2 days after the admission \(3 total days\)\.

Administrative

Administrative reporting is not available for this indicator\.

Medical record

Documentation in the outpatient medical record must include evidence of receipt of notification of inpatient admission on the day of admission through 2 days after the admission \(3 total days\)\. Evidence that the information was integrated in the appropriate medical record and is accessible to the PCP or ongoing care provider on the day of admission through 2 days after admission \(3 total days\) meets criteria\.

Documentation in the outpatient medical record must include evidence of receipt of notification of inpatient admission that includes evidence of the date when the documentation was received\. Any of the following examples meet criteria:

- Communication between inpatient providers or staff and the member’s PCP or ongoing care provider \(e\.g\., phone call, email, fax\)\.
- Communication about admission between emergency department and the member’s PCP or ongoing care provider \(e\.g\., phone call, email, fax\)\.
- Communication about admission to the member’s PCP or ongoing care provider through a health information exchange; an automated admission, or discharge and transfer \(ADT\) alert system\.
- Communication about admission with the member’s PCP or ongoing care provider through a shared electronic medical record \(EMR\) system\. When using a shared EMR system, documentation of a “received date” is not required to meet criteria\. Evidence that the information was filed integrated in the EMR and is accessible to the PCP or ongoing care provider on the day of admission through 2 days after the admission \(3 total days\) meets criteria\.
- Communication about admission to the member’s PCP or ongoing care provider from the member’s health plan\.
- Indication that the member’s PCP or ongoing care provider admitted the member to the hospital\.
- Indication that a specialist admitted the member to the hospital and notified the member’s PCP or ongoing care provider\.
- Indication that the PCP or ongoing care provider placed orders for tests and treatments any time during the member’s inpatient stay\.
- Documentation that the PCP or ongoing care provider performed a preadmission exam or received communication about a planned inpatient admission\. 
- The time frame for communicating the planned inpatient admission is not limited to the day of admission through 2 days after the admission   
\(3 total days\); documentation that the PCP or ongoing care provider performed a preadmission exam or received notification of a planned admission prior to the admission date also meets criteria\. 
- The planned admission documentation or preadmission exam must clearly pertain to the denominator event\.

__Note:__ When an ED visit results in an inpatient admission, notification that a provider sent the member to the ED does not meet criteria\. Evidence that the PCP or ongoing care provider communicated with the ED about the admission meets criteria\.

*Receipt of Discharge Information*

Documentation of receipt of discharge information on the day of discharge through 2 days after the discharge \(3 total days\)\.

Administrative

Administrative reporting is not available for this indicator\.

Medical record

Documentation in the outpatient medical record must include evidence of receipt of discharge information on the day of discharge through 2 days after the discharge \(3 total days\) with evidence of the date when the documentation was received\. Evidence that the information was integrated in the appropriate medical record and is accessible to the PCP or ongoing care provider on the day of discharge through 2 days after discharge \(3 total days\) meets criteria\.

Discharge information may be included in, but not limited to, a discharge summary or summary of care record or be located in structured fields in an EHR\. At a minimum, the discharge information must include all of the following:

- The practitioner responsible for the member’s care during the inpatient stay\.
- Procedures or treatment provided\.
- Diagnoses at discharge\.
- Current medication list\. 
- Testing results, or documentation of pending tests or no tests pending\. 
- Instructions for patient care post\-discharge\. 

__Note:__ If the PCP or ongoing care provider is the discharging provider, the discharge information must be documented in the medical record on the day of discharge through 2 days after the discharge \(3 total days\)\. 

When using a shared EMR system, documentation of a “received date” in the EMR is not required to meet criteria\. Evidence that the information was filed integrated in the EMR and is accessible to the PCP or ongoing care provider on the day of discharge through 2 days after the discharge \(3 total days\) meets criteria\. 

*Patient Engagement After Inpatient Discharge*

Documentation of patient engagement \(e\.g\., office visits, visits to the home, or telehealth\) provided within 30 days after discharge\. Do not include patient engagement that occurs on the date of discharge\.

Administrative

Refer to *Administrative Specification* to identify positive numerator hits from administrative data\.

Medical record

Documentation in the outpatient medical record must include evidence of patient engagement within 30 days after discharge\. Any of the following meet criteria:

- An outpatient visit, including office visits and home visits\. 
- A telephone visit\.
- A synchronous telehealth visit where real\-time interaction occurred between the member and provider using audio and video communication\. 
- An e\-visit or virtual check\-in \(asynchronous telehealth where two\-way interaction, which was not in real\-time, occurred between the member and provider\)\. 

__Note: __If the member is unable to communicate with the provider, interaction between the member’s caregiver and the provider meets criteria\.

*Medication Reconciliation Post\-Discharge*

Medication reconciliation conducted by a prescribing practitioner, clinical pharmacist, physician assistant or registered nurse, as documented through either administrative data or medical record review on the date of discharge through 30 days after discharge \(31 total days\)\.

Administrative

Refer to *Administrative Specification* to identify positive numerator hits from administrative data\.

Medical record

Documentation in the outpatient medical record must include evidence of medication reconciliation and the date when it was performed\. Any of the following meet criteria:

- Documentation of the current medications with a notation that the provider reconciled the current and discharge medications\.
- Documentation of the current medications with a notation that references the discharge medications \(e\.g\., no changes in medications since discharge, same medications at discharge, discontinue all discharge medications\)\.
- Documentation of the member’s current medications with a notation that the discharge medications were reviewed\.
- Documentation of a current medication list, a discharge medication list and notation that both lists were reviewed on the same date of service\.
- Documentation of the current medications with evidence that the member was seen for post\-discharge hospital follow\-up with evidence of medication reconciliation or review\. Evidence that the member was seen for post\-discharge hospital follow\-up requires documentation that indicates the provider was aware of the member’s hospitalization or discharge\.
- Documentation in the discharge summary that the discharge medications were reconciled with the most recent medication list in the outpatient medical record\. There must be evidence that the discharge summary was filed in the outpatient chart on the date of discharge through 30 days after discharge \(31 total days\)\.
- Notation that no medications were prescribed or ordered upon discharge\. 

*Note*

- *The following notations or examples of documentation do not count as numerator compliant:*
- *Notification of Inpatient Admission and Receipt of Discharge Information:*
- *Documentation that the member or the member’s family notified the member’s PCP or ongoing care provider of the admission or discharge\.*
- *Documentation of notification that does not include a time frame or date when the documentation was received\.*
- *Medication Reconciliation Post\-Discharge: *
- *The following examples *\(without a reference to “hospitalization,” “admission” or “inpatient stay”\) *are not considered evidence that the provider was aware of the member’s hospitalization or discharge:*
- *Documentation of “post\-op/surgery follow\-up\.” *
- *Documentation only of a procedure that is typically inpatient \(e\.g\. open\-heart surgery\)\. *
- *Documentation indicating that the visit was with the same provider who admitted the member or who performed the surgery\.*
- *The Medication Reconciliation Post\-Discharge numerator assesses whether medication reconciliation occurred\. It does not attempt to assess the quality of the medication list documented in the medical record or the process used to document the most recent medication list in the medical record\.*
- *The denominator is based on the discharge date found in administrative/claims data, but organizations may use other systems \(including data found during medical record review\) to identify data errors and make corrections\.*
- *If a different discharge date is found in the medical record, and the organization chooses to use that date, the organization must assess all indicators using the updated discharge date, including those that were previously compliant based on administrative data\.*
- *Refer to Appendix 3 for the definition of *PCP* and *ongoing care provider*\.*
- *A medication reconciliation performed without the member present meets criteria\.*

<a id="_Hlk72301832"></a><a id="_Hlk72301804"></a>__Data Elements for Reporting __

Organizations that submit HEDIS data to NCQA must provide the following data elements\.

__*Table TRC\-3: Data Elements for Transitions of Care*__

__Metric__

__Age__

__Data Element __

__Reporting Instructions__

__A__

MedicationReconciliationPostDischarge

18\-64

CollectionMethod

For each Metric, repeat per Stratification

ü

PatientEngagementAfterInpatientDischarge

65\+

EligiblePopulation__\*__

For each Metric and Stratification

ü

NotificationInpatientAdmission

Total

ExclusionAdminRequired__\*†__

For each Metric and Stratification

ü

ReceiptDischargeInformation

NumeratorByAdminElig__†__

For each Metric and Stratification

CYAR__†__

Only for Total \(Percent\)

MinReqSampleSize

For each Metric, repeat per Stratification

OversampleRate

For each Metric, repeat per Stratification

OversampleRecordsNumber

\(Count\)

ExclusionValidDataErrors

For each Metric, repeat per Stratification

ExclusionEmployeeOrDep

For each Metric, repeat per Stratification

OversampleRecsAdded

For each Metric, repeat per Stratification

Denominator

For each Stratification, repeat per Metric

NumeratorByAdmin__†__

For each Metric and Stratification

ü

NumeratorByMedicalRecords

For each Metric and Stratification

NumeratorBySupplemental

For each Metric and Stratification

ü

Rate

\(Percent\)

ü

<a id="_Hlk72301854"></a>__\*__Repeat the EligiblePopulation and ExclusionAdminRequired values for metrics using the administrative method\.

__†__These data elements are only reported or calculated for the MedicationReconciliationPostDischarge and PatientEngagementAfterInpatientDischarge Metrics\.

__Rules for Allowable Adjustments of HEDIS__

The “Rules for Allowable Adjustments of HEDIS” \(the “Rules”\) describe how NCQA’s HEDIS measure specifications can be adjusted for other populations, if applicable\. The Rules, reviewed and approved by NCQA measure experts, provide for expanded use of HEDIS measures without changing their clinical intent\. 

__Adjusted HEDIS measures may not be used for HEDIS health plan reporting\. __

### Rules for Allowable Adjustments of Transitions of Care

__NONCLINICAL COMPONENTS__

__Eligible Population__

__Adjustments Allowed \(Yes/No\)__

__Notes__

Product lines

Yes

Organizations are not required to use product line criteria; product lines may be combined and all \(or no\) product line criteria may be used\.

Ages

Yes

Age determination dates may be changed \(e\.g\., select, “age as of June 30”\)\.

Changing the denominator age range is allowed\. 

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

Only events that contain \(or map to\) codes in the value sets may be used to identify the eligible population for each rate\. The value sets and logic may not be changed\.

__*Note:*__* Organizations may choose alternate measurement\-period date ranges\. *

*Organizations may assess at the member level \(vs\. discharge level\) by applying measure logic appropriately \(i\.e\., percentage of members with documentation of medication reconciliation after each discharge\)\.*

__Denominator Exclusions__

__Adjustments Allowed \(Yes/No\)__

__Notes__

Required exclusions

Yes

The hospice and deceased member exclusions are not required\. Refer to *Exclusions* in the *Guidelines for the Rules for Allowable Adjustments*\.

__Numerator Criteria__

__Adjustments Allowed \(Yes/No\)__

__Notes__

- Notification of Inpatient Admission
- Receipt of Discharge Information

No

Allowable adjustments are not permitted for these components of the Transitions of Care measure\. 

- Patient Engagement After Inpatient Discharge
- Medication Reconciliation Post\-Discharge

No

Value sets and logic may not be changed\.

