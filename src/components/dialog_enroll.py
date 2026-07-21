import streamlit as st
from src.database.db import enroll_student_to_subject
from src.database.config import supabase
import time


@st.dialog("Enroll in Subject")
def enroll_dialog():
    st.write("Enter the Subject Code provided by your teacher to enroll.")

    join_code = st.text_input(
        "Subject Code",
        placeholder="Eg: CSAI102"
    )

    if st.button("Enroll Now", type="primary", width="stretch"):
        join_code = join_code.strip()
        if not join_code:
            st.warning("Please enter a subject code.")
            return

        # Check if subject exists
        res = (
            supabase.table("subjects")
            .select("subject_id, name, subject_code")
            .eq("subject_code", join_code)
            .execute()
        )

        if not res.data:
            st.warning("Invalid subject code.")
            return

        subject = res.data[0]
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
            st.warning("You are already enrolled in this subject.")
        else:
            enroll_student_to_subject(student_id, subject["subject_id"])
            st.success(f"Successfully enrolled in {subject['name']}!")
            time.sleep(1)
            st.rerun()