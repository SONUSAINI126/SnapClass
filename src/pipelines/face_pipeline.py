import dlib
import numpy as np
from sklearn.svm import SVC
import streamlit as st
from src.database.db import get_all_students
from PIL import Image
 
RESEMBLANCE_THRESHOLD = 0.6
AMBIGUITY_MARGIN = 0.15  # min gap between top-2 SVM probabilities to trust the pick
 
def _normalize_embedding(emb):
    """Handle dict/list/numpy array embeddings uniformly."""
    if isinstance(emb, dict):
        for key in ('embedding', 'encoding', 'face_encoding', 'vector'):
            if emb.get(key) is not None:
                emb = emb[key]
                break
        else:
            emb = list(emb.values())[0]
    return np.array(emb, dtype=np.float64)


def _validate_image(image_np):
    """Ensure dlib receives uint8 RGB/HW3 array."""
    if not isinstance(image_np, np.ndarray):
        raise TypeError("Image must be a numpy array")
    # Grayscale → RGB
    if image_np.ndim == 2:
        image_np = np.stack([image_np] * 3, axis=-1)
    # RGBA → RGB
    if image_np.ndim == 3 and image_np.shape[2] == 4:
        image_np = image_np[:, :, :3]
    # Float → uint8
    if image_np.dtype != np.uint8:
        if image_np.max() <= 1.0:
            image_np = (image_np * 255).astype(np.uint8)
        else:
            image_np = image_np.astype(np.uint8)
    # Resize if absurdly large (saves RAM / dlib crash)
    MAX_DIM = 2560
    h, w = image_np.shape[:2]
    if max(h, w) > MAX_DIM:
        scale = MAX_DIM / max(h, w)
        new_w, new_h = int(w * scale), int(h * scale)
        image_np = np.array(Image.fromarray(image_np).resize((new_w, new_h)))
    return image_np

@st.cache_resource
def load_dlib_models():
    """Load dlib models once per process. Unlike get_trained_model, this IS
    safe to cache — these models never change, only loading them is expensive."""
    import face_recognition_models  # lazy import: a failure here only breaks
                                     # face features when first used, not the
                                     # whole app at startup
    detector = dlib.get_frontal_face_detector()
    sp = dlib.shape_predictor(
        face_recognition_models.pose_predictor_model_location()
    )
    facerec = dlib.face_recognition_model_v1(
        face_recognition_models.face_recognition_model_location()
    )
    return detector, sp, facerec
 
 
def get_face_embeddings(image_np):
    image_np = _validate_image(image_np)
    detector, sp, facerec = load_dlib_models()
    faces = detector(image_np, 1)
    encodings = []
    for face in faces:
        shape = sp(image_np, face)
        face_descriptor = facerec.compute_face_descriptor(image_np, shape, 1)
        encodings.append(np.array(face_descriptor, dtype=np.float64))
    return encodings
 
 
def get_trained_model(student_db=None):
    """NOT cached — student list changes. But now accepts external data."""
    X = []
    y = []
    if student_db is None:
        student_db = get_all_students()
    if not student_db:
        return None

    for student in student_db:
        embedding = student.get('face_embedding')
        if embedding:
            X.append(_normalize_embedding(embedding))
            y.append(student.get('student_id'))   # Keep original type (int/str)

    if len(X) == 0:
        return None

    clf = None
    if len(set(y)) >= 2:
        try:
            clf = SVC(kernel='linear', probability=True, class_weight='balanced')
            clf.fit(X, y)
        except ValueError:
            clf = None

    return {'clf': clf, 'X': X, 'y': y}
 
 
def train_classifier():
    """Kept for backward compatibility with any existing caller. Nothing
    needs pre-training/caching anymore — get_trained_model() always
    rebuilds fresh and cheaply, so there's nothing to invalidate."""
    model_data = get_trained_model()
    return bool(model_data)
 
 
def predict_attendance(class_image_np, student_db=None):
    encodings = get_face_embeddings(class_image_np)
    detected_student = {}

    model_data = get_trained_model(student_db)
    if not model_data:
        return detected_student, [], len(encodings)

    clf = model_data['clf']
    X_train = model_data['X']
    y_train = model_data['y']
    all_students = sorted(set(y_train), key=lambda x: str(x))

    for encoding in encodings:
        predicted_id = None
        best_distance = float('inf')

        # ── SVM path ──
        if clf is not None:
            try:
                probs = clf.predict_proba([encoding])[0]
                order = np.argsort(probs)[::-1]
                best_prob = probs[order[0]]

                # Ambiguity check
                margin_ok = True
                if len(order) > 1:
                    margin_ok = (best_prob - probs[order[1]]) >= AMBIGUITY_MARGIN

                if margin_ok:
                    predicted_id = clf.classes_[order[0]]
            except Exception:
                predicted_id = None

        # ── Fallback / Verification ──
        if predicted_id is None:
            # Nearest neighbor across ALL students (fixes the single-student bug)
            for emb_raw, sid in zip(X_train, y_train):
                emb_existing = _normalize_embedding(emb_raw)
                dist = np.linalg.norm(emb_existing - encoding)
                if dist < best_distance:
                    best_distance = dist
                    predicted_id = sid

            if best_distance <= RESEMBLANCE_THRESHOLD:
                detected_student[predicted_id] = True
        else:
            # Verify SVM pick with actual embedding distance
            matches = [(i, sid) for i, sid in enumerate(y_train) if sid == predicted_id]
            if matches:
                idx, _ = matches[0]
                student_embedding = _normalize_embedding(X_train[idx])
                best_match_score = np.linalg.norm(student_embedding - encoding)
                if best_match_score <= RESEMBLANCE_THRESHOLD:
                    detected_student[predicted_id] = True

    return detected_student, all_students, len(encodings)