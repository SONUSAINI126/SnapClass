import streamlit as st
from src.database.db import enroll_student_to_subject
from src.database.config import supabase
import time


@st.dialog("Quick Enrollment!")
def auto_enroll_dialog(subject_code):
    
    join_code = st.query_params.get('join-code')
    if join_code:
        if st.session_state.login_type != 'student':
            # Don't force switch if already logged in as teacher
            if st.session_state.get('is_logged_in') and st.session_state.get('user_role') == 'teacher':
                st.warning("Please log out as teacher first to enroll as a student.")
                st.query_params.clear()
                return
            st.session_state.login_type = 'student'
            st.rerun()

    student_id = st.session_state.student_data['student_id']

    res = supabase.table('subjects').select('subject_id,name').eq('subject_code',subject_code).execute()
    if not res.data:
        st.error('Subject Code not found!')
        if st.button('Close'):
            st.query_params.clear()
            st.rerun()
        return
    
    subject = res.data[0]

        # Check if already enrolled
    check = (
            supabase.table("subject_students")
            .select("*")
            .eq("subject_id", subject["subject_id"])
            .eq("student_id", student_id)
            .execute()
        )
    if check.data:
        st.info('You are already enrolled')
        if st.button('Got it!'):
            st.query_params.clear()
            st.rerun()
        return
    st.markdown(f"Would you like to enroll in **{subject['name']}**?")

    col1,col2 = st.columns(2)
    with col1:
        if st.button('No Thanks'):
            st.query_params.clear()
            st.rerun()
            return
    
    with col2:
        if st.button('Yes enroll now!',type='primary',width='stretch'):
            enroll_student_to_subject(student_id,subject['subject_id'])
            st.success('Joined Successfully')
            st.query_params.clear()
            time.sleep(2)
            st.rerun()


    