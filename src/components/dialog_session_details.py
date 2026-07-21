import streamlit as st
import pandas as pd
from src.database.db import get_attendance_session_details


@st.dialog("📋 Session Details")
def session_details_dialog(teacher_id, subject_id, subject_name, subject_code, course, section, timestamp, present_count, total_count):
    
    rate = round((present_count / total_count) * 100) if total_count > 0 else 0
    
    st.markdown(f"""
        <div style="
            background: linear-gradient(135deg, #4F46E5 0%, #7C3AED 100%);
            border-radius: 16px;
            padding: 20px;
            margin-bottom: 20px;
            color: white;
        ">
            <h3 style="color: white; margin: 0; font-size: 1.2rem;">{subject_name}</h3>
            <p style="color: rgba(255,255,255,0.85); margin: 4px 0 0 0; font-size: 0.9rem;">
                {course} | Section {section} | {subject_code}
            </p>
            <div style="
                display: flex;
                gap: 16px;
                margin-top: 12px;
                padding-top: 12px;
                border-top: 1px solid rgba(255,255,255,0.2);
            ">
                <div>
                    <div style="font-size: 1.5rem; font-weight: 700;">{present_count}</div>
                    <div style="font-size: 0.75rem; opacity: 0.8;">Present</div>
                </div>
                <div>
                    <div style="font-size: 1.5rem; font-weight: 700;">{total_count - present_count}</div>
                    <div style="font-size: 0.75rem; opacity: 0.8;">Absent</div>
                </div>
                <div>
                    <div style="font-size: 1.5rem; font-weight: 700;">{rate}%</div>
                    <div style="font-size: 0.75rem; opacity: 0.8;">Rate</div>
                </div>
            </div>
        </div>
    """, unsafe_allow_html=True)

    with st.spinner("Loading student details..."):
        records = get_attendance_session_details(teacher_id, subject_id, timestamp)

    if not records:
        st.warning("No student records found for this session.")
        return

    student_data = []
    present_list = []
    absent_list = []

    for r in records:
        student = r.get("students", {})
        is_present = bool(r.get("is_present", False))
        
        student_info = {
            "Roll No": student.get("roll_no") or student.get("student_id", "N/A"),
            "Student Name": student.get("name", "Unknown"),
            "Status": "✅ Present" if is_present else "❌ Absent",
            "Timestamp": r.get("timestamp", "N/A")[:19].replace("T", " ") if r.get("timestamp") else "N/A"
        }
        student_data.append(student_info)
        
        if is_present:
            present_list.append(student_info)
        else:
            absent_list.append(student_info)

    df = pd.DataFrame(student_data)

    tab_all, tab_present, tab_absent = st.tabs([
        f"👥 All ({len(student_data)})",
        f"✅ Present ({len(present_list)})",
        f"❌ Absent ({len(absent_list)})"
    ])

    with tab_all:
        st.dataframe(df, hide_index=True, use_container_width=True)

    with tab_present:
        if present_list:
            st.dataframe(pd.DataFrame(present_list), hide_index=True, use_container_width=True)
        else:
            st.info("No students were present.")

    with tab_absent:
        if absent_list:
            st.dataframe(pd.DataFrame(absent_list), hide_index=True, use_container_width=True)
        else:
            st.info("No students were absent. Perfect attendance! 🎉")