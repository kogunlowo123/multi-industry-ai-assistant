"""
Healthcare Industry Plugin — HIPAA-Aware AI Assistant
Architect: Kehinde (Kenny) Samson Ogunlowo
Based on experience at Cigna and NantHealth (FHIR/HL7 environments)
"""

import re
import logging
from typing import Optional
from ..core.assistant import IndustryPlugin, Industry, ComplianceFramework, ConversationContext, AssistantResponse

logger = logging.getLogger(__name__)

# HIPAA-prohibited topics without clinical context
RESTRICTED_TOPICS = [
    "prescribe", "diagnose", "treatment recommendation for specific patient",
    "alter medical records", "share patient data"
]

PHI_PATTERNS = [
    r'\b\d{3}-\d{2}-\d{4}\b',           # SSN
    r'\b\d{10}\b',                        # NPI (National Provider Identifier)  
    r'\bMRN[:\s]+\w+',                   # Medical Record Number
    r'\b[A-Z]{2}\d{6,}\b',              # Insurance ID patterns
    r'\bDOB[:\s]+\d{1,2}/\d{1,2}/\d{4}', # Date of Birth
]

HEALTHCARE_SYSTEM_EXTENSION = """
HEALTHCARE CONTEXT — HIPAA COMPLIANCE ACTIVE

You are assisting in a HIPAA-regulated healthcare environment. Additional rules:

MANDATORY BEHAVIORS:
1. Never generate, store, or transmit actual PHI (Protected Health Information)
2. When discussing patient scenarios, use anonymized/synthetic examples only  
3. Always recommend consultation with licensed clinicians for clinical decisions
4. Reference ICD-10, CPT, SNOMED CT, and LOINC codes accurately when relevant
5. Surface applicable CMS, FDA, or HIPAA regulatory guidance when relevant
6. Flag any HL7 FHIR R4 interoperability implications in data questions

CLINICAL DECISION SUPPORT GUARDRAIL:
- You MAY provide: general medical education, protocol explanations, coding guidance,
  operational workflows, regulatory compliance information, EHR optimization advice
- You MUST NOT: make diagnoses, prescribe treatments for specific patients, 
  interpret individual lab results as clinical advice, or contradict a treating clinician

FHIR RESOURCES you understand: Patient, Observation, Condition, MedicationRequest,
DiagnosticReport, Encounter, Practitioner, Organization, Coverage, Claim

When in doubt: recommend involving a licensed healthcare professional.
"""


class HealthcarePlugin(IndustryPlugin):
    """
    HIPAA-compliant healthcare AI plugin.
    
    Capabilities:
    - Clinical decision support (non-prescriptive)
    - HL7 FHIR R4 query assistance
    - ICD-10 / CPT coding guidance  
    - HIPAA compliance Q&A
    - EHR workflow optimization (Epic, Cerner, Meditech patterns)
    - Revenue cycle management support
    - Healthcare interoperability (HL7, HL7 FHIR, DICOM)
    """

    @property
    def industry(self) -> Industry:
        return Industry.HEALTHCARE

    @property
    def compliance_frameworks(self) -> list[ComplianceFramework]:
        return [ComplianceFramework.HIPAA]

    async def augment_system_prompt(self, base_prompt: str, context: ConversationContext) -> str:
        role_context = ""
        if context.user_role:
            role_context = f"\nUser Role: {context.user_role} — tailor technical depth accordingly."
        return base_prompt + HEALTHCARE_SYSTEM_EXTENSION + role_context

    async def post_process_response(self, response: str, context: ConversationContext) -> AssistantResponse:
        # Scan response for accidental PHI leakage
        phi_in_response = self._scan_for_phi(response)
        if phi_in_response:
            logger.critical(f"PHI detected in LLM response — redacting. Session: {context.session_id}")
            response = self._redact_phi(response)

        disclaimers = [
            "⚕️ This response is for informational purposes only and does not constitute medical advice.",
            "For clinical decisions, always consult a licensed healthcare professional.",
        ]
        
        if "diagnos" in response.lower() or "treatment" in response.lower():
            disclaimers.append(
                "🔴 Clinical decision support flagged — requires licensed clinician review before action."
            )

        requires_review = (
            "prescrib" in response.lower() or
            "specific patient" in response.lower() or
            phi_in_response
        )

        return AssistantResponse(
            content=response,
            industry=self.industry,
            compliance_disclaimers=disclaimers,
            sources=[
                {"name": "CMS.gov", "url": "https://www.cms.gov"},
                {"name": "HL7 FHIR R4", "url": "https://hl7.org/fhir/R4/"},
                {"name": "HHS HIPAA", "url": "https://www.hhs.gov/hipaa"}
            ],
            confidence_score=0.92 if not requires_review else 0.70,
            session_id=context.session_id,
            requires_human_review=requires_review,
            pii_detected=phi_in_response
        )

    async def validate_query(self, query: str, context: ConversationContext) -> tuple[bool, str]:
        query_lower = query.lower()
        for restricted in RESTRICTED_TOPICS:
            if restricted in query_lower:
                return False, f"Query involves restricted healthcare action: '{restricted}'. Escalating to clinical staff."
        
        # Check for embedded PHI in query
        if self._scan_for_phi(query):
            logger.warning("PHI detected in input query — will be redacted before processing")
        
        return True, ""

    def _scan_for_phi(self, text: str) -> bool:
        for pattern in PHI_PATTERNS:
            if re.search(pattern, text, re.IGNORECASE):
                return True
        return False

    def _redact_phi(self, text: str) -> str:
        for pattern in PHI_PATTERNS:
            text = re.sub(pattern, "[REDACTED-PHI]", text, flags=re.IGNORECASE)
        return text


class HealthcareQueryExamples:
    """Sample queries demonstrating healthcare assistant capabilities."""
    
    EXAMPLES = [
        {
            "query": "What are the ICD-10 codes for Type 2 Diabetes with CKD Stage 3?",
            "category": "Medical Coding",
            "expected_codes": ["E11.65", "N18.3"]
        },
        {
            "query": "How do I structure a FHIR R4 Bundle for an ADT A01 admission event?",
            "category": "HL7 FHIR Interoperability",
            "expected_resources": ["Encounter", "Patient", "Practitioner", "Location"]
        },
        {
            "query": "What are the HIPAA minimum necessary standard requirements for EHR access?",
            "category": "HIPAA Compliance",
            "reference": "45 CFR §164.514(d)"
        },
        {
            "query": "Explain the prior authorization workflow for specialty medications under Medicare Part D",
            "category": "Revenue Cycle Management",
            "cms_reference": "Medicare Part D Coverage Determination"
        }
    ]
