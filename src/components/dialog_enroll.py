import streamlit as st
from src.database.db import enroll_student_to_subject, get_subject_by_enrollment_code
from src.database.config import supabase
import time


@st.dialog("Enroll in Subject")
def enroll_dialog():
    if "enroll_confirm_subject" not in st.session_state:
        st.session_state.enroll_confirm_subject = None

    st.write("Enter the **Enrollment Code** provided by your teacher.")

    join_code = st.text_input(
        "Enrollment Code",
        placeholder="Eg: DSA-A7K92"
    )

    # Step 1: Lookup
    if st.button("Find Class", type="secondary", width="stretch"):
        join_code = join_code.strip().upper()
        if not join_code:
            st.warning("Please enter an enrollment code.")
            return

        subject = get_subject_by_enrollment_code(join_code)
        if not subject:
            st.warning("Invalid enrollment code. Please check with your teacher.")
            return

        st.session_state.enroll_confirm_subject = subject
        st.rerun()

    # Step 2: Confirm
    if st.session_state.enroll_confirm_subject:
        subject = st.session_state.enroll_confirm_subject
        teacher_name = subject.get('teachers', {}).get('name', 'Unknown')

        st.markdown(f"""
            <div style="background: #F8FAFC; border-radius: 12px; padding: 16px; margin: 16px 0; border: 1px solid #E2E8F0;">
                <h4 style="margin: 0 0 8px 0; color: #0F172A;">{subject['name']}</h4>
                <p style="margin: 0; color: #64748B; font-size: 0.9rem;">
                    Teacher: <b>{teacher_name}</b><br/>
                    Course: {subject.get('course', 'N/A')}<br/>
                    Section: {subject['section']}
                </p>
            </div>
        """, unsafe_allow_html=True)

        student_id = st.session_state.student_data["student_id"]

        # Check if already enrolled
        check = (
            supabase.table("subject_students")
            .select("*")
            .eq("subject_id", subject["subject_id"])
            .eq("student_id", student_id)
            .execute()
        )
        if check.data:
            st.info("You are already enrolled in this class.")
            if st.button("Close", width='stretch'):
                st.session_state.enroll_confirm_subject = None
                st.rerun()
            return

        c1, c2 = st.columns(2)
        with c1:
            if st.button("Cancel", width='stretch'):
                st.session_state.enroll_confirm_subject = None
                st.rerun()
        with c2:
            if st.button("Confirm Enrollment", type='primary', width='stretch'):
                enroll_student_to_subject(student_id, subject["subject_id"])
                st.success(f"Successfully enrolled in {subject['name']}!")
                st.session_state.enroll_confirm_subject = None
                time.sleep(1)
                st.rerun()