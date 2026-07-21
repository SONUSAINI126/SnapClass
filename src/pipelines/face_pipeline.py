import face_recognition
import numpy as np
import cv2
import streamlit as st
from src.database.db import get_all_students

RESEMBLANCE_THRESHOLD = 0.6

def check_image_quality(image_np):
    """Check image brightness and blur - RELAXED thresholds."""
    gray = cv2.cvtColor(image_np, cv2.COLOR_RGB2GRAY)
    brightness = np.mean(gray)
    
    if brightness < 15:  # Very dark only
        return False, "Image too dark"
    
    laplacian_var = cv2.Laplacian(gray, cv2.CV_64F).var()
    if laplacian_var < 30:  # Very blurry only
        return False, "Image too blurry"
    
    return True, "OK"

def get_face_embeddings(image_np):
    """Get face embeddings from image."""
    # Quality check (relaxed)
    quality_ok, msg = check_image_quality(image_np)
    if not quality_ok:
        st.warning(f"⚠️ {msg} — trying anyway...")
        # Don't return empty, try detection anyway
    
    # Detect faces
    face_locations = face_recognition.face_locations(image_np)
    
    if len(face_locations) == 0:
        return []  # No face found
    
    embeddings = []
    for (top, right, bottom, left) in face_locations:
        face_width = right - left
        face_height = bottom - top
        
        # Relaxed minimum size
        if face_width < 30 or face_height < 30:
            continue
            
        face_image = image_np[top:bottom, left:right]
        encodings = face_recognition.face_encodings(image_np, [(top, right, bottom, left)])
        
        if encodings:
            embeddings.append({
                'embedding': encodings[0],
                'bbox': (top, right, bottom, left),
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
    
    # 🔥 FIX: Check minimum students
    if len(known_ids) == 0:
        st.warning("No students have registered their face yet.")
        return {}, [], num_faces
    
    if len(known_ids) == 1:
        # Only 1 student registered — use simple distance check instead of SVM
        detected = {}
        all_ids = []
        
        for face_data in embeddings:
            encoding = face_data['embedding']
            
            # Compare with the only known student
            dist = np.linalg.norm(known_embeddings[0] - encoding)
            
            if dist < RESEMBLANCE_THRESHOLD:
                student_id = known_ids[0]
                detected[student_id] = {
                    'confidence': float(1.0 - dist),  # Approximate confidence
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
        
        # Confidence check
        probs = clf.predict_proba([encoding])[0]
        max_prob = np.max(probs)
        
        if max_prob < 0.60:
            continue
            
        # Distance check
        student_idx = known_ids.index(predicted_id)
        dist = np.linalg.norm(known_embeddings[student_idx] - encoding)
        
        if dist < RESEMBLANCE_THRESHOLD:
            detected[predicted_id] = {
                'confidence': float(max_prob),
                'distance': float(dist)
            }
            all_ids.append(predicted_id)
    
    return detected, all_ids, num_faces