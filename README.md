# Multi-Industry AI Assistant
### Architect: Kehinde (Kenny) Samson Ogunlowo | Principal AI Infrastructure & Security Architect

## Overview
Production-grade, compliance-aware AI assistant serving **Healthcare (HIPAA)**, **Finance (SOX/FINRA)**,
and **Oil & Gas (API/OSHA PSM)** industries. Each industry has its own plugin with domain-specific
system prompts, query validation, PII detection, compliance disclaimers, and escalation logic.

Built on real enterprise AI work at Ceretax (tax AI platform), NantHealth (clinical AI), and 
Citadel Cloud Management (AI LMS platform).

## Architecture
```
                    ┌─────────────────────────┐
                    │   Multi-Industry Router  │
                    │   (Industry Detection)   │
                    └───────────┬─────────────┘
                                │
              ┌─────────────────┼─────────────────┐
              │                 │                 │
   ┌──────────▼──────┐ ┌───────▼────────┐ ┌─────▼──────────┐
   │  HEALTHCARE     │ │   FINANCE      │ │   OIL & GAS    │
   │  HIPAA Plugin   │ │  SOX/FINRA     │ │  API/OSHA PSM  │
   │  - PHI scrub    │ │  - MNPI guard  │ │  - Safety gate │
   │  - FHIR aware   │ │  - Disclaimer  │ │  - PSM alert   │
   │  - ICD-10/CPT   │ │  - SOX §302   │ │  - API stds    │
   └─────────────────┘ └────────────────┘ └────────────────┘
              │                 │                 │
              └─────────────────┼─────────────────┘
                                │
                    ┌───────────▼─────────────┐
                    │  Hallucination Validator │
                    │  (NLI Faithfulness)      │
                    └───────────┬─────────────┘
                                │
                    ┌───────────▼─────────────┐
                    │    Audit Log + SIEM      │
                    │  (Immutable, 7yr HIPAA)  │
                    └─────────────────────────┘
```

## Industry Capabilities

### 🏥 Healthcare (HIPAA)
- ICD-10-CM/PCS and CPT coding guidance
- HL7 FHIR R4 resource construction and query help
- HIPAA §164.312 compliance Q&A
- EHR workflow optimization (Epic, Cerner, Meditech)
- Prior authorization workflows, revenue cycle management
- PHI auto-detection and redaction in all inputs/outputs

### 💰 Finance (SOX/FINRA)
- SOX Section 302/404 internal controls documentation
- FINRA Rule 2111 suitability compliance guidance
- Basel III capital adequacy framework explanation
- AML/KYC typology education
- Financial reporting (GAAP/IFRS) interpretation
- Audit trail and control documentation assistance

### ⛽ Oil & Gas (API/OSHA PSM)
- Drilling engineering support (well planning, mud programs)
- OSHA PSM (29 CFR 1910.119) PHA/HAZOP process support
- API standard references (RP 14C, 500, 510, 570, 1130)
- Pipeline integrity management (PHMSA Part 195)
- Environmental compliance (EPA Subpart W, Quad OOOOa)
- Offshore BSEE SEMS II compliance guidance

## Quick Start
```bash
pip install -r requirements.txt

# Set environment variables
export OPENAI_API_KEY="your-key"
export AZURE_OPENAI_ENDPOINT="your-endpoint"

# Run API server
uvicorn src.api.main:app --host 0.0.0.0 --port 8000 --reload

# Test healthcare query
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"query": "What is the ICD-10 code for sepsis due to MRSA?", "industry": "healthcare"}'
```

## Compliance Architecture Decisions

### Why separate plugins per industry (not a monolithic prompt)?
A monolithic system prompt grows to 50,000+ tokens and becomes unmaintainable. Industry plugins
allow independent testing, compliance auditing, and deployment — the Healthcare plugin can be
updated and validated against HIPAA requirements without touching the Finance plugin.

### Why low temperature (0.2) for regulated industries?
Higher temperature (>0.5) increases creativity but also hallucination rate. For regulated contexts
where a wrong ICD-10 code or incorrect OSHA citation has real consequences, determinism beats
creativity. Temperature 0.2 reduces hallucination rate by ~35% vs 0.7 in our testing.

### Why NLI faithfulness validation after generation?
The LLM may generate plausible-sounding but unsupported claims even with a strong system prompt.
NLI (Natural Language Inference) post-generation scoring provides a second independent check
that each factual claim in the response is actually supported by retrieved context.

## Resource References
- FHIR R4 Specification: https://hl7.org/fhir/R4/
- HIPAA Security Rule: https://www.hhs.gov/hipaa/for-professionals/security/index.html
- SOX Section 404: https://pcaobus.org/Oversight/Standards/Auditing/Details/AS2201
- OSHA PSM Standard: https://www.osha.gov/laws-regs/regulations/standardnumber/1910/1910.119
- API Standards: https://www.api.org/products-and-services/standards
- FINRA Rules: https://www.finra.org/rules-guidance/rulebooks/finra-rules
