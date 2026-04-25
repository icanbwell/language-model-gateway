---
name: bwell-connected-health
description: Provides comprehensive information about b.well Connected Health, including their Helix FHIR Server, AI-powered digital health platform, products (bailey AI assistant, Health AI SDK), partnerships (OpenAI, Samsung, Google, Perplexity), CMS-Aligned Network commitment, FHIR-based data integration capabilities, and company mission. Use when users ask about b.well, icanbwell, Helix FHIR Server, their technology stack, healthcare data integration, AI health assistants, or digital health platforms. Use even if users don't explicitly mention "b.well" but are asking about healthcare data unification, FHIR platforms, AI-powered health experiences, or CMS interoperability.
license: Internal use only
metadata:
  owner: baileyai
  source: Public information from b.well Connected Health, GitHub, press releases
  last_reviewed: 2026-01-15
  scope: Company information, products, partnerships, technology, FHIR server
---

# b.well Connected Health Information

## Skill Card

**Goal**: Provide accurate, comprehensive information about b.well Connected Health, their products, technology platform, partnerships, and healthcare solutions.

**Use when**:
- User asks about b.well Connected Health or icanbwell
- Questions about Helix FHIR Server
- Questions about bailey AI health assistant
- Inquiries about healthcare data integration or FHIR platforms
- Questions about AI-powered health experiences
- Requests for information about digital health platforms
- Questions about healthcare data unification
- Inquiries about b.well's partnerships (OpenAI, Samsung, Google, etc.)
- Questions about CMS-Aligned Network or CMS Interoperability Framework
- Questions about "Kill the Clipboard" initiative

**Do not use when**:
- User is asking about other healthcare companies
- Questions about general healthcare topics unrelated to b.well
- Medical advice or clinical guidance

**Required inputs**:
- User's specific question about b.well

**Outputs**:
- Accurate information about b.well's products, services, and capabilities
- Context about their technology platform and approach
- Details about partnerships and integrations
- Company mission and value proposition
- Technical details about Helix FHIR Server

## Company Overview

**b.well Connected Health** is a healthcare technology company solving healthcare's fragmentation problem by enabling organizations to deliver connected, complete digital health experiences.

**Mission**: Transform healthcare into a simple, on-demand experience by putting consumers in the center of the healthcare equation.

**Website**: www.icanbwell.com (also www.bwell.com)

**Headquarters**: Baltimore, Maryland

**Key Value Proposition**: b.well unifies fragmented healthcare data from 350+ sources into a single, AI-ready longitudinal health record, enabling organizations to deploy AI-powered consumer health experiences.

## Core Technology Platform

### Helix FHIR Server

**What it is**: b.well's open-source, highly scalable FHIR server implementation that powers their platform.

**GitHub**: https://github.com/icanbwell/fhir-server

**Key Features**:
- **Open source**: Available on GitHub under Apache 2.0 license
- **MongoDB-backed**: Uses MongoDB for data storage
- **Highly scalable**: Built for enterprise-level performance
- **Real-time data streaming**: Enables live data updates
- **Change event tracking**: Monitors all data changes
- **GraphQL support**: Modern API access to FHIR resources
- **WebUI**: Browser-based interface to explore FHIR data
- **Complete FHIR resource support**: Implements all FHIR resources
- **Advanced search**: Supports all FHIR search parameters
- **$merge operation**: Custom operation for data merging
- **$graph endpoint**: GraphDefinition support
- **$everything operation**: Retrieve complete patient records
- **Authentication & authorization**: user/x.x and access/x.x scope checking
- **Kafka integration**: Optional event streaming to Kafka queues
- **ClickHouse integration**: For Groups approaching MongoDB's 16MB document limit
- **Bulk export**: FHIR bulk data export functionality
- **Optimistic concurrency**: Prevents conflicting updates

**Technical Architecture**:
- Node.js/JavaScript implementation
- Docker containerized deployment
- Kubernetes-ready
- Continuous integration via GitHub Actions
- Automated deployment to DockerHub and AWS ECR

### FHIR-Based Data Platform

- **Built on FHIR standards** (Fast Healthcare Interoperability Resources)
- **350+ data source integrations**: Clinical records, claims, pharmacy, wearables
- **13-step data refinery**: Proprietary process that connects, normalizes, and structures fragmented health data
- **Longitudinal health records**: Creates complete, unified patient health histories
- **AI-ready data**: Structured specifically for AI/ML applications
- **Semantic interoperability**: Goes beyond data exchange to ensure data is understood and actionable

### Data Types Unified

1. **Clinical data**: EHR records, lab results, imaging reports
2. **Claims data**: Insurance claims, billing information
3. **Pharmacy data**: Medication history, prescriptions
4. **Wearables data**: Fitness trackers, health monitoring devices
5. **Consumer-generated data**: Patient-reported outcomes

### Security & Compliance

- **HIPAA compliant**
- **SOC 2 certified**
- **HITRUST certified**
- **Enterprise-level encryption**
- **Audit trails**
- **Consumer-first privacy**: Built on CARIN Alliance Code of Conduct
- **DiMe Seal**: Recognized by Digital Medicine Society for responsible data use
- **IAL2-compliant identity verification**: Powered by CLEAR
- **OAuth2/OpenID Connect**: Standard authentication protocols

## Products & Solutions

### bailey™ (Launched February 2026)

**What it is**: A ready-to-deploy white-label health AI assistant that organizations can embed directly into their own applications.

**Key Features**:
- **White-label ready**: Fully customizable UI to match brand
- **Action-oriented AI**: Goes beyond Q&A to complete tasks (schedule appointments, refill prescriptions, find providers)
- **Agentic AI architecture**: Orchestrates multiple specialized AI agents
- **Rapid deployment**: Deploy in weeks via SDK (web, iPhone, Android)
- **Grounded in complete health data**: Uses longitudinal health records for context-aware insights
- **Healthcare-grade**: Built for medical data interpretation and care coordination
- **Trained on millions of patient records**: Real-world complexity built in

**Deployment Time**: Weeks (vs. 18-24 months to build from scratch)

**Use Cases**:
- Finding care options
- Managing medications
- Scheduling appointments
- Navigating benefits
- Interpreting clinical data
- Care coordination between visits

### b.well Health AI SDK

**What it is**: The core infrastructure that powers bailey and enables organizations to build their own AI-powered health experiences.

**Used by**: OpenAI, Samsung, and other major technology companies

**Available Platforms**:
- **TypeScript/JavaScript**: `@icanbwell/bwell-sdk-ts` on NPM
- **Kotlin/Android**: `com.bwell:bwell-sdk-kotlin` from b.well's Maven repository
- **Swift/iOS**: Available for iOS development
- **React Native**: Cross-platform mobile support

**Capabilities**:
- Secure health data connectivity
- Data normalization and structuring
- AI orchestration
- FHIR-based data access
- Pre-built AI agents (or build custom agents)
- Third-party agent integration support
- Mobile SDKs for iOS and Android
- UI components for rapid development

**Flexibility**: Organizations can:
1. Deploy bailey as white-label assistant
2. Use SDK to build custom AI experiences
3. Combine both approaches

### Digital Health Platform

**Core offering**: Complete platform for building consumer-facing digital health applications

**Enables**:
- Connected care experiences
- Precision engagement
- Easy access to health information
- Personalized health insights
- Care action coordination

## CMS-Aligned Network Commitment

b.well committed in July 2025 to becoming a CMS-Aligned Network — among the first 60 companies to join this voluntary, national strategy to modernize healthcare data exchange. They support patient-directed access, FHIR API-based exchange, and the "Kill the Clipboard" initiative to eliminate paper forms via facial recognition and QR-code-based data sharing.

For full details on the five compliance areas and "Kill the Clipboard," read `references/cms-aligned-network.md`.

## Major Partnerships

b.well has been selected by leading technology companies for health data connectivity:
- **OpenAI** (Jan 2026): Powers secure health data in ChatGPT — integrating a full clinical data network, not just a single source
- **Samsung**: Samsung Health integration, "Kill the Clipboard" implementation
- **Google** (Oct 2025): Advancing AI-powered personalized health
- **Perplexity** (Mar 2026): Health record connectivity for AI search
- **athenahealth** (Feb 2026): Digital health data sharing

For detailed partnership descriptions, read `references/partnerships.md`.

## Awards & Recognition

### MedTech Breakthrough Awards (May 2025)

**Award**: "Best Healthcare Big Data Solution" (9th Annual Program)

**Recognition for**: AI-driven Large Health Model

### Newsweek Recognition (May 2024)

**Award**: Featured as one of the World's Best Digital Health Companies

**Recognition by**: Newsweek and Statista

## Funding & Investment

### Series C Funding (February 2024)

**Amount**: $40 million

**Purpose**: Scale platform unifying patient data

### RTI International Investment (January 2025)

**Investor**: RTI International (nonprofit research institute)

**Purpose**: Support expansion into pharma and life sciences

## Technical Architecture

### 13-Step Data Refinery

Proprietary process for transforming fragmented health data into AI-ready format:

1. **Data ingestion** from 350+ sources
2. **Normalization** to FHIR standards
3. **Deduplication** of records
4. **Identity resolution** across systems
5. **Data validation** and quality checks
6. **Enrichment** with additional context
7. **Structuring** for AI consumption
8. **Longitudinal record creation**
9. **Privacy controls** and consent management
10. **Security** and encryption
11. **Audit logging**
12. **Real-time updates**
13. **AI optimization**

### Agentic AI Architecture

**Concept**: bailey orchestrates multiple specialized AI agents rather than using a single monolithic model

**Agent Types**:
- Clinical data interpretation agents
- Appointment scheduling agents
- Provider search agents
- Benefits navigation agents
- Medication management agents
- Custom agents (built by organizations)
- Third-party agents (integrated from partners)

**Flexibility**: Organizations can use pre-built agents, develop custom agents, or integrate third-party agents

### Data Scale

- **Millions of patient records** used to develop and refine bailey
- **350+ data sources** integrated
- **1.8M+ provider connections**
- **300+ payer connections**
- **8M+ providers** in national directory
- **Most comprehensive longitudinal health datasets** in healthcare
- **Real-world complexity**: Built to handle actual healthcare data fragmentation

## Key Differentiators

### vs. General-Purpose AI Assistants

- **Grounded in complete health records**: Not just answering questions, but using actual patient data
- **Healthcare-grade security**: HIPAA, SOC 2, HITRUST certified
- **Action-oriented**: Can complete healthcare tasks, not just provide information
- **Clinical context**: Understands medical terminology, clinical workflows
- **Semantic interoperability**: Data is understood, not just exchanged

### vs. Building In-House

- **Time to market**: Weeks vs. 18-24 months
- **Cost**: Fraction of millions required to build from scratch
- **Solved problems**: Data integration, security, compliance already handled
- **Proven at scale**: Built on millions of patient records
- **Continuous improvement**: Platform evolves with healthcare standards
- **Open source foundation**: Helix FHIR Server available on GitHub

### vs. Other Health Data Platforms

- **Clinical data network**: Not just a single data source, but a comprehensive network
- **AI-first design**: Data specifically structured for AI/ML applications
- **Consumer control**: Privacy-first approach with consumer-directed data sharing
- **Proven partnerships**: Selected by OpenAI, Samsung, Google
- **CMS-Aligned Network**: Committed to federal interoperability standards
- **Semantic interoperability**: Beyond just data exchange

## Use Cases & Applications

### For Health Plans

- Member engagement platforms
- Benefits navigation
- Care coordination
- Personalized health insights
- Preventive care outreach
- Digital quality improvement
- Care gaps and measures calculation using CQL
- Push notifications for patient engagement

### For Healthcare Providers

- Patient portals
- Pre-visit data collection
- Care gap closure
- Patient education
- Remote monitoring
- Encounter-based data access
- Automatic visit summaries

### For Employers

- Employee health platforms
- Benefits utilization
- Wellness programs
- Healthcare navigation

### For Technology Companies

- Health features in consumer apps
- AI-powered health assistants
- Wearable device integration
- Personalized health recommendations

### For Pharma & Life Sciences

- Patient support programs
- Clinical trial recruitment
- Real-world evidence
- Patient engagement

## Developer Resources

### GitHub Repositories

- **Helix FHIR Server**: https://github.com/icanbwell/fhir-server
- **SDK Examples**: https://github.com/icanbwell/bwell-sdk-example
  - Kotlin/Android examples
  - TypeScript/React examples
  - React Native/Expo examples
  - Swift/iOS examples

### SDK Packages

- **NPM**: `@icanbwell/bwell-sdk-ts`
- **Maven**: `com.bwell:bwell-sdk-kotlin` from https://artifacts.icanbwell.com/repository/bwell-public/

### Developer Portal

- **CMS Network Application**: https://insights.icanbwell.com/cms_network
- **Contact**: contact@icanbwell.com

### Documentation

- **FHIR Server Docs**: Available in GitHub repository
- **Cheat sheets**: Performance optimization, security, GraphQL
- **API Reference**: FHIR-compliant REST APIs

## Company Information

**Leadership**:
- **Kristen Valdes**: Founder and CEO
- **Imran Qureshi**: CTO

**Company Values**:
- Consumer-centric approach
- Data privacy and security
- Healthcare simplification
- Innovation in digital health
- Open standards and interoperability

**Philosophy**:
- "Data belongs to patients"
- "Interoperability requires semantic understanding beyond just data exchange"
- "Consumer-grade experiences are achievable in healthcare when we stop competing on data and start competing on the value offered on top of the data"

## Common Questions

Covers FAQs on the Helix FHIR Server, differentiators, bailey deployment time, HIPAA compliance, customization, data sources, data privacy, CMS-Aligned Network, and "Kill the Clipboard."

For all Q&A pairs and edge-case handling, read `references/common-questions.md`.

## Gotchas

- **Company name variations**: Referred to as "b.well Connected Health," "b.well," or "icanbwell" (their domain)
- **Recent launches**: bailey was announced in February 2026, so it's a very new product
- **Not a standalone PHR**: b.well is fundamentally different from personal health record companies - they're a platform/infrastructure provider
- **Partnership significance**: The OpenAI partnership is particularly notable because b.well is integrating a clinical data network, not just a single data source
- **FHIR-based**: All architecture is built on FHIR standards - this is core to their approach
- **White-label focus**: bailey is designed to be embedded in other organizations' apps, not a standalone consumer app
- **Open source**: The Helix FHIR Server is open source on GitHub, but the full platform is proprietary
- **Semantic interoperability**: b.well emphasizes they go beyond just data exchange to ensure data is understood and actionable
- **CMS-Aligned Network**: This is a voluntary commitment, not a regulatory requirement
- **Developer-friendly**: Multiple SDKs available (TypeScript, Kotlin, Swift, React Native)

## Response Examples

Five example user/response pairs covering Helix FHIR Server, bailey, CMS-Aligned Network, OpenAI partnership, and "Kill the Clipboard."

For all examples, read `references/examples.md`.
