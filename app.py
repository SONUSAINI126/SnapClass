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
        login_type = st.session_state.get('login_type')

        if login_type == "teacher":
            get_teacher_screen()()
        elif login_type == "student":
            get_student_screen()()
        else:
            get_home_screen()()

        # Handle join-code from shared links
        join_code = st.query_params.get('join-code')
        if join_code:
            # If not logged in as student, switch to student portal
            if st.session_state.get('login_type') != 'student':
                # Don't force switch if already logged in as teacher
                if st.session_state.get('is_logged_in') and st.session_state.get('user_role') == 'teacher':
                    st.warning("Please log out as teacher first to enroll as a student.")
                    if 'join-code' in st.query_params:
                        del st.query_params['join-code']
                    return
                st.session_state['login_type'] = 'student'
                st.rerun()
                return

            # Only show enroll dialog if actually logged in as student
            if (st.session_state.get('is_logged_in') 
                and st.session_state.get('user_role') == 'student'
                and 'student_data' in st.session_state):
                get_auto_enroll_dialog()(join_code)
            else:
                # Not logged in as student yet, clear param to prevent loop
                if 'join-code' in st.query_params:
                    del st.query_params['join-code']

    except Exception as e:
        st.error("🚨 App Error Detected")
        st.code(traceback.format_exc())
        st.info("Please screenshot this error and share it for debugging.")

if __name__ == '__main__':
    main()