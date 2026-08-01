import streamlit as st
from src.database.db import upsert_attendance_logs
import pandas as pd
from io import BytesIO


def show_attendance_result(df, logs):
    # FIX: Guard against empty DataFrame or missing Status column
    if df.empty or 'Status' not in df.columns:
        st.warning("No attendance records to display.")
        return

    total = len(df)
    present = len(df[df['Status'] == '✅ Present'])
    absent = total - present
    percentage = round((present / total) * 100) if total > 0 else 0

    st.markdown(f"""
        <div style="
            background: linear-gradient(135deg, #4F46E5 0%, #7C3AED 100%);
            border-radius: 16px;
            padding: 20px;
            margin-bottom: 20px;
            color: white;
        ">
            <div style="display: flex; justify-content: space-between; align-items: center;">
                <div>
                    <h3 style="color: white; margin: 0; font-size: 1.3rem;">Attendance Summary</h3>
                    <p style="color: rgba(255,255,255,0.8); margin: 4px 0 0 0; font-size: 0.9rem;">
                        {present} Present · {absent} Absent · {percentage}% Rate
                    </p>
                </div>
                <div style="
                    background: rgba(255,255,255,0.2);
                    border-radius: 50%;
                    width: 60px;
                    height: 60px;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    font-size: 1.5rem;
                    font-weight: 700;
                ">
                    {percentage}%
                </div>
            </div>
        </div>
    """, unsafe_allow_html=True)

    st.markdown("<p style='color: #64748B; margin-bottom: 12px;'>Please review attendance before confirming.</p>", unsafe_allow_html=True)

    display_cols = ['Name', 'Roll No', 'Status']
    if 'Source' in df.columns:
        display_cols.insert(2, 'Source')
    if 'Confidence' in df.columns:
        display_cols.insert(2, 'Confidence')

    styled_df = df[display_cols].copy()
    styled_df['Roll No'] = styled_df['Roll No'].astype(str)

    st.dataframe(styled_df, hide_index=True, use_container_width=True)

    excel_buffer = BytesIO()
    df.to_excel(excel_buffer, index=False, engine='openpyxl')
    excel_buffer.seek(0)

    col_dl, col_discard, col_confirm = st.columns([1, 1, 1])

    with col_dl:
        st.download_button(
            label="📥 Download Excel",
            data=excel_buffer,
            file_name=f"attendance_{pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            width='stretch',
            type="secondary"
        )

    with col_discard:
        if st.button("🗑️ Discard", width='stretch', type="tertiary"):
            st.session_state.show_attendance_dialog = False
            st.session_state.voice_attendance_results = None
            st.session_state.attendance_images = []
            st.session_state.attendance_df = None
            st.session_state.attendance_logs = None
            st.session_state.show_voice_dialog = False
            st.rerun()

    with col_confirm:
        if st.button('✅ Confirm and Save', width='stretch', type='primary'):
            try:
                upsert_attendance_logs(logs)
                st.toast("🎉 Attendance saved successfully!", icon="✅")
                st.session_state.show_attendance_dialog = False
                st.session_state.attendance_images = []
                st.session_state.voice_attendance_results = None
                st.session_state.attendance_df = None
                st.session_state.attendance_logs = None
                st.session_state.show_voice_dialog = False
                st.rerun()
            except Exception as e:
                st.error(f'❌ Failed to save attendance: {str(e)}')
                st.info("💡 No records were saved. Please check your connection and try again.")


def attendance_result_dialog(df, logs):
    show_attendance_result(df, logs)