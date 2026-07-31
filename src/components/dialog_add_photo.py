import streamlit as st
from PIL import Image

MAX_FILE_SIZE_MB = 10
MAX_IMAGE_DIMENSION = 4096


@st.dialog("Capture or Upload Photos")
def add_photos_dialog():
    if "attendance_images" not in st.session_state:
        st.session_state.attendance_images = []
    st.write("Add classroom photos to scan for attendance.")

    if "photo_tab" not in st.session_state:
        st.session_state.photo_tab = "camera"

    t1, t2 = st.columns(2)

    with t1:
        type_camera = "primary" if st.session_state.photo_tab == "camera" else "tertiary"
        if st.button("Camera", type=type_camera, width="stretch"):
            st.session_state.photo_tab = "camera"
            st.rerun()

    with t2:
        type_upload = "primary" if st.session_state.photo_tab == "upload" else "tertiary"
        if st.button("Upload Photos", type=type_upload, width="stretch"):
            st.session_state.photo_tab = "upload"
            st.rerun()

    # ---------------- CAMERA ----------------
    if st.session_state.photo_tab == "camera":
        cam_photo = st.camera_input("Take Snapshot", key="dialog_cam")

        # FIX: Only add photo when explicit button is clicked
        # This prevents infinite loop from camera_input persisting across reruns
        if cam_photo:
            st.image(cam_photo, caption="Preview")
            if st.button("📷 Add This Photo", key="add_cam_btn", type="primary", width="stretch"):
                st.session_state.attendance_images.append(Image.open(cam_photo))
                st.toast("Photo Captured Successfully!")
                st.rerun()

    # ---------------- UPLOAD ----------------
    elif st.session_state.photo_tab == "upload":
        uploaded_files = st.file_uploader(
            "Choose image files",
            type=["jpg", "jpeg", "png"],
            accept_multiple_files=True,
            key="dialog_upload",
        )

        if uploaded_files:
            st.write(f"{len(uploaded_files)} file(s) selected")
            
            # FIX: Only process files when explicit button is clicked
            if st.button(f"⬆️ Add {len(uploaded_files)} Photo(s)", key="add_upload_btn", type="primary", width="stretch"):
                valid_files = []
                for f in uploaded_files:
                    file_size_mb = len(f.getvalue()) / (1024 * 1024)
                    if file_size_mb > MAX_FILE_SIZE_MB:
                        st.warning(f"❌ {f.name} exceeds {MAX_FILE_SIZE_MB}MB limit. Skipped.")
                        continue

                    try:
                        img = Image.open(f)
                        img.verify()
                        f.seek(0)
                        img = Image.open(f)

                        if img.width > MAX_IMAGE_DIMENSION or img.height > MAX_IMAGE_DIMENSION:
                            st.warning(f"❌ {f.name} too large ({img.width}x{img.height}). Max: {MAX_IMAGE_DIMENSION}px.")
                            continue

                        valid_files.append(img)
                    except Exception:
                        st.warning(f"❌ {f.name} is not a valid image. Skipped.")
                        continue

                for img in valid_files:
                    st.session_state.attendance_images.append(img)

                if valid_files:
                    st.toast(f"✅ {len(valid_files)} photo(s) uploaded successfully!")
                st.rerun()

    st.divider()
    if st.button('Done', type='primary', width='stretch'):
        st.rerun()