-- ==============================
-- Student NLQ Project (Oracle)
-- ==============================

BEGIN EXECUTE IMMEDIATE 'DROP TABLE audit_log CASCADE CONSTRAINTS'; EXCEPTION WHEN OTHERS THEN NULL; END;
/
BEGIN EXECUTE IMMEDIATE 'DROP TABLE attendance CASCADE CONSTRAINTS'; EXCEPTION WHEN OTHERS THEN NULL; END;
/
BEGIN EXECUTE IMMEDIATE 'DROP TABLE enrollments CASCADE CONSTRAINTS'; EXCEPTION WHEN OTHERS THEN NULL; END;
/
BEGIN EXECUTE IMMEDIATE 'DROP TABLE fees CASCADE CONSTRAINTS'; EXCEPTION WHEN OTHERS THEN NULL; END;
/
BEGIN EXECUTE IMMEDIATE 'DROP TABLE courses CASCADE CONSTRAINTS'; EXCEPTION WHEN OTHERS THEN NULL; END;
/
BEGIN EXECUTE IMMEDIATE 'DROP TABLE students CASCADE CONSTRAINTS'; EXCEPTION WHEN OTHERS THEN NULL; END;
/

BEGIN EXECUTE IMMEDIATE 'DROP SEQUENCE seq_students'; EXCEPTION WHEN OTHERS THEN NULL; END;
/
BEGIN EXECUTE IMMEDIATE 'DROP SEQUENCE seq_courses'; EXCEPTION WHEN OTHERS THEN NULL; END;
/

CREATE SEQUENCE seq_students START WITH 1001 INCREMENT BY 1;
CREATE SEQUENCE seq_courses  START WITH 3001 INCREMENT BY 1;

CREATE TABLE students (
  student_id   NUMBER PRIMARY KEY,
  full_name    VARCHAR2(100) NOT NULL,
  department   VARCHAR2(50) NOT NULL,
  semester     NUMBER(2) CHECK (semester BETWEEN 1 AND 12),
  cgpa         NUMBER(3,2) CHECK (cgpa BETWEEN 0 AND 4),
  phone        VARCHAR2(30),
  created_at   TIMESTAMP DEFAULT SYSTIMESTAMP
);

CREATE TABLE courses (
  course_id    NUMBER PRIMARY KEY,
  course_code  VARCHAR2(20) UNIQUE NOT NULL,
  title        VARCHAR2(100) NOT NULL,
  credit_hours NUMBER(2) DEFAULT 3 CHECK (credit_hours BETWEEN 1 AND 6)
);

CREATE TABLE enrollments (
  student_id   NUMBER NOT NULL,
  course_id    NUMBER NOT NULL,
  grade        VARCHAR2(2),
  CONSTRAINT pk_enroll PRIMARY KEY (student_id, course_id),
  CONSTRAINT fk_enroll_student FOREIGN KEY (student_id) REFERENCES students(student_id),
  CONSTRAINT fk_enroll_course  FOREIGN KEY (course_id)  REFERENCES courses(course_id)
);

CREATE TABLE attendance (
  student_id    NUMBER NOT NULL,
  course_id     NUMBER NOT NULL,
  total_classes NUMBER DEFAULT 0 CHECK (total_classes >= 0),
  present       NUMBER DEFAULT 0 CHECK (present >= 0),
  CONSTRAINT pk_att PRIMARY KEY (student_id, course_id),
  CONSTRAINT fk_att_student FOREIGN KEY (student_id) REFERENCES students(student_id),
  CONSTRAINT fk_att_course  FOREIGN KEY (course_id)  REFERENCES courses(course_id)
);

CREATE TABLE fees (
  student_id    NUMBER PRIMARY KEY,
  total_fee     NUMBER(10,2) DEFAULT 0 CHECK (total_fee >= 0),
  paid_amount   NUMBER(10,2) DEFAULT 0 CHECK (paid_amount >= 0),
  status        VARCHAR2(20) DEFAULT 'UNPAID' CHECK (status IN ('UNPAID','PARTIAL','PAID')),
  CONSTRAINT fk_fee_student FOREIGN KEY (student_id) REFERENCES students(student_id)
);

CREATE TABLE audit_log (
  audit_id   NUMBER GENERATED ALWAYS AS IDENTITY,
  action     VARCHAR2(30),
  table_name VARCHAR2(30),
  row_id     VARCHAR2(30),
  changed_at TIMESTAMP DEFAULT SYSTIMESTAMP,
  detail     VARCHAR2(200)
);

-- Auto ID triggers
CREATE OR REPLACE TRIGGER trg_students_id
BEFORE INSERT ON students
FOR EACH ROW
BEGIN
  IF :NEW.student_id IS NULL THEN
    :NEW.student_id := seq_students.NEXTVAL;
  END IF;
END;
/

CREATE OR REPLACE TRIGGER trg_courses_id
BEFORE INSERT ON courses
FOR EACH ROW
BEGIN
  IF :NEW.course_id IS NULL THEN
    :NEW.course_id := seq_courses.NEXTVAL;
  END IF;
END;
/

-- Audit trigger for CGPA change
CREATE OR REPLACE TRIGGER trg_cgpa_audit
AFTER UPDATE OF cgpa ON students
FOR EACH ROW
BEGIN
  INSERT INTO audit_log(action, table_name, row_id, detail)
  VALUES('UPDATE', 'STUDENTS', TO_CHAR(:OLD.student_id),
         'cgpa '||:OLD.cgpa||' -> '||:NEW.cgpa);
END;
/

-- Helpful views
CREATE OR REPLACE VIEW v_student_profile AS
SELECT student_id, full_name, department, semester, cgpa, phone, created_at
FROM students;

CREATE OR REPLACE VIEW v_fee_status AS
SELECT s.student_id, s.full_name, f.total_fee, f.paid_amount, f.status
FROM students s JOIN fees f ON f.student_id = s.student_id;
