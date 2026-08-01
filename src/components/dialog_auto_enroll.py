import streamlit as st
from src.database.db import enroll_student_to_subject
from src.database.config import supabase
import time


@st.dialog("Quick Enrollment!")
def auto_enroll_dialog(subject_code):

    # ===== GUARD 1: Must be logged in =====
    if not st.session_state.get("is_logged_in"):
        st.error("🔒 Please log in as a student first.")
        if st.button("Go to Student Login", type="primary", width="stretch"):
            st.session_state["login_type"] = "student"
            st.rerun()
        return

    # ===== GUARD 2: Must be student role =====
    if st.session_state.get("user_role") != "student":
        st.error("👨‍🏫 Only students can enroll in subjects.")
        if st.button("Close", type="secondary", width="stretch"):
            st.rerun()
        return

    # ===== GUARD 3: Must have student_data =====
    if "student_data" not in st.session_state:
        st.error("👤 Student profile not found. Please log in again.")
        st.session_state["is_logged_in"] = False
        st.session_state["user_role"] = None
        if st.button("Go to Login", type="primary", width="stretch"):
            st.session_state["login_type"] = "student"
            st.rerun()
        return

    student_id = st.session_state.student_data["student_id"]

    # ===== FETCH SUBJECT =====
    try:
        res = supabase.table("subjects").select("subject_id,name").eq("subject_code", subject_code).execute()
    except Exception as e:
        st.error(f"Database error: {e}")
        return

    if not res.data:
        st.error(f"❌ Subject code '{subject_code}' not found!")
        if st.button("Close", type="secondary", width="stretch"):
            st.rerun()
        return

    subject = res.data[0]

    # ===== CHECK ALREADY ENROLLED =====
    try:
        check = (
            supabase.table("subject_students")
            .select("*")
            .eq("subject_id", subject["subject_id"])
            .eq("student_id", student_id)
            .execute()
        )
    except Exception as e:
        st.error(f"Database error: {e}")
        return

    if check.data:
        st.info(f"✅ You are already enrolled in **{subject['name']}**")
        if st.button("Got it!", type="primary", width="stretch"):
            st.rerun()
        return

    # ===== ENROLLMENT UI =====
    st.markdown(f"### Would you like to enroll in?")
    st.markdown(f"<h2 style='color: #4F46E5;'>{subject['name']}</h2>", unsafe_allow_html=True)
    st.markdown(f"**Subject Code:** `{subject_code}`")

    col1, col2 = st.columns(2)
    with col1:
        if st.button("❌ No Thanks", type="secondary", width="stretch"):
            st.rerun()

    with col2:
        if st.button("✅ Yes, Enroll Now!", type="primary", width="stretch"):
            try:
                enroll_student_to_subject(student_id, subject["subject_id"])
                st.success(f"🎉 Successfully enrolled in {subject['name']}!")
                time.sleep(1.5)
                st.rerun()
            except Exception as e:
                st.error(f"Enrollment failed: {e}")