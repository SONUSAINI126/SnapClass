import streamlit as st
from supabase import create_client, Client

_supabase_client = None

def get_supabase_client() -> Client:
    """Lazy initialization of Supabase client with validation."""
    global _supabase_client

    if _supabase_client is not None:
        return _supabase_client

    required_secrets = ["SUPABASE_URL", "SUPABASE_KEY"]
    missing = [s for s in required_secrets if s not in st.secrets]

    if missing:
        raise RuntimeError(
            f"Missing required secrets: {', '.join(missing)}. "
            f"Please configure them in .streamlit/secrets.toml"
        )

    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]

    if not url.startswith("https://"):
        raise ValueError("SUPABASE_URL must start with https://")

    _supabase_client = create_client(url, key)
    return _supabase_client


# Backward compatibility
supabase = get_supabase_client()
