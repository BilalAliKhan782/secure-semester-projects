CREATE OR REPLACE PACKAGE pkg_student AS
  PROCEDURE add_student(
    p_name IN VARCHAR2,
    p_department IN VARCHAR2,
    p_semester IN NUMBER,
    p_cgpa IN NUMBER,
    p_phone IN VARCHAR2,
    o_student_id OUT NUMBER
  );

  FUNCTION attendance_percentage(
    p_student_id IN NUMBER,
    p_course_code IN VARCHAR2
  ) RETURN NUMBER;

  PROCEDURE update_fee_status(p_student_id IN NUMBER);
END pkg_student;
/

CREATE OR REPLACE PACKAGE BODY pkg_student AS

  PROCEDURE add_student(
    p_name IN VARCHAR2,
    p_department IN VARCHAR2,
    p_semester IN NUMBER,
    p_cgpa IN NUMBER,
    p_phone IN VARCHAR2,
    o_student_id OUT NUMBER
  ) IS
  BEGIN
    INSERT INTO students(full_name, department, semester, cgpa, phone)
    VALUES(p_name, p_department, p_semester, p_cgpa, p_phone)
    RETURNING student_id INTO o_student_id;

    INSERT INTO fees(student_id, total_fee, paid_amount, status)
    VALUES(o_student_id, 100000, 0, 'UNPAID'); -- demo default fee
  END;

  FUNCTION attendance_percentage(
    p_student_id IN NUMBER,
    p_course_code IN VARCHAR2
  ) RETURN NUMBER IS
    v_course_id NUMBER;
    v_total NUMBER;
    v_present NUMBER;
  BEGIN
    SELECT course_id INTO v_course_id FROM courses WHERE course_code = p_course_code;

    SELECT total_classes, present
      INTO v_total, v_present
    FROM attendance
    WHERE student_id=p_student_id AND course_id=v_course_id;

    IF v_total = 0 THEN
      RETURN 0;
    END IF;

    RETURN ROUND((v_present / v_total) * 100, 2);
  EXCEPTION
    WHEN NO_DATA_FOUND THEN
      RETURN 0;
  END;

  PROCEDURE update_fee_status(p_student_id IN NUMBER) IS
    v_total NUMBER(10,2);
    v_paid  NUMBER(10,2);
  BEGIN
    SELECT total_fee, paid_amount INTO v_total, v_paid
    FROM fees WHERE student_id=p_student_id FOR UPDATE;

    IF v_paid = 0 THEN
      UPDATE fees SET status='UNPAID' WHERE student_id=p_student_id;
    ELSIF v_paid < v_total THEN
      UPDATE fees SET status='PARTIAL' WHERE student_id=p_student_id;
    ELSE
      UPDATE fees SET status='PAID' WHERE student_id=p_student_id;
    END IF;
  END;

END pkg_student;
/
