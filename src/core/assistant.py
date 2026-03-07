"""
Multi-Industry AI Assistant — Core Engine
Architect: Kehinde (Kenny) Samson Ogunlowo
Industries: Healthcare, Finance, Oil & Gas
Built on real enterprise AI deployments at Cigna, Ceretax, and Patterson UTI
"""

import asyncio
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional, AsyncGenerator
from enum import Enum
import uuid
from datetime import datetime

logger = logging.getLogger(__name__)


class Industry(str, Enum):
    HEALTHCARE = "healthcare"
    FINANCE = "finance"
    OIL_GAS = "oil_gas"


class ComplianceFramework(str, Enum):
    HIPAA = "hipaa"
    SOX = "sox"
    FINRA = "finra"
    API_1130 = "api_1130"       # American Petroleum Institute
    ISO_55001 = "iso_55001"     # Asset Management (Oil & Gas)
    SEC_REG = "sec_regulation"


@dataclass
class ConversationContext:
    session_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    industry: Optional[Industry] = None
    user_role: Optional[str] = None
    compliance_frameworks: list[ComplianceFramework] = field(default_factory=list)
    conversation_history: list[dict] = field(default_factory=list)
    metadata: dict = field(default_factory=dict)
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())


@dataclass
class AssistantResponse:
    content: str
    industry: Industry
    compliance_disclaimers: list[str]
    sources: list[dict]
    confidence_score: float
    session_id: str
    requires_human_review: bool = False
    pii_detected: bool = False
    audit_log_id: Optional[str] = None


class IndustryPlugin(ABC):
    """Base class for industry-specific AI plugins."""

    @property
    @abstractmethod
    def industry(self) -> Industry:
        pass

    @property
    @abstractmethod
    def compliance_frameworks(self) -> list[ComplianceFramework]:
        pass

    @abstractmethod
    async def augment_system_prompt(self, base_prompt: str, context: ConversationContext) -> str:
        """Add industry-specific instructions to the system prompt."""
        pass

    @abstractmethod
    async def post_process_response(self, response: str, context: ConversationContext) -> AssistantResponse:
        """Apply industry-specific post-processing (PII scrubbing, disclaimers, etc.)."""
        pass

    @abstractmethod
    async def validate_query(self, query: str, context: ConversationContext) -> tuple[bool, str]:
        """Validate if query is appropriate for this industry context."""
        pass


class MultiIndustryAssistant:
    """
    Orchestrates industry-specific AI assistance with compliance guardrails.
    Supports Healthcare (HIPAA), Finance (SOX/FINRA), and Oil & Gas (API standards).
    
    Architecture pattern used at: Cigna AI initiatives, Ceretax tax AI, Patterson UTI operations.
    """

    BASE_SYSTEM_PROMPT = """You are an expert enterprise AI assistant with deep knowledge 
    across multiple regulated industries. You provide accurate, compliance-aware responses 
    grounded in authoritative sources. You clearly distinguish between factual information 
    and opinions, always cite your reasoning, and flag when professional consultation is required.
    
    Core principles:
    1. Accuracy over speed — only answer what you know with high confidence
    2. Compliance-first — always surface relevant regulatory considerations  
    3. Transparency — explain your reasoning and acknowledge limitations
    4. Safety — escalate to human experts when appropriate
    """

    def __init__(
        self,
        llm_client,
        plugins: dict[Industry, IndustryPlugin],
        audit_service=None,
        pii_detector=None
    ):
        self.llm_client = llm_client
        self.plugins = plugins
        self.audit_service = audit_service
        self.pii_detector = pii_detector

    async def chat(
        self,
        query: str,
        context: ConversationContext,
        stream: bool = False
    ) -> AssistantResponse:
        """Main entry point for multi-turn conversation."""
        
        logger.info(f"Processing query for session {context.session_id}, industry: {context.industry}")

        # Get industry plugin
        plugin = self.plugins.get(context.industry)
        if not plugin:
            raise ValueError(f"No plugin registered for industry: {context.industry}")

        # Validate query
        is_valid, rejection_reason = await plugin.validate_query(query, context)
        if not is_valid:
            logger.warning(f"Query rejected: {rejection_reason}")
            return AssistantResponse(
                content=f"I'm unable to process this request: {rejection_reason}",
                industry=context.industry,
                compliance_disclaimers=[rejection_reason],
                sources=[],
                confidence_score=0.0,
                session_id=context.session_id,
                requires_human_review=True
            )

        # PII detection (HIPAA and Finance critical)
        pii_detected = False
        if self.pii_detector:
            pii_detected = await self.pii_detector.scan(query)
            if pii_detected and context.industry == Industry.HEALTHCARE:
                logger.warning(f"PII detected in healthcare query, session: {context.session_id}")
                query = await self.pii_detector.redact(query)

        # Build augmented system prompt
        system_prompt = await plugin.augment_system_prompt(self.BASE_SYSTEM_PROMPT, context)

        # Prepare messages with conversation history
        messages = self._build_messages(query, context)

        # Call LLM
        raw_response = await self.llm_client.complete(
            system=system_prompt,
            messages=messages,
            temperature=0.2,  # Low temp for factual/compliance work
            max_tokens=2048
        )

        # Post-process through industry plugin
        response = await plugin.post_process_response(raw_response, context)
        response.pii_detected = pii_detected

        # Update conversation history
        context.conversation_history.append({"role": "user", "content": query})
        context.conversation_history.append({"role": "assistant", "content": response.content})

        # Audit logging (HIPAA/SOX requirement)
        if self.audit_service:
            response.audit_log_id = await self.audit_service.log(
                session_id=context.session_id,
                industry=context.industry.value,
                query_hash=hash(query),
                response_id=str(uuid.uuid4()),
                requires_review=response.requires_human_review
            )

        return response

    def _build_messages(self, query: str, context: ConversationContext) -> list[dict]:
        """Build message array with history for multi-turn conversation."""
        messages = []
        
        # Include last 10 turns for context (cost control)
        recent_history = context.conversation_history[-20:] if context.conversation_history else []
        messages.extend(recent_history)
        messages.append({"role": "user", "content": query})
        
        return messages
