import streamlit as st
import segno
import io


@st.dialog("Share Class Link")
def share_subject_dialog(subject_name, subject_code):
    app_domain = st.secrets.get("APP_DOMAIN", "snapclass-main-sonu.streamlit.app")
    join_url = f"{app_domain}/?join-code={subject_code}"

    st.markdown(f"""
        <div style="
            background: linear-gradient(135deg, #4F46E5 0%, #7C3AED 100%);
            border-radius: 12px;
            padding: 16px;
            margin-bottom: 20px;
            color: white;
        ">
            <h3 style="color: white; margin: 0; font-size: 1.1rem;">{subject_name}</h3>
            <p style="color: rgba(255,255,255,0.8); margin: 4px 0 0 0; font-size: 0.85rem;">
                Share this link or QR code with students
            </p>
        </div>
    """, unsafe_allow_html=True)

    qr = segno.make(join_url)
    out = io.BytesIO()
    qr.save(out, kind="png", scale=10, border=2)

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("<h4 style='color: #0F172A; font-size: 1rem; margin-bottom: 12px;'>🔗 Copy Link</h4>", unsafe_allow_html=True)
        
        st.code(join_url, language="text")
        st.code(subject_code, language="text")
        
        st.markdown("""
            <p style="color: #94A3B8; font-size: 0.8rem; margin-top: 8px;">
                💡 Tip: Share via WhatsApp, Email, or LMS
            </p>
        """, unsafe_allow_html=True)

    with col2:
        st.markdown("<h4 style='color: #0F172A; font-size: 1rem; margin-bottom: 12px;'>📱 Scan QR Code</h4>", unsafe_allow_html=True)
        st.image(out.getvalue(), use_container_width=True)
        st.markdown("""
            <p style="color: #94A3B8; font-size: 0.8rem; text-align: center; margin-top: 4px;">
                Students can scan to join instantly
            </p>
        """, unsafe_allow_html=True)