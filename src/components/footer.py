import streamlit as st


def footer_home():
    """Footer for home screen (dark blue background)"""
    st.markdown(
        """
        <div style="
            text-align: center;
            margin-top: 40px;
            padding: 20px 0;
            color: rgba(255,255,255,0.85);
            font-size: 13px;
            font-weight: 500;
            letter-spacing: 0.5px;
            font-family: 'Outfit', sans-serif;
        ">
            <div style="
                display: inline-flex;
                align-items: center;
                gap: 8px;
                background: rgba(255,255,255,0.1);
                padding: 8px 20px;
                border-radius: 50px;
                backdrop-filter: blur(10px);
            ">
                <span>Made with</span>
                <span style="color: #EC4899; font-size: 16px;">❤️ by</span>
                <a href="https://www.linkedin.com/in/sonu-saini-here/" style="text-decoration: none;">
                <span style="
                    font-weight: 700;
                    background: linear-gradient(90deg, #FFD700 0%, #FBBF24 35%, #F59E0B 70%, #FDE68A 100%);
                    -webkit-background-clip: text;
                    -webkit-text-fill-color: transparent;
                    background-clip: text;
                    letter-spacing: 0.4px;
                    text-shadow: 0 0 12px rgba(251,191,36,0.25);
                ">
                    Sonu Saini
                </span>
                </a>
            </div>
            <div style="margin-top: 8px; opacity: 0.6; font-size: 11px;">
                SnapClass v1.0
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def footer_dashboard():
    """Footer for dashboard screens (light background)"""
    st.markdown(
        """
        <div style="
            text-align: center;
            margin-top: 50px;
            padding: 24px 0 16px 0;
            color: #64748B;
            font-size: 13px;
            font-weight: 500;
            letter-spacing: 0.5px;
            font-family: 'Outfit', sans-serif;
            border-top: 1px solid #E2E8F0;
        ">
            <div style="
                display: inline-flex;
                align-items: center;
                gap: 8px;
                background: #F1F5F9;
                padding: 8px 20px;
                border-radius: 50px;
            ">
                <span>Made with</span>
                <span style="color: #EC4899; font-size: 16px;">❤️ by</span>
                <a href="https://www.linkedin.com/in/sonu-saini-here/" style="text-decoration: none;">
                <span style="
                    font-weight: 700;
                    background: linear-gradient(90deg, #FFD700 0%, #FBBF24 35%, #F59E0B 70%, #FDE68A 100%);
                    -webkit-background-clip: text;
                    -webkit-text-fill-color: transparent;
                    background-clip: text;
                    letter-spacing: 0.4px;
                    text-shadow: 0 0 12px rgba(251,191,36,0.25);
                ">
                    Sonu Saini
                </span>
                </a>
            </div>
            <div style="margin-top: 8px; opacity: 0.6; font-size: 11px;">
                SnapClass v1.0
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )