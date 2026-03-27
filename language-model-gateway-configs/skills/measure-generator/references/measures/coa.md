## <a id="Care_for_Older_COA"></a><a id="_Toc400546115"></a><a id="_Toc74750487"></a><a id="_Toc171402972"></a><a id="COA"></a>Care for Older Adults \(COA\)

Summary of Changes to HEDIS MY 2025

- Removed the Pain Assessment indicator\.

Description

The percentage of adults 66 years of age and older who had both of the following during the measurement year:

- Medication Review\.
- Functional Status Assessment\.

Definitions

Medication list

A list of the member’s medications in the medical record\. The medication list may include medication names only or may include medication names, dosages and frequency, over\-the\-counter \(OTC\) medications and herbal or supplemental therapies\.

Medication review

A review of all a member’s medications, including prescription medications, OTC medications and herbal or supplemental therapies\.

Standardized tool

A set of structured questions that elicit member information\. May include person\-reported outcome measures, screening or assessment tools or standardized questionnaires developed by the health plan to assess risks and needs\.

Eligible Population

Product line

Medicare \(only SNP and MMP benefit packages\)\.

Ages

66 years and older as of December 31 of the measurement year\.

Continuous enrollment

The measurement year\. 

Allowable gap

No more than one gap in continuous enrollment of up to 45 days during the measurement year\.

Anchor date

December 31 of the measurement year\.

Benefit

Medical\.

Event/diagnosis

None\. 

Required exclusions

Exclude members who meet either of the following criteria:

- Members who use hospice services \(Hospice Encounter Value Set; Hospice Intervention Value Set\) or elect to use a hospice benefit any time during the measurement year\. Organizations that use the Monthly Membership Detail Data File to identify these members must use only the run date of the file to determine if the member elected to use a hospice benefit during the measurement year\. 
- Members who die any time during the measurement year\. 

Administrative Specification 

__Denominator__

The eligible population\.

Numerators

__*Medication   
Review*__

Either of the following meets criteria\.

- Both of the following during the same visit during the measurement year where the provider type is a prescribing practitioner or clinical pharmacist\. Do not include codes with a modifier \(CPT CAT II Modifier Value Set\)\. 
- At least one medication review \(Medication Review Value Set\)\.
- The presence of a medication list in the medical record \(Medication List Value Set\)\.
- Transitional care management services \(Transitional Care Management Services Value Set\) during the measurement year\.

Do not include services provided in an acute inpatient setting \(Acute Inpatient Value Set; Acute Inpatient POS Value Set\)\. 

__*Functional Status Assessment*__

At least one functional status assessment \(Functional Status Assessment Value Set\) during the measurement year\. Do not include services provided in an acute inpatient setting \(Acute Inpatient Value Set; Acute Inpatient POS Value Set\)\. Do not include codes with a modifier \(CPT CAT II Modifier Value Set\)\.

Hybrid Specification

Denominator

A systematic sample drawn from the eligible population\. Organizations may reduce the sample size using the current year’s administrative rate or the prior year’s audited, product line\-specific rate\. Refer to the *Guidelines for Calculations and Sampling* for information on reducing the sample size\.

Numerators

*Medication Review *

At least one medication review conducted by a prescribing practitioner or clinical pharmacist during the measurement year __*and*__ the presence of a medication list in the medical record, as documented through either administrative data or medical record review\. 

A medication list, signed and dated during the measurement year by the appropriate practitioner type \(prescribing practitioner or clinical pharmacist\), meets criteria \(the practitioner’s signature is considered evidence that the medications were reviewed\)\.

Administrative

Refer to *Administrative Specification* to identify positive numerator hits from administrative data\.

Medical record

Documentation must come from the same medical record and must include one of the following:

- A medication list in the medical record __*and *__evidence of a medication review by a prescribing practitioner or clinical pharmacist and the date when it was performed\. 
- Notation that the member is not taking any medication and the date when it was noted\.

A review of side effects for a single medication at the time of prescription alone is not sufficient\. An outpatient visit is not required to meet criteria\. Do not include medication lists or medication reviews performed in an acute inpatient setting\.

*Functional Status Assessment*

At least one functional status assessment during the measurement year, as documented through either administrative data or medical record review\.

Administrative

Refer to *Administrative Specification* to identify positive numerator hits from administrative data\.

Medical record

Documentation in the medical record must include evidence of a complete functional status assessment and the date when it was performed\.

Notations for a complete functional status assessment must include one of the following: 

- Notation that Activities of Daily Living \(ADL\) were assessed or that at least five of the following were assessed: bathing, dressing, eating, transferring \[e\.g\., getting in and out of chairs\], using toilet, walking\.
- Notation that Instrumental Activities of Daily Living \(IADL\) were assessed or at least four of the following were assessed: shopping for groceries, driving or using public transportation, using the telephone, cooking or meal preparation, housework, home repair, laundry, taking medications, handling finances\. 
- Result of assessment using a standardized functional status assessment tool, not limited to:
- SF\-36®\.
- Assessment of Living Skills and Resources \(ALSAR\)\.
- Barthel ADL Index Physical Self\-Maintenance \(ADLS\) Scale©\. 
- Bayer ADL \(B\-ADL\) Scale\. 
- Barthel Index©\.
- Edmonton Frail Scale©\.
- Extended ADL \(EADL\) Scale\.
- Groningen Frailty Index\.
- Independent Living Scale \(ILS\)\.
- Katz Index of Independence in ADL©\.
- Kenny Self\-Care Evaluation\.
- Klein\-Bell ADL Scale\. 
- Kohlman Evaluation of Living Skills \(KELS\)\.
- Lawton & Brody’s IADL scales©\.
- Patient Reported Outcome Measurement Information System \(PROMIS\) Global or Physical Function Scales©\.

A functional status assessment limited to an acute or single condition, event or body system \(e\.g\., lower back, leg\) does not meet criteria for a comprehensive functional status assessment\.* *The components of the functional status assessment numerator may take place during separate visits within the measurement year\. Do not include comprehensive functional status assessments performed in an acute inpatient setting\.

*Note*

- *Refer to Appendix 3 for the definition of *clinical pharmacist* and *prescribing practitioner*\.*
- *A medication review performed without the member present meets criteria\.*
- *The Functional Status Assessment indicator does not require a specific setting; therefore, services rendered during a telephone visit, e\-visit or virtual check\-in meet criteria\. *

Data Elements for Reporting 

Organizations that submit HEDIS data to NCQA must provide the following data elements\.

__*Table COA\-3: Data Elements for Care for Older Adults*__

__Metric__

__Data Element __

__Reporting Instructions__

__A__

MedicationReview

CollectionMethod

For each Metric

ü

FunctionalStatusAssessment

EligiblePopulation__\*__

For each Metric

ü

ExclusionAdminRequired__\*__

For each Metric

ü

NumeratorByAdminElig

For each Metric

CYAR

\(Percent\)

MinReqSampleSize

Repeat per Metric

OversampleRate

Repeat per Metric

OversampleRecordsNumber

\(Count\)

ExclusionValidDataErrors

Repeat per Metric

ExclusionEmployeeOrDep

Repeat per Metric

OversampleRecsAdded

Repeat per Metric

Denominator

Repeat per Metric

NumeratorByAdmin

For each Metric

ü

NumeratorByMedicalRecords

For each Metric

NumeratorBySupplemental

For each Metric

ü

Rate

\(Percent\)

ü

__\*__Repeat the EligiblePopulation and ExclusionAdminRequired values for metrics using the Administrative Method\.

Rules for Allowable Adjustments of HEDIS

The “Rules for Allowable Adjustments of HEDIS” \(the “Rules”\) describe how NCQA’s HEDIS measure specifications can be adjusted for other populations, if applicable\. The Rules, reviewed and approved by NCQA measure experts, provide for expanded use of HEDIS measures without changing their clinical intent\. 

__Adjusted HEDIS measures may not be used for HEDIS health plan reporting\.__

### Rules for Allowable Adjustments of Care for Older Adults

__NONCLINICAL COMPONENTS__

Eligible Population

Adjustments Allowed \(Yes/No\)

Notes

Product lines

Yes

Organizations are not required to use product line criteria; product lines may be combined and all \(or no\) product line criteria may be used\.

Ages

Yes, with limits

Age determination dates may be changed \(e\.g\., select, “age as of June 30”\)\. 

The denominator age may be changed within the specified age range \(66 years and older\)\. 

The denominator age may be expanded to 18 years of age and older only for dual\-eligible members and Medicaid LTSS members\. 

Continuous enrollment, allowable gap, anchor date

Yes

Organizations are not required to use enrollment criteria; adjustments are allowed\.

Benefit

Yes

Organizations are not required to use a benefit; adjustments are allowed\.

Other

Yes

Organizations may use additional eligible population criteria to focus on an area of interest defined by gender, race, ethnicity, socio\-economic or sociodemographic characteristics, geographic region or another characteristic\. 

__CLINICAL COMPONENTS__

Eligible Population

Adjustments Allowed \(Yes/No\)

Notes

Event/diagnosis

NA

There is no event/diagnosis for this measure\. 

Denominator Exclusions

Adjustments Allowed \(Yes/No\)

Notes

Required exclusions

Yes

The hospice and deceased member exclusions are not required\. Refer to *Exclusions* in the *Guidelines for the Rules for Allowable Adjustments*\.

Numerator Criteria

Adjustments Allowed \(Yes/No\)

Notes

- Medication Review
- Functional Status Assessment

No

Value sets and logic may not be changed\.

