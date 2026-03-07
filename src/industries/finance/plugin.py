"""
Finance Industry Plugin — SOX/FINRA-Compliant AI Assistant
Architect: Kehinde (Kenny) Samson Ogunlowo
Regulatory frameworks: SOX, FINRA, SEC, Basel III, DORA
"""

import re
import logging
from ..core.assistant import IndustryPlugin, Industry, ComplianceFramework, ConversationContext, AssistantResponse

logger = logging.getLogger(__name__)

FINANCE_SYSTEM_EXTENSION = """
FINANCE CONTEXT — SOX, FINRA, SEC COMPLIANCE ACTIVE

You are assisting in a regulated financial services environment. Additional rules:

MANDATORY BEHAVIORS:
1. Never provide specific investment advice or recommend specific securities
2. Always include appropriate regulatory disclaimers for financial information
3. Reference applicable SEC rules, FINRA regulations, and Basel requirements accurately
4. Surface material non-public information (MNPI) risks when relevant
5. Flag SOX Section 302/404 implications for internal control discussions
6. Apply AML/KYC considerations to transaction and customer discussions

YOU MAY ASSIST WITH:
- Financial modeling methodologies and frameworks (not specific recommendations)
- Regulatory compliance interpretation (SOX, FINRA, MiFID II, Dodd-Frank)
- Risk management frameworks (VaR, CVaR, stress testing methodologies)
- Audit and internal controls documentation
- Financial reporting standards (US GAAP, IFRS)
- Treasury operations and cash management concepts
- Fraud detection patterns and AML typologies (educational)

YOU MUST NOT:
- Recommend specific securities, funds, or investment strategies
- Predict market movements with certainty
- Assist with market manipulation, insider trading, or regulatory evasion
- Generate false financial statements or misleading disclosures

IMPORTANT: All financial analysis is for educational/operational purposes only.
Past performance does not guarantee future results.
"""

PROHIBITED_ACTIVITIES = [
    "insider trading", "front running", "wash trading",
    "market manipulation", "false disclosure", "accounting fraud",
    "MNPI", "evade reporting", "launder"
]


class FinancePlugin(IndustryPlugin):
    """
    SOX/FINRA-compliant finance AI plugin.
    
    Capabilities:
    - Financial modeling methodology guidance
    - Regulatory compliance (SOX, FINRA, SEC, Basel III, DORA)
    - Risk management framework support (VaR, stress testing)
    - Internal audit and controls documentation  
    - Financial reporting (GAAP, IFRS) interpretation
    - AML/KYC compliance guidance
    - Treasury and cash management operations
    """

    @property
    def industry(self) -> Industry:
        return Industry.FINANCE

    @property
    def compliance_frameworks(self) -> list[ComplianceFramework]:
        return [ComplianceFramework.SOX, ComplianceFramework.FINRA, ComplianceFramework.SEC_REG]

    async def augment_system_prompt(self, base_prompt: str, context: ConversationContext) -> str:
        return base_prompt + FINANCE_SYSTEM_EXTENSION

    async def post_process_response(self, response: str, context: ConversationContext) -> AssistantResponse:
        disclaimers = [
            "📊 This response is for informational and operational purposes only.",
            "Not investment advice. Consult a registered financial advisor for investment decisions.",
            "Past performance does not guarantee future results.",
        ]

        if any(term in response.lower() for term in ["buy", "sell", "invest in", "short"]):
            disclaimers.append(
                "⚠️ Content references investment actions — this is educational context only, not a recommendation."
            )

        requires_review = any(term in response.lower() for term in ["specific security", "buy this", "sell this"])

        return AssistantResponse(
            content=response,
            industry=self.industry,
            compliance_disclaimers=disclaimers,
            sources=[
                {"name": "SEC.gov", "url": "https://www.sec.gov"},
                {"name": "FINRA", "url": "https://www.finra.org"},
                {"name": "PCAOB", "url": "https://pcaobus.org"}
            ],
            confidence_score=0.90,
            session_id=context.session_id,
            requires_human_review=requires_review
        )

    async def validate_query(self, query: str, context: ConversationContext) -> tuple[bool, str]:
        query_lower = query.lower()
        for activity in PROHIBITED_ACTIVITIES:
            if activity in query_lower:
                return False, f"Query references prohibited financial activity: '{activity}'. This request cannot be processed."
        return True, ""
