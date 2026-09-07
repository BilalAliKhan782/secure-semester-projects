from flask import Flask, render_template, request, jsonify, session
import oracledb
from pymongo import MongoClient
from datetime import datetime
import logging

import config
from nlq_rules import parse_question, fill_missing

app = Flask(__name__)
app.secret_key = config.SECRET_KEY
app.config.update(
    MAX_CONTENT_LENGTH=16 * 1024,
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Strict",
)


@app.after_request
def add_security_headers(response):
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; "
        "img-src 'self' data:; base-uri 'self'; frame-ancestors 'none'"
    )
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Referrer-Policy"] = "no-referrer"
    return response


# ---------------- Oracle helpers ----------------
def get_oracle_conn():
    return oracledb.connect(
        user=config.ORACLE_USER,
        password=config.ORACLE_PASS,
        dsn=config.ORACLE_DSN
    )

def fetch_all(cur):
    cols = [d[0].lower() for d in cur.description]
    return [dict(zip(cols, row)) for row in cur.fetchall()]


# ---------------- Mongo helpers ----------------
mongo_client = MongoClient(config.MONGO_URI, serverSelectionTimeoutMS=5000)
mongo_db = mongo_client[config.MONGO_DB]


@app.route("/")
def home():
    return render_template("chat.html")


@app.route("/api/chat", methods=["POST"])
def api_chat():
    try:
        data = request.json or {}
        question = (data.get("message") or "").strip()
        if not question:
            return jsonify({"ok": True, "title": "Message", "text": "Please type something."}), 200
        if len(question) > 500:
            return jsonify({"ok": False, "title": "Message too long", "text": "Please limit messages to 500 characters."}), 400

        # ---------- Follow-up flow ----------
        pending = session.get("pending_plan")
        if pending:
            plan = fill_missing(pending, question)
            # keep pending only if still clarifying
            if plan.get("type") != "clarify":
                session.pop("pending_plan", None)
        else:
            plan = parse_question(question)

        debug_plan = plan if config.DEBUG else None

        # ---------- Clarify ----------
        if plan.get("type") == "clarify":
            session["pending_plan"] = plan.get("pending", {})
            return jsonify({
                "ok": True,
                "title": plan.get("title", "Need more info"),
                "text": plan.get("text", "Please provide more details."),
                "debug": debug_plan
            }), 200

        # ---------- Help ----------
        if plan.get("type") == "help":
            return jsonify({
                "ok": True,
                "title": plan.get("title", "Help"),
                "text": plan.get("message", ""),
                "debug": debug_plan
            }), 200

        # ---------- Oracle SELECT ----------
        if plan.get("type") == "oracle":
            with get_oracle_conn() as conn:
                cur = conn.cursor()
                cur.execute(plan["sql"], plan.get("params", {}))
                rows = fetch_all(cur)

            return jsonify({
                "ok": True,
                "title": plan.get("title", "Oracle result"),
                "rows": rows,
                "debug": debug_plan
            }), 200

        # ---------- Oracle PL/SQL function ----------
        if plan.get("type") == "oracle_plsql":
            args = plan.get("args", {})
            if "student_id" not in args or "course_code" not in args:
                session["pending_plan"] = {"intent": "attendance_percentage", "entities": {}}
                return jsonify({
                    "ok": True,
                    "title": "Attendance percentage",
                    "text": "Which student id and course code? (e.g., 1001 DB101)",
                    "debug": debug_plan
                }), 200

            with get_oracle_conn() as conn:
                cur = conn.cursor()
                result = cur.callfunc(
                    plan["call"],
                    oracledb.NUMBER,
                    [args["student_id"], args["course_code"]]
                )

            return jsonify({
                "ok": True,
                "title": plan.get("title", "PL/SQL result"),
                "text": f"{float(result):.2f}%",
                "debug": debug_plan
            }), 200

        # ---------- Mongo ----------
        if plan.get("type") == "mongo":
            col = mongo_db[plan["collection"]]
            docs = list(
                col.find(plan["filter"], {"_id": 0})
                   .sort("created_at", -1)
                   .limit(plan.get("limit", 20))
            )

            for d in docs:
                for k, v in list(d.items()):
                    if isinstance(v, datetime):
                        d[k] = v.isoformat()

            return jsonify({
                "ok": True,
                "title": plan.get("title", "Mongo result"),
                "rows": docs,
                "debug": debug_plan
            }), 200

        # ---------- Combined ----------
        if plan.get("type") == "combined":
            sid = plan["student_id"]
            result = {"student_id": sid}

            with get_oracle_conn() as conn:
                cur = conn.cursor()

                cur.execute("SELECT * FROM v_student_profile WHERE student_id=:sid", {"sid": sid})
                r = cur.fetchone()
                if not r:
                    return jsonify({"ok": True, "title": plan.get("title", "Full profile"), "text": "Student not found.", "debug": debug_plan}), 200

                student = dict(zip([d[0].lower() for d in cur.description], r))
                result["student"] = student

                cur.execute(
                    """SELECT c.course_code, c.title, e.grade
                       FROM enrollments e
                       JOIN courses c ON c.course_id = e.course_id
                       WHERE e.student_id = :sid
                       ORDER BY c.course_code""",
                    {"sid": sid}
                )
                result["courses"] = fetch_all(cur)

                cur.execute("SELECT total_fee, paid_amount, status FROM fees WHERE student_id=:sid", {"sid": sid})
                fee = cur.fetchone()
                result["fees"] = {"total_fee": fee[0], "paid_amount": fee[1], "status": fee[2]} if fee else None

            notes = list(mongo_db["notes"].find({"student_id": sid}, {"_id": 0}).sort("created_at", -1).limit(10))
            disc  = list(mongo_db["discipline"].find({"student_id": sid}, {"_id": 0}).sort("created_at", -1).limit(10))

            def fix_dates(lst):
                for d in lst:
                    for k, v in list(d.items()):
                        if isinstance(v, datetime):
                            d[k] = v.isoformat()
                return lst

            result["notes"] = fix_dates(notes)
            result["discipline"] = fix_dates(disc)

            return jsonify({
                "ok": True,
                "title": plan.get("title", "Full profile"),
                "combined": result,
                "debug": debug_plan
            }), 200

        return jsonify({
            "ok": True,
            "title": "I couldn't map that yet",
            "text": "I understood your message, but I don't have a handler for it yet. Open Debug to see the parsed plan.",
            "debug": debug_plan
        }), 200

    except Exception:
        logging.exception("Request processing failed")
        return jsonify({
            "ok": False,
            "title": "Server error",
            "text": "The request could not be completed. Check the server logs."
        }), 500


if __name__ == "__main__":
    app.run(host=config.HOST, port=config.PORT, debug=config.DEBUG)
