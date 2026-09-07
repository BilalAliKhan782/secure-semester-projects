# NetShield v2

A Windows desktop tool that analyzes `.pcap`/`.pcapng` files through PyShark/TShark and proposes Windows Firewall rules.

Prerequisites: Python 3.13+, Wireshark/TShark, and administrator access when applying firewall changes.

```powershell
python -m pip install -r requirements.txt
python app.py
```

Firewall commands are accepted only if they match the application's narrow `netsh advfirewall firewall add rule` grammar. They are executed as argument arrays with `shell=False`. Always inspect a proposed rule before applying it.
