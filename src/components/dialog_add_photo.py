import streamlit as st
from PIL import Image

import hashlib

MAX_FILE_SIZE_MB = 10
MAX_IMAGE_DIMENSION = 4096


def _hash_bytes(data):
    """Create a hash of file bytes for duplicate detection."""
    return hashlib.md5(data).hexdigest()


@st.dialog("Capture or Upload Photos")
def add_photos_dialog():
    if "attendance_images" not in st.session_state:
        st.session_state.attendance_images = []
    if "_last_cam_hash" not in st.session_state:
        st.session_state._last_cam_hash = None
    if "_last_upload_hashes" not in st.session_state:
        st.session_state._last_upload_hashes = None

    st.write("Add classroom photos to scan for attendance.")

    if "photo_tab" not in st.session_state:
        st.session_state.photo_tab = "camera"

    t1, t2 = st.columns(2)

    with t1:
        type_camera = "primary" if st.session_state.photo_tab == "camera" else "tertiary"
        if st.button("Camera", type=type_camera, use_container_width=True):
            st.session_state.photo_tab = "camera"
            st.rerun()

    with t2:
        type_upload = "primary" if st.session_state.photo_tab == "upload" else "tertiary"
        if st.button("Upload Photos", type=type_upload, use_container_width=True):
            st.session_state.photo_tab = "upload"
            st.rerun()

    # ---------------- CAMERA ----------------
    if st.session_state.photo_tab == "camera":
        cam_photo = st.camera_input("Take Snapshot", key="dialog_cam")

        if cam_photo:
            # Hash the photo to detect if it's already been added
            cam_bytes = cam_photo.getvalue()
            cam_hash = _hash_bytes(cam_bytes)

            if cam_hash != st.session_state._last_cam_hash:
                st.session_state.attendance_images.append(Image.open(cam_photo))
                st.session_state._last_cam_hash = cam_hash
                st.toast("📷 Photo added!")
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
            # Create a combined hash of all selected files
            combined_hash = "|".join(_hash_bytes(f.getvalue()) for f in uploaded_files)

            if combined_hash != st.session_state._last_upload_hashes:
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

                st.session_state._last_upload_hashes = combined_hash
                if valid_files:
                    st.toast(f"✅ {len(valid_files)} photo(s) added!")
                st.rerun()

    st.divider()
    if st.button('Done', type='primary', use_container_width=True):
        st.rerun()