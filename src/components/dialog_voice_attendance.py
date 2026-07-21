import streamlit as st
import pandas as pd
from datetime import datetime

from src.database.config import supabase
from src.pipelines.voice_pipeline import process_bulk_audio
from src.components.dialog_attendance_results import attendance_result_dialog


# Initialize session state
if "voice_attendance_results" not in st.session_state:
    st.session_state.voice_attendance_results = None


@st.dialog("Voice Attendance")
def voice_attendance_dialog(selected_subject_id):

    st.write(
        "🎤 Record the classroom audio of students saying "
        "'I am present'. AI will identify them automatically."
    )

    audio_data = st.audio_input("Record Classroom Audio")

    if st.button(
        "Analyze Audio",
        type="primary",
        use_container_width=True
    ):

        if audio_data is None:
            st.warning("Please record audio first.")
            return

        with st.spinner("Analyzing classroom audio..."):

            # Fetch enrolled students
            enrolled_res = (
                supabase.table("subject_students")
                .select("*,students(*)")
                .eq("subject_id", selected_subject_id)
                .execute()
            )

            enrolled_students = enrolled_res.data

            if not enrolled_students:
                st.warning("No students enrolled in this subject.")
                return

            # Create candidate dictionary
            candidates_dict = {
                s["students"]["student_id"]: s["students"]["voice_embedding"]
                for s in enrolled_students
                if s["students"].get("voice_embedding")
            }

            if not candidates_dict:
                st.error("No enrolled students have registered voice profiles.")
                return

            # Read audio
            audio_bytes = audio_data.read()

            # Run voice recognition
            detected_scores = process_bulk_audio(
                audio_bytes,
                candidates_dict
            )

            results = []
            attendance_to_log = []

            current_timestamp = datetime.now().strftime(
                "%Y-%m-%dT%H:%M:%S"
            )

            # Prepare attendance data
            for node in enrolled_students:

                student = node["students"]

                score = detected_scores.get(
                    student["student_id"]
                )

                is_present = score is not None

                # Get actual roll_no - ensure it's a string
                actual_roll_no = student.get("roll_no")
                if actual_roll_no and str(actual_roll_no).strip() and str(actual_roll_no).strip().lower() not in ['none', 'null', 'nan', '']:
                    roll_no_display = str(actual_roll_no).strip()
                else:
                    roll_no_display = "⚠️ Not Set"
                
                results.append({
                    "Name": student["name"],
                    "Roll No": roll_no_display,
                    "Confidence": f"{score:.2f}" if score is not None else "-",
                    "Status": "✅ Present" if is_present else "❌ Absent",
                })

                attendance_to_log.append(
                    {
                        "student_id": student["student_id"],
                        "student_name": student.get("name", "Unknown"),
                        "roll_no": student.get("roll_no") or student["student_id"],
                        "subject_id": selected_subject_id,
                        "timestamp": current_timestamp,
                        "is_present": is_present,
                    }
                )

            # Store results in session state
            st.session_state.voice_attendance_results = (
                pd.DataFrame(results),
                attendance_to_log,
            )

            # Open attendance result dialog
            df_results, logs = st.session_state.voice_attendance_results

            attendance_result_dialog(
                df_results,
                logs,
            )