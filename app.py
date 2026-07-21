import streamlit as st

# Must be the very first Streamlit call in the script.
st.set_page_config(
    page_title="SnapClass",
    page_icon="📷",
    layout="wide",
    initial_sidebar_state="collapsed",
)

from src.screens.home_screen import home_screen
from src.screens.teacher_screen import teacher_screen
from src.screens.student_screen import student_screen
from src.components.dialog_auto_enroll import auto_enroll_dialog

def main():
    st.set_page_config(
        page_title="SnapClass-Attendance in One Go",
        page_icon="https://i.ibb.co/YTYGn5qV/logo.png"
    )
    if 'login_type' not in st.session_state:
        st.session_state['login_type'] = None

    match st.session_state['login_type']:
        case "teacher":
            teacher_screen()
        case "student":
            student_screen()
        case _:
            home_screen()

    join_code = st.query_params.get('join-code')
    if join_code:
        if st.session_state.login_type != 'student':
            st.session_state.login_type = 'student'
            st.rerun()
        if st.session_state.get('is_logged_in') and st.session_state.get('user_role') == 'student':
            auto_enroll_dialog(join_code)


main()