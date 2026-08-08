import io
import json
import smtplib
from datetime import datetime
from email.message import EmailMessage

import pandas as pd
import requests
import streamlit as st
from supabase import create_client, Client

from engine import analyze_data, make_ai_prompt

APP_NAME = "Generative Insight"
APP_VERSION = "1.1.0"

st.set_page_config(
    page_title="Generative Insight | AI Operations Copilot",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---------------- SESSION ----------------
DEFAULTS = {
    "authenticated": False, "user_email": "", "user_id": "",
    "user_name": "", "company_name": "", "user_plan": "Free",
    "file_name": "", "analysis_result": None, "analysis_df": None,
    "n8n_sent": False, "n8n_result": None,
    "copilot_answer": None, "last_question": "",
    "report_pdf": None, "report_generated_at": None,
    "show_plans": False,
}
for k, v in DEFAULTS.items():
    if k not in st.session_state:
        st.session_state[k] = v

# ---------------- BRANDING ----------------
st.markdown("""
<style>
.main-title{font-size:2.2rem;font-weight:800;color:#0b2a5b}
.brand-subtitle{font-size:1rem;color:#475569}
.hero{padding:1.5rem 1.8rem;border-radius:18px;border:1px solid #d8e7f7;
background:linear-gradient(135deg,#eef7ff,#f8fbff 55%,#fffaf5);margin:1rem 0}
.hero h2{color:#062b61;font-size:2rem;margin:0 0 .5rem}
.hero p{color:#334155;line-height:1.65}
.kpi-card{border:1px solid #dbe5f0;border-radius:16px;padding:1rem;
background:#fff;min-height:145px}
.kpi-name{color:#475569;font-size:.92rem}
.kpi-value{color:#062b61;font-size:1.9rem;font-weight:800;margin:.3rem 0 .5rem}
.kpi-good,.kpi-bad{display:inline-block;border-radius:999px;padding:.25rem .55rem;
font-size:.8rem;font-weight:700}
.kpi-good{background:#dcfce7;color:#15803d}
.kpi-bad{background:#fee2e2;color:#b91c1c}
.plan-card{border:1px solid #dbe5f0;border-radius:16px;padding:1rem;min-height:260px}
footer{visibility:hidden} #MainMenu{visibility:hidden}
</style>
""", unsafe_allow_html=True)

def secret(name, default=""):
    try:
        return st.secrets.get(name, default) or default
    except Exception:
        return default

# ---------------- CENTRAL KPI LOGIC ----------------
KPI_RULES = {
    "Productivity": {"higher": True, "unit": "%"},
    "Quality": {"higher": True, "unit": "%"},
    "SLA": {"higher": True, "unit": "%"},
    "AHT": {"higher": False, "unit": ""},
}

def get_kpi_status(name, actual, target):
    if name not in KPI_RULES:
        raise ValueError(f"Unknown KPI: {name}")
    actual, target = float(actual), float(target)
    rule = KPI_RULES[name]
    good = actual >= target if rule["higher"] else actual <= target
    return {
        "name": name, "actual": actual, "target": target,
        "gap": actual - target, "is_good": good,
        "status": "GOOD" if good else "NEEDS ATTENTION",
        "icon": "🟢" if good else "🔴",
    }

def get_kpi_statuses(p, q, s, a, pt, qt, st_, at):
    vals = {
        "Productivity": (p, pt), "Quality": (q, qt),
        "SLA": (s, st_), "AHT": (a, at)
    }
    return {k: get_kpi_status(k, *v) for k, v in vals.items()}

def kpi_value(x):
    return f"{x['actual']:.2f}" if x["name"] == "AHT" else f"{x['actual']:.2f}%"

def kpi_gap(x):
    return f"{x['gap']:+.2f} vs target" if x["name"] == "AHT" else f"{x['gap']:+.2f}% vs target"

def render_kpi(status):
    cls = "kpi-good" if status["is_good"] else "kpi-bad"
    st.markdown(f"""
    <div class="kpi-card">
      <div class="kpi-name">{status["name"]}</div>
      <div class="kpi-value">{kpi_value(status)}</div>
      <span class="{cls}">{status["icon"]} {kpi_gap(status)} · {status["status"]}</span>
    </div>
    """, unsafe_allow_html=True)

# ---------------- AUTH ----------------
def supabase() -> Client:
    url, key = secret("SUPABASE_URL"), secret("SUPABASE_ANON_KEY")
    if not url or not key:
        raise RuntimeError("Add SUPABASE_URL and SUPABASE_ANON_KEY to Streamlit Secrets.")
    return create_client(url, key)

def auth_error(e):
    msg = str(getattr(e, "message", e))
    low = msg.lower()
    if "invalid login credentials" in low: return "Invalid email or password."
    if "email not confirmed" in low: return "Please verify your email before signing in."
    if "user already registered" in low: return "This email already has an account. Please sign in."
    if "password should be at least" in low: return "Password does not meet Supabase password requirements."
    return msg

def signup(name, company, email, password):
    return supabase().auth.sign_up({
        "email": email.strip().lower(), "password": password,
        "options": {"data": {"full_name": name.strip(), "company_name": company.strip(), "plan": "Free"}}
    })

def signin(email, password):
    return supabase().auth.sign_in_with_password({
        "email": email.strip().lower(), "password": password
    })

def set_user(response):
    user = getattr(response, "user", None)
    if user is None: raise RuntimeError("Authentication succeeded but no user was returned.")
    meta = getattr(user, "user_metadata", {}) or {}
    st.session_state.authenticated = True
    st.session_state.user_email = (user.email or "").lower()
    st.session_state.user_id = user.id
    st.session_state.user_name = meta.get("full_name", "")
    st.session_state.company_name = meta.get("company_name", "")
    st.session_state.user_plan = meta.get("plan", "Free") or "Free"

def clear_analysis():
    for k, v in {
        "file_name":"", "analysis_result":None, "analysis_df":None,
        "n8n_sent":False, "n8n_result":None, "copilot_answer":None,
        "last_question":"", "report_pdf":None,
        "report_generated_at":None
    }.items(): st.session_state[k] = v

def signout():
    try: supabase().auth.sign_out()
    except Exception: pass
    st.session_state.authenticated = False
    st.session_state.user_email = st.session_state.user_id = ""
    st.session_state.user_name = st.session_state.company_name = ""
    st.session_state.user_plan = "Free"
    clear_analysis()

# ---------------- PLANS ----------------
PLANS = {
    "Free": {"max_mb":5,"copilot":True,"pdf":True,"email":False,"price":"₹0",
             "features":["5 MB file limit","Dashboard analytics","AI Copilot","PDF report"]},
    "Professional": {"max_mb":25,"copilot":True,"pdf":True,"email":True,"price":"₹1,999/mo",
             "features":["25 MB file limit","AI Copilot","PDF + email reports","n8n automation"]},
    "Business": {"max_mb":100,"copilot":True,"pdf":True,"email":True,"price":"Custom",
             "features":["100 MB file limit","Advanced automation","Custom workflows","Team deployment"]},
}

def show_pricing():
    st.markdown("### 💳 Plans")
    cols = st.columns(3)
    for col, (name, cfg) in zip(cols, PLANS.items()):
        with col:
            st.markdown('<div class="plan-card">', unsafe_allow_html=True)
            st.markdown(f"#### {name}")
            st.markdown(f"### {cfg['price']}")
            for f in cfg["features"]: st.write(f"✓ {f}")
            url = secret(f"{name.upper()}_CHECKOUT_URL")
            if url:
                st.link_button("Upgrade" if name != "Free" else "Current plan", url, use_container_width=True)
            else:
                st.button("Current plan" if st.session_state.user_plan == name else "Coming soon",
                          disabled=True, use_container_width=True, key=f"plan_{name}")
            st.markdown("</div>", unsafe_allow_html=True)

# ---------------- ROBUST FILE READER ----------------
def clean_df(df):
    df = df.copy()
    df.columns = [str(c).replace("\ufeff","").strip() for c in df.columns]
    return df.dropna(axis=1, how="all").dropna(axis=0, how="all").reset_index(drop=True)

def read_uploaded(uploaded):
    name = uploaded.name.lower()
    uploaded.seek(0)
    if name.endswith(".csv"):
        try: df = pd.read_csv(uploaded)
        except pd.errors.EmptyDataError: raise ValueError("The CSV file is empty.")
        except pd.errors.ParserError as e: raise ValueError(f"CSV format could not be parsed: {e}")
        df = clean_df(df)
        if df.empty or not len(df.columns): raise ValueError("CSV contains no usable data.")
        return df

    if name.endswith((".xlsx",".xls")):
        try:
            uploaded.seek(0)
            book = pd.ExcelFile(uploaded)
        except Exception as e:
            raise ValueError(f"Excel file could not be opened. Re-save it as .xlsx and try again. Details: {e}")
        sheets = [str(s).strip() for s in (book.sheet_names or []) if str(s).strip()]
        if not sheets: raise ValueError("Excel workbook has no readable worksheets.")

        preferred = next((s for s in sheets if s.lower()=="operational_data"), None)
        candidates = ([preferred] if preferred else []) + [s for s in sheets if s != preferred]
        last_error = None
        for sheet in candidates:
            try:
                uploaded.seek(0)
                df = clean_df(pd.read_excel(uploaded, sheet_name=sheet))
                if not df.empty and len(df.columns): return df
            except Exception as e: last_error = e
        raise ValueError("No worksheet contains readable operational data." + (f" Last error: {last_error}" if last_error else ""))
    raise ValueError("Unsupported file type. Upload CSV, XLS or XLSX.")

REQUIRED = ["Employee_ID","Employee_Name","Team","Target","Production","AHT_Actual","Quality_%","SLA_%"]

def validate(df):
    return [c for c in REQUIRED if c not in df.columns]

# ---------------- N8N / AI ----------------
def normalize_response(r):
    try: data = r.json()
    except ValueError: return {"answer": r.text}
    if isinstance(data, list) and data: data = data[0]
    return data if isinstance(data, dict) else {"answer": data}

def parse_answer(data):
    ans = data
    if isinstance(data, dict):
        ans = data.get("answer") or data.get("response") or data.get("output") or data.get("text") or data.get("message")
    if isinstance(ans, str):
        text = ans.strip().replace("```json","",1).replace("```","",1).strip()
        try: return json.loads(text)
        except json.JSONDecodeError: return text
    return ans

def df_text(df):
    return "No records available." if df is None or df.empty else df.to_string(index=False)

def copilot_context(company, report, result, pt, qt, st_, at, risk, summary):
    o = result["overall"]
    return f"""Company: {company}
Report: {report}
Productivity: {float(o['productivity']):.2f}% | Target: {pt}%
Quality: {float(o['quality']):.2f}% | Target: {qt}%
SLA: {float(o['sla']):.2f}% | Target: {st_}%
Average AHT: {float(o['aht']):.2f} | Target: {at}
Overall Risk: {risk}
Operational Findings:
{df_text(result.get('findings'))}
Recommended Actions:
{df_text(result.get('actions'))}
Employee Risk:
{df_text(result.get('employees'))}
Team Performance:
{df_text(result.get('team'))}
KPI Summary:
{chr(10).join(summary)}"""

# ---------------- PDF / EMAIL ----------------
def create_pdf(company, report, result, risk, summary, recommendation, targets):
    try:
        from reportlab.lib import colors
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.units import mm
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
    except ImportError:
        raise RuntimeError("Add reportlab to requirements.txt for PDF reports.")

    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, rightMargin=14*mm, leftMargin=14*mm,
                            topMargin=14*mm, bottomMargin=14*mm, title=f"{company} - {report}")
    styles = getSampleStyleSheet()
    title = ParagraphStyle("GI_Title", parent=styles["Title"], fontSize=20, leading=24)
    head = ParagraphStyle("GI_Head", parent=styles["Heading2"], fontSize=13, leading=16, spaceBefore=10, spaceAfter=6)
    body = ParagraphStyle("GI_Body", parent=styles["BodyText"], fontSize=9, leading=12)
    story = [Paragraph("Generative Insight", title),
             Paragraph(f"<b>{company}</b> — {report}<br/>Generated: {datetime.now():%d %b %Y, %H:%M}", body),
             Spacer(1,8), Paragraph("Executive Overview",head), Paragraph(f"<b>Risk:</b> {risk}",body)]
    o = result["overall"]
    rows = [["KPI","Actual","Target","Status"]]
    for name,key,tkey in [("Productivity","productivity","productivity"),("Quality","quality","quality"),("SLA","sla","sla"),("AHT","aht","aht")]:
        s = get_kpi_status(name,o[key],targets[tkey])
        rows.append([name,kpi_value(s),f"{s['target']:.2f}%" if name!="AHT" else f"{s['target']:.2f}",s["status"]])
    t = Table(rows,colWidths=[43*mm,40*mm,40*mm,50*mm])
    t.setStyle(TableStyle([("BACKGROUND",(0,0),(-1,0),colors.HexColor("#111827")),
                           ("TEXTCOLOR",(0,0),(-1,0),colors.white),("GRID",(0,0),(-1,-1),.35,colors.grey),
                           ("FONTNAME",(0,0),(-1,0),"Helvetica-Bold"),("FONTSIZE",(0,0),(-1,-1),8),
                           ("VALIGN",(0,0),(-1,-1),"MIDDLE"),("TOPPADDING",(0,0),(-1,-1),6),("BOTTOMPADDING",(0,0),(-1,-1),6)]))
    story += [t, Paragraph("KPI Summary",head)]
    for x in summary: story.append(Paragraph(x.replace("🟢 ","").replace("🔴 ",""),body))
    story += [Paragraph("Management Recommendation",head), Paragraph(recommendation,body)]
    for title_, key in [("Team Performance","team"),("Operational Findings","findings"),("Recommended Actions","actions"),("Employee Risk","employees")]:
        d = result.get(key)
        if isinstance(d,pd.DataFrame) and not d.empty:
            d = d.iloc[:50,:8]
            data = [[str(c) for c in d.columns]] + [[str(v)[:90] for v in row] for row in d.itertuples(index=False,name=None)]
            if data:
                tbl=Table(data,colWidths=[180*mm/max(len(data[0]),1)]*len(data[0]),repeatRows=1)
                tbl.setStyle(TableStyle([("BACKGROUND",(0,0),(-1,0),colors.HexColor("#111827")),
                                         ("TEXTCOLOR",(0,0),(-1,0),colors.white),("GRID",(0,0),(-1,-1),.25,colors.grey),
                                         ("FONTSIZE",(0,0),(-1,-1),6),("VALIGN",(0,0),(-1,-1),"TOP")]))
                story += [Paragraph(title_,head),tbl,Spacer(1,5)]
    story.append(Paragraph("Generated by Generative Insight AI Operations Copilot. Validate AI recommendations against operational evidence.",body))
    doc.build(story); buf.seek(0); return buf.getvalue()

def email_report(recipient, subject, body, pdf):
    host=secret("SMTP_HOST"); port=int(secret("SMTP_PORT","587")); user=secret("SMTP_USERNAME")
    password=secret("SMTP_PASSWORD"); sender=secret("SMTP_FROM",user)
    if not all([host,user,password,sender]): raise RuntimeError("SMTP settings are not configured.")
    msg=EmailMessage(); msg["Subject"]=subject; msg["From"]=sender; msg["To"]=recipient; msg.set_content(body)
    msg.add_attachment(pdf,maintype="application",subtype="pdf",filename="operations_report.pdf")
    with smtplib.SMTP(host,port,timeout=30) as server:
        server.starttls(); server.login(user,password); server.send_message(msg)

# ---------------- AUTH SCREEN ----------------
if not st.session_state.authenticated:
    st.markdown('<div class="main-title">Generative Insight</div>',unsafe_allow_html=True)
    st.markdown('<div class="brand-subtitle">Insights today. Intelligence tomorrow.</div>',unsafe_allow_html=True)
    st.caption("AI / ML   |   Annotation   |   Web & App Development")

    # IMPORTANT: This is actual HTML, not a code block.
    st.markdown("""
    <div class="hero">
      <h2>AI-powered operational intelligence</h2>
      <div class="brand-subtitle">Turn operational data into management decisions.</div>
      <p>Create your account, upload Excel/CSV operational data, identify KPI risks,
      investigate team and employee performance, ask the AI Operations Copilot questions,
      and generate management-ready reports.</p>
    </div>
    """,unsafe_allow_html=True)

    if not secret("SUPABASE_URL") or not secret("SUPABASE_ANON_KEY"):
        st.error("🔐 Add SUPABASE_URL and SUPABASE_ANON_KEY in Streamlit Secrets.")
        st.stop()

    signup_tab, login_tab, pricing_tab = st.tabs(["🆕 Create Account","🔐 Sign In","💳 Plans"])

    with signup_tab:
        st.markdown("### Create your Generative Insight account")
        st.caption("Start with the Free plan. You can upgrade later.")
        with st.form("signup_form"):
            name=st.text_input("Full Name",placeholder="e.g. Sunil Sethy")
            company=st.text_input("Company / Organization",placeholder="e.g. ABC Technologies")
            email=st.text_input("Work Email",placeholder="name@company.com")
            pw=st.text_input("Password",type="password")
            confirm=st.text_input("Confirm Password",type="password")
            submit=st.form_submit_button("🚀 Create Free Account",type="primary",use_container_width=True)
        if submit:
            if not name.strip(): st.warning("Please enter your full name.")
            elif not company.strip(): st.warning("Please enter your company or organization.")
            elif "@" not in email: st.warning("Please enter a valid email address.")
            elif len(pw)<6: st.warning("Please use at least 6 characters.")
            elif pw!=confirm: st.warning("Passwords do not match.")
            else:
                try:
                    with st.spinner("Creating your account..."):
                        r=signup(name,company,email,pw)
                    if getattr(r,"user",None) is not None and getattr(r,"session",None) is not None:
                        set_user(r); st.success("✅ Account created."); st.rerun()
                    else:
                        st.success("✅ Account created. Check your email for verification before signing in.")
                except Exception as e: st.error(f"❌ Could not create account: {auth_error(e)}")

    with login_tab:
        st.markdown("### Welcome back")
        with st.form("login_form"):
            email=st.text_input("Email",placeholder="name@company.com")
            pw=st.text_input("Password",type="password")
            submit=st.form_submit_button("🔐 Sign In",type="primary",use_container_width=True)
        if submit:
            if not email.strip() or not pw: st.warning("Enter email and password.")
            else:
                try:
                    with st.spinner("Signing you in..."): r=signin(email,pw)
                    set_user(r); st.success("✅ Signed in."); st.rerun()
                except Exception as e: st.error(f"❌ Sign in failed: {auth_error(e)}")
        st.info("If email confirmation is enabled, verify your email before signing in.")

    with pricing_tab: show_pricing()
    st.stop()

# ---------------- SIDEBAR ----------------
plan=PLANS.get(st.session_state.user_plan,PLANS["Free"])
with st.sidebar:
    st.markdown("## 🤖 Generative Insight")
    st.caption("AI Operations Copilot")
    st.success(f"Plan: **{st.session_state.user_plan}**")
    if st.session_state.user_name: st.caption(st.session_state.user_name)
    st.caption(st.session_state.user_email)
    st.divider(); st.header("⚙️ KPI Controls")
    pt=st.number_input("Productivity target %",1,200,90)
    qt=st.number_input("Quality target %",1,100,95)
    slat=st.number_input("SLA target %",1,100,97)
    at=st.number_input("AHT target",1,1000,50)
    st.divider()
    if st.button("💳 View Plans",use_container_width=True): st.session_state.show_plans=True
    if st.button("🔄 Reset Analysis",use_container_width=True): clear_analysis(); st.rerun()
    if st.button("🚪 Sign Out",use_container_width=True): signout(); st.rerun()
if st.session_state.show_plans: show_pricing(); st.divider()

# ---------------- HEADER / SETUP ----------------
st.markdown('<div class="main-title">🤖 AI Operations Manager</div>',unsafe_allow_html=True)
st.markdown("Executive operational intelligence → risk detection → AI decisions → action plans → management reports")
st.subheader("🏢 Report Setup")
c1,c2,c3=st.columns(3)
with c1: company_name=st.text_input("Company Name",value=st.session_state.company_name,placeholder="e.g. ABC Technologies")
with c2: manager_email=st.text_input("Manager Email",placeholder="manager@company.com")
with c3: report_name=st.text_input("Report Name",value="Daily Operations Report")

# ---------------- UPLOAD ----------------
uploaded=st.file_uploader(f"📁 Upload Excel or CSV operational data — max {plan['max_mb']} MB",
                          type=["xlsx","xls","csv"])
if not uploaded:
    st.info("Upload operational data to activate the executive dashboard.")
    st.markdown("### Required columns")
    st.code("Employee_ID, Employee_Name, Team, Target, Production, AHT_Actual, Quality_%, SLA_%, Attendance, Error_Count, Error_Category")
    a,b,c,d=st.columns(4); a.metric("Risk Detection","✓"); b.metric("Employee Risk","✓"); c.metric("AI Copilot","✓"); d.metric("Management Report","✓")
    st.stop()

size=uploaded.size/(1024*1024)
if size>plan["max_mb"]:
    st.error(f"File is {size:.2f} MB. Your {st.session_state.user_plan} plan supports up to {plan['max_mb']} MB."); st.stop()

if st.session_state.file_name!=uploaded.name:
    clear_analysis(); st.session_state.file_name=uploaded.name

try: df=read_uploaded(uploaded)
except Exception as e:
    st.error(f"❌ Could not read the uploaded file: {e}")
    st.info("For Excel, ensure at least one worksheet contains data. For CSV, save it as a standard comma-separated CSV.")
    st.stop()

with st.expander("📁 Uploaded file details",expanded=False):
    st.write(f"**File:** {uploaded.name}  |  **Size:** {size:.2f} MB  |  **Rows:** {len(df):,}  |  **Columns:** {len(df.columns):,}")
    st.code(", ".join(map(str,df.columns)))

missing=validate(df)
if missing:
    st.error("❌ Required columns are missing:")
    st.write(missing)
    st.code(", ".join(REQUIRED))
    st.stop()

try:
    result=analyze_data(df,productivity_target=pt,quality_target=qt,sla_target=slat,aht_target=at)
except Exception as e:
    st.error(f"❌ Analysis failed: {e}"); st.stop()

st.session_state.analysis_result=result; st.session_state.analysis_df=df

# ---------------- KPI / RISK ----------------
o=result["overall"]
p,q,s,a=map(float,[o["productivity"],o["quality"],o["sla"],o["aht"]])
statuses=get_kpi_statuses(p,q,s,a,pt,qt,slat,at)
breaches=sum(not x["is_good"] for x in statuses.values())
risk=["🟢 LOW RISK","🟡 MEDIUM RISK","🟠 HIGH RISK","🔴 CRITICAL RISK"][min(breaches,3)]

actions=result.get("actions",pd.DataFrame())
action_count=len(actions) if isinstance(actions,pd.DataFrame) else 0
high_count=0
if isinstance(actions,pd.DataFrame) and not actions.empty:
    for col in ["Priority","priority","Priority_Level","priority_level"]:
        if col in actions.columns:
            high_count=int(actions[col].astype(str).str.lower().isin(["high","critical"]).sum()); break

st.markdown(f'<div class="hero"><h2>Executive Health: {risk}</h2><p>{company_name or "Your organization"} · {report_name}</p></div>',unsafe_allow_html=True)
r1,r2,r3,r4=st.columns(4)
r1.metric("Operational Risk",risk); r2.metric("KPI Breaches",breaches,delta=f"{4-breaches} on target"); r3.metric("Action Items",action_count); r4.metric("High/Critical Actions",high_count)

st.subheader("📊 KPI Performance vs Target")
k1,k2,k3,k4=st.columns(4)
for col,name in zip([k1,k2,k3,k4],["Productivity","Quality","SLA","AHT"]):
    with col: render_kpi(statuses[name])

summary=[
    f"{statuses['Productivity']['icon']} Productivity: {p:.1f}% vs {pt}% target — {statuses['Productivity']['status']}.",
    f"{statuses['Quality']['icon']} Quality: {q:.1f}% vs {qt}% target — {statuses['Quality']['status']}.",
    f"{statuses['SLA']['icon']} SLA: {s:.1f}% vs {slat}% target — {statuses['SLA']['status']}.",
    f"{statuses['AHT']['icon']} AHT: {a:.1f} vs {at} target — {statuses['AHT']['status']}."
]
recommendation=("Immediate management attention is recommended. Multiple KPI thresholds are breached." if breaches>=3
                else "Management should review the affected KPIs and initiate targeted corrective actions." if breaches
                else "Operations are within defined KPI thresholds. Continue monitoring performance.")

st.subheader("🧠 Executive Summary")
for x in summary: st.write(x)
st.info(f"💡 **Management Recommendation:** {recommendation}")

# ---------------- N8N ----------------
n8n_url=secret("N8N_WEBHOOK_URL"); copilot_url=secret("N8N_COPILOT_WEBHOOK_URL")
if n8n_url and not st.session_state.n8n_sent:
    if company_name.strip() and manager_email.strip():
        try:
            uploaded.seek(0)
            r=requests.post(n8n_url,files={"file":(uploaded.name,uploaded.getvalue(),uploaded.type or "application/octet-stream")},
                            data={"company_name":company_name.strip(),"manager_email":manager_email.strip(),"report_name":report_name.strip()},timeout=120)
            if r.status_code<300:
                st.session_state.n8n_result=normalize_response(r); st.session_state.n8n_sent=True; st.success("✅ Operational automation completed.")
            else: st.error(f"❌ n8n workflow failed: HTTP {r.status_code}")
        except requests.exceptions.Timeout: st.warning("⏱️ n8n timed out. The workflow may still be running.")
        except requests.exceptions.RequestException as e: st.error(f"❌ Could not connect to n8n: {e}")
    else: st.warning("Enter Company Name and Manager Email to run n8n automation.")

# ---------------- TABS ----------------
tabs=st.tabs(["📊 Executive Dashboard","🚨 AI Insights","👥 Employee Risk","✅ Action Center","🤖 Management Copilot","📄 Reports","💳 Billing"])

with tabs[0]:
    left,right=st.columns([1.4,1]); team=result.get("team",pd.DataFrame()); employees=result.get("employees",pd.DataFrame())
    with left:
        st.subheader("Team Performance")
        if isinstance(team,pd.DataFrame) and not team.empty:
            st.dataframe(team,use_container_width=True,hide_index=True)
            if "Team" in team.columns and "Productivity_%" in team.columns: st.bar_chart(team.set_index("Team")["Productivity_%"])
        else: st.info("No team-level data available.")
    with right:
        st.subheader("Management Snapshot")
        if isinstance(employees,pd.DataFrame) and not employees.empty:
            st.metric("Employees analyzed",len(employees))
            if "Risk_Score" in employees.columns: st.metric("Highest employee risk score",f"{employees['Risk_Score'].max():.2f}")
        for x in summary: st.write(x)

with tabs[1]:
    st.subheader("🚨 Automated Findings"); findings=result.get("findings",pd.DataFrame())
    if isinstance(findings,pd.DataFrame) and not findings.empty: st.dataframe(findings,use_container_width=True,hide_index=True)
    else: st.success("✅ No threshold breaches detected.")
    st.info("Root causes are evidence-based hypotheses. The available data may not prove causality.")

with tabs[2]:
    st.subheader("👥 Employee Risk"); employees=result.get("employees",pd.DataFrame())
    if isinstance(employees,pd.DataFrame) and not employees.empty:
        sort=[x for x in ["Risk_Score","Avg_Productivity"] if x in employees.columns]
        if sort: employees=employees.sort_values(sort,ascending=[False]*len(sort))
        st.dataframe(employees,use_container_width=True,hide_index=True)
    else: st.info("No employee-level risk data available.")

with tabs[3]:
    st.subheader("✅ Recommended Actions")
    if isinstance(actions,pd.DataFrame) and not actions.empty: st.dataframe(actions,use_container_width=True,hide_index=True)
    else: st.success("No action items generated.")

with tabs[4]:
    st.subheader("🤖 Management Copilot")
    question=st.text_input("Ask your operational question",placeholder="Which team has the quality drop and what action should be taken?",key="copilot_question")
    ask=st.button("🚀 Ask Management Copilot",type="primary",use_container_width=True)
    if ask:
        if not question.strip(): st.warning("Please enter a question.")
        elif not copilot_url: st.error("N8N_COPILOT_WEBHOOK_URL is not configured.")
        else:
            payload={"question":question.strip(),"company_name":company_name.strip(),"report_name":report_name.strip(),
                     "context":copilot_context(company_name,report_name,result,pt,qt,slat,at,risk,summary)}
            try:
                with st.spinner("🤖 Management Copilot is analyzing..."):
                    r=requests.post(copilot_url,json=payload,headers={"Content-Type":"application/json"},timeout=120)
                if r.status_code<300:
                    st.session_state.copilot_answer=parse_answer(normalize_response(r)); st.session_state.last_question=question.strip()
                else: st.error(f"❌ Copilot workflow failed: HTTP {r.status_code}")
            except requests.exceptions.Timeout: st.error("⏱️ Management Copilot timed out.")
            except requests.exceptions.RequestException as e: st.error(f"❌ Copilot request failed: {e}")
    if st.session_state.copilot_answer:
        st.divider(); st.caption(f"Question: {st.session_state.last_question}")
        ans=st.session_state.copilot_answer
        if isinstance(ans,dict):
            if ans.get("what_is_happening"): st.markdown("#### 🔎 What is happening"); st.info(ans["what_is_happening"])
            if ans.get("contributing_factors"):
                st.markdown("#### 🔍 Contributing Factors")
                for x in ans["contributing_factors"]: st.write(f"• {x}")
            if ans.get("recommended_actions"):
                st.markdown("#### ✅ Recommended Actions")
                for i,x in enumerate(ans["recommended_actions"],1): st.markdown(f"**{i}.** {x}")
            d1,d2,d3=st.columns(3)
            d1.metric("Priority",ans.get("priority","N/A")); d2.metric("Owner",ans.get("owner","N/A")); d3.metric("Timeline",ans.get("timeline","N/A"))
            if ans.get("data_sufficiency"): st.warning(ans["data_sufficiency"])
        elif isinstance(ans,str): st.markdown(ans)
        else: st.code(str(ans))

with tabs[5]:
    st.subheader("📄 Management Reports")
    if not plan["pdf"]: st.warning("PDF reporting is not available on your current plan.")
    else:
        targets={"productivity":pt,"quality":qt,"sla":slat,"aht":at}
        if st.button("📄 Generate Executive PDF",type="primary",use_container_width=True):
            try:
                with st.spinner("Generating management report..."):
                    st.session_state.report_pdf=create_pdf(company_name or "Organization",report_name or "Operations Report",result,risk,summary,recommendation,targets)
                st.session_state.report_generated_at=datetime.now()
            except Exception as e: st.error(f"❌ Could not generate PDF: {e}")
        if st.session_state.report_pdf:
            fname=f"{company_name or 'operations'}_report_{datetime.now():%Y%m%d_%H%M}.pdf"
            st.download_button("⬇️ Download Executive PDF",st.session_state.report_pdf,fname,"application/pdf",use_container_width=True)
        st.divider(); st.subheader("📧 Email Report")
        if not plan["email"]: st.info("Email delivery is available on Professional and Business plans.")
        else:
            recipient=st.text_input("Recipient email",value=manager_email,key="report_recipient")
            if st.button("📨 Email PDF Report",use_container_width=True):
                if not recipient.strip(): st.warning("Enter a recipient email.")
                elif not st.session_state.report_pdf: st.warning("Generate the PDF first.")
                else:
                    try:
                        email_report(recipient.strip(),f"{company_name} - {report_name}","Please find attached the management report.",st.session_state.report_pdf)
                        st.success("✅ Report emailed successfully.")
                    except Exception as e: st.error(f"❌ Email failed: {e}")
        st.divider(); st.subheader("📥 Data Exports")
        e1,e2=st.columns(2)
        with e1:
            if isinstance(team,pd.DataFrame): st.download_button("⬇️ Team Analysis CSV",team.to_csv(index=False).encode(), "team_analysis.csv","text/csv",use_container_width=True)
        with e2:
            if isinstance(actions,pd.DataFrame): st.download_button("⬇️ Action Plan CSV",actions.to_csv(index=False).encode(), "action_plan.csv","text/csv",use_container_width=True)

with tabs[6]:
    st.subheader("💳 Subscription & Billing"); st.info(f"You are currently using the **{st.session_state.user_plan}** plan."); show_pricing()

with st.expander("🧠 AI Analyst Context / Prompt",expanded=False):
    st.code(make_ai_prompt(result),language="text")

st.divider()
st.caption(f"© {datetime.now().year} Generative Insight · AI Operations Copilot v{APP_VERSION} · Validate AI recommendations before taking material business action.")
