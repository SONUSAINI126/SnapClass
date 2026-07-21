from resemblyzer import VoiceEncoder, preprocess_wav
import numpy as np
import streamlit as st
import io
import librosa
from sklearn.metrics.pairwise import cosine_similarity


@st.cache_resource
def load_voice_encoder():
    return VoiceEncoder()   


def get_voice_embedding(audio_bytes):
    try:
        encoder = load_voice_encoder()
        audio, sr = librosa.load(io.BytesIO(audio_bytes), sr=16000)
        wav = preprocess_wav(audio)
        embedding = encoder.embed_utterance(wav)
        return embedding.tolist()
    except Exception as e:
        st.error(f"Error processing audio: {e}")
        return None


def identify_speaker(new_embedding, candidates_dict, threshold=0.65):
    if new_embedding is None or not candidates_dict:
        return None, 0.0

    valid_candidates = {k: v for k, v in candidates_dict.items() if v is not None}
    if not valid_candidates:
        return None, 0.0

    new_emb = np.array(new_embedding).reshape(1, -1)
    best_sid = None
    best_score = -1.0

    for sid, stored_embedding in valid_candidates.items():
        stored_emb = np.array(stored_embedding).reshape(1, -1)
        similarity = cosine_similarity(new_emb, stored_emb)[0][0]

        if similarity > best_score:
            best_score = similarity
            best_sid = sid

    if best_score >= threshold:
        return best_sid, best_score

    return None, best_score


def process_bulk_audio(audio_bytes, candidates_dict, threshold=0.65):
    try:
        encoder = load_voice_encoder()
        audio, sr = librosa.load(io.BytesIO(audio_bytes), sr=16000)
        segments = librosa.effects.split(audio, top_db=30)

        identified_results = {}

        for start, end in segments:
            if (end - start) < sr * 0.5:      
                continue
            segment_audio = audio[start:end]
            wav = preprocess_wav(segment_audio)
            embedding = encoder.embed_utterance(wav)

            sid, score = identify_speaker(embedding, candidates_dict, threshold)
            if sid:
                if sid not in identified_results or score > identified_results[sid]:
                    identified_results[sid] = score

        return identified_results
    except Exception as e:
        st.error(f"Error processing bulk audio: {e}")
        return {}
