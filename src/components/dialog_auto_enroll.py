import streamlit as st
from src.database.db import enroll_student_to_subject
from src.database.config import supabase
import time


@st.dialog("Quick Enrollment!")
def auto_enroll_dialog(subject_code):
    
    # Safety check: must be logged in as student
    if not st.session_state.get('is_logged_in'):
        st.error("Please log in as a student first.")
        if st.button('Go to Student Login'):
            st.session_state['login_type'] = 'student'
            if 'join-code' in st.query_params:
                del st.query_params['join-code']
            st.rerun()
        return

    if st.session_state.get('user_role') != 'student':
        st.error("Only students can enroll in subjects.")
        if st.button('Close'):
            if 'join-code' in st.query_params:
                del st.query_params['join-code']
            st.rerun()
        return

    if 'student_data' not in st.session_state:
        st.error("Student data not found. Please log in again.")
        st.session_state['is_logged_in'] = False
        st.session_state['user_role'] = None
        if 'join-code' in st.query_params:
            del st.query_params['join-code']
        st.rerun()
        return

    student_id = st.session_state.student_data['student_id']

    res = supabase.table('subjects').select('subject_id,name').eq('subject_code',subject_code).execute()
    if not res.data:
        st.error('Subject Code not found!')
        if st.button('Close'):
            if 'join-code' in st.query_params:
                del st.query_params['join-code']
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
            if 'join-code' in st.query_params:
                del st.query_params['join-code']
            st.rerun()
        return
    
    st.markdown(f"Would you like to enroll in **{subject['name']}**?")

    col1,col2 = st.columns(2)
    with col1:
        if st.button('No Thanks'):
            if 'join-code' in st.query_params:
                del st.query_params['join-code']
            st.rerun()
            return
    
    with col2:
        if st.button('Yes enroll now!',type='primary',width='stretch'):
            enroll_student_to_subject(student_id,subject['subject_id'])
            st.success('Joined Successfully')
            if 'join-code' in st.query_params:
                del st.query_params['join-code']
            time.sleep(2)
            st.rerun()