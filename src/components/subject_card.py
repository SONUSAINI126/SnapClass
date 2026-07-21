import streamlit as st

def subject_card(name, code, course, section, stats=None, footer_callback=None):
    html = '<div style="background:white; border-left: 5px solid #4F46E5; padding: 24px; border-radius: 16px; border-top: 1px solid #F1F5F9; border-right: 1px solid #F1F5F9; border-bottom: 1px solid #F1F5F9; margin-bottom: 20px; box-shadow: 0 2px 12px rgba(0, 0, 0, 0.04); font-family: Outfit, sans-serif;">'
    
    html += f'<h3 style="margin: 0 0 8px 0; color: #0F172A; font-size: 1.3rem; font-weight: 700; letter-spacing: -0.3px;">{name}</h3>'
    
    html += '<p style="color: #64748B; margin: 0 0 16px 0; font-size: 0.9rem; font-weight: 500;">'
    html += f'Code: <span style="background: #EEF2FF; color: #4F46E5; padding: 3px 10px; border-radius: 6px; font-size: 0.8rem; font-weight: 600; font-family: monospace;">{code}</span>'
    html += '<span style="margin: 0 8px; color: #CBD5E1;">|</span>'
    html += f'<span style="background: #F0FDF4; color: #166534; padding: 3px 10px; border-radius: 6px; font-size: 0.8rem; font-weight: 600;">{course}</span>'
    html += '<span style="margin: 0 8px; color: #CBD5E1;">|</span>'
    html += f'Section: <span style="font-weight: 600; color: #334155;">{section}</span>'
    html += '</p>'
    
    if stats:
        html += '<div style="display: flex; gap: 10px; flex-wrap: wrap; margin-bottom: 8px;">'
        for icon, label, value in stats:
            html += '<div style="background: #F8FAFC; padding: 6px 14px; border-radius: 10px; font-size: 0.85rem; color: #475569; font-weight: 500; border: 1px solid #E2E8F0; display: flex; align-items: center; gap: 6px;">'
            html += f'<span style="font-size: 1rem;">{icon}</span>'
            html += f'<span><b style="color: #0F172A;">{value}</b> {label}</span>'
            html += '</div>'
        html += '</div>'
    
    html += '</div>'
    
    st.markdown(html, unsafe_allow_html=True)

    if footer_callback:
        footer_callback()