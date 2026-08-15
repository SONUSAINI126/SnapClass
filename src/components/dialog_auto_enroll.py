import streamlit as st
from src.database.db import enroll_student_to_subject
from src.database.config import supabase
import time


@st.dialog("Quick Enrollment!")
def auto_enroll_dialog(join_code):
    student_id = st.session_state.student_data['student_id']
    
    subject = None
    code_clean = str(join_code).strip().upper()
    
    st.caption(f"Debug: received code '{code}'")
    # 1. Try enrollment_code first (new architecture)
    try:
        res = supabase.table('subjects').select('*').eq('enrollment_code', code_clean).execute()
        if res.data:
            subject = res.data[0]
    except Exception:
        pass
    
    # 2. Fallback to subject_code (legacy / migration not yet run)
    if not subject:
        res = supabase.table('subjects').select('*').eq('subject_code', code_clean).execute()
        if not res.data:
            st.error('Invalid code! Class not found.')
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
        st.info('You are already enrolled in this class.')
        if st.button('Got it!'):
            st.query_params.clear()
            st.rerun()
        return
    
    # Fetch teacher name safely (separate query to avoid FK join issues)
    teacher_name = "Unknown"
    if subject.get('teacher_id'):
        try:
            t_res = supabase.table('teachers').select('name').eq('teacher_id', subject['teacher_id']).execute()
            if t_res.data:
                teacher_name = t_res.data[0]['name']
        except Exception:
            pass
    
    st.markdown(f"""
        <div style="background: #F8FAFC; border-radius: 12px; padding: 16px; margin-bottom: 16px; border: 1px solid #E2E8F0;">
            <h4 style="margin: 0 0 8px 0; color: #0F172A;">{subject['name']}</h4>
            <p style="margin: 0; color: #64748B; font-size: 0.9rem;">
                Teacher: <b>{teacher_name}</b><br/>
                Course: {subject.get('course', 'N/A')}<br/>
                Section: {subject['section']}
            </p>
        </div>
    """, unsafe_allow_html=True)

    st.markdown("Would you like to enroll in this class?")

    col1, col2 = st.columns(2)
    with col1:
        if st.button('No Thanks'):
            st.query_params.clear()
            st.rerun()

    with col2:
        if st.button('Yes, enroll now!', type='primary', width='stretch'):
            enroll_student_to_subject(student_id, subject['subject_id'])
            st.success('Joined Successfully')
            st.query_params.clear()
            time.sleep(2)
            st.rerun()