import dlib
import numpy as np
import cv2
import streamlit as st
from src.database.db import get_all_students
import os

RESEMBLANCE_THRESHOLD = 0.6

# ========== LOAD DLIB MODELS ==========
@st.cache_resource
def load_face_models():
    """Load dlib face detection and recognition models."""
    # Models face_recognition_models se aayenge
    try:
        import face_recognition_models
        MODELS_AVAILABLE = True
    except ImportError:
        MODELS_AVAILABLE = False
        st.error("Face recognition models not available")

    face_rec_model_path = face_recognition_models.face_recognition_model_location()
    predictor_path = face_recognition_models.pose_predictor_model_location()

    detector = dlib.get_frontal_face_detector()
    predictor = dlib.shape_predictor(predictor_path)
    face_rec = dlib.face_recognition_model_v1(face_rec_model_path)

    return detector, predictor, face_rec

detector, predictor, face_rec = load_face_models()


def check_image_quality(image_np):
    """Check image brightness and blur - RELAXED thresholds."""
    gray = cv2.cvtColor(image_np, cv2.COLOR_RGB2GRAY)
    brightness = np.mean(gray)

    if brightness < 15:
        return False, "Image too dark"

    laplacian_var = cv2.Laplacian(gray, cv2.CV_64F).var()
    if laplacian_var < 30:
        return False, "Image too blurry"

    return True, "OK"


def get_face_embeddings(image_np):
    """Get face embeddings from image using dlib directly."""
    quality_ok, msg = check_image_quality(image_np)
    if not quality_ok:
        st.warning(f"⚠️ {msg} — trying anyway...")

    # dlib uses BGR, convert RGB to BGR
    img_bgr = cv2.cvtColor(image_np, cv2.COLOR_RGB2BGR)

    # Detect faces
    faces = detector(img_bgr, 1)

    if len(faces) == 0:
        return []

    embeddings = []
    for face in faces:
        face_width = face.width()
        face_height = face.height()

        # Relaxed minimum size
        if face_width < 30 or face_height < 30:
            continue

        # Get landmarks
        shape = predictor(img_bgr, face)

        # Get face encoding (128-d vector)
        encoding = np.array(face_rec.compute_face_descriptor(img_bgr, shape))

        embeddings.append({
            'embedding': encoding,
            'bbox': (face.top(), face.right(), face.bottom(), face.left()),
            'size': (face_width, face_height)
        })

    return embeddings


def predict_attendance(image_np):
    """Predict which students are in the photo."""
    embeddings = get_face_embeddings(image_np)

    num_faces = len(embeddings)
    if num_faces == 0:
        return {}, [], 0

    all_students = get_all_students()
    if not all_students:
        return {}, [], num_faces

    # Build known embeddings
    known_embeddings = []
    known_ids = []

    for student in all_students:
        emb = student.get('face_embedding')
        if emb:
            known_embeddings.append(np.array(emb))
            known_ids.append(student['student_id'])

    if len(known_ids) == 0:
        st.warning("No students have registered their face yet.")
        return {}, [], num_faces

    if len(known_ids) == 1:
        detected = {}
        all_ids = []

        for face_data in embeddings:
            encoding = face_data['embedding']
            dist = np.linalg.norm(known_embeddings[0] - encoding)

            if dist < RESEMBLANCE_THRESHOLD:
                student_id = known_ids[0]
                detected[student_id] = {
                    'confidence': float(1.0 - dist),
                    'distance': float(dist)
                }
                all_ids.append(student_id)

        return detected, all_ids, num_faces

    # 2+ students — use SVM
    from sklearn.svm import SVC
    clf = SVC(probability=True)
    clf.fit(known_embeddings, known_ids)

    detected = {}
    all_ids = []

    for face_data in embeddings:
        encoding = face_data['embedding']
        predicted_id = int(clf.predict([encoding])[0])

        probs = clf.predict_proba([encoding])[0]
        max_prob = np.max(probs)

        if max_prob < 0.60:
            continue

        student_idx = known_ids.index(predicted_id)
        dist = np.linalg.norm(known_embeddings[student_idx] - encoding)

        if dist < RESEMBLANCE_THRESHOLD:
            detected[predicted_id] = {
                'confidence': float(max_prob),
                'distance': float(dist)
            }
            all_ids.append(predicted_id)

    return detected, all_ids, num_faces


def get_trained_model():
    """Return known face embeddings for duplicate detection during registration."""
    all_students = get_all_students()
    if not all_students:
        return None

    known_embeddings = []
    known_ids = []

    for student in all_students:
        emb = student.get('face_embedding')
        if emb:
            known_embeddings.append(np.array(emb))
            known_ids.append(student['student_id'])

    if len(known_ids) == 0:
        return None

    return {'X': known_embeddings, 'y': known_ids}