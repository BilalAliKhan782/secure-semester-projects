import os
import secrets

ORACLE_USER = os.getenv("ORACLE_USER", "student_user")
ORACLE_PASS = os.getenv("ORACLE_PASS", "")

# Use one of these DSN formats. Prefer the 1521/XEPDB1 one.
ORACLE_DSN  = os.getenv("ORACLE_DSN", "localhost:1521/XEPDB1")

MONGO_URI   = os.getenv("MONGO_URI", "mongodb://localhost:27017/")
MONGO_DB    = os.getenv("MONGO_DB", "student_mongo")

SECRET_KEY  = os.getenv("SECRET_KEY") or secrets.token_hex(32)
DEBUG       = os.getenv("FLASK_DEBUG", "0") == "1"
HOST        = os.getenv("FLASK_HOST", "127.0.0.1")
PORT        = int(os.getenv("FLASK_PORT", "5000"))
