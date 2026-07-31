import streamlit as st
import pandas as pd
from datetime import datetime
from io import BytesIO


@st.dialog("📊 Subject Attendance Report")
def subject_report_dialog(subject_id, subject_name, subject_code, course, section, teacher_id):
    from src.database.config import supabase
    
    st.markdown(f"""
        <div style="
            background: linear-gradient(135deg, #4F46E5 0%, #7C3AED 100%);
            border-radius: 16px;
            padding: 24px;
            margin-bottom: 24px;
            color: white;
        ">
            <h2 style="color: white; margin: 0; font-size: 1.5rem; font-weight: 800;">Attendance Report</h2>
            <p style="color: rgba(255,255,255,0.85); margin: 8px 0 0 0; font-size: 1rem;">
                📚 {subject_name} | 🎓 {course} | 📋 Section {section}
            </p>
            <p style="color: rgba(255,255,255,0.7); margin: 4px 0 0 0; font-size: 0.85rem;">
                Subject Code: {subject_code}
            </p>
        </div>
    """, unsafe_allow_html=True)

    with st.spinner("Generating report..."):
        # Get all attendance for this subject
        attendance_res = supabase.table('attendance_logs').select(
            "*,students(student_id,name,roll_no)"
        ).eq('subject_id', subject_id).execute()
        
        attendance_data = attendance_res.data if attendance_res.data else []
        
        # Get all enrolled students
        enrolled_res = supabase.table('subject_students').select(
            "*,students(student_id,name,roll_no)"
        ).eq('subject_id', subject_id).execute()
        
        enrolled_data = enrolled_res.data if enrolled_res.data else []

    if not enrolled_data:
        st.warning("No students enrolled in this subject.")
        return

    # Calculate total unique sessions
    unique_sessions = set()
    for r in attendance_data:
        ts = r.get('timestamp')
        if ts:
            unique_sessions.add(ts[:10])  # Just the date part
    
    total_classes = len(unique_sessions)

    # Build student attendance summary
    student_stats = {}
    
    # Initialize all enrolled students
    for node in enrolled_data:
        student = node.get('students', {})
        sid = student.get('student_id')
        if sid and sid not in student_stats:
            student_stats[sid] = {
                'roll_no': student.get('roll_no') or sid,
                'name': student.get('name', 'Unknown'),
                'present': 0,
                'total': total_classes,
            }

    # Count attendance
    for r in attendance_data:
        if r.get('is_present'):
            sid = r.get('student_id')
            if sid in student_stats:
                student_stats[sid]['present'] += 1

    # Build report dataframe
    report_rows = []
    sr_no = 1
    
    for sid, stats in sorted(student_stats.items(), key=lambda x: x[1]['roll_no']):
        attendance_pct = round((stats['present'] / stats['total'] * 100), 2) if stats['total'] > 0 else 0
        
        report_rows.append({
            'Sr. No.': sr_no,
            'Roll No.': stats['roll_no'],
            'Student Name': stats['name'],
            'Total Attendance': f"{stats['present']}/{stats['total']}",
            'Attendance %': f"{attendance_pct:.2f}%",
            '_pct': attendance_pct,  # For sorting/filtering
            '_present': stats['present'],
        })
        sr_no += 1

    df_report = pd.DataFrame(report_rows)

    # Summary stats
    total_students = len(report_rows)
    avg_attendance = round(df_report['_pct'].mean(), 2) if total_students > 0 else 0
    above_75 = len(df_report[df_report['_pct'] >= 75])
    below_75 = len(df_report[df_report['_pct'] < 75])

    # Summary Card
    st.markdown(f"""
        <div style="
            background: #F8FAFC;
            border: 1px solid #E2E8F0;
            border-radius: 12px;
            padding: 20px;
            margin-bottom: 20px;
        ">
            <h3 style="color: #0F172A; margin: 0 0 16px 0; font-size: 1.1rem;">📋 Summary</h3>
            <div style="display: flex; gap: 20px; flex-wrap: wrap;">
                <div style="flex: 1; min-width: 150px;">
                    <div style="color: #64748B; font-size: 0.85rem;">Total Students</div>
                    <div style="color: #0F172A; font-size: 1.5rem; font-weight: 700;">{total_students}</div>
                </div>
                <div style="flex: 1; min-width: 150px;">
                    <div style="color: #64748B; font-size: 0.85rem;">Total Classes</div>
                    <div style="color: #0F172A; font-size: 1.5rem; font-weight: 700;">{total_classes}</div>
                </div>
                <div style="flex: 1; min-width: 150px;">
                    <div style="color: #64748B; font-size: 0.85rem;">Avg Attendance</div>
                    <div style="color: #4F46E5; font-size: 1.5rem; font-weight: 700;">{avg_attendance:.2f}%</div>
                </div>
                <div style="flex: 1; min-width: 150px;">
                    <div style="color: #64748B; font-size: 0.85rem;">≥75% Attendance</div>
                    <div style="color: #10B981; font-size: 1.5rem; font-weight: 700;">{above_75}</div>
                </div>
                <div style="flex: 1; min-width: 150px;">
                    <div style="color: #64748B; font-size: 0.85rem;">&lt;75% Attendance</div>
                    <div style="color: #EF4444; font-size: 1.5rem; font-weight: 700;">{below_75}</div>
                </div>
            </div>
        </div>
    """, unsafe_allow_html=True)

    # Filter options
    col1, col2 = st.columns(2)
    with col1:
        filter_option = st.selectbox(
            "Filter Students",
            ["All Students", "≥75% Attendance", "<75% Attendance", "100% Attendance", "0% Attendance"],
            key=f"filter_{subject_id}"
        )
    
    with col2:
        sort_by = st.selectbox(
            "Sort By",
            ["Roll No", "Name", "Attendance % (High to Low)", "Attendance % (Low to High)"],
            key=f"sort_{subject_id}"
        )

    # Apply filters
    filtered_df = df_report.copy()
    
    if filter_option == "≥75% Attendance":
        filtered_df = filtered_df[filtered_df['_pct'] >= 75]
    elif filter_option == "<75% Attendance":
        filtered_df = filtered_df[filtered_df['_pct'] < 75]
    elif filter_option == "100% Attendance":
        filtered_df = filtered_df[filtered_df['_pct'] == 100]
    elif filter_option == "0% Attendance":
        filtered_df = filtered_df[filtered_df['_pct'] == 0]

    # Apply sorting
    if sort_by == "Roll No":
        filtered_df = filtered_df.sort_values('Roll No.')
    elif sort_by == "Name":
        filtered_df = filtered_df.sort_values('Student Name')
    elif sort_by == "Attendance % (High to Low)":
        filtered_df = filtered_df.sort_values('_pct', ascending=False)
    elif sort_by == "Attendance % (Low to High)":
        filtered_df = filtered_df.sort_values('_pct', ascending=True)

    # Display table
    display_df = filtered_df[['Sr. No.', 'Roll No.', 'Student Name', 'Total Attendance', 'Attendance %']].copy()
    display_df['Sr. No.'] = range(1, len(display_df) + 1)  # Re-number after filter

    st.dataframe(
        display_df,
        hide_index=True,
        width='stretch',
        column_config={
            "Attendance %": st.column_config.ProgressColumn(
                "Attendance %",
                help="Attendance percentage",
                format="%s",
                min_value=0,
                max_value=100,
            ),
        }
    )

    # Excel Download
    st.divider()
    
    excel_buffer = BytesIO()
    
    with pd.ExcelWriter(excel_buffer, engine='openpyxl') as writer:
        # Sheet 1: Attendance Report
        export_df = filtered_df[['Sr. No.', 'Roll No.', 'Student Name', 'Total Attendance', 'Attendance %']].copy()
        export_df.to_excel(writer, index=False, sheet_name='Attendance Report')
        
        # Sheet 2: Summary
        summary_data = {
            'Metric': [
                'Subject Name', 'Subject Code', 'Course', 'Section',
                'Total Students', 'Total Classes Conducted',
                'Average Attendance %', 'Students with ≥75%',
                'Students with <75%', 'Report Generated On'
            ],
            'Value': [
                subject_name, subject_code, course, section,
                total_students, total_classes,
                f"{avg_attendance:.2f}%", above_75,
                below_75, datetime.now().strftime("%Y-%m-%d %I:%M %p")
            ]
        }
        pd.DataFrame(summary_data).to_excel(writer, index=False, sheet_name='Summary')
        
        # Auto-adjust widths
        for sheet_name in writer.sheets:
            worksheet = writer.sheets[sheet_name]
            for column in worksheet.columns:
                max_length = 0
                column_letter = column[0].column_letter
                for cell in column:
                    try:
                        if cell.value and len(str(cell.value)) > max_length:
                            max_length = len(str(cell.value))
                    except:
                        pass
                adjusted_width = min(max_length + 2, 50)
                worksheet.column_dimensions[column_letter].width = adjusted_width

    excel_buffer.seek(0)

    col1, col2 = st.columns([1, 2])
    with col1:
        st.download_button(
            label="📥 Download Report (Excel)",
            data=excel_buffer,
            file_name=f"Attendance_Report_{subject_code}_{datetime.now().strftime('%Y%m%d')}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            width='stretch',
            type="primary",
            icon=":material/download:"
        )