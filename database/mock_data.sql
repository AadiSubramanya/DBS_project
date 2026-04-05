INSERT INTO USERS (username, password_hash, full_name, role, email) VALUES ('admin', '123', 'System Admin', 'Admin', 'admin@mcq.com');
INSERT INTO USERS (username, password_hash, full_name, role, email) VALUES ('teacher', '123', 'Default Teacher', 'Instructor', 'teacher@test.com');
INSERT INTO USERS (username, password_hash, full_name, role, email) VALUES ('student', '123', 'Default Student', 'Student', 'student@test.com');

INSERT INTO SUBJECTS (name, description) VALUES ('Mathematics', 'Core mathematical concepts');
INSERT INTO SUBJECTS (name, description) VALUES ('Physics', 'Fundamental laws of nature');
INSERT INTO SUBJECTS (name, description) VALUES ('Chemistry', 'Structure and properties of matter');
INSERT INTO SUBJECTS (name, description) VALUES ('Biology', 'Study of living organisms');
INSERT INTO SUBJECTS (name, description) VALUES ('Computer Science', 'Programming and algorithms');

COMMIT;