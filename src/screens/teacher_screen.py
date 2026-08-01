import streamlit as st
import numpy as np
import pandas as pd
from datetime import datetime
from io import BytesIO
import time
from src.components.subject_card import subject_card
from src.components.footer import footer_dashboard
from src.components.header import header_dashboard
from src.UI.base_layout import (
    style_background_dashboard,
    style_base_layout,
    style_dashboard_shell,
)
from src.components.dialog_share_subject import share_subject_dialog
from src.components.dialog_subject_report import subject_report_dialog

from src.database.db import (
    check_teacher_exists, create_teacher, teacher_login, 
    get_teacher_subjects, get_attendance_for_teacher,
    get_all_attendance_for_teacher_detailed,
    sanitize_string, validate_password, VALID_USERNAME_PATTERN
)

from src.components.dialog_create_subject import create_subject_dialog
from src.components.dialog_add_photo import add_photos_dialog
from src.pipelines.face_pipeline import predict_attendance
from src.components.dialog_attendance_results import attendance_result_dialog
from src.database.config import supabase
from src.components.dialog_voice_attendance import voice_attendance_dialog
from src.components.dialog_delete_subject import delete_subject_dialog
from src.components.dialog_session_details import session_details_dialog


MAX_ATTEMPTS = 5
LOCKOUT_SECONDS = 300


def teacher_screen():
    style_base_layout()
    style_background_dashboard()
    style_dashboard_shell()

    if "teacher_data" in st.session_state:
        teacher_dashboard()
    elif (
        "teacher_login_type" not in st.session_state
        or st.session_state["teacher_login_type"] == "login"
    ):
        teacher_screen_login()
    else:
        teacher_screen_register()


def teacher_dashboard():
    teacher_data = st.session_state.teacher_data
    c1, c2 = st.columns(2, vertical_alignment="center")

    with c1:
        header_dashboard()

    with c2:
        if st.button(
            "Logout",
            key="login_back",
            type="secondary",
            shortcut="control+backspace",
        ):
            st.session_state["is_logged_in"] = False
            del st.session_state["teacher_data"]
            st.rerun()

    st.space()

    if "current_teacher_tab" not in st.session_state:
        st.session_state.current_teacher_tab = "Take Attendance"

    tab1, tab2, tab3 = st.columns(3)

    with tab1:
        type1 = 'primary' if st.session_state.current_teacher_tab == "Take Attendance" else 'tertiary'
        if st.button('Take Attendance', type=type1, width='stretch', icon=':material/assignment_turned_in:'):
            st.session_state.current_teacher_tab = "Take Attendance"
            st.rerun()

    with tab2:
        type2 = 'primary' if st.session_state.current_teacher_tab == "Manage Subjects" else 'tertiary'
        if st.button('Manage Subjects', type=type2, width='stretch', icon=':material/book_ribbon:'):
            st.session_state.current_teacher_tab = "Manage Subjects"
            st.rerun()

    with tab3:
        type3 = 'primary' if st.session_state.current_teacher_tab == "Attendance Records" else 'tertiary'
        if st.button('Attendance Records', type=type3, width='stretch', icon=':material/school:'):
            st.session_state.current_teacher_tab = "Attendance Records"
            st.rerun()

    st.divider()

    if st.session_state.current_teacher_tab == "Take Attendance":
        teacher_tab_take_attendance()
    if st.session_state.current_teacher_tab == "Manage Subjects":
        teacher_tab_manage_subjects()
    if st.session_state.current_teacher_tab == "Attendance Records":
        teacher_tab_attendance_records()

    footer_dashboard()


def teacher_tab_take_attendance():
    teacher_id = st.session_state.teacher_data["teacher_id"]
    st.header("Take Attendance")

    if 'attendance_images' not in st.session_state:
        st.session_state.attendance_images = []

    subjects = get_teacher_subjects(teacher_id)

    if not subjects:
        st.warning("You haven't created any subjects yet! Please create one to begin!")
        return

    subject_options = {f"{s['name']} ({s.get('course', 'N/A')}) - {s['subject_code']}": s['subject_id'] for s in subjects}

    col1, col2 = st.columns([3, 1], vertical_alignment='bottom')

    with col1:
        selected_subject_label = st.selectbox('Select Subject', options=list(subject_options.keys()))

    with col2:
        if st.button('Add Photos', type='primary', icon=':material/photo_prints:', width='stretch'):
            add_photos_dialog()

    selected_subject_id = subject_options[selected_subject_label]
    st.divider()

    if st.session_state.attendance_images:
        st.markdown("""
            <h3 style="color: #0F172A; font-size: 1.2rem; font-weight: 700; margin: 16px 0 12px 0;">
                📸 Added Photos
            </h3>
        """, unsafe_allow_html=True)

        gallery_cols = st.columns(4)

        for idx, img in enumerate(st.session_state.attendance_images):
            with gallery_cols[idx % 4]:
                st.markdown("""
                    <div style="
                        border-radius: 12px;
                        overflow: hidden;
                        box-shadow: 0 2px 8px rgba(0,0,0,0.08);
                        border: 1px solid #E2E8F0;
                    ">
                """, unsafe_allow_html=True)
                st.image(img,caption=f'Photo {idx+1}')
                st.markdown("</div>", unsafe_allow_html=True)

    has_photos = bool(st.session_state.attendance_images)
    st.divider()

    c1, c2, c3 = st.columns(3)

    with c1:
        if st.button(
            "Clear All Photos",
            key="clear_all_photos_bottom",
            width='stretch',
            type='tertiary',
            icon=':material/delete:',
            disabled=not has_photos
        ):
            st.session_state.attendance_images = []
            st.rerun()

    with c2:
        run_face_clicked = st.button(
            "Run Face Analysis",
            key="run_face_analysis",
            width='stretch',
            type='secondary',
            icon=':material/analytics:',
            disabled=not has_photos
        )

    with c3:
        voice_attendance_clicked = st.button(
            "Use Voice Attendance",
            key="voice_attendance",
            type='primary',
            width='stretch',
            icon=':material/mic:'
        )

    def get_existing_attendance_row(student_id, subject_id):
        today = datetime.now().strftime("%Y-%m-%d")
        res = supabase.table('attendance_logs').select('id,is_present')\
            .eq('student_id', student_id).eq('subject_id', subject_id)\
            .gte('timestamp', f"{today}T00:00:00").execute()
        return res.data[0] if res.data else None

    if run_face_clicked and has_photos:
        with st.status("🔍 Processing classroom photos...", expanded=True) as status:
            progress_bar = st.progress(0)
            all_detected_ids = {}

            for idx, img in enumerate(st.session_state.attendance_images):
                img_np = np.array(img.convert("RGB"))
                detected, _, _ = predict_attendance(img_np)

                if detected:
                    for sid in detected.keys():
                        student_id = int(sid)
                        all_detected_ids.setdefault(student_id, []).append(f"Photo {idx+1}")

                progress_bar.progress((idx + 1) / len(st.session_state.attendance_images))

            status.update(label="✅ Photo analysis complete!", state="complete")

            try:
                enrolled_res = (
                    supabase.table("subject_students")
                    .select("*,students(student_id,name,roll_no)")
                    .eq("subject_id", selected_subject_id)
                    .execute()
                )
                enrolled_students = enrolled_res.data
            except Exception as e:
                st.error(f"Failed to fetch students: {e}")
                enrolled_students = []

            if not enrolled_students:
                st.warning("No students enrolled in this course")
            else:
                results = []
                attendance_to_log = []
                current_timestamp = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")

                for node in enrolled_students:
                    student = node["students"]

                    existing_row = get_existing_attendance_row(student["student_id"], selected_subject_id)
                    sources = all_detected_ids.get(int(student["student_id"]), [])
                    is_present = len(sources) > 0

                    if existing_row and (existing_row["is_present"] or not is_present):
                         # Already logged present, or still not seen in any photo — nothing new
                         continue

                    actual_roll_no = student.get("roll_no")
                    if actual_roll_no and str(actual_roll_no).strip() and str(actual_roll_no).strip().lower() not in ['none', 'null', 'nan', '']:
                        roll_no_display = str(actual_roll_no).strip()
                    else:
                        roll_no_display = "⚠️ Not Set"

                    results.append({
                        "Name": student["name"],
                        "Roll No": roll_no_display,
                        "Source": ", ".join(sources) if is_present else "-",
                        "Status": "✅ Present" if is_present else "❌ Absent",
                    })

                    attendance_to_log.append({
                        "student_id": student["student_id"],
                        "student_name": student.get("name", "Unknown"),
                        "roll_no": student.get("roll_no") or student["student_id"],
                        "subject_id": selected_subject_id,
                        "timestamp": current_timestamp,
                        "is_present": is_present,
                    })

                # FIX: Guard against empty results (all students already have attendance today)
                if not results:
                    st.info("✅ All students already have attendance recorded for today.")
                    st.session_state.attendance_images = []
                    st.rerun()
                    return

                st.session_state.show_attendance_dialog = True
                st.session_state.attendance_df = pd.DataFrame(results)
                st.session_state.attendance_logs = attendance_to_log
                st.rerun()

    if voice_attendance_clicked:
        st.session_state.show_voice_dialog = True
        st.session_state.voice_subject_id = selected_subject_id
        st.rerun()

    if st.session_state.get("show_attendance_dialog"):
        attendance_result_dialog(
            st.session_state.attendance_df,
            st.session_state.attendance_logs
        )

    if st.session_state.get("show_voice_dialog"):
        voice_attendance_dialog(st.session_state.voice_subject_id)


def teacher_tab_manage_subjects():
    teacher_id = st.session_state.teacher_data['teacher_id']
    col1, col2 = st.columns(2)

    with col1:
        st.header("Manage Subjects")

    with col2:
        if st.button("Add New Subject", type='primary', icon=':material/add_circle:', width='stretch'):
            create_subject_dialog(teacher_id)

    subjects = get_teacher_subjects(teacher_id)
    if subjects:
        for i, sub in enumerate(subjects):
            stats = [
                ("👥", "Students", sub["total_students"]),
                ("🏛️", "Classes", sub["total_classes"])
            ]

            def subject_actions(sub=sub, idx=i):
                report_col, share_col, delete_col = st.columns(3)

                with report_col:
                    if st.button(
                        "📊 Report",
                        key=f"report_{sub['subject_code']}_{sub['section']}_{idx}",
                        icon=":material/assessment:",
                        width='stretch',
                        type="primary"
                    ):
                        subject_report_dialog(
                            sub["subject_id"],
                            sub["name"],
                            sub["subject_code"],
                            sub.get("course", "N/A"),
                            sub["section"],
                            teacher_id
                        )

                with share_col:
                    if st.button(
                        "🔗 Share",
                        key=f"share_{sub['subject_code']}_{sub['section']}_{idx}",
                        icon=":material/share:",
                        width='stretch',
                        type="secondary"
                    ):
                        share_subject_dialog(
                            f"{sub['name']} - {sub.get('course', 'N/A')} ({sub['section']})",
                            sub["subject_code"]
                        )

                with delete_col:
                    if st.button(
                        "🗑️ Delete",
                        key=f"delete_{sub['subject_code']}_{sub['section']}_{idx}",
                        icon=":material/delete_forever:",
                        width='stretch',
                        type="tertiary"
                    ):
                        delete_subject_dialog(
                            sub["subject_id"],
                            sub["name"],
                            sub["subject_code"],
                            sub.get("course", "N/A"),
                            sub["section"],
                            teacher_id
                        )

                st.space()

            subject_card(
                name=sub["name"],
                code=sub["subject_code"],
                course=sub.get("course", "N/A"),
                section=sub["section"],
                stats=stats,
                footer_callback=subject_actions
            )
    else:
        st.markdown("""
            <div style="
                text-align: center;
                padding: 60px 20px;
                background: white;
                border-radius: 20px;
                border: 2px dashed #CBD5E1;
                margin-top: 20px;
            ">
                <div style="font-size: 48px; margin-bottom: 16px;">📚</div>
                <h3 style="color: #334155; margin: 0 0 8px 0;">No Subjects Yet</h3>
                <p style="color: #94A3B8; margin: 0;">Create your first subject to get started!</p>
            </div>
        """, unsafe_allow_html=True)


def teacher_tab_attendance_records():
    st.header("Attendance Records")

    teacher_id = st.session_state.teacher_data["teacher_id"]
    records = get_attendance_for_teacher(teacher_id)

    if not records:
        st.info("No attendance records found.")
        return

    session_data = []
    for r in records:
        ts = r.get("timestamp")
        subject = r.get("subjects", {})

        session_data.append({
            "ts_group": datetime.fromisoformat(ts).date() if ts else None,
            "timestamp_raw": ts,
            "Time": datetime.fromisoformat(ts).strftime("%Y-%m-%d %I:%M %p") if ts else "N/A",
            "Subject": subject.get("name", "Unknown"),
            "Subject Code": subject.get("subject_code", "N/A"),
            "Course": subject.get("course", "N/A"),
            "Section": subject.get("section", "N/A"),
            "subject_id": subject.get("subject_id"),
            "is_present": bool(r.get("is_present", False)),
        })

    df_sessions = pd.DataFrame(session_data)

    session_summary = (
            df_sessions.groupby([
                "ts_group", "Subject", "Subject Code", "Course", "Section", "subject_id"
            ])
            .agg(
                Present_Count=("is_present", "sum"),
                Total_Count=("is_present", "count"),
                timestamp_raw=("timestamp_raw", "max"),  # latest update time that day
            )
            .reset_index()
        )
    session_summary["Time"] = session_summary["timestamp_raw"].apply(
            lambda ts: datetime.fromisoformat(ts).strftime("%Y-%m-%d %I:%M %p") if ts else "N/A"
        )

    session_summary["Attendance Rate"] = (
        (session_summary["Present_Count"] / session_summary["Total_Count"] * 100)
        .round(1)
    ).astype(str) + "%"

    session_summary = session_summary.sort_values(by="ts_group", ascending=False)

    st.markdown("<p style='color: #64748B; margin-bottom: 16px;'>Click on any session to view full student details</p>", unsafe_allow_html=True)

    for idx, row in session_summary.iterrows():
        rate = float(row["Attendance Rate"].replace("%", ""))
        rate_color = "#10B981" if rate >= 75 else "#F59E0B" if rate >= 50 else "#EF4444"

        col1, col2, col3 = st.columns([3, 1, 1])

        with col1:
            if st.button(
                f"📅 {row['Time']} | {row['Subject']} ({row['Course']}) - Sec {row['Section']}",
                key=f"session_btn_{idx}",
                width='stretch',
                type="secondary"
            ):
                session_details_dialog(
                    teacher_id,
                    row["subject_id"],
                    row["Subject"],
                    row["Subject Code"],
                    row["Course"],
                    row["Section"],
                    str(row["ts_group"]),
                    int(row["Present_Count"]),
                    int(row["Total_Count"])
                )

        with col2:
            st.markdown(f"""
                <div style="
                    background: {rate_color}15;
                    color: {rate_color};
                    padding: 8px 16px;
                    border-radius: 10px;
                    text-align: center;
                    font-weight: 600;
                    font-size: 0.9rem;
                ">
                    {int(row['Present_Count'])} / {int(row['Total_Count'])} Students
                </div>
            """, unsafe_allow_html=True)

        with col3:
            st.markdown(f"""
                <div style="
                    background: {rate_color}15;
                    color: {rate_color};
                    padding: 8px 16px;
                    border-radius: 10px;
                    text-align: center;
                    font-weight: 700;
                    font-size: 1rem;
                ">
                    {row['Attendance Rate']}
                </div>
            """, unsafe_allow_html=True)

    st.divider()
    st.markdown("<h3 style='color: #0F172A; font-size: 1.1rem; margin-bottom: 12px;'>📥 Download Reports</h3>", unsafe_allow_html=True)

    detailed_records = get_all_attendance_for_teacher_detailed(teacher_id)

    if detailed_records:
        excel_data = []
        for r in detailed_records:
            ts = r.get("timestamp")
            student = r.get("students", {})
            subject = r.get("subjects", {})

            excel_data.append({
                "Date": datetime.fromisoformat(ts).strftime("%Y-%m-%d") if ts else "N/A",
                "Time": datetime.fromisoformat(ts).strftime("%I:%M %p") if ts else "N/A",
                "Subject Name": subject.get("name", "Unknown"),
                "Subject Code": subject.get("subject_code", "N/A"),
                "Course": subject.get("course", "N/A"),
                "Section": subject.get("section", "N/A"),
                "Roll No": student.get("roll_no") or student.get("student_id", "N/A"),
                "Student Name": student.get("name", "Unknown"),
                "Status": "Present" if r.get("is_present") else "Absent",
            })

        df_excel = pd.DataFrame(excel_data)

        student_summary = df_excel.groupby([
            "Roll No", "Student Name", "Subject Name", "Subject Code", "Course", "Section"
        ]).agg(
            Classes_Attended=("Status", lambda x: (x == "Present").sum()),
            Total_Classes=("Status", "count"),
        ).reset_index()

        student_summary["Attendance %"] = (
            (student_summary["Classes_Attended"] / student_summary["Total_Classes"] * 100)
            .round(1)
        ).astype(str) + "%"

        excel_buffer = BytesIO()

        with pd.ExcelWriter(excel_buffer, engine='openpyxl') as writer:
            df_excel.to_excel(writer, index=False, sheet_name='All Records')
            student_summary.to_excel(writer, index=False, sheet_name='Student Summary')

            session_summary_export = session_summary[[
                "Time", "Subject", "Subject Code", "Course", "Section",
                "Present_Count", "Total_Count", "Attendance Rate"
            ]].copy()
            session_summary_export.columns = [
                "Date & Time", "Subject", "Code", "Course", "Section",
                "Present", "Total", "Rate"
            ]
            session_summary_export.to_excel(writer, index=False, sheet_name='Session Summary')

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
                label="📊 Download Complete Excel Report",
                data=excel_buffer,
                file_name=f"attendance_complete_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                width='stretch',
                type="primary",
                icon=":material/download:"
            )

        with col2:
            st.markdown("""
                <p style="color: #94A3B8; font-size: 0.85rem; margin-top: 8px;">
                    Contains 3 sheets: All Records, Student Summary, and Session Summary
                </p>
            """, unsafe_allow_html=True)


def login_teacher(username, password):
    if not username or not password:
        return False

    teacher = teacher_login(username, password)

    if teacher:
        st.session_state.user_role = 'teacher'
        st.session_state.teacher_data = teacher
        st.session_state.is_logged_in = True
        st.session_state.login_attempts = 0
        return True
    return False


def teacher_screen_login():
    # FIX: Initialize session state inside function (safe for Streamlit reruns)
    if "login_attempts" not in st.session_state:
        st.session_state.login_attempts = 0
    if "last_attempt_time" not in st.session_state:
        st.session_state.last_attempt_time = 0

    c1, c2 = st.columns(2, vertical_alignment="center")

    with c1:
        header_dashboard()

    with c2:
        if st.button(
            "Back to Home",
            key="login_back",
            type="secondary",
            shortcut="control+backspace",
        ):
            st.session_state["login_type"] = None
            st.rerun()

    st.header("Login using Password")
    st.space()
    st.space()

    # Check lockout using .get() with default for extra safety
    login_attempts = st.session_state.get("login_attempts", 0)
    if login_attempts >= MAX_ATTEMPTS:
        time_since_last = time.time() - st.session_state.get("last_attempt_time", 0)
        if time_since_last < LOCKOUT_SECONDS:
            remaining = int(LOCKOUT_SECONDS - time_since_last)
            st.error(f"⛔ Too many failed attempts. Please wait {remaining} seconds.")
            return
        else:
            st.session_state.login_attempts = st.session_state.get("login_attempts", 0) + 1
            st.session_state.last_attempt_time = time.time()
            remaining = MAX_ATTEMPTS - st.session_state.get("login_attempts", 0)
            st.error(f"Invalid credentials. {remaining} attempts remaining before lockout.")

    teacher_username = st.text_input(
        "Username",
        key="teacher_login_username",
        placeholder="Enter your username",
    )

    teacher_password = st.text_input(
        "Password",
        key="teacher_login_password",
        placeholder="Enter your password",
        type="password",
    )

    st.divider()

    c1, c2 = st.columns(2)

    with c1:
        if st.button(
            "Login",
            icon=":material/passkey:",
            shortcut="control+enter",
            width="stretch",
        ):
            if login_teacher(teacher_username, teacher_password):
                st.toast("Welcome back!", icon="👋")
                time.sleep(1)
                st.rerun()
            else:
                st.session_state.login_attempts += 1
                st.session_state.last_attempt_time = time.time()
                remaining = MAX_ATTEMPTS - st.session_state.login_attempts
                st.error(f"Invalid credentials. {remaining} attempts remaining before lockout.")

    with c2:
        if st.button(
            "Register Instead",
            type="primary",
            icon=":material/person_add:",
            shortcut="alt+n",
            width="stretch",
        ):
            st.session_state["teacher_login_type"] = "register"
            st.rerun()

    footer_dashboard()


def register_teacher(teacher_username, teacher_name, teacher_password, teacher_password_confirm):
    # Validate inputs using sanitize_string
    try:
        username = sanitize_string(teacher_username, 50, VALID_USERNAME_PATTERN)
        name = sanitize_string(teacher_name, 100)
        password = validate_password(teacher_password)
    except ValueError as e:
        return False, str(e)

    if not all([username, name, password]):
        return False, "All fields are required!"

    if check_teacher_exists(username):
        return False, "Username already taken!"

    if teacher_password != teacher_password_confirm:
        return False, "Passwords do not match!"

    try:
        create_teacher(username, password, name)
        return True, "Successfully Created! Login Now"
    except Exception as e:
        return False, str(e)


def teacher_screen_register():
    c1, c2 = st.columns(2, vertical_alignment="center")

    with c1:
        header_dashboard()

    with c2:
        if st.button(
            "Back to Home",
            key="register_back",
            type="secondary",
            shortcut="control+backspace",
        ):
            st.session_state["login_type"] = None
            st.rerun()

    st.header("Register a New Account")

    teacher_username = st.text_input(
        "Username",
        key="teacher_register_username",
        placeholder="Choose username (letters, numbers, underscores only)",
    )

    teacher_name = st.text_input(
        "Full Name",
        key="teacher_register_name",
        placeholder="Enter your full name",
    )

    teacher_password = st.text_input(
        "Password",
        key="teacher_register_password",
        placeholder="Min 8 chars, 1 upper, 1 lower, 1 digit, 1 special",
        type="password",
    )

    teacher_password_confirm = st.text_input(
        "Confirm Password",
        key="teacher_register_confirm_password",
        placeholder="Confirm password",
        type="password",
    )

    st.divider()

    c1, c2 = st.columns(2)

    with c1:
        if st.button(
            "Register",
            type="primary",
            icon=":material/person_add:",
            width="stretch",
        ):
            success, msg = register_teacher(
                teacher_username,
                teacher_name,
                teacher_password,
                teacher_password_confirm,
            )
            if success:
                st.success(msg)
                time.sleep(1)
                st.session_state["teacher_login_type"] = "login"
                st.rerun()
            else:
                st.error(msg)
                if "already taken" in msg:
                    st.info("💡 Already have an account? Click 'Login Instead' below.")

    with c2:
        if st.button(
            "Login Instead",
            type="secondary",
            width="stretch",
        ):
            st.session_state["teacher_login_type"] = "login"
            st.rerun()

    footer_dashboard()