import streamlit as st

def style_background_home():
    st.markdown("""
        <style>
            .stApp {
               background: #5865F2 !important;
            }

            .stApp div[data-testid="stColumn"] {
            background-color: #E0E3FF !important;   /* removes blue bg */
            padding: 2.0rem !important;        
            color:white;         /* reduced padding */
            border-radius: 2.5rem !important;             /* smaller radius */
            box-shadow: none !important;                /* optional: remove shadow too, or keep it */
            max-width: fit-content !important;          /* shrink to fit content */
            margin:0 auto !important;                  /* center the columns */
    }
            
        </style>
    """, unsafe_allow_html=True)


def style_background_dashboard():
    st.markdown("""
        <style>
            .stApp {
                background: #E0E3FF !important;
            }

            .css-18e3th9 {
                background: transparent !important;
            }
        </style>
    """, unsafe_allow_html=True)


def style_base_layout():
    st.markdown("""
        <style>
            @import url('https://fonts.googleapis.com/css2?family=Climate+Crisis&family=Outfit:wght@100..900&display=swap');

            /* Hide Streamlit's default menu, footer, and header */

            MainMenu, footer, header {
                 visibility: hidden;
            }

            /* Adjust the padding and max-width of the main content container */

            .block-container {
                padding-top: 1.5rem !important;
                padding-left: 1.5rem !important;
                padding-right: 1.5rem !important;
                max-width: 900px !important;
            }

            h1, h2, h3, h4, p {
                font-family: 'Outfit', sans-serif !important;
            }

            h1, h2 {
                font-family: 'Climate Crisis', sans-serif !important;
            }

            h1 {
                font-size: 3.5rem !important;
                line-height: 1.05 !important;
                margin-bottom: 0.70rem !important;
                background: transparent !important; 
                
}

            h2 {
                color: black !important;
                font-size: 2rem !important;
                line-height: 1.05 !important;
                margin-bottom: 0.5rem !important;
                background: none !important;
            }

            button, [role="button"] {
                border-radius: 1.5rem !important;
                background-color: #5865F2 !important;
                color: #ffffff !important;
                padding: 0.75rem 1.25rem !important;
                border: none !important;
                transition: transform 0.25s ease-in-out, box-shadow 0.25s ease-in-out !important;
            }

            button[kind="secondary"] {
                background-color: #EB459E !important;
            }

            button[kind="tertiary"]{
                border-radius: 1.5rem !important;
                background-color: black !important;
                color: white !important;
                padding: 10px 20px !important;
                border: none !important;
                transition: transform 0.25s ease-in-out, box-shadow 0.25s ease-in-out !important;
                }
            
            
            }
            button:hover, [role="button"]:hover {
                transform: scale(1.02);
                box-shadow: 0 12px 24px rgba(0, 0, 0, 0.12) !important;
            }

            .dashboard-shell {
                padding: 2rem;
                max-width: 900px !important;
                margin: 2rem auto;
                background: rgba(255, 255, 255, 0.92) !important;
                border-radius: 2rem !important;
                box-shadow: 0 24px 60px rgba(0, 0, 0, 0.08) !important;
            }
        </style>
    """, unsafe_allow_html=True)



def style_dashboard_shell():
    return
