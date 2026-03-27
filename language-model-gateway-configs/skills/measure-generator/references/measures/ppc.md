## <a id="Prenatal_Postpartum_Care_PPC"></a><a id="_Toc400546165"></a><a id="_Toc74826751"></a><a id="_Toc171403034"></a><a id="PPC"></a>Prenatal and Postpartum Care \(PPC\)

Summary of Changes to HEDIS MY 2025

- Removed the data source reporting requirement from the race and ethnicity stratification\. 

Description 

The percentage of deliveries of live births on or between October 8 of the year prior to the measurement year and October 7 of the measurement year\. For these members, the measure assesses the following facets of prenatal and postpartum care:

- *Timeliness of Prenatal Care\. *The percentage of deliveries that received a prenatal care visit in the first trimester on or before the enrollment start date or within 42 days of enrollment in the organization\.
- *Postpartum Care\. *The percentage of deliveries that had a postpartum visit on or between 7 and   
84 days after delivery\.

Definitions

First trimester

280–176 days prior to delivery \(or estimated delivery date \[EDD\]\)\.

Eligible Population

Product lines

Commercial, Medicaid \(report each product line separately\)\.

Stratification

For each product line, report the following stratifications by race and total, and stratifications by ethnicity and total: 

- *Race:*
- American Indian or Alaska Native\.
- Asian\.
- Black or African American\.
- Native Hawaiian or Other Pacific Islander\.
- White\.
- Some Other Race\.
- Two or More Races\.
- Asked But No Answer\.
- Unknown\.
- Total\. 
- *Ethnicity:*
- Hispanic or Latino\.
- Not Hispanic or Latino\.
- Asked But No Answer\.
- Unknown\.
- Total\.

__Note: __Stratifications are mutually exclusive, and the sum of all categories in each stratification is the total population\.

Age

None specified\.

Continuous enrollment

43 days prior to delivery through 60 days after delivery\.

Allowable gap

None\.

Anchor date

Date of delivery\. 

Benefit

Medical\.

Event/diagnosis

Live birth deliveries on or between October 8 of the year prior to the measurement year and October 7 of the measurement year\. Include deliveries that occur in any setting\. 

Follow the steps below to identify the eligible population, which is the denominator for both rates\.

*Step 1*

Identify deliveries\. Identify all members with a delivery \(Deliveries Value Set\) on or between October 8 of the year prior to the measurement year and October 7 of the measurement year\.

__Note:__ The intent is to identify the date of delivery \(the date of the “procedure”\)\. If the date of delivery cannot be interpreted on the claim, use the date of service or, for inpatient claims, the date of discharge\. 

*Step 2*

Remove non\-live births \(Non Live Births Value Set\)\. 

*Step 3*

Identify continuous enrollment\. Determine if enrollment was continuous 43 days prior to delivery through 60 days after delivery, with no gaps\.

*Step 4*

Remove multiple deliveries in a 180\-day period\. If a member has more than one delivery in a 180\-day period, include only the first eligible delivery\. Then, if applicable include the next delivery that occurs after the 180\-day period\. Identify deliveries chronologically, including only one per 180\-day period\.

__Note: __The denominator for this measure is based on deliveries, not on members\. All eligible deliveries that were not removed in steps 1–4 remain in the denominator\. 

Required exclusions

Exclude members who meet either of the following criteria:

- Members who use hospice services \(Hospice Encounter Value Set; Hospice Intervention Value Set\) or elect to use a hospice benefit any time during the measurement year\. Organizations that use the Monthly Membership Detail Data File to identify these members must use only the run date of the file to determine if the member elected to use a hospice benefit during the measurement year\. 
- Members who die any time during the measurement year\.

Administrative Specification

Denominator

The eligible population\. 

Numerator

*Timeliness of Prenatal Care*

A prenatal visit during the required time frame\. Follow the steps below to identify numerator compliance\. 

*Step 1*

Identify members who were continuously enrolled \(with no gaps\) from at least 219 days before delivery \(or EDD\) through 60 days after delivery\. 

These members must have a prenatal visit during the first trimester\. 

*Step 2*

Identify members who were not continuously enrolled from at least 219 days before delivery \(or EDD\) through 60 days after delivery\.

These members must have a prenatal visit any time during the period that begins 280 days prior to delivery and ends 42 days after their enrollment start date\. 

Do not count visits that occur on or after the date of delivery\. Visits that occur prior to the member’s enrollment start date during the pregnancy meet criteria\. 

*Step 3*

Identify prenatal visits that occurred during the required timeframe \(the time frame identified in step 1 or 2\)\. Any of the following, where the practitioner type is an OB/GYN or other prenatal care practitioner or PCP, meet criteria for a prenatal visit:

- A bundled service \(Prenatal Bundled Services Value Set\) where the organization can identify the date when prenatal care was initiated \(because bundled service codes are used on the date of delivery, these codes may be used only if the claim form indicates when prenatal care was initiated\)\. 
- A visit for prenatal care \(Stand Alone Prenatal Visits Value Set\)\. Do not include codes with a modifier \(CPT CAT II Modifier Value Set\)\. 
- A prenatal visit \(Prenatal Visits Value Set\) __*with*__ a pregnancy\-related diagnosis code \(Pregnancy Diagnosis Value Set\)\. 

*Postpartum Care*

A postpartum visit on or between 7 and 84 days after delivery\. Any of the following meet criteria:

- A postpartum visit \(Postpartum Care Value Set\)\. Do not include codes with a modifier \(CPT CAT II Modifier Value Set\)\. 
- An encounter for postpartum care \(Encounter for Postpartum Care Value Set\)\. Do not include laboratory claims \(claims with POS code 81\)\.
- Cervical cytology \(Cervical Cytology Lab Test Value Set; Cervical Cytology Result or Finding Value Set\)\.
- A bundled service \(Postpartum Bundled Services Value Set\) where the organization can identify the date when postpartum care was rendered \(because bundled service codes are used on the date of delivery, not on the date of the postpartum visit, these codes may be used only if the claim form indicates when postpartum care was rendered\)\.

Exclude services provided in an acute inpatient setting \(Acute Inpatient Value Set; Acute Inpatient POS Value Set\)\. 

__Note:__ The practitioner requirement only applies to the Hybrid Specification\. The organization is not required to identify practitioner type in administrative data\.

Hybrid Specification

Denominator

A systematic sample drawn from the eligible population for each product line\. 

Organizations may reduce the sample size using the current year’s administrative rate or the prior year’s audited, product line\-specific rate for the lower of the two indicators\. 

Refer to the *Guidelines for Calculations and Sampling* for information on reducing the sample size\.

Numerator

*Timeliness of Prenatal Care*

A prenatal visit during the required time frame\. Refer to *Administrative Specification* to identify the required time frame for each member based on the date of enrollment in the organization and the gaps in enrollment during the pregnancy\.

Administrative

Refer to *Administrative Specification* to identify positive numerator hits from the administrative data\.

Medical record

Prenatal care visit to an OB/GYN or other prenatal care practitioner, or PCP\. For visits to a PCP, a diagnosis of pregnancy must be present\. Documentation in the medical record must include a note indicating the date when the prenatal care visit occurred and evidence of *one* of the following\.

- Documentation indicating the member is pregnant or references to the pregnancy; for example:
- Documentation in a standardized prenatal flow sheet, __*or*__
- Documentation of last menstrual period \(LMP\), EDD or gestational age, __*or*__
- A positive pregnancy test result, __*or*__
- Documentation of gravidity and parity, __*or *__
- Documentation of complete obstetrical history, __*or*__
- Documentation of prenatal risk assessment and counseling/education\.
- A basic physical obstetrical examination that includes auscultation for fetal heart tone, __*or*__ pelvic exam with obstetric observations, __*or*__ measurement of fundus height \(a standardized prenatal flow sheet may be used\)\.
- Evidence that a prenatal care procedure was performed, such as:
- Screening test in the form of an obstetric panel \(must include all of the following: hematocrit, differential WBC count, platelet count, hepatitis B surface antigen, rubella antibody, syphilis test, RBC antibody screen, Rh and ABO blood typing\), __*or*__
- TORCH antibody panel alone, __*or*__ 

- A rubella antibody test/titer with an Rh incompatibility \(ABO/Rh\) blood typing, __*or*__
- Ultrasound of a pregnant uterus\. 

*Postpartum Care*

A postpartum visit on or between 7 and 84 days after delivery, as documented through either administrative data or medical record review\. 

Administrative

Refer to *Administrative Specification *to identify positive numerator hits from the administrative data\.

Medical record

Postpartum visit to an OB/GYN or other prenatal care practitioner, or PCP on or between 7 and 84 days after delivery\. Do not include postpartum care provided in an acute inpatient setting\. 

Documentation in the medical record must include a note indicating the date when a postpartum visit occurred and *one* of the following:

- Pelvic exam\. 
- Evaluation of weight, BP, breasts and abdomen\.
- Notation of “breastfeeding” is acceptable for the “evaluation of breasts” component\.
- Notation of postpartum care, including, but not limited to:
- Notation of “postpartum care,” “PP care,” “PP check,” “6\-week check\.”
- A preprinted “Postpartum Care” form in which information was documented during the visit\.
- Perineal or cesarean incision/wound check\.
- Screening for depression, anxiety, tobacco use, substance use disorder, or preexisting mental health disorders\.
- Glucose screening for members with gestational diabetes\.
- Documentation of any of the following topics:
- Infant care or breastfeeding\.
- Resumption of intercourse, birth spacing or family planning\. 
- Sleep/fatigue\.
- Resumption of physical activity\. 
- Attainment of healthy weight\.

*Note*

- *Criteria for identifying prenatal care for members who were not enrolled during the first trimester allow more flexibility than criteria for members who were enrolled\. *
- *For members who were enrolled at least 219 days before delivery, the organization has sufficient opportunity to provide prenatal care by the end of the first trimester\.*
- *For members who were not enrolled at least 219 days before delivery, the organization has sufficient opportunity to provide prenatal care within 42 days after enrollment\.*
- *Services that occur over multiple visits count toward this measure if all services are within the time frame established in the measure\. Ultrasound and lab results alone are not considered a visit; they must be combined with an office visit with an appropriate practitioner in order to count for this measure\.*
- *For each member, the organization must use one date \(date of delivery or EDD\) to define the start and end of the first trimester\. If multiple EDDs are documented, the organization must define a method to determine which EDD to use, and use that date consistently\. If the organization elects to use EDD, and the EDD is not on or between October 8 of the year prior to the measurement year and October 7 of the measurement year, the member is removed as a valid data error and replaced by the next member of the oversample\. The LMP may not be used to determine the first trimester\.*
- *The organization may use EDD to identify the first trimester for the Timeliness of Prenatal Care rate and use the date of delivery for the Postpartum Care rate\.*
- *A Pap test does not count as a prenatal care visit for the administrative and hybrid specification of the Timeliness of Prenatal Care rate, but is acceptable for the Postpartum Care rate as evidence of a pelvic exam\. A colposcopy alone is not numerator compliant for either rate\.*
- *The intent is that a prenatal visit is with a PCP or OB/GYN or other prenatal care practitioner\. Ancillary services \(lab, ultrasound\) may be delivered by an ancillary provider\. Nonancillary services \(e\.g\., fetal heart tone, prenatal risk assessment\) must be delivered by the required provider type\.*
- *The intent is to assess whether prenatal and preventive care was rendered on a routine, outpatient basis rather than assessing treatment for emergent events\.*
- *Refer to Appendix 3 for the definition of *PCP* and *OB/GYN and other prenatal care practitioner\.
- *For both rates and for both Administrative and Hybrid data collection methods, services provided during a telephone visit, e\-visit or virtual check\-in are eligible for use in reporting\. *

__Data Elements for Reporting __

Organizations that submit HEDIS data to NCQA must provide the following data elements\.

__*Table PPC\-A\-1/2: Data Elements for Prenatal and Postpartum Care*__

__Metric__

__Data Element __

__Reporting Instructions__

__A__

TimelinessPrenatalCare

CollectionMethod

For each Metric

ü

PostpartumCare

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

Rate

\(Percent\)

ü

__*Table PPC\-B\-1/2: Data Elements for Prenatal and Postpartum Care: Stratifications by Race*__

__Metric__

TimelinessPrenatalCare

PostpartumCare

__Race__

__Data Element__

__Reporting Instructions__

__A__

AmericanIndianOrAlaskaNative

CollectionMethod

For each Metric, repeat per Stratification

ü

Asian

EligiblePopulation__\*__

For each Stratification, repeat per Metric

ü

BlackOrAfricanAmerican 

Denominator

For each Stratification, repeat per Metric

NativeHawaiianOrOtherPacificIslander 

Numerator

For each Metric and Stratification

ü

White

Rate

\(Percent\)

ü

SomeOtherRace

TwoOrMoreRaces

AskedButNoAnswer

Unknown

__*Table PPC\-C\-1/2: Data Elements for Prenatal and Postpartum Care: Stratifications by Ethnicity*__

__Metric__

__Ethnicity__

__Data Element__

__Reporting Instructions__

__A__

TimelinessPrenatalCare

HispanicOrLatino

CollectionMethod

For each Metric, repeat per Stratification

ü

PostpartumCare

NotHispanicOrLatino

EligiblePopulation__\*__

For each Stratification, repeat per Metric

ü

AskedButNoAnswer

Denominator

For each Stratification, repeat per Metric

Unknown

Numerator

For each Metric and Stratification

ü

Rate

\(Percent\)

ü

__\*__Repeat the EligiblePopulation and ExclusionAdminRequired values for metrics using the Administrative Method\.

Rules for Allowable Adjustments of HEDIS

The “Rules for Allowable Adjustments of HEDIS” \(the “Rules”\) describe how NCQA’s HEDIS measure specifications can be adjusted for other populations, if applicable\. The Rules, reviewed and approved by NCQA measure experts, provide for expanded use of HEDIS measures without changing their clinical intent\. 

__Adjusted HEDIS measures may not be used for HEDIS health plan reporting\. __

### Rules for Allowable Adjustments of Prenatal and Postpartum Care

__NONCLINICAL COMPONENTS__

__Eligible Population__

__Adjustments Allowed \(Yes/No\)__

__Notes__

Product lines

Yes

Organizations are not required to use product line criteria; product lines may be combined and all \(or no\) product line criteria may be used\.

Ages

NA

There are no ages specified in this measure\.

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

Only events that contain \(or map to\) codes in the value sets may be used to identify visits\. The value sets and logic may not be changed\.

Organizations may not change the logic but may change the delivery date and account for the impact on other date\-dependent events\.

__*Note:*__* Organizations may assess at the member level \(vs\. discharge level\) by applying measure logic appropriately \(i\.e\., percentage of members with deliveries\)\.*

__Denominator Exclusions__

__Adjustments Allowed \(Yes/No\)__

__Notes__

Required exclusions

Yes

The hospice and deceased member exclusions are not required\. Refer to *Exclusions* in the *Guidelines for the Rules for Allowable Adjustments*\.

__Numerator Criteria__

__Adjustments Allowed \(Yes/No\)__

__Notes__

- Timeliness of Prenatal Care
- Postpartum Care

No

Value sets and logic may not be changed\. If the delivery\-date range is changed, all numerator events must be measured in relation to the new range\. 

