import streamlit as st
import sys
import os

# Must be the very first Streamlit call in the script.
st.set_page_config(
    page_title="SnapClass-Attendance in One Go",
    page_icon="https://i.ibb.co/YTYGn5qV/logo.png",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# Add src to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

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
    if 'login_type' not in st.session_state:
        st.session_state['login_type'] = None

    match st.session_state['login_type']:
        case "teacher":
            get_teacher_screen()()
        case "student":
            get_student_screen()()
        case _:
            get_home_screen()()

    join_code = st.query_params.get('join-code')
    if join_code:
        if st.session_state.login_type != 'student':
            st.session_state.login_type = 'student'
            st.rerun()
        if st.session_state.get('is_logged_in') and st.session_state.get('user_role') == 'student':
            get_auto_enroll_dialog()(join_code)

if __name__ == '__main__':
    main()