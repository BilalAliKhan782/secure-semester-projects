# Voice v2

An educational Tkinter symptom-analysis application with typed NLP and microphone input.

```powershell
python -m pip install -r requirements.txt
python app.py
```

Use Python 3.13 on Windows for a prebuilt PyAudio package. An optional background image can be placed at `aibg.jpg` or selected with the `MEDICAL_APP_BG` environment variable.

Passwords are stored locally using salted PBKDF2-HMAC-SHA256. Runtime account, feedback, and history files are ignored by Git. Voice recognition sends audio to Google's recognition service and therefore requires internet access.

This software does not provide medical advice. Seek a qualified healthcare professional for diagnosis or treatment, and use local emergency services for urgent symptoms.
