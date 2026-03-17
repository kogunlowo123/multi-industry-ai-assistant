# Industry Adaptation Guide

## Overview
The `multi-industry-ai-assistant` provides a HIPAA/SOX/OSHA-compliant AI assistant with multi-industry regulatory intelligence. It uses LLM-powered natural language processing to interpret regulatory queries, retrieve relevant compliance documents via RAG, and generate actionable guidance tailored to specific industry frameworks. The system supports configurable compliance profiles for PHI/PII handling, audit logging, and data retention.

## Healthcare
### Compliance Requirements
- HIPAA, HITRUST, HL7 FHIR, 21st Century Cures Act
### Configuration Changes
- Set `INDUSTRY_PROFILE=hipaa` to activate healthcare compliance profile.
- Set `ENABLE_PHI_REDACTION=true` to enable automatic PHI detection and redaction before LLM processing.
- Set `RETENTION_DAYS=2190` (6 years) to meet HIPAA record retention requirements.
- Load healthcare regulatory corpus (45 CFR Parts 160-164) into the vector store.
- Configure audit logging to capture all PHI access events with user identity and timestamp.
- Add HIPAA-specific disclaimers to response formatting templates.
### Example Use Case
A hospital compliance team uses the assistant to answer questions about breach notification requirements (45 CFR 164.408), receiving grounded responses with specific regulatory citations, mandatory timelines, and step-by-step notification procedures.

## Finance
### Compliance Requirements
- SOX, PCI-DSS, SOC 2, Dodd-Frank
### Configuration Changes
- Set `INDUSTRY_PROFILE=sox` to activate financial compliance profile.
- Set `RETENTION_DAYS=2555` (7 years) to meet SOX record retention requirements.
- Load financial regulatory corpus (Sarbanes-Oxley Act, SEC regulations, PCAOB standards) into the vector store.
- Configure audit logging with immutable storage for SOX audit trail requirements.
- Enable financial data classification tags on all queries and responses.
- Add SOX-specific disclaimers about professional judgment and auditor consultation.
### Example Use Case
A finance team uses the assistant to understand Section 404 internal control requirements, receiving guidance on control testing procedures, documentation standards, and management certification obligations with specific SOX section citations.

## Industrial Safety (OSHA)
### Compliance Requirements
- OSHA 29 CFR 1900-1999, ANSI standards, NFPA codes
### Configuration Changes
- Set `INDUSTRY_PROFILE=osha` to activate industrial safety compliance profile.
- Load OSHA regulatory corpus (29 CFR Parts 1903-1990) into the vector store.
- Configure incident reporting guidance aligned with 29 CFR 1904 recordkeeping requirements.
- Enable workplace hazard classification in query processing.
- Add safety-specific disclaimers about professional safety consultation.
### Example Use Case
A plant safety manager queries the assistant about fall protection requirements for elevated work platforms, receiving specific 29 CFR 1910.28 citations, guardrail specifications, training requirements, and documentation obligations.

## Government
### Compliance Requirements
- FedRAMP, NIST 800-53, CMMC, FISMA
### Configuration Changes
- Set `INDUSTRY_PROFILE=government` to activate government compliance profile.
- Load NIST 800-53 control catalog and FedRAMP requirements into the vector store.
- Configure CUI handling markers on queries and responses.
- Set `RETENTION_DAYS=2555` for federal record retention.
- Enable FIPS 140-2 compliant encryption for all data flows.
- Add government-specific disclaimers about classified information handling.
### Example Use Case
A federal contractor uses the assistant to map NIST 800-53 controls to their system security plan, receiving specific control descriptions, implementation guidance, and assessment procedures with NIST SP references.

## Education
### Compliance Requirements
- FERPA, COPPA, Title IX, ADA Section 508
### Configuration Changes
- Set `INDUSTRY_PROFILE=education` to activate education compliance profile.
- Load FERPA regulations (34 CFR Part 99) and COPPA rules into the vector store.
- Enable student record data classification in PHI/PII detection.
- Configure age-appropriate response filtering for COPPA compliance.
- Add education-specific disclaimers about institutional policy consultation.
### Example Use Case
A university registrar queries the assistant about directory information disclosure rules under FERPA, receiving specific 34 CFR 99.3 citations, opt-out requirements, and notification procedures.

## Cross-Industry Best Practices
- Always validate the compliance profile matches the query domain to prevent cross-contamination of regulatory guidance.
- Enable audit logging regardless of industry profile for traceability and accountability.
- Configure faithfulness validation thresholds (`FAITHFULNESS_THRESHOLD`) to prevent hallucinated regulatory citations.
- Regularly update the regulatory document corpus to reflect current regulations and amendments.
- Include disclaimers in all responses advising users to consult qualified professionals for binding legal or compliance decisions.
- Test retrieval accuracy with industry-specific evaluation datasets before production deployment.
- Configure data retention policies per industry requirements (6 years HIPAA, 7 years SOX, varies by industry).
