import streamlit as st
from src.database.db import create_subject, COURSES


@st.dialog("Create New Subject")
def create_subject_dialog(teacher_id):
    st.markdown("""
        <p style="color: #64748B; margin-bottom: 20px;">
            Fill in the details below to create a new class.
        </p>
    """, unsafe_allow_html=True)

    sub_id = st.text_input(
        "Subject Code",
        placeholder="CSAI102",
        help="A unique code students will use to join"
    )

    sub_name = st.text_input(
        "Subject Name",
        placeholder="Introduction to Computer Science"
    )

    sub_course = st.selectbox(
        "Course",
        options=COURSES,
        help="Select the degree/course program"
    )

    custom_course = ""
    if sub_course == "Other":
        custom_course = st.text_input(
            "Enter Custom Course Name",
            placeholder="e.g. Data Science, Cyber Security",
            help="Type the full name of the course"
        )

    sub_section = st.text_input(
        "Section",
        placeholder="A",
        help="Class section (A, B, C, etc.)"
    )

    st.divider()

    final_course = custom_course.strip().upper() if sub_course == "Other" and custom_course else sub_course

    if st.button("Create Subject", type="primary", use_container_width=True):
        sub_id_clean = sub_id.strip().upper() if sub_id else ""

        if not all([sub_id_clean, sub_name, final_course, sub_section]):
            st.warning("⚠️ Please fill all the fields")
            return

        if len(sub_id_clean) < 3:
            st.warning("⚠️ Subject code must be at least 3 characters")
            return

        if sub_course == "Other" and not custom_course.strip():
            st.warning("⚠️ Please enter a custom course name")
            return

        try:
            create_subject(sub_id_clean, sub_name, final_course, sub_section, teacher_id)
            st.success(f"✅ Subject created successfully! ({final_course} - {sub_section})")
            st.balloons()
            st.rerun()
        except ValueError as e:
            if "already exists" in str(e):
                st.error(f"⛔ {e}")
            else:
                st.error(f"❌ Validation error: {e}")
        except Exception as e:
            st.error(f"❌ Error: {str(e)}")
