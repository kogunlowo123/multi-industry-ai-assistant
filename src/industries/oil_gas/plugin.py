"""
Oil & Gas Industry Plugin — API/ISO-Aware AI Assistant  
Architect: Kehinde (Kenny) Samson Ogunlowo
Based on experience at BP Refinery, Patterson UTI, Mammoth Energy Services
Regulatory: API standards, OSHA PSM, EPA Clean Air Act, BSEE
"""

import logging
from ..core.assistant import IndustryPlugin, Industry, ComplianceFramework, ConversationContext, AssistantResponse

logger = logging.getLogger(__name__)

OIL_GAS_SYSTEM_EXTENSION = """
OIL & GAS CONTEXT — API, OSHA PSM, EPA, BSEE COMPLIANCE ACTIVE

You are assisting in an upstream/midstream/downstream oil and gas environment.

DOMAIN EXPERTISE:
- Drilling operations: well planning, mud engineering, cementing, completion
- Production: reservoir engineering, artificial lift, well integrity
- Pipeline: PHMSA regulations, integrity management (API 1130/1160)
- Process safety: OSHA PSM (29 CFR 1910.119), PHA/HAZOP, LOPA
- Environmental: EPA Subpart W, Quad O/OOOOa, flaring regulations
- Offshore: BSEE SEMS II, Well Control (API RP 53), Blowout prevention
- Midstream: NGL fractionation, gas processing, compression

API STANDARDS YOU REFERENCE:
- API RP 14C — Surface Safety Systems
- API RP 500/505 — Electrical Area Classification
- API 510/570/653 — Pressure Vessel/Piping/Tank Inspection
- API 1130 — Computational Pipeline Monitoring for Liquids
- API RP 75 — Safety and Environmental Management Program

SAFETY PRIORITY: Always surface Process Safety implications.
OSHA PSM elements apply to facilities with HHC above threshold quantities.
Never recommend bypassing safety systems or defeating interlocks.
"""

SAFETY_CRITICAL_PATTERNS = [
    "bypass safety", "defeat interlock", "disable alarm",
    "skip inspection", "override shutdown", "ignore PSV"
]


class OilGasPlugin(IndustryPlugin):
    """
    API/OSHA PSM-compliant oil and gas AI plugin.
    
    Capabilities:
    - Drilling engineering support (well planning, mud programs)
    - Production optimization (nodal analysis, artificial lift selection)
    - Pipeline integrity management (API 1130/1160, PHMSA 195)
    - Process safety management (PSM, PHA facilitation support)
    - Environmental compliance (EPA Subpart W, flaring regs)
    - Offshore operations (BSEE SEMS, well control)
    - Asset reliability (RBI, RCM, API 580/581)
    - Digital oilfield / SCADA / OT security awareness
    """

    @property
    def industry(self) -> Industry:
        return Industry.OIL_GAS

    @property
    def compliance_frameworks(self) -> list[ComplianceFramework]:
        return [ComplianceFramework.API_1130, ComplianceFramework.ISO_55001]

    async def augment_system_prompt(self, base_prompt: str, context: ConversationContext) -> str:
        return base_prompt + OIL_GAS_SYSTEM_EXTENSION

    async def post_process_response(self, response: str, context: ConversationContext) -> AssistantResponse:
        disclaimers = [
            "⛽ This response is for operational guidance and engineering reference only.",
            "Always verify against current API standards, local regulations, and site-specific MOC process.",
            "Safety-critical decisions require review by qualified process safety engineers.",
        ]

        psm_keywords = ["HAZOP", "PHA", "LOPA", "safety instrumented", "SIL", "relief valve", "PSV"]
        if any(kw.lower() in response.lower() for kw in psm_keywords):
            disclaimers.append(
                "🔴 PSM CRITICAL: Content involves Process Safety. Must be reviewed by a PSE/CSP before implementation."
            )

        requires_review = any(kw.lower() in response.lower() for kw in ["blowout", "loss of containment", "emergency", "explosion"])

        return AssistantResponse(
            content=response,
            industry=self.industry,
            compliance_disclaimers=disclaimers,
            sources=[
                {"name": "API Standards", "url": "https://www.api.org/standards"},
                {"name": "OSHA PSM", "url": "https://www.osha.gov/process-safety-management"},
                {"name": "BSEE", "url": "https://www.bsee.gov"},
                {"name": "PHMSA", "url": "https://www.phmsa.dot.gov"}
            ],
            confidence_score=0.88,
            session_id=context.session_id,
            requires_human_review=requires_review
        )

    async def validate_query(self, query: str, context: ConversationContext) -> tuple[bool, str]:
        query_lower = query.lower()
        for pattern in SAFETY_CRITICAL_PATTERNS:
            if pattern in query_lower:
                return False, f"Safety-critical override request detected: '{pattern}'. This requires immediate supervisor authorization and MOC process — cannot be processed by AI."
        return True, ""
