import dlib
import numpy as np
from sklearn.svm import SVC
import streamlit as st
from src.database.db import get_all_students
from PIL import Image

# ── Tunable thresholds ───────────────────────────────────────────────
# dlib face descriptors: same-person distance is usually < 0.5,
# different-person distance is usually > 0.6. 0.6 is the "loose" cutoff
# used for grouping/attendance. For LOGIN (1:1 auth) we want a much
# stricter cutoff so strangers / lookalikes never get let in.
ATTENDANCE_THRESHOLD = 0.55   # used for classify-against-everyone (roll call)
LOGIN_THRESHOLD = 0.45        # used for verify-against-one (login) - strict
AMBIGUITY_MARGIN = 0.15       # min gap between top-2 SVM probabilities to trust the pick


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
    if image_np.ndim == 2:
        image_np = np.stack([image_np] * 3, axis=-1)
    if image_np.ndim == 3 and image_np.shape[2] == 4:
        image_np = image_np[:, :, :3]
    if image_np.dtype != np.uint8:
        if image_np.max() <= 1.0:
            image_np = (image_np * 255).astype(np.uint8)
        else:
            image_np = image_np.astype(np.uint8)
    MAX_DIM = 2560
    h, w = image_np.shape[:2]
    if max(h, w) > MAX_DIM:
        scale = MAX_DIM / max(h, w)
        new_w, new_h = int(w * scale), int(h * scale)
        image_np = np.array(Image.fromarray(image_np).resize((new_w, new_h)))
    return image_np


@st.cache_resource
def load_dlib_models():
    import face_recognition_models
    detector = dlib.get_frontal_face_detector()
    sp = dlib.shape_predictor(
        face_recognition_models.pose_predictor_model_location()
    )
    facerec = dlib.face_recognition_model_v1(
        face_recognition_models.face_recognition_model_location()
    )
    return detector, sp, facerec


def get_face_embeddings(image_np):
    """Returns list of (embedding, face_rect) for every face found in the image."""
    image_np = _validate_image(image_np)
    detector, sp, facerec = load_dlib_models()
    faces = detector(image_np, 1)
    results = []
    for face in faces:
        shape = sp(image_np, face)
        face_descriptor = facerec.compute_face_descriptor(image_np, shape, 1)
        results.append((np.array(face_descriptor, dtype=np.float64), face))
    return results


# ══════════════════════════════════════════════════════════════════
#  1:1 VERIFICATION — use this for LOGIN. Never use identification
#  (predict_attendance) for login. This function only ever compares
#  the captured face against the ONE claimed identity's stored
#  photos, and enforces a hard distance threshold. No match = no
#  login, full stop. It never "falls back" to guessing someone else.
# ══════════════════════════════════════════════════════════════════
def verify_login(captured_image_np, claimed_student_id, student_db=None):
    """
    Args:
        captured_image_np: webcam frame as numpy array
        claimed_student_id: the ID/username the person is claiming to be
            (from the login form, NOT inferred from the face)
        student_db: optional pre-fetched list of student records

    Returns:
        dict with keys:
            status: "match" | "no_match" | "no_face" | "multiple_faces" | "not_registered"
            distance: float or None
    """
    faces = get_face_embeddings(captured_image_np)

    if len(faces) == 0:
        return {"status": "no_face", "distance": None}
    if len(faces) > 1:
        # Reject ambiguous frames outright for a login/auth context
        return {"status": "multiple_faces", "distance": None}

    captured_embedding = faces[0][0]

    if student_db is None:
        student_db = get_all_students()

    stored_embeddings = []
    for student in student_db:
        if str(student.get('student_id')) == str(claimed_student_id):
            emb = student.get('face_embedding')
            if emb:
                stored_embeddings.append(_normalize_embedding(emb))

    if not stored_embeddings:
        # This person has no enrolled face data at all — they are not
        # registered for face login. Do NOT compare them against anyone
        # else's embeddings.
        return {"status": "not_registered", "distance": None}

    best_distance = min(
        np.linalg.norm(stored - captured_embedding) for stored in stored_embeddings
    )

    if best_distance <= LOGIN_THRESHOLD:
        return {"status": "match", "distance": best_distance}
    else:
        return {"status": "no_match", "distance": best_distance}


# ══════════════════════════════════════════════════════════════════
#  1:N IDENTIFICATION — use this ONLY for attendance / roll-call style
#  "who is in this photo", where you WANT to find the closest known
#  face. Even here, unknown faces must be rejected via threshold,
#  not silently assigned to the nearest student.
# ══════════════════════════════════════════════════════════════════
def get_trained_model(student_db=None):
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
            y.append(student.get('student_id'))

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
    model_data = get_trained_model()
    return bool(model_data)


def predict_attendance(class_image_np, student_db=None):
    """
    Identify all recognizable students in a group photo.
    Returns (detected_student_ids: set, all_enrolled_ids: list, num_faces_found: int)

    IMPORTANT: any face whose best match distance exceeds ATTENDANCE_THRESHOLD
    is treated as "unknown" and is NOT added to detected_student_ids, no
    matter how much closer it is than every other student. There is no
    silent nearest-neighbor fallback anymore.
    """
    faces = get_face_embeddings(class_image_np)
    encodings = [f[0] for f in faces]
    detected_student = set()

    model_data = get_trained_model(student_db)
    if not model_data:
        return detected_student, [], len(encodings)

    clf = model_data['clf']
    X_train = model_data['X']
    y_train = model_data['y']
    all_students = sorted(set(y_train), key=lambda x: str(x))

    # Precompute normalized embeddings once (not per-encoding, per-student)
    X_train_norm = [_normalize_embedding(e) if not isinstance(e, np.ndarray) else e
                     for e in X_train]

    for encoding in encodings:
        candidate_id = None
        candidate_distance = float('inf')

        if clf is not None:
            try:
                probs = clf.predict_proba([encoding])[0]
                order = np.argsort(probs)[::-1]
                best_prob = probs[order[0]]
                margin_ok = True
                if len(order) > 1:
                    margin_ok = (best_prob - probs[order[1]]) >= AMBIGUITY_MARGIN
                if margin_ok:
                    candidate_id = clf.classes_[order[0]]
            except Exception:
                candidate_id = None

        if candidate_id is not None:
            # verify SVM's pick against distance to ALL of that student's
            # stored embeddings (not just the first one found)
            dists = [
                np.linalg.norm(emb - encoding)
                for emb, sid in zip(X_train_norm, y_train)
                if sid == candidate_id
            ]
            if dists:
                candidate_distance = min(dists)
        else:
            # no confident SVM pick (or only one student enrolled) ->
            # nearest neighbor across everyone, but STILL threshold-gated
            for emb, sid in zip(X_train_norm, y_train):
                dist = np.linalg.norm(emb - encoding)
                if dist < candidate_distance:
                    candidate_distance = dist
                    candidate_id = sid

        # ── the actual fix: hard reject if nobody is close enough ──
        if candidate_id is not None and candidate_distance <= ATTENDANCE_THRESHOLD:
            detected_student.add(candidate_id)
        # else: unknown face in the photo, correctly ignored

    return detected_student, all_students, len(encodings)