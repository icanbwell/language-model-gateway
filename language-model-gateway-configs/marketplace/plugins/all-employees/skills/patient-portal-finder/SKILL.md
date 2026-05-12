---
name: patient-portal-finder
description: >
  Find the patient portal for any healthcare provider or hospital. Use this skill whenever
  the user wants to locate where to log in to view health records, test results, appointment
  history, billing, or any patient-facing online account at a specific provider — even if they
  don't use the word "portal." Trigger on phrases like "find the patient portal for [provider]",
  "where do I log in at [hospital]", "what portal does [clinic] use", "how do I access my
  records at [provider]", or any request to locate a patient login. Also identifies the
  EMR/EHR platform in use (Epic MyChart, Cerner/Oracle Health, Healow, etc.).
  Input is typically a provider name, not a URL. If the provider name is ambiguous (e.g.,
  "St. Mary's Hospital" exists in many cities), ask for the user's location before proceeding.
license: Internal use only
metadata:
  owner: baileyai
  source: Web search and provider websites
  last_reviewed: 2026-04-21
  scope: Patient portal discovery, EMR/EHR identification
---

# Patient Portal Finder

Given a healthcare provider name, find their patient portal login page, return the URL,
take a screenshot, and identify the EMR/EHR platform in use.

The strategy below is ordered by efficiency — start at Step 1 and only move forward
when the current step doesn't yield a confirmed portal URL.

---

## Step 1: Web search

Search: `"[provider name]" patient portal`

- Identify the provider's **official domain** from results (ignore third-party aggregators
  like Healthgrades, Zocdoc, or Yelp — they rarely link directly to the portal).
- If results clearly reveal the portal URL and EMR system, note them and skip to Step 4.
- If the provider name is ambiguous (e.g., "St. Mary's," "Mercy Hospital," "Community
  Health Center"), check whether you need to ask the user for their city/state before
  continuing — a wrong provider is worse than a short clarifying question.

---

## Step 2: Visit the homepage

Navigate to the provider's official homepage and scan for links/buttons with keywords:
`patient portal`, `patient login`, `my health`, `mychart`, `myhealth`, `healow`,
`follow my health`, `patient access`, `sign in`, `log in`, `view my records`.

- If a clear portal link is found → **skip to Step 4**.
- Note: many providers host their portal on a completely different domain (e.g., a MyChart
  subdomain like `mychart.providerhealth.org`), so don't assume the portal is on the main
  site — the homepage link is just the fastest way to find the real URL.

---

## Step 3: Deeper search (if portal not yet found)

Try these in order until one resolves:

**Common path patterns** — append to the provider's domain one at a time:
```
/patient-portal
/patients
/mychart
/myhealth
/my-health
/portal
/patient-login
/patientportal
/myhealthrecord
```

**Common subdomains:**
```
mychart.[domain]
portal.[domain]
patients.[domain]
myhealth.[domain]
```

**Targeted web searches:**
- `site:[domain] patient portal login`
- `"[provider name]" patient portal login`

**Check the parent health system** — many clinic and hospital brands are subsidiaries of
larger systems (e.g., "Weill Cornell Medicine" uses NewYork-Presbyterian's MyChart).
Search: `"[provider name]" health system` to find the parent, then repeat Steps 1–3 for
the parent system.

---

## Step 4: Navigate and screenshot

- Navigate to the confirmed portal URL.
- Take a screenshot to confirm the page loaded correctly.
- Do **not** attempt to fill in login credentials or interact with login forms — this is
  the user's private health account and Claude should never handle credentials on their behalf.

---

## Step 5: Identify the EMR/EHR platform

Examine the portal URL, page title, branding, and footer/copyright text. Common platforms:

| Platform | Signals |
|---|---|
| **Epic MyChart** | "mychart" in URL or page title, MyChart branding, Epic logo in footer |
| **Cerner / Oracle Health** | "cernerhealth.com", "healthelife", Oracle Health branding |
| **Healow** (eClinicalWorks) | "healow.com" in URL, Healow app references |
| **FollowMyHealth** (Veradigm) | "followmyhealth.com" in URL |
| **Athenahealth** | "athenahealth.com", "athenacommunicator" in URL |
| **NextGen** | "nextgen.com", "NextGen Patient Portal" branding |
| **Meditech** | "meditech.com", "mtwireless" in URL |
| **Allscripts / Veradigm** | "allscripts.com" in URL |
| **DrChrono** | "drchrono.com" in URL |
| **PatientFusion** | "patientfusion.com" in URL |
| **Kaiser Permanente** | Proprietary — "kp.org", "My Health Manager" branding |
| **VA MyHealtheVet** | "myhealth.va.gov" — VA-specific, not a commercial EMR |
| **Canvas Medical** | "canvasmedical.com" — newer independent practices |

**When signals conflict** (e.g., URL says "myhealth" but branding says Cerner): trust the
URL domain and footer copyright text over page title, and note the uncertainty in your output.

If the platform can't be confirmed from the portal page alone, check the web search results
from Step 1 for references to the EMR vendor.

---

## Step 6: Handle special cases

**Multiple portals** — some large health systems have separate portals for different purposes
(billing vs. health records, or separate portals for different facilities). List all options
and briefly explain what each is for, so the user can pick the right one.

**App-only portals** — some platforms (notably Healow and some Cerner deployments) strongly
push users toward a mobile app rather than a web login. If the portal page primarily
promotes an app download, note this clearly and still provide any available web login URL.

**No web portal exists** — smaller independent practices, urgent care chains, and some
specialists may not have a patient portal at all. This is more common than people expect.

---

## Output format

Always provide all three of the following:

1. 🔗 **Portal URL** — the direct link to the patient portal login page
2. 🖥️ **EMR/EHR System** — the platform identified (or "Unknown — could not confirm" if unclear)
3. 📸 **Screenshot** — confirmation that the portal page loaded

Also include:
- **How it was found** (homepage link / common path / web search / parent health system)
- **Any uncertainty** (e.g., "URL suggests MyChart but MyChart branding was not visible on the page")

**Example output:**

> 🔗 **Portal URL:** https://mychart.mountsinai.org/
>
> 🖥️ **EMR/EHR System:** Epic MyChart — confirmed via "mychart" subdomain and MyChart branding
>
> 📸 **Screenshot:** [screenshot attached]
>
> **Found via:** Homepage — "MyChart Patient Portal" link in the top navigation bar

---

## If no portal is found after all steps

1. Report clearly that no patient portal was found despite a thorough search.
2. Explain the most likely reason (e.g., small practice without a portal, portal may be
   accessible only after an in-person visit to get an activation code, or the provider
   may be part of a larger system with a portal under a different name).
3. Suggest next steps:
   - Call the provider's main line and ask specifically for their "patient portal" or
     "online health records access."
   - Check any after-visit summary or discharge paperwork — activation codes or portal
     instructions are often printed there.
   - Ask the provider's front desk staff if they use a mobile app instead of a web portal.
