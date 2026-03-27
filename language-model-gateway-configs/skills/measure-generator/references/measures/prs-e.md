## <a id="Prenatal_Immunization_Status_PRSE"></a><a id="_Toc74830501"></a><a id="_Toc171403077"></a>Prenatal Immunization Status \(PRS\-E\)\*

__\*Developed with support from the Department of Health and Human Services \(DHHS\), Office of the Assistant Secretary for Health \(OASH\), National Vaccine Program Office \(NVPO\)\.__

Summary of Changes to HEDIS MY 2025

- Removed “Programming Guidance” from the *Characteristics* section\. 
- Removed the *Data criteria \(element level\)* section\. 
- Removed the data source reporting requirement from the race and ethnicity stratification\. 

Description

The percentage of deliveries in the measurement period in which members had received influenza and tetanus, diphtheria toxoids and acellular pertussis \(Tdap\) vaccinations\.

Measurement period

January 1–December 31\.

Clinical recommendation statement

Advisory Committee on Immunization Practices \(ACIP\) clinical guidelines recommend that all women who are pregnant or who might be pregnant in the upcoming influenza season receive inactivated influenza vaccines\. ACIP also recommends that pregnant women receive one dose of Tdap during each pregnancy, preferably during the early part of gestational weeks 27–36, regardless of prior history of receiving Tdap\.

Citations

Murthy, N\., A\.P\. Wodi, V\.V\. McNally, M\.F\. Daley, S\. Cineas\. 2024\. “Advisory Committee on Immunization Practices Recommended Immunization Schedule for Adults Aged 19 Years or Older—United States, 2024\.” *MMWR Morb Mortal Wkly Rep* 73:11–15\. DOI: http://dx\.doi\.org/10\.15585/mmwr\.mm7301a3 

Characteristics

Scoring

Proportion\.

Type

Process\.

Stratification

- Immunization Status: Influenza\.
- Product line:
- Commercial\.
- Medicaid\.
- Race \(for each product line\):
- Race—American Indian or Alaska Native\.
- Race—Asian\.
- Race—Black or African American\.
- Race—Native Hawaiian or Other Pacific Islander\.
- Race—White\.
- Race—Some Other Race\.
- Race—Two or More Races\.

- Race—Asked But No Answer\.
- Race—Unknown\.
- Ethnicity \(for each product line\):
- Ethnicity—Hispanic or Latino\.
- Ethnicity—Not Hispanic or Latino\.
- Ethnicity—Asked But No Answer\.
- Ethnicity—Unknown\.
- Immunization Status: Tdap\.
- Product line:
- Commercial\.
- Medicaid\.
- Race \(for each product line\):
- Race—American Indian or Alaska Native\.
- Race—Asian\.
- Race—Black or African American\.
- Race—Native Hawaiian or Other Pacific Islander\.
- Race—White\.
- Race—Some Other Race\.
- Race—Two or More Races\.
- Race—Asked But No Answer\.
- Race—Unknown\.
- Ethnicity \(for each product line\):
- Ethnicity—Hispanic or Latino\.
- Ethnicity—Not Hispanic or Latino\.
- Ethnicity—Asked But No Answer\.
- Ethnicity—Unknown\.
- Immunization Status: Combination\.
- Product line:
- Commercial\.
- Medicaid\.
- Race \(for each product line\):
- Race—American Indian or Alaska Native\.
- Race—Asian\.
- Race—Black or African American\.
- Race—Native Hawaiian or Other Pacific Islander\.
- Race—White\.
- Race—Some Other Race\.
- Race—Two or More Races\.
- Race—Asked But No Answer\.
- Race—Unknown\.

- Ethnicity \(for each product line\):
- Ethnicity—Hispanic or Latino\.
- Ethnicity—Not Hispanic or Latino\.
- Ethnicity—Asked But No Answer\.
- Ethnicity—Unknown\.

Risk adjustment

None\.

Improvement notation

A higher rate indicates better performance\.

Guidance

__General Rules:__

- The denominator for this measure is based on deliveries, not on members\.
- Initial population: 
- Include deliveries that occur in any setting\.
- Determine the delivery date using the date as of the end of the delivery\. 
- If a member has more than one delivery in a 180\-day period, include only the first eligible delivery\. Then, if applicable, include the next delivery that occurs after the 180\-day period\. Identify deliveries chronologically, including only one per 180\-day period\.

__Note:__ Removal of multiple deliveries in a 180\-day period is based on eligible deliveries\. Assess each delivery for exclusions and participation before removing multiple deliveries in a 180\-day period\.

__Allocation:__  
The member was enrolled with a medical benefit and had no gaps in enrollment throughout the 28 days prior to the delivery date through the delivery date\.

__Reporting:__  
For all plans, the race and ethnicity stratifications are mutually exclusive, and the sum of all categories in each stratification is the total population\.

Definitions

Participation

The identifiers and descriptors for each organization’s coverage used to define members’ eligibility for measure reporting\. Allocation for reporting is based on eligibility during the participation period\.

Participation period

28 days prior to the delivery date through the delivery date\.

Pregnancy episode

Pregnancy start date is calculated by subtracting the gestational age \(in weeks\) at the time of delivery from the delivery date\. Use the last gestational age assessment or diagnosis within 1 day of the start or end of the delivery\.

Initial population

__Initial population 1  
__Deliveries \(Deliveries Value Set\) during the measurement period that meet the following criteria:

- Meet requirements for participation\.
- Have a gestational age assessment \(SNOMED CT code 412726003; value is not null\) or gestational age diagnosis within 1 day of the start or end of the delivery\. A code from any of the following value sets meets criteria for gestational age diagnosis:
- Weeks of Gestation Less Than 37 Value Set\.
- 37 Weeks Gestation Value Set\.
- 38 Weeks Gestation Value Set\.
- 39 Weeks Gestation Value Set\.
- 40 Weeks Gestation Value Set\.
- 41 Weeks Gestation Value Set\.
- 42 Weeks Gestation Value Set\.
- 43 weeks gestation \(ICD\-10\-CM code Z3A\.49\)\.

__Initial population 2  
__Same as the initial population 1\.

__Initial population 3  
__Same as the initial population 1\.

Exclusions

__Exclusions 1__

- Deliveries that occurred at less than 37 weeks gestation\. Length of gestation in weeks is identified by one of two methods:
- Gestational age assessment \(SNOMED CT code 412726003; value <37 weeks\), __*or*__
- Gestational age diagnosis \(Weeks of Gestation Less Than 37 Value Set\)\.
- Exclude all episodes for members who use hospice services \(Hospice Encounter Value Set; Hospice Intervention Value Set\) or elect to use a hospice benefit any time during the measurement period\. Organizations that use the Monthly Membership Detail Data File to identify these members must use only the run date of the file to determine if the member elected to use a hospice benefit during the measurement period\. 
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

__Numerator 1—Immunization Status: Influenza__

- Deliveries where members received an adult influenza vaccine \(Adult Influenza Immunization Value Set; Adult Influenza Vaccine Procedure Value Set\) on or between July 1 of the year prior to the measurement period and the delivery date, __*or*__
- Deliveries where members had anaphylaxis due to the influenza vaccine \(SNOMED CT code 471361000124100\) on or before the delivery date\.

__Numerator 2—Immunization Status: Tdap__

- Deliveries where members received at least one Tdap vaccine \(CVX code 115; Tdap Vaccine Procedure Value Set\) during the pregnancy \(including on the delivery date\), __*or*__
- Deliveries where members had any of the following:
- Anaphylaxis due to the diphtheria, tetanus or pertussis vaccine \(Anaphylaxis Due to Diphtheria, Tetanus or Pertussis Vaccine Value Set\) on or before the delivery date\.
- Encephalitis due to the diphtheria, tetanus or pertussis vaccine \(Encephalitis Due to Diphtheria, Tetanus or Pertussis Vaccine Value Set\) on or before the delivery date\.

__Numerator 3—Immunization Status: Combination  
__Deliveries that met criteria for both numerator 1 __*and*__ numerator 2\.

__Data Elements for Reporting __

Organizations that submit data to NCQA must provide the following data elements\.

__*Table PRS\-E\-A\-1/2 Data Elements for Prenatal Immunization Status*__ 

__Metric__

__Data Element__

__Reporting Instructions__

Influenza

InitialPopulationByEHR

Repeat per Metric

Tdap

InitialPopulationByCaseManagement

Repeat per Metric

Combination

InitialPopulationByHIERegistry

Repeat per Metric

 

InitialPopulationByAdmin

Repeat per Metric

InitialPopulation

\(Sum over SSoRs\)

 

ExclusionsByEHR

Repeat per Metric

 

ExclusionsByCaseManagement

Repeat per Metric

 

ExclusionsByHIERegistry

Repeat per Metric

 

ExclusionsByAdmin

Repeat per Metric

 

Exclusions

\(Sum over SSoRs\)

Denominator

Repeat per Metric

NumeratorByEHR

For each Metric

NumeratorByCaseManagement

For each Metric

NumeratorByHIERegistry

For each Metric

NumeratorByAdmin

For each Metric

Numerator

\(Sum over SSoRs\)

Rate

\(Percent\)

### Table PRS\-E\-B\-1/2: Data Elements for Prenatal Immunization Status: Stratifications by Race 

Metric

Race

Data Element

Reporting Instructions

Influenza 

AmericanIndianOrAlaskaNative

InitialPopulation 

For each Stratification, repeat per Metric 

Tdap 

Asian

Exclusions 

For each Stratification, repeat per Metric 

Combination 

BlackOrAfricanAmerican

Denominator 

For each Stratification, repeat per Metric 

 

NativeHawaiianOrOtherPacificIslander

Numerator 

For each Metric and Stratification 

 

White

Rate 

\(Percent\) 

 

SomeOtherRace 

 

 

 

TwoOrMoreRaces 

 

 

 

AskedButNoAnswer 

 

 

 

Unknown 

 

 

### Table PRS\-E\-C\-1/2: Data Elements for Prenatal Immunization Status: Stratifications by Ethnicity 

Metric 

Ethnicity 

Data Element 

Reporting Instructions 

Influenza 

HispanicOrLatino 

InitialPopulation 

For each Stratification, repeat per Metric

Tdap 

NotHispanicOrLatino 

Exclusions 

For each Stratification, repeat per Metric

Combination 

AskedButNoAnswer 

Denominator 

For each Stratification, repeat per Metric

 

Unknown 

Numerator 

For each Metric and Stratification

 

 

Rate 

\(Percent\) 

Rules for Allowable Adjustments of HEDIS

The “Rules for Allowable Adjustments of HEDIS” \(the “Rules”\) describe how NCQA’s HEDIS measure specifications can be adjusted for other populations, if applicable\. The Rules, reviewed and approved by NCQA measure experts, provide for expanded use of HEDIS measures without changing their clinical intent\. 

__Adjusted HEDIS measures may not be used for HEDIS health plan reporting\. __

### Rules for Allowable Adjustments of Prenatal Immunization Status

__NONCLINICAL COMPONENTS __

__Eligible Population__

__Adjustments Allowed \(Yes/No\)__

__Notes__

Product lines

Yes

Organizations are not required to use product line criteria; product lines may be combined and all \(or no\) product line criteria may be used\.

Ages

NA

There are no age criteria for this measure\.

Allocation

Yes

Organizations are not required to use enrollment criteria; adjustments are allowed\.

Benefits

Yes

Using a benefit is not required; adjustments are allowed\.

Other

Yes

Organizations may use additional eligible population criteria to focus on an area of interest defined by gender, race, ethnicity, socioeconomic or sociodemographic characteristics, geographic region or another characteristic\. 

__CLINICAL COMPONENTS__

__Initial Population__

__Adjustments Allowed \(Yes/No\)__

__Notes__

Event/diagnosis

No

Only events or diagnoses that contain \(or map to\) codes in the VSDs may be used to identify visits with a diagnosis\. The VSDs and logic may not be changed\.

__Exclusions__

__Adjustments Allowed \(Yes/No\)__

__Notes__

Exclusions

Yes, with limits

Apply exclusions according to specified value sets\.

Organizations may choose to not exclude deliveries that occurred at less than 37 weeks gestation\.

Exclusions: Hospice and deceased member

Yes

These exclusions are not required\. Refer to *Exclusions* in the *Guidelines for the Rules for Allowable Adjustments*\.

__Denominator__

__Adjustments Allowed \(Yes/No\)__

__Notes__

Denominators

No

The logic may not be changed\. 

__Numerator Criteria__

__Adjustments Allowed \(Yes/No\)__

__Notes__

- Influenza
- Tdap
- Combination

No

Value sets, direct reference codes and logic may not be changed\.

<a id="_Hlk503278152"></a>

