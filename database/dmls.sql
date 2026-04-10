/* ============================================================
   ONLINE EXAMINATION SYSTEM - COMPLETE SQL QUERY COLLECTION
   Compatible with Oracle Database
   ============================================================ */

/* ---------------------------
   AUTHENTICATION & AUDIT
   --------------------------- */

-- Fetch user details for login
SELECT user_id, role, full_name, password_hash
FROM USERS
WHERE username = :1;

-- Register a new user
INSERT INTO USERS (username, password_hash, full_name, role, email)
VALUES (:1, :2, :3, :4, :5);

-- Insert audit log entry
INSERT INTO AUDIT_LOGS (user_id, action)
VALUES (:1, :2);


/* ---------------------------
   ADMIN DASHBOARD
   --------------------------- */

-- List all users
SELECT user_id, username, full_name, role, email
FROM USERS
ORDER BY user_id;

-- List all subjects
SELECT subject_id, name, description
FROM SUBJECTS
ORDER BY name;

-- Count total users
SELECT COUNT(*) FROM USERS;

-- Count total tests
SELECT COUNT(*) FROM TESTS;

-- Retrieve column names for any table (replace table name dynamically)
SELECT column_name
FROM user_tab_columns
WHERE table_name = '<TABLE_NAME>'
ORDER BY column_id;

-- View all data from a specific table (replace <TABLE_NAME>)
SELECT * FROM <TABLE_NAME>;

-- Total number of test attempts
SELECT COUNT(*) FROM TEST_ATTEMPTS;

-- Average percentage score across all attempts
SELECT AVG(
    CASE
        WHEN max_score > 0 THEN (score / max_score) * 100
        ELSE 0
    END
)
FROM TEST_ATTEMPTS;

-- Count of currently active tests
SELECT COUNT(*)
FROM TESTS
WHERE is_active = 1;


/* ---------------------------
   ADMIN ACTIONS
   --------------------------- */

-- Add a new subject
INSERT INTO SUBJECTS (name, description)
VALUES (:1, :2);

-- Delete a subject
DELETE FROM SUBJECTS
WHERE subject_id = :1;

-- Delete a user
DELETE FROM USERS
WHERE user_id = :1;

-- Clear all audit logs
DELETE FROM AUDIT_LOGS;


/* ---------------------------
   INSTRUCTOR DASHBOARD
   --------------------------- */

-- Fetch all subjects
SELECT subject_id, name
FROM SUBJECTS
ORDER BY name;

-- Fetch instructor-created tests with remaining time
SELECT
    t.test_id,
    t.title,
    t.duration_minutes,
    s.name,
    t.is_active,
    CASE
        WHEN t.is_active = 1 AND t.start_time IS NOT NULL THEN
            GREATEST(
                0,
                FLOOR(
                    (CAST(t.start_time AS DATE) + t.duration_minutes / 1440 - SYSDATE) * 86400
                )
            )
        ELSE 0
    END AS remaining_secs,
    t.start_time
FROM TESTS t
LEFT JOIN SUBJECTS s ON t.subject_id = s.subject_id
WHERE t.creator_id = :1
ORDER BY t.test_id DESC;


/* ---------------------------
   INSTRUCTOR ACTIONS
   --------------------------- */

-- Create a new test
INSERT INTO TESTS (creator_id, subject_id, title, duration_minutes, is_active)
VALUES (:1, :2, :3, :4, 0);

-- Retrieve latest test ID for the instructor
SELECT MAX(test_id)
FROM TESTS
WHERE creator_id = :1;

-- Delete a test
DELETE FROM TESTS
WHERE test_id = :1
  AND creator_id = :2;

-- Check current test status
SELECT is_active
FROM TESTS
WHERE test_id = :1
  AND creator_id = :2;

-- Activate a test and set start time
UPDATE TESTS
SET is_active = :1,
    start_time = SYSTIMESTAMP
WHERE test_id = :2;

-- Deactivate a test
UPDATE TESTS
SET is_active = :1
WHERE test_id = :2;


/* ---------------------------
   MANAGE TEST (INSTRUCTOR)
   --------------------------- */

-- Fetch test information
SELECT title, subject_id
FROM TESTS
WHERE test_id = :1
  AND creator_id = :2;

-- Create and approve a new question
INSERT INTO QUESTIONS (
    subject_id,
    instructor_id,
    text,
    option_a,
    option_b,
    option_c,
    option_d,
    correct_option,
    status
)
VALUES (:1, :2, :3, :4, :5, :6, :7, :8, 'Approved');

-- Retrieve latest question ID for the instructor
SELECT MAX(question_id)
FROM QUESTIONS
WHERE instructor_id = :1;

-- Add a question to a test
INSERT INTO TEST_QUESTIONS (test_id, question_id, points)
VALUES (:1, :2, 1);

-- Remove a question from a test
DELETE FROM TEST_QUESTIONS
WHERE test_id = :1
  AND question_id = :2;

-- Fetch questions already included in a test
SELECT
    q.question_id,
    q.text,
    q.option_a,
    q.option_b,
    q.option_c,
    q.option_d,
    q.correct_option
FROM QUESTIONS q
JOIN TEST_QUESTIONS tq ON q.question_id = tq.question_id
WHERE tq.test_id = :1;

-- Fetch available questions not yet added to the test
SELECT q.question_id, q.text
FROM QUESTIONS q
WHERE q.subject_id = :1
  AND q.question_id NOT IN (
        SELECT question_id
        FROM TEST_QUESTIONS
        WHERE test_id = :2
  );


/* ---------------------------
   STUDENT DASHBOARD
   --------------------------- */

-- Fetch available tests for a student
SELECT
    t.test_id,
    t.title,
    t.duration_minutes,
    s.name
FROM TESTS t
LEFT JOIN SUBJECTS s ON t.subject_id = s.subject_id
WHERE t.is_active = 1
  AND SYSTIMESTAMP <= t.start_time + NUMTODSINTERVAL(t.duration_minutes, 'MINUTE')
  AND t.test_id NOT IN (
        SELECT test_id
        FROM TEST_ATTEMPTS
        WHERE student_id = :1
  );

-- Fetch completed tests for a student
SELECT
    t.title,
    a.score,
    a.max_score
FROM TEST_ATTEMPTS a
JOIN TESTS t ON a.test_id = t.test_id
WHERE a.student_id = :1;


/* ---------------------------
   STUDENT TEST TAKING
   --------------------------- */

-- Verify that a test is active and calculate remaining time
SELECT
    t.title,
    t.duration_minutes,
    t.subject_id,
    GREATEST(
        1,
        FLOOR(
            (CAST(t.start_time AS DATE) + t.duration_minutes / 1440 - SYSDATE) * 86400
        )
    ) AS remaining_secs
FROM TESTS t
WHERE t.test_id = :1
  AND t.is_active = 1
  AND SYSDATE <= CAST(t.start_time AS DATE) + t.duration_minutes / 1440;

-- Fetch subject name
SELECT name
FROM SUBJECTS
WHERE subject_id = :1;

-- Fetch correct answers for scoring
SELECT q.question_id, q.correct_option
FROM QUESTIONS q
JOIN TEST_QUESTIONS tq ON q.question_id = tq.question_id
WHERE tq.test_id = :1;

-- Insert a new test attempt
INSERT INTO TEST_ATTEMPTS (test_id, student_id, score, max_score)
VALUES (:1, :2, 0, :3);

-- Retrieve latest attempt ID
SELECT MAX(attempt_id)
FROM TEST_ATTEMPTS
WHERE test_id = :1
  AND student_id = :2;

-- Insert student answers
INSERT INTO STUDENT_ANSWERS (
    attempt_id,
    question_id,
    selected_option,
    is_correct
)
VALUES (:1, :2, :3, :4);

-- Update final score
UPDATE TEST_ATTEMPTS
SET score = :1
WHERE attempt_id = :2;

-- Fetch questions for test display
SELECT
    q.question_id,
    q.text,
    q.option_a,
    q.option_b,
    q.option_c,
    q.option_d
FROM QUESTIONS q
JOIN TEST_QUESTIONS tq ON q.question_id = tq.question_id
WHERE tq.test_id = :1;


/* ---------------------------
   INSTRUCTOR TEST ANALYTICS
   --------------------------- */

-- Verify test ownership
SELECT title, is_active
FROM TESTS
WHERE test_id = :1
  AND creator_id = :2;

-- Overall test statistics
SELECT
    COUNT(*),
    ROUND(AVG(CASE WHEN max_score > 0 THEN score/max_score*100 ELSE 0 END), 1),
    ROUND(MAX(CASE WHEN max_score > 0 THEN score/max_score*100 ELSE 0 END), 1),
    ROUND(MIN(CASE WHEN max_score > 0 THEN score/max_score*100 ELSE 0 END), 1),
    SUM(CASE WHEN max_score > 0 AND score/max_score >= 0.5 THEN 1 ELSE 0 END)
FROM TEST_ATTEMPTS
WHERE test_id = :1;

-- Score distribution
SELECT
    SUM(CASE WHEN max_score > 0 AND score/max_score*100 <= 25 THEN 1 ELSE 0 END),
    SUM(CASE WHEN max_score > 0 AND score/max_score*100 > 25 AND score/max_score*100 <= 50 THEN 1 ELSE 0 END),
    SUM(CASE WHEN max_score > 0 AND score/max_score*100 > 50 AND score/max_score*100 <= 75 THEN 1 ELSE 0 END),
    SUM(CASE WHEN max_score > 0 AND score/max_score*100 > 75 THEN 1 ELSE 0 END)
FROM TEST_ATTEMPTS
WHERE test_id = :1;

-- Per-question accuracy analytics
SELECT
    q.question_id,
    q.text,
    q.option_a,
    q.option_b,
    q.option_c,
    q.option_d,
    q.correct_option,
    agg.attempts,
    agg.correct_count,
    agg.accuracy
FROM QUESTIONS q
JOIN TEST_QUESTIONS tq ON tq.question_id = q.question_id
JOIN (
    SELECT
        q2.question_id,
        COUNT(sa.attempt_id) AS attempts,
        SUM(NVL(sa.is_correct, 0)) AS correct_count,
        ROUND(
            SUM(NVL(sa.is_correct, 0)) * 100.0 /
            NULLIF(COUNT(sa.attempt_id), 0),
            1
        ) AS accuracy
    FROM QUESTIONS q2
    JOIN TEST_QUESTIONS tq2 ON tq2.question_id = q2.question_id
    LEFT JOIN STUDENT_ANSWERS sa
        ON sa.question_id = q2.question_id
        AND sa.attempt_id IN (
            SELECT attempt_id
            FROM TEST_ATTEMPTS
            WHERE test_id = :1
        )
    WHERE tq2.test_id = :2
    GROUP BY q2.question_id
) agg ON q.question_id = agg.question_id
WHERE tq.test_id = :3
ORDER BY accuracy ASC NULLS LAST;

-- Individual student results
SELECT
    u.full_name,
    u.username,
    a.score,
    a.max_score,
    ROUND(
        CASE
            WHEN a.max_score > 0 THEN a.score/a.max_score*100
            ELSE 0
        END,
        1
    )
FROM TEST_ATTEMPTS a
JOIN USERS u ON u.user_id = a.student_id
WHERE a.test_id = :1
ORDER BY a.score DESC;

/* ===========================
   END OF SQL QUERY COLLECTION
   =========================== */