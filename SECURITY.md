# Security policy

## Reporting a vulnerability

Please report suspected vulnerabilities privately through GitHub's **Security → Report a vulnerability** feature. Do not open a public issue containing credentials, personal information, packet captures, or exploit details.

## Operational guidance

- Use test data only. These projects are educational and have not received a professional penetration test.
- Keep secrets in environment variables or an untracked `.env` file.
- Run the web application behind HTTPS before exposing it beyond localhost.
- Treat packet captures and medical histories as sensitive personal data.
- Review NetShield's generated rule, scope, direction, protocol, address, and port before approving a firewall change.
- Keep Python, Wireshark/TShark, database servers, and dependencies patched.
