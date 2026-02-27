---
name: vaccine-eligibility-pediatric
description: Determine whether a pediatric patient is due for vaccines by comparing immunization history to the CDC child and adolescent schedule.
license: Internal use only
metadata:
  owner: baileyai
  source: CDC Child and Adolescent Immunization Schedule
  source_url: https://www.cdc.gov/vaccines/hcp/imz-schedules/child-adolescent-schedule.html
  last_reviewed: 2026-02-26
---
# Vaccine Eligibility Assessment (Pediatrics)

## Purpose
Use this skill to determine whether a pediatric patient (birth through 18 years) is due for vaccines. Compare the patient's immunization history and risk factors against CDC child and adolescent schedule guidance. Do not log or expose PHI/PII. If required inputs are missing, ask targeted follow-up questions before making determinations.

## Required Inputs
- Patient age and date of birth
- Today's date
- Immunization history (vaccine name, dates, dose counts, series completion)
- Clinical risk factors (immunocompromised, chronic disease, pregnancy status for adolescents, asplenia, diabetes, liver disease, etc.)
- Travel, occupational, or lifestyle risks (daycare/school exposure, travel, MSM, injection drug use, etc.)
- Allergy list and prior vaccine reactions (from record or caregiver report)
- Active medication list (especially immunosuppressants, chemotherapy, biologics, high-dose steroids)
- Contraindication/precaution history (immunosuppression, pregnancy status, recent blood products, acute illness)

## Expected Outputs
- Vaccines due now vs due later (with brief rationale and timing)
- Up-to-date vaccines with last dose date, how long ago, and why no dose is recommended now
  - Always state the reason in record-based terms (e.g., series complete, interval not met, age/risk not eligible yet) and cite the relevant record date(s)
- Contraindicated or precautionary vaccines (with reason and what info is needed if uncertain)
- Follow-up questions required to make a safe determination when data is missing
  - Ask questions one at a time
  - Always check the patient record first and only ask for information not already documented
- Summary of checks performed (no PHI/PII; high-level only)

## Decision Flow (Pediatric Focus)
1. Confirm pediatric scope (birth through 18 years). If patient is 19+, switch to the adult skill (vaccine-eligibility-adult).
2. Retrieve allergy list and active medication list; ask targeted follow-up questions if missing.
3. Gather or verify immunization history; if incomplete or unknown, assume unvaccinated for missing series and continue without restarting.
4. Apply routine pediatric schedule by age group.
5. Apply risk-based indications (medical conditions, pregnancy, occupation, travel, behavior).
6. Screen contraindications and precautions using allergy history, medication list, and other risk data before recommending any vaccine.
7. Identify gaps and generate due-now vs due-later recommendations.
8. If any required data is missing, ask follow-up questions and defer final determination for affected vaccines.

## Required Follow-up Questions (Ask Only What Is Missing)
- Ask only one question at a time and wait for the response before asking the next
- Before asking, confirm the data is not already present in the patient record
- Immunization history: "Which vaccines have been received and on what dates?" "Do you have records for DTaP, IPV, Hib, PCV, MMR, Varicella, HepA, HepB, Tdap, HPV, MenACWY, MenB, influenza, COVID-19?"
- Allergy or prior reaction: "Any severe allergy to vaccine components (yeast, gelatin, neomycin, latex)?" "Any anaphylaxis or severe reaction to a prior vaccine dose?"
- Medications: "Which medications are currently taken, including immunosuppressants, chemotherapy, biologics, or high-dose steroids?"
- Pregnancy (adolescents): "Are you currently pregnant? If yes, how many weeks gestation?" "Are you trying to become pregnant?"
- Immunocompromise: "Do you have HIV, cancer treatment, transplant history, or take immunosuppressive meds (including high-dose steroids)?"
- Acute illness: "Are you moderately or severely ill today or have a high fever?"
- Recent blood products: "Any blood transfusions or immune globulin in the past 3-11 months?"
- Risk factors: "Do you have chronic heart or lung disease, diabetes, liver disease, kidney disease, asplenia, or a CSF leak or cochlear implant?"
- School or travel: "Daycare, school, or college dorm exposure?" "Recent or planned travel to endemic areas?"
- Behavioral risks (adolescents): "MSM or injection drug use?"

## Output Template (Use This Structure)
- Due now:
  - Vaccine: rationale and timing or interval
- Due later:
  - Vaccine: rationale and timing or interval
- Up-to-date:
  - Vaccine: last dose date; how long ago; why guidelines do not recommend another dose now
    - Use one of: series complete; interval window not met; age/risk criteria not met yet
    - Tie the rationale to records: "based on your records" + date(s) or documented series completion
    - Example format: "Influenza: last dose Oct 2024 (4 months ago); annual vaccine, so not due until next season."
- Contraindicated or precaution:
  - Vaccine: reason and what info is missing (if applicable)
- Follow-up questions:
  - List only unanswered questions that block a safe determination
- Checks performed:
  - Brief high-level summary (for example, reviewed allergy list for severe reactions; reviewed medications for immunosuppression)

---

## BY AGE GROUP

### INFANTS AND CHILDREN (Birth - 18 years)

AT BIRTH:
- Hepatitis B (within 24 hours if mother HBsAg-negative and birth weight >=2000g)

AGE 2 MONTHS:
- DTaP, Hib, IPV (Polio), PCV, Rotavirus, Hepatitis B

AGE 4 MONTHS:
- DTaP, Hib, IPV, PCV, Rotavirus

AGE 6 MONTHS:
- DTaP, Hib (if using ActHIB, Hiberix, Pentacel, or Vaxelis), IPV, PCV, Rotavirus (if using RotaTeq), Hepatitis B, Influenza (start annual)

AGE 12-15 MONTHS:
- Hib booster, PCV booster, MMR, Varicella, Hepatitis A

AGE 15-18 MONTHS:
- DTaP booster

AGE 4-6 YEARS:
- DTaP booster, IPV booster, MMR, Varicella

AGE 11-12 YEARS:
- Tdap, HPV (2-dose series), MenACWY

AGE 16 YEARS:
- MenACWY booster, MenB (based on shared clinical decision-making, preferred age 16-18)

---

## BY MEDICAL CONDITION

### PREGNANCY (Adolescents)
- MUST RECEIVE:
  - Tdap: each pregnancy, weeks 27-36
  - RSV (Abrysvo): if 32-36 weeks gestation, September-January
  - Influenza: if during flu season
  - COVID-19: based on shared clinical decision-making

- CONTRAINDICATED:
  - MMR, Varicella, live vaccines, Zoster

### IMMUNOCOMPROMISED (HIV, cancer, transplant, immunosuppressive drugs)
- Additional doses needed for:
  - Hib: if asplenia, HIV, or other conditions
  - Pneumococcal: enhanced schedule with both PCV and PPSV23
  - MenACWY: 2-dose primary series, boosters every 5 years
  - MenB: 3-dose series, boosters every 2-3 years
  - HPV: 3-dose series even if started age 9-14
  - Hepatitis B: may need higher doses or additional doses

- CONTRAINDICATED:
  - Live vaccines if severely immunocompromised (MMR, Varicella, LAIV)

### ASPLENIA (including Sickle Cell Disease)
- Hib: 1 dose if not previously received
- Pneumococcal: enhanced schedule
- MenACWY: 2-dose series, boosters every 5 years
- MenB: 3-dose series, boosters every 2-3 years

### CHRONIC LIVER DISEASE
- Hepatitis A: 2-dose series
- Hepatitis B: complete series
- Pneumococcal: per age-based schedule

### DIABETES
- Hepatitis B: complete series
- Pneumococcal: per age-based schedule

### CHRONIC HEART OR LUNG DISEASE
- Pneumococcal: enhanced schedule
- Annual influenza

### HEALTHCARE WORKERS (Adolescents)
- MMR: 2-dose series (regardless of birth year)
- Varicella: 2-dose series if no evidence of immunity
- Hepatitis B: complete series
- Annual influenza
- Tdap: if not received
- COVID-19: per current recommendations

---

## CATCH-UP VACCINATION

### Key Principles
- Never restart a series - just continue from where they left off
- Use minimum intervals only when rapid protection is needed
- Refer to catch-up tables for specific intervals

### Common Catch-Up Scenarios

Incomplete childhood series:
- Complete remaining doses using age-appropriate formulations
- DTaP to Tdap or Td after age 7

No vaccination records:
- Assume unvaccinated unless documented otherwise

---

## SPECIAL SITUATIONS

TRAVEL:
- Hepatitis A: if traveling to endemic areas
- Typhoid, Yellow Fever, Japanese Encephalitis: destination-specific
- Meningococcal: if traveling to meningitis belt or Hajj
- Routine vaccines: ensure up to date

COLLEGE STUDENTS (especially in dorms):
- MenACWY: 1 dose if not received at age 16+
- MenB: based on shared clinical decision-making

MEN WHO HAVE SEX WITH MEN (Adolescents):
- Hepatitis A: 2-dose series
- Hepatitis B: complete series
- HPV: through age 26 (ages 27-45 based on shared clinical decision-making)
- Mpox: if at risk, 2-dose series

INJECTION DRUG USE (Adolescents):
- Hepatitis A: 2-dose series
- Hepatitis B: complete series

---

## EVIDENCE OF IMMUNITY

Don't need vaccine if:
- Measles, Mumps, Rubella: documented 2 doses MMR, lab evidence, or documented disease
- Varicella: documented 2 doses, lab evidence, or documented disease by provider
- Hepatitis A or B: lab evidence of immunity or documented vaccination series

---

## CONTRAINDICATIONS VS PRECAUTIONS

Contraindication = DO NOT GIVE
Precaution = Weigh risks and benefits, may defer

Common Contraindications:
- Severe allergic reaction to vaccine component or previous dose
- Pregnancy (for live vaccines)
- Severe immunocompromise (for live vaccines)

Common Precautions:
- Moderate or severe acute illness
- Recent receipt of antibody-containing blood products (for live vaccines)

---

## QUICK DECISION ALGORITHM

1. Determine age
2. Check routine vaccines for that age
3. Assess medical conditions (immunocompromised, chronic disease, pregnancy, etc.)
4. Check occupational, behavioral, and travel risk factors
5. Review vaccination history - what is documented
6. Identify gaps - compare history to recommendations
7. Check contraindications before recommending
8. Provide catch-up schedule if behind

---

This condensed guide provides the essential logic for determining vaccine needs based on age, medical conditions, and risk factors from the CDC schedules.

# VACCINE CONTRAINDICATIONS AND PATIENT RECORD SCREENING GUIDE

## TYPES OF CONTRAINDICATIONS

### 1. Severe allergic reactions
What to check in records:
- Allergy history (medication allergies, food allergies)
- Previous vaccine reactions
- Anaphylaxis history

Specific allergens by vaccine:
- Egg allergy: previously thought contraindication for influenza vaccine, but no longer a contraindication (can give with observation)
- Yeast allergy: Hepatitis B, HPV vaccines
- Gelatin allergy: MMR, Varicella, Zoster vaccines
- Neomycin allergy: MMR, Varicella, IPV vaccines
- Latex allergy: some vaccine packaging (check specific products)
- Previous dose reaction: any vaccine where patient had anaphylaxis to prior dose

---

### 2. Immunocompromised status
What to check in records:
- HIV status and CD4 counts
- Cancer diagnosis and treatment status
- Transplant history (solid organ or bone marrow)
- Current medications (especially immunosuppressants)
- Chemotherapy or radiation therapy
- Congenital immunodeficiency disorders

Key contraindications:
- Live vaccines contraindicated if severely immunocompromised:
  - MMR
  - Varicella
  - Zoster (live version - Zostavax, not Shingrix)
  - LAIV (nasal flu)
  - Rotavirus (if SCID)
  - Yellow Fever

Steroid threshold: 2 weeks of >=20 mg per day prednisone (or >=2 mg per kg per day) means severely immunosuppressive

---

### 3. Pregnancy
What to check in records:
- Pregnancy status (current pregnancy, weeks gestation)
- Pregnancy intentions (for patients of childbearing age)
- Last menstrual period

Contraindications:
- Live vaccines contraindicated:
  - MMR
  - Varicella
  - LAIV (nasal flu)
  - Yellow Fever (unless high-risk travel)

Safe and recommended in pregnancy:
- Tdap (each pregnancy, weeks 27-36)
- Influenza (injectable)
- COVID-19
- RSV (Abrysvo at 32-36 weeks, Sept-Jan)
- Hepatitis A and B

---

### 4. Neurologic conditions
What to check in records:
- Seizure history and control status
- Progressive neurologic disorders
- Encephalopathy history
- Guillain-Barre Syndrome (GBS) history

Specific contraindications:
- DTaP or Tdap: encephalopathy within 7 days of previous pertussis-containing vaccine
- DTaP: progressive or unstable neurologic disorder (precaution)
- Influenza or Tetanus vaccines: GBS within 6 weeks of previous dose (precaution, not absolute contraindication)

Not contraindications:
- Stable neurologic conditions (cerebral palsy, controlled seizures, developmental delay)
- Family history of seizures

---

### 5. Recent blood products
What to check in records:
- Blood transfusions (date and type)
- Immune globulin administration (IVIG, specific immune globulins)
- Monoclonal antibodies

Affects: MMR and Varicella vaccines
Interval needed: 3-11 months depending on product and dose (check specific tables)

---

### 6. Current illness
What to check in records:
- Current symptoms and severity
- Temperature or fever
- Recent illness history

Key principle:
- Mild illness (with or without fever) is not a contraindication - vaccinate
- Moderate to severe acute illness is a precaution - defer vaccination until improved

---

### 7. Specific vaccine contraindications

Rotavirus:
- SCID (Severe Combined Immunodeficiency) - absolute contraindication
- History of intussusception - absolute contraindication
- Age restrictions: first dose must be given by 14 weeks 6 days; series completed by 8 months

LAIV (Nasal Flu):
- Pregnancy
- Immunocompromised
- Children 2-4 years with asthma or wheezing history
- Aspirin therapy in children or adolescents
- Close contacts of severely immunosuppressed persons
- Cochlear implants
- CSF leaks
- Recent antiviral use (within specific timeframes)

HPV:
- Pregnancy (precaution, not absolute contraindication, but defer)

Hepatitis B:
- Yeast allergy

Meningococcal:
- Complement deficiency (actually an indication, not contraindication)

---

## PATIENT RECORD SECTIONS TO CHECK

1. Allergy section
- Medication allergies (especially antibiotics, vaccines)
- Food allergies (eggs, yeast, gelatin)
- Latex allergy
- Type of reaction (anaphylaxis vs mild reaction)

2. Problem list or diagnoses
- HIV or AIDS
- Cancer (active or history)
- Immunodeficiency disorders
- Asplenia (functional or anatomic)
- Chronic kidney disease or dialysis
- Chronic liver disease
- Diabetes
- Heart disease
- Chronic lung disease or asthma
- Neurologic disorders
- Autoimmune conditions

3. Medication list
- Immunosuppressants (methotrexate, biologics, etc.)
- Chemotherapy
- Steroids (dose and duration)
- Aspirin (for children - affects varicella, LAIV)
- Antiviral medications (affects LAIV, varicella)

4. Immunization history
- Previous vaccine doses and dates
- Previous vaccine reactions
- Recent vaccines (timing for live vaccines)

5. Laboratory results
- HIV status and CD4 counts
- Pregnancy test (if indicated)
- Hepatitis B serology
- Antibody titers (for immunity evidence)

6. Surgical or procedure history
- Splenectomy
- Transplants
- Cochlear implants

7. Transfusion or blood product history
- Recent blood transfusions
- IVIG administration
- Immune globulin products

8. Pregnancy or reproductive history
- Current pregnancy status
- Weeks gestation
- Pregnancy intentions
- Breastfeeding status (not a contraindication for any vaccine)

9. Social history
- Occupation (healthcare worker, lab worker)
- Living situation (daycare, school, college dorm, long-term care)
- Travel plans
- High-risk behaviors

10. Family history
- Family history of immunodeficiency (first-degree relatives)
- Note: family history of seizures, SIDS, or vaccine reactions are not contraindications

---

## Commonly misperceived as contraindications (but are not)

These are safe to vaccinate:
- Mild illness with or without low-grade fever
- Current antibiotic therapy (except for live typhoid)
- Prematurity (except hep B in specific circumstances)
- Recent exposure to infectious disease
- Breastfeeding
- Pregnancy of mother or household contact
- Immunodeficient family member or household contact (except for LAIV in caregivers of severely immunosuppressed)
- History of penicillin allergy
- Family history of adverse events after vaccination
- Family history of seizures or SIDS

---

## Quick screening questions to ask every patient

1. "Are you sick today?" (moderate or severe illness)
2. "Do you have any allergies to medications, foods, or vaccines?"
3. "Have you ever had a serious reaction to a vaccine?"
4. "Do you have any long-term health problems?" (cancer, HIV, etc.)
5. "Are you taking any medications that affect your immune system?"
6. "For patients who could become pregnant: Are you pregnant or could you be pregnant?"
7. "Have you received any vaccines in the past 4 weeks?" (for live vaccines)
8. "Have you received any blood products, transfusions, or immune globulin in the past year?"
9. "Do you have a history of Guillain-Barre Syndrome?"
10. "For children: Do you have asthma or have you had wheezing?" (for LAIV)

---

## Documentation to review before each vaccination

- Screening checklist completed (use standardized forms like Immunize.org checklists)
- Allergy list reviewed
- Problem list reviewed
- Medication list reviewed
- Immunization history reviewed
- Pregnancy status confirmed (if applicable)
- Contraindications ruled out
- Precautions assessed (risk vs benefit)

---

This comprehensive screening approach will help you identify true contraindications while avoiding missed opportunities due to misconceptions. The key is systematic review of these specific record sections before each vaccination encounter.

MANDATORY: If you're not sure about a condition, ask the user for more details about the patient's history and risk factors to make an informed recommendation. Always prioritize patient safety and follow contraindications.

MANDATORY DATE CALCULATION RULE:
You MUST use calculate_date_difference for ANY question involving time elapsed or date comparisons, especially when stating how long ago a vaccine was given. This includes "when was my last...", "how long ago...", or any reference to timing of past events.
NEVER estimate time manually. Always:
1. Retrieve medical data
2. Call get_current_date to get current date
3. Call calculate_date_difference with event date and current date
4. Use exact result (never "about X months ago")