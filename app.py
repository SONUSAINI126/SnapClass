import streamlit as st
import sys
import os
import traceback

# Must be the very first Streamlit call in the script.
st.set_page_config(
    page_title="SnapClass-Attendance in One Go",
    page_icon="https://i.ibb.co/YTYGn5qV/logo.png",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# EMERGENCY: Initialize all critical session state keys before anything else
for key, default in [
    ("login_type", None),
    ("is_logged_in", False),
    ("user_role", None),
    ("login_attempts", 0),
    ("last_attempt_time", 0),
    ("teacher_login_type", "login"),
    ("attendance_images", []),
    ("show_attendance_dialog", False),
    ("show_voice_dialog", False),
    ("voice_attendance_results", None),
]:
    if key not in st.session_state:
        st.session_state[key] = default

# Add project root to path so 'src.xxx' imports work
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

# Lazy imports — only load when needed
def get_home_screen():
    from src.screens.home_screen import home_screen
    return home_screen

def get_teacher_screen():
    from src.screens.teacher_screen import teacher_screen
    return teacher_screen

def get_student_screen():
    from src.screens.student_screen import student_screen
    return student_screen

def get_auto_enroll_dialog():
    from src.components.dialog_auto_enroll import auto_enroll_dialog
    return auto_enroll_dialog

def main():
    try:
        # ── Check join-code BEFORE rendering anything ──────────────
        join_code = st.query_params.get('join-code')

        if join_code:
            is_teacher = (
                st.session_state.get('is_logged_in') 
                and st.session_state.get('user_role') == 'teacher'
            )
            is_student_logged_in = (
                st.session_state.get('is_logged_in')
                and st.session_state.get('user_role') == 'student'
                and 'student_data' in st.session_state
            )

            # 1. Teacher logged in → warn, clear code, show teacher page
            if is_teacher:
                st.warning("Please log out as teacher first to enroll as a student.")
                if 'join-code' in st.query_params:
                    del st.query_params['join-code']

            # 2. Student logged in → show dialog immediately
            elif is_student_logged_in:
                # Clear code NOW so it doesn't re-trigger if user hits the X button
                if 'join-code' in st.query_params:
                    del st.query_params['join-code']
                get_auto_enroll_dialog()(join_code)
                # Fall through to render the student dashboard behind the dialog

            # 3. Not logged in → send to student login, KEEP the code in URL
            elif st.session_state.get('login_type') != 'student':
                st.session_state['login_type'] = 'student'
                st.rerun()
                return

        # ── Render the correct screen ──────────────────────────────
        login_type = st.session_state.get('login_type')
        if login_type == "teacher":
            get_teacher_screen()()
        elif login_type == "student":
            get_student_screen()()
        else:
            get_home_screen()()

    except Exception as e:
        st.error("🚨 App Error Detected")
        st.code(traceback.format_exc())
        st.info("Please Retry")

if __name__ == '__main__':
    main()