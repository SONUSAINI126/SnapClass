import streamlit as st
import time
from src.database.db import delete_subject


@st.dialog("🗑️ Delete Subject")
def delete_subject_dialog(subject_id, subject_name, subject_code, course, section, teacher_id):
    st.markdown(f"""
        <div style="
            background: #FEF2F2;
            border: 1px solid #FCA5A5;
            border-radius: 12px;
            padding: 20px;
            margin-bottom: 20px;
        ">
            <h3 style="color: #DC2626; margin: 0 0 8px 0; font-size: 1.2rem;">⚠️ Warning: Permanent Deletion</h3>
            <p style="color: #7F1D1D; margin: 0; font-size: 0.95rem;">
                You are about to delete <b>{subject_name} ({course} - {section})</b>. 
                This will permanently remove:
            </p>
            <ul style="color: #7F1D1D; margin: 8px 0 0 0; padding-left: 20px;">
                <li>All student enrollments</li>
                <li>All attendance records</li>
                <li>The subject itself</li>
            </ul>
            <p style="color: #991B1B; margin: 12px 0 0 0; font-weight: 600;">
                Students will be able to re-register with the same code next year.
            </p>
        </div>
    """, unsafe_allow_html=True)

    confirm_text = st.text_input(
        f'Type "{subject_code}" to confirm deletion',
        placeholder=f"Enter {subject_code}"
    )

    col_cancel, col_delete = st.columns(2)

    with col_cancel:
        if st.button("Cancel", use_container_width=True, type="secondary"):
            st.rerun()

    with col_delete:
        if st.button(
            "🗑️ Delete Permanently",
            use_container_width=True,
            type="primary",
            disabled=(confirm_text.strip().upper() != subject_code.strip().upper())
        ):
            with st.spinner("Deleting subject..."):
                success, msg = delete_subject(subject_id)
            
            if success:
                st.success(f"✅ {msg}")
                st.balloons()
                time.sleep(1.5)
                st.rerun()
            else:
                st.error(f"❌ Failed: {msg}")