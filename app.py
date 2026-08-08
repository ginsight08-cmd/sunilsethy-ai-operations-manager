import io
import json
import hashlib
import smtplib
from datetime import datetime
from email.message import EmailMessage

import pandas as pd
import requests
import streamlit as st

# Hide developer options in the Streamlit interface
st.set_option("client.toolbarMode", "viewer")

from supabase import create_client, Client
from engine import analyze_data, make_ai_prompt
