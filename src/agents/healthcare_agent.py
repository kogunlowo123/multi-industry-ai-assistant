"""
Healthcare AI Agent
===================
Author: Kehinde (Kenny) Samson Ogunlowo
Role:   Principal AI Infrastructure & Security Architect

HIPAA-compliant AI assistant for clinical decision support.
Implements PHI detection, clinical guardrails, and evidence-based responses.

Compliance: HIPAA 45 CFR Part 164, FDA 21 CFR Part 11, HL7 FHIR R4
"""

from __future__ import annotations

import asyncio
import logging
import re
from dataclasses import dataclass, field
from enum import Enum
from typing import AsyncGenerator, Optional

import structlog
from langchain.callbacks.streaming_stdout import StreamingStdOutCallbackHandler
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_openai import AzureChatOpenAI

from ..rag.pipeline import RAGPipeline
from ..guardrails.phi_detector import PHIDetector
from ..shared.models import ChatRequest, ChatResponse, Citation, ConfidenceLevel
from .base_agent import BaseAgent, AgentConfig

logger = structlog.get_logger(__name__)


class ClinicalUrgency(Enum):
    ROUTINE = "routine"
    URGENT = "urgent"
    EMERGENCY = "emergency"
    LIFE_THREATENING = "life_threatening"


# PHI patterns for detection (HIPAA Safe Harbor identifiers)
PHI_PATTERNS = {
    "ssn": r"\b\d{3}-\d{2}-\d{4}\b",
    "mrn": r"\b(MRN|Medical Record Number)[:\s]*[A-Z0-9\-]{6,15}\b",
    "dob": r"\b(DOB|Date of Birth|Born)[:\s]*\d{1,2}[/\-]\d{1,2}[/\-]\d{2,4}\b",
    "phone": r"\b(\+1[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b",
    "email": r"\b[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Z|a-z]{2,}\b",
    "npi": r"\b(NPI)[:\s]*\d{10}\b",
    "name_pattern": r"\b(Patient|Pt|Mr\.|Mrs\.|Ms\.|Dr\.)\s+[A-Z][a-z]+\s+[A-Z][a-z]+\b",
}

EMERGENCY_KEYWORDS = [
    "chest pain", "difficulty breathing", "cannot breathe", "stroke", "seizure",
    "unconscious", "unresponsive", "severe bleeding", "overdose", "heart attack",
    "myocardial infarction", "cardiac arrest", "anaphylaxis", "anaphylactic",
    "sepsis", "septic shock", "suicidal", "suicide", "self-harm", "overdosed"
]


@dataclass
class HealthcareAgentConfig(AgentConfig):
    """Configuration specific to the healthcare agent."""
    model_name: str = "gpt-4o"
    temperature: float = 0.1  # Low temperature for clinical accuracy
    max_tokens: int = 2048
    enable_phi_detection: bool = True
    enable_streaming: bool = True
    require_citations: bool = True
    citation_sources: list[str] = field(default_factory=lambda: [
        "PubMed", "FDA", "CDC", "WHO", "UpToDate", "Clinical Guidelines"
    ])


HEALTHCARE_SYSTEM_PROMPT = """You are ClinicalAI, an advanced healthcare information assistant built for 
healthcare professionals and administrators. You were developed by Citadel Cloud Management.

## YOUR ROLE
You support clinical staff, healthcare administrators, and informed patients with:
- Clinical information and medical literature synthesis
- Drug interaction analysis and pharmacology information  
- ICD-10/CPT coding guidance and documentation support
- FHIR R4 resource structure guidance
- Healthcare regulatory (HIPAA, CMS, Joint Commission) Q&A
- Clinical workflow optimization

## MANDATORY GUARDRAILS — NEVER VIOLATE

### 1. NEVER provide a definitive diagnosis
You provide clinical INFORMATION and educational content only. Always direct to licensed 
healthcare providers for diagnosis, treatment decisions, and prescribing.

### 2. ALWAYS cite authoritative sources
Every clinical claim must reference: PubMed DOI, FDA labeling, clinical guidelines 
(AHA, ADA, ACOG, etc.), or peer-reviewed medical literature.

### 3. EMERGENCY ESCALATION — IMMEDIATE PRIORITY
If ANY message suggests a medical emergency (chest pain, difficulty breathing, stroke symptoms,
overdose, severe bleeding, anaphylaxis, sepsis), IMMEDIATELY respond:
"🚨 MEDICAL EMERGENCY — CALL 911 (US) or your local emergency services immediately. 
Do not wait. This is time-sensitive."
Then provide basic first aid guidance while waiting for emergency services.

### 4. PHI PROTECTION
Never store, reference, or encourage sharing of Protected Health Information (PHI).
If PHI is detected in input, acknowledge the query without repeating the PHI,
and remind the user not to share patient identifiers.

### 5. PEDIATRIC AND VULNERABLE POPULATION CAUTION
Apply extra caution for queries involving:
- Pediatric patients (weight-based dosing, age-specific considerations)
- Pregnant patients (teratogenicity, pregnancy categories)
- Elderly patients (polypharmacy, renal/hepatic adjustments)
- Immunocompromised patients

### 6. MEDICATION SAFETY
For all medication discussions:
- Include contraindications
- Note major drug-drug interactions
- Reference current FDA black box warnings where applicable
- Note generic vs. brand distinctions

## RESPONSE FORMAT

Structure clinical responses as:
1. **Direct Answer** (2-3 sentences addressing the query)
2. **Clinical Context** (relevant pathophysiology, mechanism)
3. **Evidence Base** (key studies, guidelines — with citations)
4. **Clinical Considerations** (contraindications, special populations, monitoring)
5. **References** (formatted citations with DOI/source links when available)
6. **Disclaimer** (appropriate professional consultation recommendation)

## TONE
Professional, precise, evidence-based. Use proper medical terminology with lay explanations 
where appropriate. Match the apparent clinical sophistication of the questioner.

Current date: {current_date}
Institution context: {institution_context}
"""


class HealthcareAgent(BaseAgent):
    """
    HIPAA-compliant Healthcare AI Agent.
    
    Provides evidence-based clinical decision support with mandatory 
    PHI detection, emergency escalation, and citation requirements.
    """

    def __init__(
        self,
        config: HealthcareAgentConfig,
        rag_pipeline: RAGPipeline,
        phi_detector: PHIDetector,
        llm_client: AzureChatOpenAI,
    ):
        super().__init__(config)
        self.config = config
        self.rag = rag_pipeline
        self.phi_detector = phi_detector
        self.llm = llm_client
        self._setup_chain()

        logger.info(
            "healthcare_agent_initialized",
            model=config.model_name,
            phi_detection=config.enable_phi_detection,
            citations_required=config.require_citations,
        )

    def _setup_chain(self) -> None:
        """Build the LangChain conversation chain."""
        self.prompt = ChatPromptTemplate.from_messages([
            SystemMessage(content=HEALTHCARE_SYSTEM_PROMPT),
            MessagesPlaceholder(variable_name="chat_history"),
            HumanMessage(content="{input}\n\n## Retrieved Context\n{context}"),
        ])

        self.chain = (
            self.prompt
            | self.llm
            | StrOutputParser()
        )

    async def _detect_emergency(self, message: str) -> bool:
        """Check if message contains emergency indicators."""
        message_lower = message.lower()
        return any(keyword in message_lower for keyword in EMERGENCY_KEYWORDS)

    async def _detect_phi_in_input(self, message: str) -> dict[str, list[str]]:
        """Detect PHI patterns in user input."""
        detected = {}
        for phi_type, pattern in PHI_PATTERNS.items():
            matches = re.findall(pattern, message, re.IGNORECASE)
            if matches:
                detected[phi_type] = matches
        return detected

    async def _mask_phi_for_logging(self, text: str) -> str:
        """Mask PHI before logging (audit compliance)."""
        masked = text
        for phi_type, pattern in PHI_PATTERNS.items():
            replacement = f"[{phi_type.upper()}-REDACTED]"
            masked = re.sub(pattern, replacement, masked, flags=re.IGNORECASE)
        return masked

    async def _assess_clinical_urgency(self, message: str) -> ClinicalUrgency:
        """Assess the urgency level of the clinical query."""
        message_lower = message.lower()

        life_threatening_terms = ["cardiac arrest", "code blue", "pulseless", "apnea"]
        emergency_terms = ["chest pain", "stroke", "seizure", "overdose", "anaphylaxis"]
        urgent_terms = ["fever", "elevated troponin", "abnormal labs", "declining"]

        if any(t in message_lower for t in life_threatening_terms):
            return ClinicalUrgency.LIFE_THREATENING
        elif any(t in message_lower for t in emergency_terms):
            return ClinicalUrgency.EMERGENCY
        elif any(t in message_lower for t in urgent_terms):
            return ClinicalUrgency.URGENT
        return ClinicalUrgency.ROUTINE

    async def chat(
        self,
        request: ChatRequest,
        chat_history: list[dict],
    ) -> ChatResponse:
        """
        Process a healthcare query with full guardrail stack.
        
        Flow:
        1. PHI detection in input
        2. Emergency check
        3. RAG context retrieval
        4. LLM response generation
        5. Response safety validation
        6. Compliance metadata attachment
        """
        log = logger.bind(
            session_id=request.session_id,
            industry="healthcare",
            message_preview=await self._mask_phi_for_logging(request.message[:50])
        )

        # ── Step 1: PHI Detection ─────────────────────────────────────────────
        phi_detected = {}
        if self.config.enable_phi_detection:
            phi_detected = await self._detect_phi_in_input(request.message)
            if phi_detected:
                phi_types = ", ".join(phi_detected.keys())
                log.warning("phi_detected_in_input", phi_types=phi_types)
                # Return PHI warning without processing the PHI
                return ChatResponse(
                    response=(
                        f"⚠️ **PHI Detected in Your Message**\n\n"
                        f"Your message appears to contain Protected Health Information: "
                        f"**{phi_types}**.\n\n"
                        f"For HIPAA compliance, please remove patient identifiers "
                        f"(name, MRN, DOB, SSN, phone, email) before submitting clinical queries.\n\n"
                        f"You can rephrase your question without the specific patient "
                        f"identifiers and I'll be happy to help."
                    ),
                    citations=[],
                    confidence=ConfidenceLevel.HIGH,
                    compliance_flags=["PHI_DETECTED", "HIPAA_GUARDRAIL_TRIGGERED"],
                    industry="healthcare",
                )

        # ── Step 2: Emergency Check ───────────────────────────────────────────
        is_emergency = await self._detect_emergency(request.message)
        if is_emergency:
            urgency = await self._assess_clinical_urgency(request.message)
            log.critical("emergency_detected", urgency=urgency.value)

            emergency_response = (
                "🚨 **MEDICAL EMERGENCY DETECTED**\n\n"
                "**CALL 911 (or your local emergency number) IMMEDIATELY.**\n\n"
                "Do not delay. Time-critical emergencies require immediate professional intervention.\n\n"
                "---\n\n"
                "**While waiting for emergency services:**\n"
            )

            # Add basic first aid guidance based on urgency type
            message_lower = request.message.lower()
            if "cardiac arrest" in message_lower or "not breathing" in message_lower:
                emergency_response += (
                    "- Begin CPR if the person is unresponsive and not breathing normally\n"
                    "- 30 chest compressions to 2 rescue breaths (or hands-only CPR)\n"
                    "- Use AED if available\n"
                )
            elif "choking" in message_lower:
                emergency_response += (
                    "- Perform Heimlich maneuver for conscious adult\n"
                    "- Back blows and chest thrusts for infants\n"
                )

            emergency_response += (
                "\n---\n\n"
                "I can provide medical information after the emergency is addressed. "
                "This is not a substitute for emergency medical care."
            )

            return ChatResponse(
                response=emergency_response,
                citations=[],
                confidence=ConfidenceLevel.HIGH,
                compliance_flags=["EMERGENCY_ESCALATION", f"URGENCY_{urgency.value.upper()}"],
                industry="healthcare",
            )

        # ── Step 3: RAG Retrieval ─────────────────────────────────────────────
        log.info("retrieving_clinical_context")
        retrieved_docs = await self.rag.retrieve(
            query=request.message,
            namespace="healthcare",
            top_k=5,
            min_score=0.75,
        )

        context = self.rag.format_context(retrieved_docs)
        citations = [
            Citation(
                source=doc.metadata.get("source", "Unknown"),
                title=doc.metadata.get("title", ""),
                url=doc.metadata.get("url"),
                relevance_score=doc.metadata.get("score", 0.0),
            )
            for doc in retrieved_docs
        ]

        # ── Step 4: Format Chat History ───────────────────────────────────────
        formatted_history = []
        for msg in chat_history[-10:]:  # Last 10 turns (context window management)
            if msg["role"] == "user":
                formatted_history.append(HumanMessage(content=msg["content"]))
            elif msg["role"] == "assistant":
                formatted_history.append(AIMessage(content=msg["content"]))

        # ── Step 5: Generate Response ─────────────────────────────────────────
        from datetime import datetime
        log.info("generating_clinical_response", context_docs=len(retrieved_docs))

        response_text = await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: self.chain.invoke({
                "input": request.message,
                "context": context if context else "No relevant clinical context retrieved. Responding from training knowledge with appropriate caveats.",
                "chat_history": formatted_history,
                "current_date": datetime.now().strftime("%B %d, %Y"),
                "institution_context": request.metadata.get("institution", "General Healthcare Setting"),
            })
        )

        # ── Step 6: Response Validation ───────────────────────────────────────
        compliance_flags = []
        if not citations and self.config.require_citations:
            compliance_flags.append("NO_CITATIONS_RETRIEVED")
            response_text += (
                "\n\n---\n⚠️ *Note: This response is based on general medical knowledge. "
                "For the most current guidelines, consult authoritative sources such as "
                "PubMed, UpToDate, or specialty society guidelines.*"
            )

        # Ensure disclaimer is present
        disclaimer_terms = ["consult", "physician", "healthcare provider", "professional"]
        if not any(term in response_text.lower() for term in disclaimer_terms):
            response_text += (
                "\n\n---\n*⚕️ This information is for educational purposes only and does not "
                "constitute medical advice. Always consult a licensed healthcare provider for "
                "diagnosis and treatment decisions.*"
            )

        log.info(
            "healthcare_response_generated",
            response_length=len(response_text),
            citations_count=len(citations),
            compliance_flags=compliance_flags,
        )

        return ChatResponse(
            response=response_text,
            citations=citations,
            confidence=ConfidenceLevel.HIGH if retrieved_docs else ConfidenceLevel.MEDIUM,
            compliance_flags=compliance_flags,
            industry="healthcare",
            urgency=ClinicalUrgency.ROUTINE.value,
        )

    async def stream_chat(
        self,
        request: ChatRequest,
        chat_history: list[dict],
    ) -> AsyncGenerator[str, None]:
        """
        Streaming variant of chat for real-time UI updates.
        Runs guardrails before streaming begins.
        """
        # Run full guardrail stack first (non-streaming)
        phi_detected = await self._detect_phi_in_input(request.message)
        if phi_detected:
            yield "⚠️ PHI detected in your message. Please remove patient identifiers and resubmit."
            return

        is_emergency = await self._detect_emergency(request.message)
        if is_emergency:
            yield "🚨 MEDICAL EMERGENCY — CALL 911 IMMEDIATELY. Do not wait."
            return

        # Retrieve context
        retrieved_docs = await self.rag.retrieve(
            query=request.message,
            namespace="healthcare",
            top_k=5,
        )
        context = self.rag.format_context(retrieved_docs)

        # Stream LLM response
        async for chunk in self.llm.astream(
            self.prompt.format_messages(
                input=request.message,
                context=context,
                chat_history=[],
                current_date="",
                institution_context="",
            )
        ):
            if hasattr(chunk, 'content'):
                yield chunk.content
