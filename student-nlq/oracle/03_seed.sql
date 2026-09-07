-- ============================================
-- 03_seed.sql (SAFE re-runnable seed)
-- Creates 3 courses + 20 students + sample enrollments/attendance/fees
-- ============================================

-- ----------------------------
-- Courses (safe insert)
-- ----------------------------
MERGE INTO courses c
USING (SELECT 'DB101' AS course_code, 'Database Systems' AS title, 3 AS credit_hours FROM dual) x
ON (c.course_code = x.course_code)
WHEN NOT MATCHED THEN
  INSERT (course_code, title, credit_hours)
  VALUES (x.course_code, x.title, x.credit_hours);

MERGE INTO courses c
USING (SELECT 'CS102' AS course_code, 'Programming Fundamentals' AS title, 3 AS credit_hours FROM dual) x
ON (c.course_code = x.course_code)
WHEN NOT MATCHED THEN
  INSERT (course_code, title, credit_hours)
  VALUES (x.course_code, x.title, x.credit_hours);

MERGE INTO courses c
USING (SELECT 'AI201' AS course_code, 'Introduction to AI' AS title, 3 AS credit_hours FROM dual) x
ON (c.course_code = x.course_code)
WHEN NOT MATCHED THEN
  INSERT (course_code, title, credit_hours)
  VALUES (x.course_code, x.title, x.credit_hours);

COMMIT;

-- ----------------------------
-- Students + fees via package (20 total)
-- NOTE: pkg_student.add_student sets student_id internally (1001..)
-- We guard inserts so re-running seed won't create duplicates.
-- ----------------------------
DECLARE
  v_id NUMBER;

  PROCEDURE add_if_missing(p_name VARCHAR2, p_dept VARCHAR2, p_sem NUMBER, p_cgpa NUMBER, p_phone VARCHAR2) IS
    v_exists NUMBER;
  BEGIN
    SELECT COUNT(*)
    INTO v_exists
    FROM students
    WHERE UPPER(full_name) = UPPER(p_name);

    IF v_exists = 0 THEN
      pkg_student.add_student(p_name, p_dept, p_sem, p_cgpa, p_phone, v_id);
    END IF;
  END;
BEGIN
  -- Original 3 (keep same)
  add_if_missing('Ahmed Raza',  'BSCS', 3, 3.10, '0312-1111111');
  add_if_missing('Fatima Noor', 'BSSE', 2, 3.65, '0333-2222222');
  add_if_missing('Hassan Ali',  'BSCS', 5, 2.85, '0300-3333333');

  -- Add 17 more (Total 20)
  add_if_missing('Ali Khan',        'BSCS', 2, 3.20, '0301-4444444');
  add_if_missing('Sara Ahmed',      'BSCS', 4, 3.45, '0302-5555555');
  add_if_missing('Usman Tariq',     'BSSE', 6, 2.90, '0303-6666666');
  add_if_missing('Ayesha Malik',    'BSCS', 1, 3.80, '0304-7777777');
  add_if_missing('Hamza Iqbal',     'BSSE', 5, 2.75, '0305-8888888');
  add_if_missing('Zainab Noor',     'BSCS', 3, 3.10, '0306-9999999');
  add_if_missing('Bilal Hassan',    'BSSE', 7, 2.60, '0307-1010101');

  add_if_missing('Hira Siddiqui',   'BSCS', 6, 3.55, '0308-1212121');
  add_if_missing('Danish Ali',      'BSSE', 8, 3.00, '0309-1313131');
  add_if_missing('Laiba Fatima',    'BSCS', 5, 3.90, '0310-1414141');
  add_if_missing('Saad Raza',       'BSSE', 2, 2.85, '0311-1515151');
  add_if_missing('Mariam Yousuf',   'BSCS', 7, 3.65, '0312-1616161');

  add_if_missing('Fahad Khan',      'BSSE', 4, 2.95, '0313-1717171');
  add_if_missing('Anum Sheikh',     'BSCS', 8, 3.25, '0314-1818181');
  add_if_missing('Hassan Javed',    'BSSE', 3, 2.70, '0315-1919191');
  add_if_missing('Noor Ul Ain',     'BSCS', 1, 3.50, '0316-2020202');
  add_if_missing('Ammar Latif',     'BSCS', 6, 3.05, '0317-2121212');
END;
/
COMMIT;

-- ----------------------------
-- Enrollments (safe insert)
-- PK likely: (student_id, course_id)
-- ----------------------------
MERGE INTO enrollments e
USING (
  SELECT 1001 AS student_id, c.course_id, 'B+' AS grade
  FROM courses c WHERE c.course_code='DB101'
) x
ON (e.student_id = x.student_id AND e.course_id = x.course_id)
WHEN NOT MATCHED THEN
  INSERT (student_id, course_id, grade)
  VALUES (x.student_id, x.course_id, x.grade);

MERGE INTO enrollments e
USING (
  SELECT 1002 AS student_id, c.course_id, 'A' AS grade
  FROM courses c WHERE c.course_code='DB101'
) x
ON (e.student_id = x.student_id AND e.course_id = x.course_id)
WHEN NOT MATCHED THEN
  INSERT (student_id, course_id, grade)
  VALUES (x.student_id, x.course_id, x.grade);

MERGE INTO enrollments e
USING (
  SELECT 1003 AS student_id, c.course_id, 'C' AS grade
  FROM courses c WHERE c.course_code='CS102'
) x
ON (e.student_id = x.student_id AND e.course_id = x.course_id)
WHEN NOT MATCHED THEN
  INSERT (student_id, course_id, grade)
  VALUES (x.student_id, x.course_id, x.grade);

COMMIT;

-- ----------------------------
-- Attendance (safe insert)
-- PK likely: (student_id, course_id)
-- ----------------------------
MERGE INTO attendance a
USING (
  SELECT 1001 AS student_id, c.course_id, 20 AS total_classes, 16 AS present
  FROM courses c WHERE c.course_code='DB101'
) x
ON (a.student_id = x.student_id AND a.course_id = x.course_id)
WHEN NOT MATCHED THEN
  INSERT (student_id, course_id, total_classes, present)
  VALUES (x.student_id, x.course_id, x.total_classes, x.present)
WHEN MATCHED THEN
  UPDATE SET a.total_classes = x.total_classes, a.present = x.present;

MERGE INTO attendance a
USING (
  SELECT 1002 AS student_id, c.course_id, 20 AS total_classes, 19 AS present
  FROM courses c WHERE c.course_code='DB101'
) x
ON (a.student_id = x.student_id AND a.course_id = x.course_id)
WHEN NOT MATCHED THEN
  INSERT (student_id, course_id, total_classes, present)
  VALUES (x.student_id, x.course_id, x.total_classes, x.present)
WHEN MATCHED THEN
  UPDATE SET a.total_classes = x.total_classes, a.present = x.present;

MERGE INTO attendance a
USING (
  SELECT 1003 AS student_id, c.course_id, 18 AS total_classes, 12 AS present
  FROM courses c WHERE c.course_code='CS102'
) x
ON (a.student_id = x.student_id AND a.course_id = x.course_id)
WHEN NOT MATCHED THEN
  INSERT (student_id, course_id, total_classes, present)
  VALUES (x.student_id, x.course_id, x.total_classes, x.present)
WHEN MATCHED THEN
  UPDATE SET a.total_classes = x.total_classes, a.present = x.present;

COMMIT;

-- ----------------------------
-- Fees example updates (safe)
-- ----------------------------
UPDATE fees SET paid_amount = 50000 WHERE student_id=1001;
BEGIN pkg_student.update_fee_status(1001); END;
/
UPDATE fees SET paid_amount = 100000 WHERE student_id=1002;
BEGIN pkg_student.update_fee_status(1002); END;
/
COMMIT;

-- ----------------------------
-- Quick verification
-- ----------------------------
SELECT COUNT(*) AS total_students FROM students;
