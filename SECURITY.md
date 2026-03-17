# Security Policy

## Reporting a Vulnerability

If you discover a security vulnerability in this project, please report it responsibly.

**Do NOT open a public GitHub issue for security vulnerabilities.**

Instead, please email: **kogunlowo@gmail.com**

Include the following in your report:
- Description of the vulnerability
- Steps to reproduce
- Potential impact
- Suggested fix (if any)

You will receive an acknowledgment within 48 hours and a detailed response within 7 days.

## Security Best Practices

This project follows these security practices:

- API keys and credentials are managed via environment variables or secret stores
- PHI/PII data is detected and redacted before LLM processing
- Audit logging is enabled for all queries and responses (HIPAA/SOX compliance)
- Input validation via Pydantic models prevents prompt injection
- No hardcoded credentials in source code
- Encryption at rest and in transit for all sensitive data flows
- Role-based access control for industry-specific compliance profiles

## Supported Versions

| Version | Supported          |
| ------- | ------------------ |
| Latest  | :white_check_mark: |

## Disclosure Policy

We follow a coordinated disclosure process. Please allow us reasonable time to address any reported vulnerabilities before public disclosure.
