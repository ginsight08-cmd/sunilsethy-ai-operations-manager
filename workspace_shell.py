"""Shared, accessible product identity and navigation for authenticated pages."""
from datetime import datetime
from html import escape
import streamlit as st


def render_header(product_name, logo_html=''):
    st.markdown(f'''<header class="gi-product-header">
<a class="gi-product-brand" href="https://www.generativeinsight.in/" target="_blank" rel="noopener noreferrer" aria-label="Generative Insight website">{logo_html}<span>Generative <strong>Insight</strong><small>{escape(product_name)}</small></span></a>
<nav aria-label="Workspace shortcuts"><a href="#workspace-settings">Workspace settings</a><a href="https://www.generativeinsight.in/" target="_blank" rel="noopener noreferrer">Explore products ↗</a></nav>
</header>''', unsafe_allow_html=True)


def render_footer():
    st.markdown(f'''<footer class="gi-product-footer">
<div class="gi-footer-grid"><div><strong class="gi-footer-brand">Generative Insight</strong><p>Clarity for your next decision.</p><small>Review your data, understand performance and turn findings into practical action.</small></div>
<nav aria-label="Product links"><strong>Our workspaces</strong><a href="https://generative-insight-bpo.streamlit.app/" target="_blank" rel="noopener noreferrer">IT Operations Manager ↗</a><a href="https://generative-insight-procurement.streamlit.app/" target="_blank" rel="noopener noreferrer">AI Procurement ↗</a><a href="https://generative-insight-vakil.streamlit.app/" target="_blank" rel="noopener noreferrer">AI Vakil ↗</a></nav>
<div><strong>Make your next step count</strong><p>Manage your account, choose a workspace and adjust targets from Workspace settings.</p><a class="gi-footer-cta" href="#workspace-settings">Open workspace settings ↑</a></div></div>
<div class="gi-footer-bottom"><span>© {datetime.now().year} Generative Insight</span><span>Separate product accounts · Review AI-assisted recommendations before acting</span><a href="https://www.generativeinsight.in/" target="_blank" rel="noopener noreferrer">Visit our website ↗</a></div>
</footer>''',unsafe_allow_html=True)
