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

**Announcement**: July 2025 - b.well committed to becoming a CMS-Aligned Network under the CMS Interoperability Framework

**Significance**: Among the first 60 companies to commit to this voluntary, national strategy to modernize healthcare data exchange

**What it means**: b.well pledges to support:
- Patient-directed data access
- FHIR API-based exchange
- Consumer-facing tools that put consumers and providers first
- Open standards and secure data sharing

### Five Key Areas of Compliance

1. **Patient Access & Empowerment**
   - Standardized FHIR APIs with OAuth2/OpenID Connect
   - US Core V3 clinical data flows
   - Comprehensive audit logging
   - Patient-controlled consent management via FHIR Consent resources

2. **Provider Access & Delegation**
   - Chart notes and clinical documents accessible
   - Appointment data and care quality metrics
   - Encounter-based queries
   - Delegated access models for care coordination

3. **Data Availability & Standards Compliance**
   - Automatic conversion of all data formats to FHIR
   - AI-powered record locator for patient matching
   - National provider directory with 8+ million healthcare providers

4. **Network Connectivity & Transparency**
   - **1.8M+ provider connections**
   - **300+ payer connections**
   - TEFCA integration
   - HINs and HIEs connectivity
   - Medicare Blue Button 2.0 (CARIN IG)
   - VA integration
   - Proprietary pharmacy and laboratory networks
   - Patient Access APIs for providers and payers

5. **Identity, Security & Trust**
   - HITRUST certification
   - IAL2-compliant identity verification
   - Passwordless authentication via CLEAR
   - Facial recognition for identity (like boarding a plane)

### "Kill the Clipboard" Initiative

**What it is**: Federal initiative to eliminate paper forms and disconnected patient portals

**b.well's Implementation**:
- Medical record access through facial recognition (no usernames/passwords)
- Instant health data sharing with providers using QR codes
- SMART Health Links for secure data exchange
- Automatic digital visit summaries and care plans
- Real-time data sharing at point of care
- Smartphones as the "front door" of healthcare

**Partnership**: Samsung and b.well bringing this to life through Samsung Health integration

**Goal**: Eradicate "portalitis" - the frustrating experience of navigating dozens of disconnected login portals

## Major Partnerships

### OpenAI Partnership (January 2026)

**Announcement**: OpenAI selected b.well to power secure health data connectivity for AI-driven health experiences in ChatGPT

**What it enables**:
- Users can authorize ChatGPT to access their health data and medical records
- Secure, consumer-controlled health data sharing
- AI-powered health insights within ChatGPT
- b.well provides the clinical data network integration

**Significance**: b.well is integrating a complete clinical data network, not just a single data source (unlike other launch partners)

### Samsung Partnership

**Product**: Samsung Health integration

**What it enables**:
- Personalized healthcare experiences through Samsung devices
- Smartphones as the "front door" of healthcare
- "Kill the Clipboard" initiative implementation
- Shoppable healthcare experiences
- End-to-end consumer experience aligned with federal initiatives

**Technology**: b.well's FHIR-based platform unifies healthcare data within Samsung Health ecosystem

### Google Partnership (October 2025)

**Purpose**: Unlock the potential of personalized health through AI

**Focus**: Advancing AI-powered personalized health experiences

**Technology**: Leverages b.well's FHIR-based platform and longitudinal health records

### Perplexity Partnership (March 2026)

**What it enables**:
- Trusted health data integration with Perplexity AI search
- Personalized health answers grounded in user's actual health records
- Secure health record connectivity for AI-powered search

**Technology**: b.well's FHIR-enabled platform connects patient health records to Perplexity's AI

### athenahealth Partnership (February 2026)

**Focus**: Digital health data sharing

**Purpose**: Enable better data connectivity and interoperability

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

### "What is the Helix FHIR Server?"

The Helix FHIR Server is b.well's open-source, highly scalable FHIR server implementation that powers their platform. It's available on GitHub (https://github.com/icanbwell/fhir-server) and provides enterprise-grade FHIR capabilities including real-time streaming, GraphQL support, advanced search, and integration with Kafka and ClickHouse. It's built on Node.js and MongoDB, with full support for all FHIR resources and operations.

### "What makes b.well different?"

Three key differentiators:
1. **Most comprehensive data integration**: 1.8M+ providers, 300+ payers, 350+ sources
2. **AI-first architecture**: Data specifically prepared for AI applications with semantic interoperability
3. **Proven partnerships**: Selected by OpenAI, Samsung, Google for health data connectivity
4. **CMS-Aligned Network**: Committed to federal interoperability standards
5. **Open source foundation**: Helix FHIR Server available on GitHub

### "How long does it take to deploy bailey?"

Weeks, not months. Traditional build: 18-24 months and millions of dollars. With b.well's SDK and platform, organizations can deploy in weeks.

### "Is b.well HIPAA compliant?"

Yes. Also SOC 2 and HITRUST certified, with enterprise-level encryption, audit trails, and IAL2-compliant identity verification.

### "Can we customize bailey?"

Yes. Bailey is white-label ready with fully customizable UI. Organizations can also build custom AI agents or integrate third-party agents using the b.well Health AI SDK.

### "What data sources does b.well integrate?"

350+ sources including:
- 1.8M+ provider connections
- 300+ payer connections
- EHR systems
- Insurance claims
- Pharmacy systems
- Wearable devices
- Lab systems
- Imaging centers
- Patient portals
- TEFCA
- HINs and HIEs
- Medicare Blue Button 2.0
- VA systems

### "How does b.well handle data privacy?"

- Consumer-first privacy model
- Built on CARIN Alliance Code of Conduct
- DiMe Seal from Digital Medicine Society
- Consumer-directed data sharing
- Transparent consent processes via FHIR Consent resources
- User controls over data access
- Granular permissions with real-time revocation
- HITRUST certification

### "What is the CMS-Aligned Network?"

A voluntary framework launched by CMS to modernize healthcare data exchange. b.well committed in July 2025 to meet federal standards for secure, standards-based health data exchange. This includes patient-directed access, FHIR API-based exchange, and consumer-facing tools. b.well was among the first 60 companies to make this commitment.

### "What is 'Kill the Clipboard'?"

A federal initiative to eliminate paper forms and disconnected patient portals. b.well and Samsung are implementing this by enabling medical record access through facial recognition, instant data sharing via QR codes, and using smartphones as the "front door" of healthcare. The goal is to eradicate "portalitis" - navigating dozens of disconnected portals.

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

## Examples

### Example 1: Explaining Helix FHIR Server

**User**: "What is the Helix FHIR Server?"

**Response**: "The Helix FHIR Server is b.well Connected Health's open-source, highly scalable FHIR server implementation that powers their platform. It's available on GitHub at https://github.com/icanbwell/fhir-server under the Apache 2.0 license. Key features include support for all FHIR resources, real-time data streaming, change event tracking, GraphQL and REST APIs, advanced search capabilities, authentication and authorization, and integrations with Kafka for event streaming and ClickHouse for scalability. It's built on Node.js and MongoDB, containerized with Docker, and ready for Kubernetes deployment. The server includes custom operations like $merge for data integration, $graph for GraphDefinition support, and $everything for retrieving complete patient records."

### Example 2: Explaining bailey

**User**: "What is bailey?"

**Response**: "bailey is b.well Connected Health's white-label AI health assistant that organizations can embed directly into their own applications. Launched in February 2026, bailey enables consumers to move from health questions to actual actions - like finding care, scheduling appointments, managing medications, or navigating benefits - all in a single conversation. Unlike general-purpose AI assistants, bailey is grounded in complete longitudinal health records and built specifically for healthcare workflows using an agentic AI architecture that orchestrates multiple specialized agents. Organizations can deploy bailey in weeks using b.well's SDK (available for web, iOS, and Android) rather than spending 18-24 months building their own AI assistant from scratch. Bailey was trained on millions of patient records and is healthcare-grade with HIPAA, SOC 2, and HITRUST certifications."

### Example 3: Explaining CMS-Aligned Network

**User**: "What is b.well's involvement with the CMS-Aligned Network?"

**Response**: "In July 2025, b.well Connected Health committed to becoming a CMS-Aligned Network under the newly launched CMS Interoperability Framework. They were among the first 60 companies to make this voluntary commitment to meet federal standards for secure, standards-based health data exchange. b.well's production environment already supports all five key areas: patient access & empowerment (FHIR APIs with OAuth2), provider access & delegation (chart notes, clinical documents), data availability & standards compliance (automatic FHIR conversion, 8M+ provider directory), network connectivity (1.8M+ providers, 300+ payers, TEFCA, HIEs), and identity, security & trust (HITRUST certified, IAL2-compliant identity via CLEAR). This commitment validates b.well's decade-long vision that true interoperability requires open standards, consumer empowerment, and semantic understanding beyond just data exchange."

### Example 4: Explaining partnerships

**User**: "Why did OpenAI choose b.well?"

**Response**: "OpenAI selected b.well in January 2026 to power secure health data connectivity for AI-driven health experiences in ChatGPT. This partnership is significant because b.well is integrating a complete clinical data network - not just a single data source like other launch partners. b.well's FHIR-based platform can securely connect users' health records from 1.8M+ providers, 300+ payers, and 350+ data sources, creating the comprehensive health context needed for AI to provide meaningful, personalized health insights. The integration enables ChatGPT users to authorize access to their medical records through consumer-controlled data sharing and receive AI-powered health guidance grounded in their actual longitudinal health data. b.well's semantic interoperability ensures the data is not just exchanged but truly understood by the AI."

### Example 5: Explaining Kill the Clipboard

**User**: "What is 'Kill the Clipboard'?"

**Response**: "'Kill the Clipboard' is a federal initiative to eliminate paper forms and disconnected patient portals in healthcare. b.well Connected Health and Samsung are bringing this to life through their partnership. The implementation includes medical record access through facial recognition (no usernames or passwords needed), instant health data sharing with providers using QR codes and SMART Health Links, automatic digital visit summaries, and using smartphones as the 'front door' of healthcare. The goal is to eradicate 'portalitis' - the frustrating experience of navigating dozens of disconnected login portals to access your own health information. As b.well CEO Kristen Valdes says: 'If you can board a plane with just facial recognition, you should be able to access your health data just as easily.' This is part of b.well's commitment to the CMS-Aligned Network and their philosophy that data belongs to patients."

## Edge Cases

### User asks about competitors

Provide factual information about b.well without making comparative claims about competitors unless you have specific, sourced information.

### User asks about pricing

Pricing information is not publicly available. Direct them to contact b.well at contact@icanbwell.com or www.bwell.com for pricing inquiries.

### User asks about specific technical implementation

For detailed technical specifications beyond what's documented here, recommend:
- Checking the Helix FHIR Server GitHub repository: https://github.com/icanbwell/fhir-server
- Reviewing the SDK examples: https://github.com/icanbwell/bwell-sdk-example
- Contacting b.well's technical team at contact@icanbwell.com
- Applying for developer portal access: https://insights.icanbwell.com/cms_network

### User asks about clinical accuracy or medical advice

Clarify that b.well provides a platform and tools, but clinical accuracy depends on the underlying health data and how organizations implement the platform. b.well does not provide medical advice - their tools enable healthcare organizations to deliver better experiences.

### User confuses b.well with other companies

b.well Connected Health (icanbwell.com) is distinct from:
- Other "well" named health companies
- Personal health record (PHR) companies
- EHR vendors
- Health insurance companies

Clarify that b.well is a healthcare data platform and AI infrastructure provider with an open-source FHIR server foundation.

### User asks about open source vs. proprietary

The Helix FHIR Server is open source (Apache 2.0 license) and available on GitHub. However, the full b.well platform including bailey, the Health AI SDK, the 13-step data refinery, and other proprietary components are commercial products. Organizations can use the open-source FHIR server independently or leverage the full commercial platform.

### User asks about TEFCA or other interoperability standards

b.well supports multiple interoperability frameworks:
- TEFCA (Trusted Exchange Framework and Common Agreement)
- FHIR (Fast Healthcare Interoperability Resources)
- US Core V3
- CARIN IG (Consumer Access to Records and Information)
- OAuth2/OpenID Connect
- SMART on FHIR

They are committed to open standards and the CMS Interoperability Framework.
