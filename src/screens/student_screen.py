import streamlit as st

from src.components.footer import footer_dashboard
from src.components.header import header_dashboard
from src.UI.base_layout import (
    style_background_dashboard,
    style_base_layout,
)
from PIL import Image
import numpy as np
import time
from src.pipelines.face_pipeline import predict_attendance, get_face_embeddings
from src.pipelines.voice_pipeline import get_voice_embedding
from src.database.db import (
    get_all_students, create_student, get_student_subjects, 
    get_student_attendance, unenroll_student_to_subject,
    sanitize_string, VALID_ROLLNO_PATTERN, check_student_exists_by_roll_no
)
from src.database.config import supabase
from src.components.dialog_enroll import enroll_dialog
from src.components.subject_card import subject_card
from src.components.dialog_voice_attendance import voice_attendance_dialog


def student_dashboard():
    student_data = st.session_state.student_data
    student_id = student_data['student_id']
    c1, c2 = st.columns(2, vertical_alignment="center")

    with c1:
        header_dashboard()

    with c2:
        if st.button(
            "Logout",
            key="student_logout",
            type="secondary",
            icon=":material/logout:",
        ):
            st.session_state["is_logged_in"] = False
            st.session_state["user_role"] = None
            st.session_state["login_type"] = None
            del st.session_state["student_data"]
            st.rerun()

    st.markdown("<br>", unsafe_allow_html=True)

    # Welcome banner
    st.markdown(f"""
        <div style="
            background: linear-gradient(135deg, #4F46E5 0%, #7C3AED 100%);
            border-radius: 16px;
            padding: 20px 24px;
            margin-bottom: 20px;
            box-shadow: 0 4px 20px rgba(79, 70, 229, 0.2);
        ">
            <h3 style="color: white; margin: 0 0 4px 0; font-size: 1.3rem;">Welcome back, {student_data.get('name', 'Student')}!</h3>
            <p style="color: rgba(255,255,255,0.8); margin: 0; font-size: 0.9rem;">Manage your attendance and enrolled subjects below.</p>
        </div>
    """, unsafe_allow_html=True)

    # Profile / Face Management Section
    with st.expander("⚙️ Manage My Profile", expanded=False):
        st.markdown(f"""
            <div style="background: #F8FAFC; border-radius: 12px; padding: 16px; margin-bottom: 12px;">
                <p style="margin: 0 0 8px 0; color: #334155; font-weight: 600; font-size: 1rem;">
                    👤 {student_data.get('name', 'Unknown')}
                </p>
                <p style="margin: 0; color: #64748B; font-size: 0.85rem;">
                    Student ID: <code style="background: #E2E8F0; padding: 2px 8px; border-radius: 4px;">{student_id}</code>
                </p>
            </div>
        """, unsafe_allow_html=True)

        roll_no = student_data.get('roll_no')
        if roll_no:
            st.write(f"**Roll Number:** {roll_no}")
        else:
            st.error("⚠️ Roll Number not set! Please contact admin.")

        face_status = "✅ Registered" if student_data.get('face_embedding') else "❌ Not Registered"
        voice_status = "✅ Registered" if student_data.get('voice_embedding') else "❌ Not Registered"

        col_status1, col_status2 = st.columns(2)
        with col_status1:
            face_ok = student_data.get('face_embedding') is not None
            face_color = "#10B981" if face_ok else "#EF4444"
            face_icon = "✅" if face_ok else "❌"
            face_text = "Face ID Registered" if face_ok else "Face ID Not Set"
            st.markdown(f"""
                <div style="
                    background: {'#ECFDF5' if face_ok else '#FEF2F2'};
                    border: 1px solid {face_color};
                    border-radius: 10px;
                    padding: 12px;
                    text-align: center;
                ">
                    <div style="font-size: 24px; margin-bottom: 4px;">{face_icon}</div>
                    <div style="color: {face_color}; font-weight: 600; font-size: 0.85rem;">{face_text}</div>
                </div>
            """, unsafe_allow_html=True)

        with col_status2:
            voice_ok = student_data.get('voice_embedding') is not None
            voice_color = "#10B981" if voice_ok else "#EF4444"
            voice_icon = "✅" if voice_ok else "❌"
            voice_text = "Voice ID Registered" if voice_ok else "Voice ID Not Set"
            st.markdown(f"""
                <div style="
                    background: {'#ECFDF5' if voice_ok else '#FEF2F2'};
                    border: 1px solid {voice_color};
                    border-radius: 10px;
                    padding: 12px;
                    text-align: center;
                ">
                    <div style="font-size: 24px; margin-bottom: 4px;">{voice_icon}</div>
                    <div style="color: {voice_color}; font-weight: 600; font-size: 0.85rem;">{voice_text}</div>
                </div>
            """, unsafe_allow_html=True)

        st.divider()

        # Clear Face/Voice ID with Confirmation
        if "confirm_clear_face" not in st.session_state:
            st.session_state.confirm_clear_face = False
        if "confirm_clear_voice" not in st.session_state:
            st.session_state.confirm_clear_voice = False

        col1, col2 = st.columns(2)

        with col1:
            if not st.session_state.confirm_clear_face:
                if st.button(
                    "🗑️ Clear My Face ID",
                    key="clear_face_btn",
                    type="secondary",
                    width="stretch",
                    icon=":material/delete_forever:"
                ):
                    st.session_state.confirm_clear_face = True
                    st.rerun()
            else:
                st.warning("⚠️ Confirm: You'll need to re-register your face.")
                c1, c2 = st.columns(2)
                with c1:
                    if st.button("Cancel", key="cancel_clear_face", type="secondary"):
                        st.session_state.confirm_clear_face = False
                        st.rerun()
                with c2:
                    if st.button("Yes, Clear", key="confirm_clear_face", type="primary"):
                        try:
                            supabase.table("students").update({"face_embedding": None}).eq("student_id", student_id).execute()
                            st.session_state.student_data['face_embedding'] = None
                            st.success("Face ID cleared!")
                            st.session_state.confirm_clear_face = False
                            time.sleep(1.5)
                            st.rerun()
                        except Exception as e:
                            st.error(f"Failed to clear face: {str(e)}")

        with col2:
            if not st.session_state.confirm_clear_voice:
                if st.button(
                    "🗑️ Clear My Voice ID",
                    key="clear_voice_btn",
                    type="secondary",
                    width="stretch",
                    icon=":material/delete_forever:"
                ):
                    st.session_state.confirm_clear_voice = True
                    st.rerun()
            else:
                st.warning("⚠️ Confirm: You'll need to re-register your voice.")
                c1, c2 = st.columns(2)
                with c1:
                    if st.button("Cancel", key="cancel_clear_voice", type="secondary"):
                        st.session_state.confirm_clear_voice = False
                        st.rerun()
                with c2:
                    if st.button("Yes, Clear", key="confirm_clear_voice", type="primary"):
                        try:
                            supabase.table("students").update({"voice_embedding": None}).eq("student_id", student_id).execute()
                            st.session_state.student_data['voice_embedding'] = None
                            st.success("Voice ID cleared!")
                            st.session_state.confirm_clear_voice = False
                            time.sleep(1.5)
                            st.rerun()
                        except Exception as e:
                            st.error(f"Failed to clear voice: {str(e)}")

        st.info("Clearing your Face/Voice ID will require re-registration on next login.")

        st.divider()

        # Account Deletion with Confirmation
        st.markdown("""
            <div style="
                background: #FEF2F2;
                border: 1px solid #FCA5A5;
                border-radius: 12px;
                padding: 16px;
                margin-top: 16px;
            ">
                <h4 style="color: #DC2626; margin: 0 0 8px 0;">🚨 Danger Zone</h4>
                <p style="color: #7F1D1D; margin: 0; font-size: 0.9rem;">
                    Deleting your account will permanently remove all your data including enrollments and attendance records.
                </p>
            </div>
        """, unsafe_allow_html=True)

        if "show_delete_confirm" not in st.session_state:
            st.session_state.show_delete_confirm = False

        if not st.session_state.show_delete_confirm:
            if st.button(
                "Delete My Account",
                key="delete_account_btn",
                type="tertiary",
                width="stretch",
                icon=":material/warning:"
            ):
                st.session_state.show_delete_confirm = True
                st.rerun()
        else:
            st.markdown("""
                <p style="color: #DC2626; font-weight: 600; margin: 12px 0;">
                    ⚠️ This action cannot be undone!
                </p>
            """, unsafe_allow_html=True)

            confirm_text = st.text_input(
                'Type "DELETE" to confirm account deletion',
                placeholder="Type DELETE",
                key="delete_confirm_input"
            )

            col_cancel, col_confirm = st.columns(2)

            with col_cancel:
                if st.button("Cancel", width='stretch', type="secondary", key="delete_cancel"):
                    st.session_state.show_delete_confirm = False
                    st.rerun()

            with col_confirm:
                if st.button(
                    "🗑️ Permanently Delete Account",
                    width='stretch',
                    type="primary",
                    disabled=(confirm_text.strip().upper() != "DELETE"),
                    key="delete_confirm_btn"
                ):
                    try:
                        with st.spinner("Deleting your account..."):
                            st.cache_resource.clear()

                            supabase.table("subject_students").delete().eq("student_id", student_id).execute()
                            supabase.table("attendance_logs").delete().eq("student_id", student_id).execute()
                            supabase.table("students").delete().eq("student_id", student_id).execute()

                        st.success("✅ Account deleted successfully!")
                        st.session_state["is_logged_in"] = False
                        st.session_state["user_role"] = None
                        st.session_state["login_type"] = None
                        st.session_state.show_delete_confirm = False
                        if "student_data" in st.session_state:
                            del st.session_state["student_data"]
                        time.sleep(2)
                        st.rerun()
                    except Exception as e:
                        st.error(f"❌ Failed to delete account: {str(e)}")

    st.markdown("<br>", unsafe_allow_html=True)

    c1, c2 = st.columns(2)
    with c1:
        st.markdown("""
            <h2 style="color: #0F172A; font-size: 1.5rem; font-weight: 700; margin: 0;">
                📚 Your Enrolled Subjects
            </h2>
        """, unsafe_allow_html=True)

    with c2:
        if st.button('Enroll in Subject', type='primary', width='stretch'):
            enroll_dialog()

    st.divider()

    with st.spinner('Loading your enrolled subjects..'):
        subjects = get_student_subjects(student_id)
        logs = get_student_attendance(student_id)

    stats_map = {}

    for log in logs:
        sid = log['subject_id']

        if sid not in stats_map:
            stats_map[sid] = {'total': 0, "attended": 0}

        stats_map[sid]['total'] += 1

        if log.get("is_present"):
            stats_map[sid]['attended'] += 1

    cols = st.columns(2)
    for i, sub_node in enumerate(subjects):
        sub = sub_node['subjects']
        sid = sub['subject_id']

        stats = stats_map.get(sid, {"total": 0, "attended": 0})

        def unenroll_button(subject_id=sid):
            if st.button(
                "Unenroll from this course",
                type="tertiary",
                width="stretch",
                icon=":material/delete_forever:",
                key=f"unenroll_{subject_id}"
            ):
                unenroll_student_to_subject(student_id, subject_id)
                st.success("Successfully unenrolled!")
                time.sleep(1)
                st.rerun()

        with cols[i % 2]:
            subject_card(
                name=sub['name'],
                code=sub['subject_code'],
                course=sub.get('course', 'N/A'),
                section=sub['section'],
                stats=[
                    ('🗓️', 'Total', stats['total']),
                    ('✅', 'Attended', stats['attended'])
                ],
                footer_callback=unenroll_button
            )

    footer_dashboard()

def _normalize_embedding(emb):
    """Handle dict/list/numpy array embeddings uniformly."""
    # If dict, extract the vector
    if isinstance(emb, dict):
        emb = (emb.get('embedding') 
               or emb.get('encoding') 
               or emb.get('face_encoding') 
               or emb.get('vector') 
               or list(emb.values())[0])
    
    # Convert to numpy array for math operations
    if hasattr(emb, 'tolist'):
        return np.array(emb)
    return np.array(emb)


def student_screen():
    style_base_layout()
    style_background_dashboard()

    if "student_data" in st.session_state:
        student_dashboard()
        return

    c1, c2 = st.columns(
        2,
        vertical_alignment="center",
        gap="xxlarge"
    )

    with c1:
        header_dashboard()

    with c2:
        if st.button(
            "Go Back to Home",
            type="secondary",
            key="student_back",
            shortcut="control+backspace",
        ):
            st.session_state["login_type"] = None
            st.rerun()

    st.header(
        "Login using FaceID",
        text_alignment="center",
    )

    st.info("📷 Please allow camera access when prompted")

    photo_source = None
    try:
        photo_source = st.camera_input(
            "Capture your selfie",
            key="student_camera",
        )
    except Exception as e:
        st.warning("⚠️ Camera access failed. Please use upload option below.")

    if not photo_source:
        photo_source = st.file_uploader(
            "Or upload a photo",
            type=["jpg", "jpeg", "png"],
            help="Make sure your face is clearly visible and well-lit"
        )

    show_registration = False

    if photo_source:
        img = np.array(Image.open(photo_source))

        with st.status("🔍 AI is analyzing your face...", expanded=True) as status:
            detected, all_ids, num_faces = predict_attendance(img)

            if num_faces == 0:
                status.update(label="❌ No face detected", state="error")
                st.error("No face detected. Tips: Ensure good lighting, face the camera directly.")
                st.button("🔄 Try Again", key="retry_no_face")
            elif num_faces > 1:
                status.update(label="⚠️ Multiple faces detected", state="error")
                st.error("Multiple faces found. Please ensure only YOUR face is visible.")
            else:
                if detected:
                    student_id = list(detected.keys())[0]
                    status.update(label="✅ Face recognized!", state="complete")
                    st.success(f"Welcome, {student_id}!")
                    all_students = get_all_students()
                    student = next((s for s in all_students if s.get('student_id') == student_id), None)

                    if student:
                        st.session_state.is_logged_in = True
                        st.session_state.user_role = "student"
                        st.session_state.student_data = student
                        st.toast(f"Welcome back, {student.get('name')}!", icon="✅")
                        time.sleep(1)
                        st.rerun()
                else:
                    status.update(label="❌ Face not recognized", state="error")
                    st.info("Face not recognized! You might be a new student.")
                    show_registration = True

    if show_registration:
        with st.container():
            st.header("New Student Registration")

            new_name = st.text_input(
                "Enter your Full Name *",
                placeholder="Eg. Sonu Saini",
                key="reg_name"
            )

            st.markdown("""
                <div style="
                    background: #FEF3C7;
                    border-left: 4px solid #F59E0B;
                    padding: 12px 16px;
                    border-radius: 8px;
                    margin: 16px 0;
                ">
                    <p style="color: #92400E; margin: 0; font-weight: 600;">
                        ⚠️ Important: Enter your actual College Roll Number
                    </p>
                    <p style="color: #A16207; margin: 4px 0 0 0; font-size: 0.85rem;">
                        This will be used by teachers in attendance reports. It cannot be changed later.
                    </p>
                </div>
            """, unsafe_allow_html=True)

            roll_no = st.text_input(
                "Enter your Roll Number *",
                placeholder="Eg. 2401015007",
                key="reg_roll_no",
                help="Your actual college/university roll number"
            )

            st.subheader("Optional: Voice Enrollment")
            st.info("Enroll your voice for voice-only attendance")

            audio_data = None
            try:
                audio_data = st.audio_input(
                    "Record your voice like: I am present, My name is Sonu Saini", 
                    key="voice_enrollment_register"
                )
            except Exception as e:
                st.warning("Microphone not available. You can skip voice enrollment.")

            # ── FIXED: Create Account Button ──────────────────────────
            if st.button('Create Account', type='primary', use_container_width=True):
                if not new_name or not new_name.strip():
                    st.error("⛔ Please enter your name")
                    return

                try:
                    roll_no_clean = sanitize_string(roll_no.strip().upper(), 20, VALID_ROLLNO_PATTERN)
                except ValueError as e:
                    st.error(f"⛔ Invalid roll number: {e}")
                    return

                if not roll_no_clean:
                    st.error("⛔ Roll Number is required!")
                    return

                if check_student_exists_by_roll_no(roll_no_clean):
                    st.error(f"⛔ A student with Roll Number '{roll_no_clean}' already exists!")
                    st.info("💡 Tip: Go back and click 'Student Portal' to login with your face.")
                    return

                from src.pipelines.face_pipeline import get_trained_model

                with st.spinner("Creating your account..."):
                    encodings = get_face_embeddings(img)

                    if not encodings:
                        st.error("Face encoding failed. Please try again with better lighting.")
                        return

                    # ── FIX: Normalize embedding regardless of format ───
                    new_emb = _normalize_embedding(encodings[0])

                    # Check for duplicate face
                    model_data = get_trained_model()
                    if model_data:
                        X_train = model_data['X']
                        y_train = model_data['y']

                        for emb_raw, sid in zip(X_train, y_train):
                            emb_existing = _normalize_embedding(emb_raw)
                            distance = np.linalg.norm(emb_existing - new_emb)
                            if distance < 0.5:
                                st.error(f"⛔ This face is already registered to student ID {sid}. Please login instead.")
                                st.info("💡 If you forgot your roll number, contact your teacher.")
                                return

                    # Convert to list for database storage
                    face_emb = new_emb.tolist()
                    voice_embedding = None

                    if audio_data:
                        audio_bytes = audio_data.read()
                        voice_embedding = get_voice_embedding(audio_bytes)

                    response_data = create_student(
                        new_name.strip(),
                        roll_no=roll_no_clean,
                        face_embedding=face_emb,
                        voice_embedding=voice_embedding
                    )

                    if response_data:
                        st.session_state.is_logged_in = True
                        st.session_state.user_role = "student"
                        st.session_state.student_data = response_data[0]
                        st.toast(f"✅ Profile created! Welcome, {new_name.strip()}!", icon="🎉")
                        time.sleep(1)
                        st.rerun()
                    else:
                        st.error("Failed to create account. Please try again.")

    footer_dashboard()