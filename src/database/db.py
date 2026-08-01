from src.database.config import supabase
import bcrypt
import re
from datetime import datetime

# ========== CONSTANTS ==========
COURSES = ["CSE", "AIML", "BCA", "MCA", "IT", "ECE", "ME", "CE", "Other"]

MAX_NAME_LENGTH = 100
MAX_USERNAME_LENGTH = 50
MAX_ROLLNO_LENGTH = 20
MAX_SUBJECT_CODE_LENGTH = 20
MAX_COURSE_LENGTH = 50
MAX_SECTION_LENGTH = 10

VALID_USERNAME_PATTERN = re.compile(r'^[a-zA-Z0-9_]+$')
VALID_ROLLNO_PATTERN = re.compile(r'^[A-Z0-9\-]+$')
VALID_SUBJECT_CODE_PATTERN = re.compile(r'^[A-Z0-9]+$')


# ========== INPUT VALIDATION HELPERS ==========
def sanitize_string(value, max_length=100, pattern=None):
    """Safely clean and validate string input."""
    if not value or not isinstance(value, str):
        return None
    value = value.strip()
    if len(value) > max_length:
        raise ValueError(f"Input exceeds maximum length of {max_length} characters")
    if pattern and not pattern.match(value):
        raise ValueError("Input contains invalid characters")
    return value


def validate_password(password):
    """Check password complexity requirements."""
    if not password or not isinstance(password, str):
        raise ValueError("Password is required")
    if len(password) < 8:
        raise ValueError("Password must be at least 8 characters")
    if not re.search(r'[A-Z]', password):
        raise ValueError("Password must contain at least one uppercase letter")
    if not re.search(r'[a-z]', password):
        raise ValueError("Password must contain at least one lowercase letter")
    if not re.search(r'[0-9]', password):
        raise ValueError("Password must contain at least one digit")
    if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
        raise ValueError("Password must contain at least one special character")
    return password


# ========== PASSWORD HASHING ==========
def hash_pass(pwd):
    return bcrypt.hashpw(pwd.encode(), bcrypt.gensalt()).decode()


def check_pass(pwd, hashed):
    return bcrypt.checkpw(pwd.encode(), hashed.encode())


# ========== TEACHER OPERATIONS ==========
def check_teacher_exists(username):
    """Check if teacher username already exists."""
    if not username:
        return False
    response = supabase.table("teachers").select("username").eq("username", username).execute()
    return len(response.data) > 0


def check_teacher_exists_by_email(email):
    """Check if teacher email already exists."""
    if not email:
        return False
    response = supabase.table("teachers").select("teacher_id").eq("email", email).execute()
    return len(response.data) > 0


def create_teacher(username, password, name):
    """Create a new teacher with validated inputs."""
    username = sanitize_string(username, MAX_USERNAME_LENGTH, VALID_USERNAME_PATTERN)
    name = sanitize_string(name, MAX_NAME_LENGTH)
    password = validate_password(password)

    if not all([username, name, password]):
        raise ValueError("All fields are required")

    data = {
        "username": username,
        "password": hash_pass(password),
        "name": name
    }
    response = supabase.table("teachers").insert(data).execute()
    return response.data


def teacher_login(username, password):
    """Authenticate teacher login."""
    response = supabase.table("teachers").select("*").eq("username", username).execute()
    if response.data:
        teacher = response.data[0]
        if check_pass(password, teacher['password']):
            return teacher
    return None


# ========== STUDENT OPERATIONS ==========
def get_all_students():
    response = supabase.table('students').select("*").execute()
    return response.data


def create_student(new_name, roll_no=None, face_embedding=None, voice_embedding=None):
    """Create a new student with validated inputs."""
    name = sanitize_string(new_name, MAX_NAME_LENGTH)
    if not name:
        raise ValueError("Name is required")

    clean_roll_no = None
    if roll_no:
        clean_roll_no = sanitize_string(str(roll_no).upper(), MAX_ROLLNO_LENGTH, VALID_ROLLNO_PATTERN)
        if not clean_roll_no:
            raise ValueError("Invalid roll number format")

    data = {
        "name": name,
        "roll_no": clean_roll_no,
        "face_embedding": face_embedding,
        "voice_embedding": voice_embedding
    }
    response = supabase.table("students").insert(data).execute()
    return response.data


def check_student_exists_by_roll_no(roll_no):
    """Check if a student with this roll number already exists."""
    if not roll_no:
        return False
    response = supabase.table('students').select('student_id').eq('roll_no', roll_no).execute()
    return len(response.data) > 0


def check_student_exists_by_name(name):
    """Check if a student with this name already exists."""
    if not name:
        return False
    response = supabase.table('students').select('student_id').eq("name", name).execute()
    return len(response.data) > 0


# ========== SUBJECT OPERATIONS ==========
def create_subject(subject_code, name, course, section, teacher_id):
    """Create a new subject with validated inputs."""
    code = sanitize_string(subject_code, MAX_SUBJECT_CODE_LENGTH, VALID_SUBJECT_CODE_PATTERN)
    sub_name = sanitize_string(name, MAX_NAME_LENGTH)
    sub_course = sanitize_string(course, MAX_COURSE_LENGTH)
    sub_section = sanitize_string(section, MAX_SECTION_LENGTH)

    if not all([code, sub_name, sub_course, sub_section]):
        raise ValueError("All subject fields are required")

    existing = supabase.table('subjects').select('subject_id').eq('subject_code', code).execute()
    if existing.data:
        raise ValueError(f"Subject code '{code}' already exists")

    data = {
        "subject_code": code,
        "name": sub_name,
        "course": sub_course,
        "section": sub_section,
        "teacher_id": teacher_id
    }
    response = supabase.table("subjects").insert(data).execute()
    return response.data


def get_teacher_subjects(teacher_id):
    response = supabase.table('subjects').select("*,attendance_logs(timestamp)").eq("teacher_id", teacher_id).execute()
    subjects = response.data

    for sub in subjects:
        # FIX: subject_students(count) embedded-aggregate syntax silently
        # returned actual rows instead of a count on this project, so
        # total_students was always stuck at 0. Query the count directly —
        # this is reliable regardless of PostgREST version/config.
        count_res = supabase.table('subject_students') \
            .select('id', count='exact') \
            .eq('subject_id', sub['subject_id']) \
            .execute()
        sub['total_students'] = count_res.count or 0

        attendance = sub.get('attendance_logs', [])
        unique_sessions = len(set(log['timestamp'] for log in attendance))
        sub['total_classes'] = unique_sessions

        sub.pop('attendance_logs', None)

    return subjects


def delete_subject(subject_id):
    """Delete a subject and all its related data with verification."""
    try:
        supabase.table('attendance_logs').delete().eq('subject_id', subject_id).execute()
        supabase.table('subject_students').delete().eq('subject_id', subject_id).execute()

        remaining_logs = supabase.table('attendance_logs').select('id').eq('subject_id', subject_id).execute()
        remaining_enrollments = supabase.table('subject_students').select('id').eq('subject_id', subject_id).execute()

        if remaining_logs.data or remaining_enrollments.data:
            raise Exception("Orphaned records detected after deletion attempt")

        supabase.table('subjects').delete().eq('subject_id', subject_id).execute()
        return True, "Subject deleted successfully!"
    except Exception as e:
        return False, str(e)


# ========== ENROLLMENT OPERATIONS ==========
def enroll_student_to_subject(student_id, subject_id):
    check = supabase.table("subject_students").select("*").eq("subject_id", subject_id).eq("student_id", student_id).execute()
    if check.data:
        raise ValueError("Student is already enrolled in this subject")

    data = {'student_id': student_id, "subject_id": subject_id}
    response = supabase.table('subject_students').insert(data).execute()
    return response.data


def unenroll_student_to_subject(student_id, subject_id):
    response = supabase.table('subject_students').delete().eq('student_id', student_id).eq('subject_id', subject_id).execute()
    return response.data


def get_student_subjects(student_id):
    response = supabase.table('subject_students').select('*,subjects(*)').eq('student_id', student_id).execute()
    return response.data


def get_student_attendance(student_id):
    response = supabase.table('attendance_logs').select('*,subjects(*)').eq('student_id', student_id).execute()
    return response.data


# ========== ATTENDANCE OPERATIONS ==========
def create_attendance(logs):
    """Insert attendance logs with deduplication."""
    if not logs:
        return []

    seen = set()
    unique_logs = []
    for log in logs:
        date_key = log['timestamp'][:10] if log.get('timestamp') else 'unknown'
        key = (log['student_id'], log['subject_id'], date_key)
        if key not in seen:
            seen.add(key)
            unique_logs.append(log)

    if len(unique_logs) < len(logs):
        print(f"[WARN] Removed {len(logs) - len(unique_logs)} duplicate attendance entries")

    response = supabase.table('attendance_logs').insert(unique_logs).execute()
    return response.data


def get_attendance_for_teacher(teacher_id):
    response = supabase.table('attendance_logs').select("*,subjects!inner(*)").eq('subjects.teacher_id', teacher_id).execute()
    return response.data


def get_attendance_session_details(teacher_id, subject_id, session_date):
    """Get full student-wise attendance for a specific day's session."""
    ownership = supabase.table('subjects').select('teacher_id').eq('subject_id', subject_id).execute()
    if not ownership.data or ownership.data[0]['teacher_id'] != teacher_id:
        return []

    response = supabase.table('attendance_logs').select(
        "*,students(student_id,name,roll_no),subjects(*)"
    ).eq('subject_id', subject_id) \
     .gte('timestamp', f"{session_date}T00:00:00") \
     .lt('timestamp', f"{session_date}T23:59:59.999999") \
     .execute()
    return response.data if response.data else []


def upsert_attendance_logs(logs):
    """Insert new attendance rows, or flip an existing absent row to present.
    Keeps exactly one row per (student, subject, day) even across multiple
    'Run Face Analysis' submissions on the same day."""
    if not logs:
        return []

    inserted = []
    for log in logs:
        date_key = log['timestamp'][:10] if log.get('timestamp') else None
        if not date_key:
            continue

        existing = supabase.table('attendance_logs').select('id,is_present') \
            .eq('student_id', log['student_id']) \
            .eq('subject_id', log['subject_id']) \
            .gte('timestamp', f"{date_key}T00:00:00") \
            .lt('timestamp', f"{date_key}T23:59:59.999999") \
            .execute()

        if existing.data:
            row = existing.data[0]
            if log.get('is_present') and not row.get('is_present'):
                supabase.table('attendance_logs').update(
                    {'is_present': True}
                ).eq('id', row['id']).execute()
        else:
            resp = supabase.table('attendance_logs').insert(log).execute()
            inserted.extend(resp.data or [])

    return inserted

def get_all_attendance_for_teacher_detailed(teacher_id):
    """Get all attendance with student details for Excel export."""
    response = supabase.table('attendance_logs').select(
        "*,students(student_id,name,roll_no),subjects(*)"
    ).eq('subjects.teacher_id', teacher_id).execute()
    return response.data if response.data else []
