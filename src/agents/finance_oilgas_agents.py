"""
Finance AI Agent
================
Author: Kehinde (Kenny) Samson Ogunlowo
Role:   Principal AI Infrastructure & Security Architect

SOX/FINRA-compliant financial AI assistant.
Implements Regulation BI guardrails, audit trail, and fiduciary disclaimers.

Compliance: SOX, FINRA Rule 2010, SEC Regulation BI, Dodd-Frank, Basel III
"""

from __future__ import annotations

import asyncio
import re
from dataclasses import dataclass
from enum import Enum
from typing import AsyncGenerator

import structlog

from ..shared.models import ChatRequest, ChatResponse, Citation, ConfidenceLevel
from .base_agent import BaseAgent, AgentConfig

logger = structlog.get_logger(__name__)


class FinancialRiskLevel(Enum):
    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"
    CRITICAL = "critical"


FINANCE_SYSTEM_PROMPT = """You are FinanceAI, an advanced financial information and regulatory 
compliance assistant developed by Citadel Cloud Management for enterprise use.

## YOUR ROLE
You support financial professionals, compliance officers, and analysts with:
- Financial regulatory interpretation (SOX, FINRA, Dodd-Frank, Basel III)
- Financial statement analysis and ratio interpretation  
- Risk framework Q&A (credit risk, market risk, operational risk)
- SEC filing analysis and disclosure guidance
- ESG reporting frameworks (TCFD, SASB, GRI)
- FinTech compliance and digital asset regulatory guidance
- Internal audit support

## MANDATORY GUARDRAILS — NEVER VIOLATE

### 1. NO INVESTMENT ADVICE (Regulation BI / FINRA Rule 2010)
You DO NOT provide:
- Specific buy/sell/hold recommendations for individual securities
- Personalized portfolio advice
- Price predictions or market timing guidance
You DO provide: financial education, regulatory information, framework analysis,
historical data context, and publicly available research summaries.

EVERY response about securities MUST include:
"This is not investment advice. Consult a registered investment advisor 
before making investment decisions."

### 2. MATERIAL NON-PUBLIC INFORMATION (MNPI) FILTER
If a query appears to involve MNPI or insider trading scenarios:
- Do not engage with the specific information
- Remind the user of SEC Rule 10b-5 and insider trading prohibitions
- Recommend consultation with legal/compliance counsel

### 3. SOX COMPLIANCE AWARENESS
For questions about financial reporting, internal controls, or auditing:
- Reference relevant SOX sections (302, 404, 409)
- Note certification requirements for executives
- Highlight control deficiency implications

### 4. AUDIT TRAIL NOTE
All interactions in regulated environments may be subject to FINRA record-keeping 
requirements (Rule 4511). Remind users in institutional settings as appropriate.

### 5. JURISDICTION AWARENESS
Financial regulations vary significantly by jurisdiction. Always note when your 
response covers US regulations vs. international frameworks (EU MiFID II, UK FCA, etc.)

## RESPONSE FORMAT

Structure financial responses as:
1. **Direct Answer** — Clear, concise response to the query
2. **Regulatory Framework** — Relevant rules, sections, or standards
3. **Practical Application** — How this applies in practice
4. **Risk Considerations** — Key risks to be aware of
5. **Sources** — SEC.gov, FINRA.org, BIS.org, FDIC.gov citations
6. **Disclaimer** — Investment/professional advice disclaimer as appropriate

Current date: {current_date}
Institutional context: {institution_context}
"""


OIL_GAS_SYSTEM_PROMPT = """You are SafetyAI, an advanced process safety and regulatory compliance 
assistant for the Oil & Gas industry, developed by Citadel Cloud Management.

## YOUR ROLE
You support operations engineers, safety professionals, and compliance teams with:
- Process Safety Management (OSHA 1910.119 / PSM) guidance
- Risk Management Program (EPA RMP) compliance
- Pipeline safety regulations (DOT PHMSA 49 CFR Parts 192/195)
- Offshore safety regulations (BSEE 30 CFR Parts 250/254)
- API standard interpretation (API RP 500, 505, 520, 521, 2218)
- Incident investigation support (root cause analysis frameworks)
- HAZOP/PHA process guidance
- Environmental compliance (EPA Clean Air Act, Subpart W GHG reporting)

## MANDATORY GUARDRAILS — NEVER VIOLATE

### 1. SAFETY-FIRST ABSOLUTE PRINCIPLE
Safety always takes precedence over production, schedule, or cost.
If ANY query involves an ACTIVE INCIDENT or EMERGENCY:
- IMMEDIATELY instruct to: stop work, activate emergency response plan, call emergency services
- Never provide operational guidance that could delay evacuation or emergency response

### 2. NO OVERRIDE OF SAFETY SYSTEMS
Never provide guidance that would justify bypassing, overriding, or defeating:
- Safety instrumented systems (SIS)
- Pressure relief devices
- Emergency shutdown systems (ESD)
- Fire and gas detection systems
Any inquiry about safety system bypass should be redirected to formal Management of Change (MOC) procedures.

### 3. REGULATORY CITATIONS REQUIRED
Every compliance response must cite:
- Specific CFR section (e.g., 29 CFR 1910.119(e) for PSM Process Hazard Analysis)
- Relevant API standard section
- PHMSA advisory or enforcement guidance where applicable

### 4. INCIDENT REPORTING AWARENESS
For queries involving near misses, incidents, or releases:
- Remind user of PSM incident investigation requirements (1910.119(m))
- Note OSHA 300 log requirements where applicable
- Note EPA emergency notification requirements (CERCLA 103, EPCRA 304)

### 5. REGION-SPECIFIC REGULATIONS
Operations differ significantly: onshore vs. offshore, US vs. international.
Always clarify which regulatory framework applies (OSHA, BSEE, IADC, IOGP, etc.)

## RESPONSE FORMAT

Structure O&G responses as:
1. **Safety Status** — Is there an immediate safety concern? Address first.
2. **Direct Answer** — Technical/regulatory response
3. **Regulatory Requirements** — Specific CFR sections, API standards
4. **Industry Best Practices** — IOGP guidelines, API recommended practices  
5. **Risk & Hazard Considerations** — Process hazards, environmental impact
6. **References** — OSHA.gov, PHMSA.dot.gov, API.org, BSEE.gov citations
7. **Disclaimer** — Engineering judgment disclaimer; recommend qualified PE review

Current date: {current_date}
Facility context: {facility_context}
"""


class FinanceAgent(BaseAgent):
    """
    SOX/FINRA-compliant Finance AI Agent.
    
    Provides financial analysis, regulatory interpretation, and 
    risk management support with mandatory investment disclaimer enforcement.
    """

    INVESTMENT_ADVICE_PATTERNS = [
        r"\b(should I|would you recommend|is it a good time to)\s+(buy|sell|invest|short)\b",
        r"\b(price target|stock pick|trade recommendation)\b",
        r"\bwill\s+\w+\s+(go up|go down|increase|decrease|rise|fall)\b",
    ]

    MNPI_PATTERNS = [
        r"\b(unreleased earnings|non-public|insider|undisclosed)\b",
        r"\b(merger|acquisition|takeover)\s+(rumor|leak|secret)\b",
    ]

    def __init__(self, config: AgentConfig, rag_pipeline, llm_client):
        super().__init__(config)
        self.rag = rag_pipeline
        self.llm = llm_client

    def _check_investment_advice_request(self, message: str) -> bool:
        """Detect if user is requesting specific investment advice."""
        for pattern in self.INVESTMENT_ADVICE_PATTERNS:
            if re.search(pattern, message, re.IGNORECASE):
                return True
        return False

    def _check_mnpi(self, message: str) -> bool:
        """Detect potential MNPI in query."""
        for pattern in self.MNPI_PATTERNS:
            if re.search(pattern, message, re.IGNORECASE):
                return True
        return False

    async def chat(
        self,
        request: ChatRequest,
        chat_history: list[dict],
    ) -> ChatResponse:
        log = logger.bind(session_id=request.session_id, industry="finance")

        # ── Regulation BI Guardrail ───────────────────────────────────────────
        if self._check_investment_advice_request(request.message):
            log.warning("investment_advice_request_blocked")
            return ChatResponse(
                response=(
                    "⚖️ **Regulation BI Compliance Notice**\n\n"
                    "I'm not able to provide specific investment recommendations "
                    "(buy/sell/hold advice) for individual securities. This complies with "
                    "SEC Regulation Best Interest (Reg BI) and FINRA Rule 2010.\n\n"
                    "**What I can help with instead:**\n"
                    "- Fundamental analysis frameworks and how to apply them\n"
                    "- Financial ratio interpretation and benchmarking\n"
                    "- Sector research methodologies\n"
                    "- Risk assessment frameworks\n"
                    "- Regulatory disclosures and filings analysis\n\n"
                    "Please rephrase your question around financial analysis concepts, "
                    "or consult a registered investment advisor (RIA) for personalized advice."
                ),
                citations=[],
                confidence=ConfidenceLevel.HIGH,
                compliance_flags=["REG_BI_GUARDRAIL", "INVESTMENT_ADVICE_BLOCKED"],
                industry="finance",
            )

        # ── MNPI Check ────────────────────────────────────────────────────────
        if self._check_mnpi(request.message):
            log.critical("potential_mnpi_detected")
            return ChatResponse(
                response=(
                    "🚨 **Compliance Alert — Potential MNPI**\n\n"
                    "Your query may involve Material Non-Public Information (MNPI). "
                    "Trading on or sharing MNPI violates SEC Rule 10b-5 and Section 10(b) "
                    "of the Securities Exchange Act of 1934.\n\n"
                    "I cannot engage with queries involving potential insider information.\n\n"
                    "**Recommended Actions:**\n"
                    "1. Consult your firm's Chief Compliance Officer immediately\n"
                    "2. Review your firm's information barrier policies\n"
                    "3. Do not trade on or share this information\n"
                    "4. Document this inquiry for your compliance records\n\n"
                    "FINRA and the SEC have sophisticated surveillance systems. "
                    "When in doubt, escalate to compliance."
                ),
                citations=[],
                confidence=ConfidenceLevel.HIGH,
                compliance_flags=["MNPI_DETECTED", "COMPLIANCE_ESCALATION_REQUIRED"],
                industry="finance",
            )

        # ── RAG Retrieval ─────────────────────────────────────────────────────
        retrieved_docs = await self.rag.retrieve(
            query=request.message,
            namespace="finance",
            top_k=5,
            min_score=0.7,
        )
        context = self.rag.format_context(retrieved_docs)

        # ── Generate Response ─────────────────────────────────────────────────
        from datetime import datetime
        from langchain_core.messages import HumanMessage, SystemMessage

        messages = [
            SystemMessage(content=OIL_GAS_SYSTEM_PROMPT.replace(
                "{current_date}", datetime.now().strftime("%B %d, %Y")
            ).replace(
                "{facility_context}", request.metadata.get("facility", "General Finance Operations")
            )),
        ]
        messages.append(HumanMessage(
            content=f"{request.message}\n\n## Retrieved Context\n{context}"
        ))

        # Use FINANCE system prompt (fix the variable above)
        messages[0] = SystemMessage(content=FINANCE_SYSTEM_PROMPT.replace(
            "{current_date}", datetime.now().strftime("%B %d, %Y")
        ).replace(
            "{institution_context}", request.metadata.get("institution", "Financial Institution")
        ))

        response = await self.llm.ainvoke(messages)

        # Ensure disclaimer is present
        response_text = response.content
        if "investment advice" not in response_text.lower():
            response_text += (
                "\n\n---\n⚠️ *This is not investment advice. Consult a registered "
                "investment advisor (RIA) before making investment decisions. "
                "Past performance does not guarantee future results.*"
            )

        citations = [
            Citation(
                source=doc.metadata.get("source", ""),
                title=doc.metadata.get("title", ""),
                url=doc.metadata.get("url"),
                relevance_score=doc.metadata.get("score", 0.0),
            )
            for doc in retrieved_docs
        ]

        return ChatResponse(
            response=response_text,
            citations=citations,
            confidence=ConfidenceLevel.HIGH if retrieved_docs else ConfidenceLevel.MEDIUM,
            compliance_flags=["INVESTMENT_DISCLAIMER_APPENDED"],
            industry="finance",
        )


class OilGasAgent(BaseAgent):
    """
    OSHA PSM / EPA RMP compliant Oil & Gas Process Safety AI Agent.
    
    Provides process safety guidance, regulatory interpretation, and
    incident support with mandatory safety-first guardrails.
    """

    EMERGENCY_KEYWORDS = [
        "gas leak", "gas release", "fire", "explosion", "blowout", "spill",
        "H2S", "hydrogen sulfide", "vapor cloud", "evacuation", "MAOP exceeded",
        "over-pressure", "toxic release", "injury", "fatality", "emergency"
    ]

    SAFETY_OVERRIDE_PATTERNS = [
        r"\b(bypass|override|disable|defeat|circumvent)\s+(safety|SIS|ESD|PSV|relief|shutdown)\b",
        r"\b(disable|remove|block)\s+(alarm|trip|interlock)\b",
    ]

    def __init__(self, config: AgentConfig, rag_pipeline, llm_client):
        super().__init__(config)
        self.rag = rag_pipeline
        self.llm = llm_client

    def _detect_emergency(self, message: str) -> bool:
        message_lower = message.lower()
        return any(kw in message_lower for kw in self.EMERGENCY_KEYWORDS)

    def _detect_safety_override_request(self, message: str) -> bool:
        for pattern in self.SAFETY_OVERRIDE_PATTERNS:
            if re.search(pattern, message, re.IGNORECASE):
                return True
        return False

    async def chat(
        self,
        request: ChatRequest,
        chat_history: list[dict],
    ) -> ChatResponse:
        log = logger.bind(session_id=request.session_id, industry="oil_gas")

        # ── Emergency Check ───────────────────────────────────────────────────
        if self._detect_emergency(request.message):
            log.critical("oilgas_emergency_detected")
            return ChatResponse(
                response=(
                    "🚨 **PROCESS SAFETY EMERGENCY — IMMEDIATE ACTION REQUIRED**\n\n"
                    "**EXECUTE EMERGENCY RESPONSE PLAN NOW:**\n\n"
                    "1. 🔴 **STOP ALL HOT WORK** — immediately\n"
                    "2. 📢 **ACTIVATE ALARM** — site emergency alarm/PA system\n"
                    "3. 🏃 **EVACUATE** — all non-essential personnel upwind/crosswind\n"
                    "4. 📞 **CALL EMERGENCY SERVICES** — 911 and site emergency number\n"
                    "5. 🚒 **NOTIFY INCIDENT COMMANDER** — via emergency radio/phone\n"
                    "6. ⛽ **IF SAFE TO DO SO** — activate Emergency Shutdown (ESD)\n\n"
                    "**DO NOT:**\n"
                    "- Re-enter the hazard zone\n"
                    "- Use non-intrinsically safe equipment in the hazard area\n"
                    "- Attempt to fight a large fire without training/equipment\n\n"
                    "**Regulatory Requirements:**\n"
                    "- OSHA 1910.119(n) — Emergency planning and response\n"
                    "- EPA 40 CFR Part 68 — Emergency contact within 15 minutes of release\n"
                    "- CERCLA Section 103 — Report releases above reportable quantities\n\n"
                    "After the emergency is controlled, I can assist with incident "
                    "investigation documentation per OSHA 1910.119(m)."
                ),
                citations=[],
                confidence=ConfidenceLevel.HIGH,
                compliance_flags=["PSM_EMERGENCY", "EPA_RMP_EMERGENCY", "OSHA_1910_119_N"],
                industry="oil_gas",
            )

        # ── Safety Override Check ─────────────────────────────────────────────
        if self._detect_safety_override_request(request.message):
            log.critical("safety_override_request_detected")
            return ChatResponse(
                response=(
                    "⛔ **Safety System Override — STOP**\n\n"
                    "I cannot provide guidance on bypassing, overriding, or defeating "
                    "safety systems. This includes SIS, ESD, PSVs, alarms, and interlocks.\n\n"
                    "**OSHA 1910.119(j)(1)(ii)** requires all safety systems to be maintained "
                    "in functional condition. Defeating safety systems without proper MOC "
                    "may constitute a willful violation.\n\n"
                    "**Required Process:**\n"
                    "1. Initiate formal **Management of Change (MOC)** procedure\n"
                    "2. Conduct **Pre-Startup Safety Review (PSSR)** if applicable\n"
                    "3. Obtain approval from operations, safety, and engineering\n"
                    "4. Implement temporary protective measures\n"
                    "5. Document and track the temporary override\n\n"
                    "Contact your Process Safety Engineer or Safety Manager."
                ),
                citations=[],
                confidence=ConfidenceLevel.HIGH,
                compliance_flags=["SAFETY_OVERRIDE_BLOCKED", "PSM_MOC_REQUIRED"],
                industry="oil_gas",
            )

        # ── RAG Retrieval ─────────────────────────────────────────────────────
        retrieved_docs = await self.rag.retrieve(
            query=request.message,
            namespace="oilgas",
            top_k=5,
            min_score=0.7,
        )
        context = self.rag.format_context(retrieved_docs)

        # ── Generate Response ─────────────────────────────────────────────────
        from datetime import datetime
        from langchain_core.messages import HumanMessage, SystemMessage

        messages = [
            SystemMessage(content=OIL_GAS_SYSTEM_PROMPT.replace(
                "{current_date}", datetime.now().strftime("%B %d, %Y")
            ).replace(
                "{facility_context}", request.metadata.get("facility", "General O&G Facility")
            )),
            HumanMessage(content=f"{request.message}\n\n## Retrieved Context\n{context}")
        ]

        response = await self.llm.ainvoke(messages)
        response_text = response.content

        # Ensure engineering disclaimer
        if "qualified" not in response_text.lower() and "engineer" not in response_text.lower():
            response_text += (
                "\n\n---\n⚙️ *This information is for general guidance only. "
                "All process safety decisions should be reviewed by a qualified "
                "Process Safety Engineer and comply with your site-specific "
                "Process Safety Management program.*"
            )

        citations = [
            Citation(
                source=doc.metadata.get("source", ""),
                title=doc.metadata.get("title", ""),
                url=doc.metadata.get("url"),
                relevance_score=doc.metadata.get("score", 0.0),
            )
            for doc in retrieved_docs
        ]

        return ChatResponse(
            response=response_text,
            citations=citations,
            confidence=ConfidenceLevel.HIGH if retrieved_docs else ConfidenceLevel.MEDIUM,
            compliance_flags=["PSM_DISCLAIMER"],
            industry="oil_gas",
        )
