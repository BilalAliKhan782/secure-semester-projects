# Secure Semester Projects

Four independently runnable semester projects, cleaned up for reproducible local use and safe public sharing.

| Project | Description | Platform |
|---|---|---|
| `voice-v2` | Desktop medical symptom assistant with typed and voice input | Windows/macOS/Linux |
| `netshield-v2` | PCAP analyzer with validated Windows Firewall recommendations | Windows |
| `student-nlq` | Natural-language web interface for Oracle and MongoDB student data | Any |
| `restaurant` | C++17 console restaurant-ordering chatbot | Any C++17 platform |

## Quick start

Each directory contains its own requirements and documentation. For Python projects, create a virtual environment and install only that project's dependencies:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r .\voice-v2\requirements.txt
```

Never commit `.env`, account files, diagnosis histories, packet captures, reports, or firewall-rule data. They are excluded by `.gitignore`.

## Safety notes

- Voice v2 is an educational demonstration, not medical advice or a diagnostic device. Voice recognition sends captured audio to Google's recognition service.
- NetShield requires administrator privileges to change firewall rules. Review every recommendation before applying it. Commands are parsed against a strict allowlist and run without a command shell.
- Student NLQ requires your own Oracle and MongoDB instances. Copy `.env.example` to `.env` and supply real values locally.
- See [SECURITY.md](SECURITY.md) for reporting and deployment guidance.
