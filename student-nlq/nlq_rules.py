import re
from typing import Dict, Any, Optional, Tuple

# -----------------------------
# Normalization
# -----------------------------
def normalize(text: str) -> str:
    t = text.strip().lower()
    t = re.sub(r"[?,!;:()\[\]{}]", " ", t)
    t = re.sub(r"\s+", " ", t).strip()
    return t

# -----------------------------
# Entity extraction
# -----------------------------
ID_RE = re.compile(r"\b(\d{3,8})\b")
CGPA_RE = re.compile(r"\b(cgpa|gpa)\b\s*(>=|>|<=|<|=)\s*([0-4](?:\.\d+)?)\b")
TOP_RE  = re.compile(r"\btop\s+(\d{1,3})\b")
COURSE_RE = re.compile(r"\b([a-z]{2,6}\d{2,4})\b")

SEM_RE_1 = re.compile(r"\bsemester\s+(\d{1,2})\b")           # "semester 5"
SEM_RE_2 = re.compile(r"\b(\d{1,2})\s*(?:th)?\s*semester\b") # "5th semester"
SEM_RE_3 = re.compile(r"\bsem\s+(\d{1,2})\b")                # "sem 5"

PAGE_RE_1 = re.compile(r"\bpage\s+(\d{1,3})\b")              # "page 2"
FIRST_RE  = re.compile(r"\bfirst\s+(\d{1,3})\b")             # "first 10"
NEXT_RE   = re.compile(r"\bnext\s+(\d{1,3})\b")              # "next 10"

DEPT_MAP = {
    "bscs": "BSCS",
    "cs": "BSCS",
    "computer science": "BSCS",
    "bsse": "BSSE",
    "se": "BSSE",
    "software engineering": "BSSE",
}

def extract_student_id(t: str) -> Optional[int]:
    m = ID_RE.search(t)
    return int(m.group(1)) if m else None

def extract_course_code(t: str) -> Optional[str]:
    m = re.search(r"\b(in|course|subject|for)\s+([a-z]{2,6}\d{2,4})\b", t)
    if m:
        return m.group(2).upper()
    m2 = COURSE_RE.search(t)
    return m2.group(1).upper() if m2 else None

def extract_dept(t: str) -> Optional[str]:
    for k, v in DEPT_MAP.items():
        if k in t:
            return v
    m = re.search(r"\b(dept|department|in)\s+([a-z]{2,10})\b", t)
    if m:
        return m.group(2).upper()
    return None

def extract_cgpa_condition(t: str) -> Optional[Tuple[str, float]]:
    m = CGPA_RE.search(t)
    if not m:
        return None
    return m.group(2), float(m.group(3))

def extract_top_n(t: str) -> Optional[int]:
    m = TOP_RE.search(t)
    if m:
        n = int(m.group(1))
        return max(1, min(n, 50))
    return None

def extract_semester(t: str) -> Optional[int]:
    for rex in (SEM_RE_1, SEM_RE_2, SEM_RE_3):
        m = rex.search(t)
        if m:
            sem = int(m.group(1))
            if 1 <= sem <= 12:
                return sem
    return None

def extract_pagination(t: str):
    """
    Returns (offset, limit) or None.
    Supports:
      - first 10 students -> offset 0, limit 10
      - next 10 students  -> offset 10, limit 10 (simple demo)
      - page 2 students   -> offset 10, limit 10 (page size 10)
    """
    m = PAGE_RE_1.search(t)
    if m:
        page = int(m.group(1))
        if page < 1:
            page = 1
        limit = 10
        offset = (page - 1) * limit
        return offset, limit

    m = FIRST_RE.search(t)
    if m:
        limit = int(m.group(1))
        limit = max(1, min(limit, 100))
        return 0, limit

    m = NEXT_RE.search(t)
    if m:
        limit = int(m.group(1))
        limit = max(1, min(limit, 100))
        return limit, limit
    return None

# -----------------------------
# Clarify helper
# -----------------------------
def need_missing(title: str, intent: str, entities: Dict[str, Any], missing: list) -> Dict[str, Any]:
    qs = []
    if "student_id" in missing:
        qs.append("Which student id? (e.g., 1001)")
    if "course_code" in missing:
        qs.append("Which course code? (e.g., DB101)")
    if "dept" in missing:
        qs.append("Which department? (e.g., BSCS / BSSE)")
    if "semester" in missing:
        qs.append("Which semester? (e.g., semester 5)")

    return {
        "type": "clarify",
        "title": title,
        "text": "I need a bit more info:\n- " + "\n- ".join(qs),
        "pending": {"intent": intent, "entities": entities}
    }

# -----------------------------
# Main parser
# -----------------------------
def parse_question(q: str) -> Dict[str, Any]:
    t = normalize(q)

    sid = extract_student_id(t)
    course = extract_course_code(t)
    dept = extract_dept(t)
    semester = extract_semester(t)
    cgpa_cond = extract_cgpa_condition(t)
    topn = extract_top_n(t)
    pag = extract_pagination(t)

    # --- help ---
    if t == "help" or "help" in t or "commands" in t:
        return {
            "type": "help",
            "title": "Help",
            "message": (
                "Try:\n"
                "- all students\n"
                "- show all students in semester 5\n"
                "- show all bscs students sorted by cgpa\n"
                "- first 10 students / next 10 students / page 2 students\n"
                "- cgpa >= 3.2\n"
                "- toppers / top 5 students\n"
                "- show student 1001\n"
                "- fee status of 1001\n"
                "- attendance percentage of 1001 in DB101\n"
                "- notes for 1001\n"
                "- full profile of 1001"
            )
        }

    # --- attendance percentage ---
    if "attendance" in t and ("percentage" in t or "percent" in t or "%" in t):
        entities = {"student_id": sid, "course_code": course}
        missing = []
        if not sid: missing.append("student_id")
        if not course: missing.append("course_code")
        if missing:
            return need_missing("Attendance percentage", "attendance_percentage", entities, missing)

        return {
            "type": "oracle_plsql",
            "title": f"Attendance % for {sid} in {course}",
            "call": "pkg_student.attendance_percentage",
            "args": {"student_id": sid, "course_code": course}
        }

    # ✅ NEW: fee status / fees
    if ("fee" in t or "fees" in t or "payment" in t) and ("status" in t or "fee" in t or "fees" in t or "payment" in t):
        if not sid:
            return need_missing("Fee status", "fee_status", {"student_id": sid}, ["student_id"])

        return {
            "type": "oracle",
            "title": f"Fee status of {sid}",
            "sql": """SELECT student_id, total_fee, paid_amount, remaining_amount, status, updated_at
                      FROM fees
                      WHERE student_id = :sid""",
            "params": {"sid": sid}
        }

    # --- notes ---
    if "notes" in t or "remarks" in t or "feedback" in t or "comments" in t:
        if not sid:
            return need_missing("Notes", "mongo_notes", {"student_id": sid}, ["student_id"])
        return {
            "type": "mongo",
            "title": f"Notes for student {sid}",
            "collection": "notes",
            "filter": {"student_id": sid},
            "limit": 20
        }

    # --- full profile ---
    if "full profile" in t or "complete profile" in t or "everything about" in t:
        if not sid:
            return need_missing("Full profile", "full_profile", {"student_id": sid}, ["student_id"])
        return {"type": "combined", "title": f"Full profile of {sid}", "student_id": sid}

    # =========================================================
    # Semester filter BEFORE "all students"
    # =========================================================

    # ---- Semester filter ----
    if ("students" in t or "student" in t) and semester is not None:
        if pag:
            offset, limit = pag
            return {
                "type": "oracle",
                "title": f"Students in semester {semester} (rows {offset+1} to {offset+limit})",
                "sql": f"""SELECT student_id, full_name, department, semester, cgpa
                           FROM students
                           WHERE semester = :sem
                           ORDER BY student_id
                           OFFSET {offset} ROWS FETCH NEXT {limit} ROWS ONLY""",
                "params": {"sem": semester}
            }

        return {
            "type": "oracle",
            "title": f"Students in semester {semester}",
            "sql": """SELECT student_id, full_name, department, semester, cgpa
                      FROM students
                      WHERE semester = :sem
                      ORDER BY student_id""",
            "params": {"sem": semester}
        }

    # ---- All students ----
    if (
        t in ("all students", "show all students", "list students", "display students")
        or ("all students" in t)
        or ("show all students" in t)
        or ("list students" in t)
        or ("display students" in t)
    ):
        if pag:
            offset, limit = pag
            return {
                "type": "oracle",
                "title": f"All students (rows {offset+1} to {offset+limit})",
                "sql": f"""SELECT student_id, full_name, department, semester, cgpa
                           FROM students
                           ORDER BY student_id
                           OFFSET {offset} ROWS FETCH NEXT {limit} ROWS ONLY""",
                "params": {}
            }

        return {
            "type": "oracle",
            "title": "All students",
            "sql": """SELECT student_id, full_name, department, semester, cgpa
                      FROM students
                      ORDER BY student_id""",
            "params": {}
        }

    # ---- Dept students sorted by CGPA ----
    if dept and ("sorted by cgpa" in t or "order by cgpa" in t or "sort by cgpa" in t):
        if pag:
            offset, limit = pag
            return {
                "type": "oracle",
                "title": f"{dept} students sorted by CGPA (rows {offset+1} to {offset+limit})",
                "sql": f"""SELECT student_id, full_name, department, semester, cgpa
                           FROM students
                           WHERE UPPER(department) = :dept
                           ORDER BY cgpa DESC
                           OFFSET {offset} ROWS FETCH NEXT {limit} ROWS ONLY""",
                "params": {"dept": dept}
            }

        return {
            "type": "oracle",
            "title": f"{dept} students sorted by CGPA",
            "sql": """SELECT student_id, full_name, department, semester, cgpa
                      FROM students
                      WHERE UPPER(department) = :dept
                      ORDER BY cgpa DESC""",
            "params": {"dept": dept}
        }

    # ---- Pagination generic ----
    if pag and ("student" in t or "students" in t):
        offset, limit = pag
        return {
            "type": "oracle",
            "title": f"Students (rows {offset+1} to {offset+limit})",
            "sql": f"""SELECT student_id, full_name, department, semester, cgpa
                       FROM students
                       ORDER BY student_id
                       OFFSET {offset} ROWS FETCH NEXT {limit} ROWS ONLY""",
            "params": {}
        }

    # --- students in dept (default sorting by cgpa) ---
    if "students" in t and dept:
        return {
            "type": "oracle",
            "title": f"Students in {dept}",
            "sql": """SELECT student_id, full_name, semester, cgpa
                      FROM students
                      WHERE UPPER(department)=:dept
                      ORDER BY cgpa DESC
                      FETCH FIRST 50 ROWS ONLY""",
            "params": {"dept": dept}
        }

    # --- cgpa filter ---
    if cgpa_cond:
        op, val = cgpa_cond
        return {
            "type": "oracle",
            "title": f"Students with CGPA {op} {val}",
            "sql": f"""SELECT student_id, full_name, department, semester, cgpa
                       FROM students
                       WHERE cgpa {op} :v
                       ORDER BY cgpa DESC
                       FETCH FIRST 50 ROWS ONLY""",
            "params": {"v": val}
        }

    # --- top students ---
    if "top" in t or "toppers" in t or "rankers" in t:
        n = topn or 10
        return {
            "type": "oracle",
            "title": f"Top {n} students by CGPA",
            "sql": f"""SELECT student_id, full_name, department, semester, cgpa
                       FROM students
                       ORDER BY cgpa DESC
                       FETCH FIRST {n} ROWS ONLY""",
            "params": {}
        }

    # --- show student ---
    if sid:
        return {
            "type": "oracle",
            "title": f"Student profile for {sid}",
            "sql": "SELECT * FROM v_student_profile WHERE student_id = :sid",
            "params": {"sid": sid}
        }

    return {
        "type": "help",
        "title": "Could not understand",
        "message": "Try: fee status of 1001, all students, page 2 students, show all students in semester 5, show all bscs students sorted by cgpa, or help"
    }


def fill_missing(pending: Dict[str, Any], user_text: str) -> Dict[str, Any]:
    intent = pending.get("intent")
    entities = pending.get("entities", {})

    t = normalize(user_text)
    sid = extract_student_id(t)
    course = extract_course_code(t)
    dept = extract_dept(t)
    semester = extract_semester(t)

    if sid is not None:
        entities["student_id"] = sid
    if course is not None:
        entities["course_code"] = course
    if dept is not None:
        entities["dept"] = dept
    if semester is not None:
        entities["semester"] = semester

    if intent == "attendance_percentage":
        sid2 = entities.get("student_id")
        course2 = entities.get("course_code")
        if not sid2 or not course2:
            missing = []
            if not sid2: missing.append("student_id")
            if not course2: missing.append("course_code")
            return need_missing("Attendance percentage", "attendance_percentage", entities, missing)

        return {
            "type": "oracle_plsql",
            "title": f"Attendance % for {sid2} in {course2}",
            "call": "pkg_student.attendance_percentage",
            "args": {"student_id": sid2, "course_code": course2}
        }

    if intent == "mongo_notes":
        sid2 = entities.get("student_id")
        if not sid2:
            return need_missing("Notes", "mongo_notes", entities, ["student_id"])
        return {
            "type": "mongo",
            "title": f"Notes for student {sid2}",
            "collection": "notes",
            "filter": {"student_id": sid2},
            "limit": 20
        }

    if intent == "fee_status":
        sid2 = entities.get("student_id")
        if not sid2:
            return need_missing("Fee status", "fee_status", entities, ["student_id"])
        return {
            "type": "oracle",
            "title": f"Fee status of {sid2}",
            "sql": """SELECT student_id, total_fee, paid_amount, remaining_amount, status, updated_at
                      FROM fees
                      WHERE student_id = :sid""",
            "params": {"sid": sid2}
        }

    return parse_question(user_text)
