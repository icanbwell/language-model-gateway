## <a id="Persistance_of_BB_PBH"></a><a id="_Toc74815065"></a><a id="_Toc171402981"></a>Persistence of Beta\-Blocker Treatment After a Heart Attack \(PBH\)

Summary of Changes to HEDIS MY 2025

- No changes to this measure\.

Description

The percentage of members 18 years of age and older during the measurement year who were hospitalized and discharged from July 1 of the year prior to the measurement year to June 30 of the measurement year with a diagnosis of AMI and who received persistent beta\-blocker treatment for 180 days \(6 months\) after discharge\.

Definition

Treatment days \(covered days\)

The actual number of calendar days covered with prescriptions within the specified 180\-day measurement interval \(e\.g\., a prescription of a 90\-day supply dispensed on the 100th day will have 81 days counted in the 180\-day interval\)\.

180\-day measurement interval

The 180\-day period that includes the discharge date and the 179 days after discharge\. 

Eligible Population

Product lines

Commercial, Medicaid, Medicare \(report each product line separately\)\.

Ages

18 years and older as of December 31 of the measurement year\.

Continuous enrollment

Discharge date through 179 days after discharge\.

Allowable gap

No more than one gap in enrollment of up to 45 days within the 180 days of the event\. To determine continuous enrollment for a Medicaid beneficiary for whom enrollment is verified monthly, the member may not have more than a 1\-month gap in coverage \(e\.g\., a member whose coverage lapses for 2 months \[60 days\] is not continuously enrolled\)\.

Anchor date

Discharge date\. 

Benefit

Medical and pharmacy\.

Event/diagnosis

An acute inpatient discharge from July 1 of the year prior to the measurement year through June 30 of the measurement year with any diagnosis of AMI \(AMI Value Set\) on the discharge claim\. To identify an acute inpatient discharge:

1\.	Identify all acute and nonacute inpatient stays \(Inpatient Stay Value Set\)\.

2\.	Exclude nonacute inpatient stays \(Nonacute Inpatient Stay Value Set\)\.

3\.	Identify the discharge date for the stay\.

If a member has more than one episode of AMI that meets the event/diagnosis criteria, from July 1 of the year prior to the measurement year through June 30 of the measurement year, include only the first discharge\.

*Direct transfers to an acute inpatient care setting\.* If the member had a direct transfer to an acute inpatient setting \(for any diagnosis\), use the discharge date from the transfer setting, not the initial discharge\. Exclude both the initial discharge and the direct transfer discharge if the transfer discharge occurs after June 30 of the measurement year\. Use the instructions below to identify direct transfers and exclude nonacute inpatient stays using the Nonacute Inpatient Stay Value Set \(step 2\)\.

*Direct transfers to a nonacute inpatient care setting\.* Exclude from the denominator, hospitalizations in which the member had a direct transfer to a nonacute inpatient care setting for any diagnosis\. Use the instructions below to identify direct transfers and confirm the stay was for nonacute inpatient care based on the presence of a nonacute code \(Nonacute Inpatient Stay Value Set\) on the claim\.

A __direct transfer__ is when the discharge date from the first inpatient setting precedes the admission date to a second inpatient setting by one calendar day or less\. For example: 

- An inpatient discharge on June 1, followed by an admission to another inpatient setting on June 1, *is a direct transfer\.*
- An inpatient discharge on June 1, followed by an admission to an inpatient setting on June 2,* is a direct transfer\.*
- An inpatient discharge on June 1, followed by an admission to another inpatient setting on June 3, *is not a direct transfer; *these are two distinct inpatient stays\.

Use the following method to identify admissions to and discharges from inpatient settings\.

1\.	Identify all acute and nonacute inpatient stays \(Inpatient Stay Value Set\)\.

2\.	If needed, identify nonacute inpatient stays \(Nonacute Inpatient Stay Value Set\)\.

3\.	Identify the admission and discharge dates for the stay\.

Required exclusions

Exclude members who meet any of the following criteria:

- Members who use hospice services \(Hospice Encounter Value Set; Hospice Intervention Value Set\) or elect to use a hospice benefit any time during the measurement year\. Organizations that use the Monthly Membership Detail Data File to identify these members must use only the run date of the file to determine if the member elected to use a hospice benefit during the measurement year\. 
- Members who die any time during the measurement year\. 
- Members with a medication dispensing event that indicates a contraindication to beta\-blocker therapy \(Asthma Exclusions Medications List\) any time during the member’s history through the end of the continuous enrollment period\.
- Members with a diagnosis that indicates a contraindication to beta\-blocker therapy \(Beta Blocker Contraindications Value Set\) any time during the member’s history through the end of the continuous enrollment period meet criteria\. Do not include laboratory claims \(claims with POS code 81\)\.

- Medicare members 66 years of age and older as of December 31 of the measurement year who meet either of the following:
- Enrolled in an Institutional SNP \(I\-SNP\) any time on or between July 1 of the year prior to the measurement year and the end of the measurement year\.
- Living long\-term in an institution any time on or between July 1 of the year prior to the measurement year and the end of the measurement year as identified by the LTI flag in the Monthly Membership Detail Data File\. Use the run date of the file to determine if a member had an LTI flag any time on or between July 1 of the year prior to the measurement year and the end of the measurement year\.
- Members 66–80 years of age as of December 31 of the measurement year \(all product lines\) with frailty __and__ advanced illness\. Members must meet __both__ frailty and advanced illness criteria to be excluded: 

1\.	__Frailty\.__ At least two indications of frailty \(Frailty Device Value Set; Frailty Diagnosis Value Set; Frailty Encounter Value Set; Frailty Symptom Value Set\) with different dates of service any time on or between July 1 of the year prior to the measurement year and the end of the measurement year\. Do not include laboratory claims \(claims with POS code 81\)\.

2\.	__Advanced Illness\.__ Either of the following during the measurement year or the year prior to the measurement year: 

- Advanced illness \(Advanced Illness Value Set\) on at least two different dates of service\. Do not include laboratory claims \(claims with POS code 81\)\.
- Dispensed dementia medication \(Dementia Medications List\)\.
- Members 81 years of age and older as of December 31 of the measurement year \(all product lines\) with at least two indications of frailty \(Frailty Device Value Set; Frailty Diagnosis Value Set; Frailty Encounter Value Set; Frailty Symptom Value Set\) with different dates of service any time on or between July 1 of the year prior to the measurement year and the end of the measurement year\. Do not include laboratory claims \(claims with POS code 81\)\.

Asthma Exclusions Medications

Description

Prescription

Bronchodilator combinations

- Budesonide\-formoterol
- Fluticasone\-vilanterol

- Fluticasone\-salmeterol
- Formoterol\-mometasone

Inhaled corticosteroids

- Beclomethasone
- Budesonide
- Ciclesonide

- Flunisolide 
- Fluticasone 
- Mometasone 

__*Dementia Medications*__

__Description__

__Prescription__

Cholinesterase inhibitors

- Donepezil

- Galantamine

- Rivastigmine 

Miscellaneous central nervous system agents

- Memantine

Dementia combinations

- Donepezil\-memantine

Administrative Specification

Denominator

The eligible population\.

Numerator

At least 135 days of treatment with beta\-blockers \(Beta Blocker Medications List\) during the 180\-day measurement interval\. This allows gaps in medication treatment of up to a total of 45 days during the 180\-day measurement interval\. 

Assess for active prescriptions and include days supply that fall within the 180\-day measurement interval\. For members who were on beta\-blockers prior to admission and those who were dispensed an ambulatory prescription during their inpatient stay, factor those prescriptions into adherence rates if the actual treatment days fall within the 180\-day measurement interval\.

Beta Blocker Medications

Description

Prescription

Noncardioselective beta\-blockers

- Carvedilol
- Labetalol
- Nadolol

- Pindolol
- Propranolol

- Timolol 
- Sotalol

Cardioselective beta\-blockers

- Acebutolol
- Atenolol

- Betaxolol
- Bisoprolol

- Metoprolol
- Nebivolol

Antihypertensive combinations

- Atenolol\-chlorthalidone
- Bendroflumethiazide\-nadolol
- Bisoprolol\-hydrochlorothiazide

- Hydrochlorothiazide\-metoprolol
- Hydrochlorothiazide\-propranolol

__Data Elements for Reporting __

Organizations that submit HEDIS data to NCQA must provide the following data elements\.

### Table PBH\-1/2/3: Data Elements for Persistence of Beta\-Blocker Treatment After a Heart Attack

__Metric__

__Data Element__

__Reporting Instructions__

BetaBlockerPersistence

Benefit

Metadata

EligiblePopulation 

Report once

ExclusionAdminRequired

Report once

NumeratorByAdmin

Report once

NumeratorBySupplemental

Report once

Rate

\(Percent\)

Rules for Allowable Adjustments of HEDIS

The “Rules for Allowable Adjustments of HEDIS” \(the “Rules”\) describe how NCQA’s HEDIS measure specifications can be adjusted for other populations, if applicable\. The Rules, reviewed and approved by NCQA measure experts, provide for expanded use of HEDIS measures without changing their clinical intent\. 

__Adjusted HEDIS measures may not be used for HEDIS health plan reporting\. __

### Rules for Allowable Adjustments of Persistence of Beta\-Blocker Treatment After a Heart Attack

__NONCLINICAL COMPONENTS__

__Eligible Population__

__Adjustments Allowed \(Yes/No\)__

__Notes__

Product lines

Yes

Organizations are not required to use product line criteria; product lines may be combined and all \(or no\) product line criteria may be used\.

Ages

Yes, with limits

Age determination dates may be changed \(e\.g\., select, “age as of June 30”\)\. 

The denominator age may* *be changed if the age is within the specified age range \(18 years and older\)\.

The denominator age may not be expanded\.

Continuous enrollment, allowable gap, anchor date

Yes

Organizations are not required to use enrollment criteria; adjustments are allowed\.

__*Note: *__*Adjusting the anchor date/discharge date will affect the treatment days and the 180\-day measurement interval calculations\.*

Benefit

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

Only events that contain \(or map to\) codes in the medication lists and value sets may be used to identify discharges\. Medication lists, value sets and logic may not be changed\.

__Denominator Exclusions__

__Adjustments Allowed \(Yes/No\)__

__Notes__

Required exclusions

Yes, with limits

Apply required exclusions according to specified value sets\. 

The hospice, deceased member, I\-SNP, LTI, frailty and advanced illness exclusions are not required\. Refer to *Exclusions* in the *Guidelines for the Rules for Allowable Adjustments*\.

__Numerator Criteria__

__Adjustments Allowed \(Yes/No\)__

__Notes__

Treatment Days/ Persistence of Beta\-Blockers

No

Value sets and logic may not be changed\.

