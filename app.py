# ============================================================
# AI EXECUTIVE SUMMARY
# ============================================================

st.divider()

st.subheader("🧠 AI Executive Summary")

overall = result["overall"]

productivity = overall["productivity"]
quality = overall["quality"]
sla = overall["sla"]
aht = overall["aht"]

summary_points = []

# ------------------------------------------------------------
# PRODUCTIVITY
# ------------------------------------------------------------

if productivity < productivity_target:

    summary_points.append(
        f"🔴 Productivity is below target "
        f"({productivity:.1f}% vs {productivity_target}%)."
    )

else:

    summary_points.append(
        f"🟢 Productivity is above target "
        f"({productivity:.1f}% vs {productivity_target}%)."
    )


# ------------------------------------------------------------
# QUALITY
# ------------------------------------------------------------

if quality < quality_target:

    summary_points.append(
        f"🔴 Quality is below target "
        f"({quality:.1f}% vs {quality_target}%)."
    )

else:

    summary_points.append(
        f"🟢 Quality is meeting target "
        f"({quality:.1f}% vs {quality_target}%)."
    )


# ------------------------------------------------------------
# SLA
# ------------------------------------------------------------

if sla < sla_target:

    summary_points.append(
        f"🔴 SLA is below target "
        f"({sla:.1f}% vs {sla_target}%)."
    )

else:

    summary_points.append(
        f"🟢 SLA is meeting target "
        f"({sla:.1f}% vs {sla_target}%)."
    )


# ------------------------------------------------------------
# AHT
# ------------------------------------------------------------

if aht > aht_target:

    summary_points.append(
        f"🟠 AHT is above target "
        f"({aht:.1f} vs {aht_target})."
    )

else:

    summary_points.append(
        f"🟢 AHT is within target "
        f"({aht:.1f} vs {aht_target})."
    )


# ------------------------------------------------------------
# OVERALL RISK
# ------------------------------------------------------------

risk_count = 0

if productivity < productivity_target:
    risk_count += 1

if quality < quality_target:
    risk_count += 1

if sla < sla_target:
    risk_count += 1

if aht > aht_target:
    risk_count += 1


if risk_count == 0:

    risk_level = "🟢 LOW RISK"

elif risk_count == 1:

    risk_level = "🟡 MEDIUM RISK"

elif risk_count == 2:

    risk_level = "🟠 HIGH RISK"

else:

    risk_level = "🔴 CRITICAL RISK"


# ------------------------------------------------------------
# RISK DISPLAY
# ------------------------------------------------------------

risk_col1, risk_col2 = st.columns([1, 3])

with risk_col1:

    st.metric(
        "Operational Risk Level",
        risk_level
    )

with risk_col2:

    st.metric(
        "KPI Areas Requiring Attention",
        risk_count
    )


# ------------------------------------------------------------
# EXECUTIVE FINDINGS
# ------------------------------------------------------------

st.markdown("### 📌 Executive Findings")

for point in summary_points:

    st.write(point)


# ------------------------------------------------------------
# MANAGEMENT RECOMMENDATION
# ------------------------------------------------------------

if risk_count == 0:

    recommendation = (
        "Operations are currently performing within "
        "defined KPI thresholds. Continue monitoring "
        "performance and maintain current processes."
    )

elif risk_count <= 2:

    recommendation = (
        "Management should review the affected KPIs, "
        "identify contributing operational factors, "
        "and initiate targeted corrective actions."
    )

else:

    recommendation = (
        "Immediate management attention is recommended. "
        "Multiple KPI thresholds are currently breached. "
        "Prioritize root-cause analysis and corrective "
        "actions."
    )


st.info(
    f"💡 **Management Recommendation:** {recommendation}"
)


# ============================================================
# MANAGEMENT COPILOT
# ============================================================

st.divider()

st.subheader("🤖 Management Copilot")

st.caption(
    "Ask questions about the uploaded operational data "
    "and get management-focused recommendations."
)


question = st.text_input(
    "Ask your operational question",
    placeholder="Example: Why is Quality below target?"
)


if question:

    # --------------------------------------------------------
    # BUILD COPILOT CONTEXT
    # --------------------------------------------------------

    findings_text = (
        result["findings"].to_string(index=False)
        if not result["findings"].empty
        else "No operational findings detected."
    )

    actions_text = (
        result["actions"].to_string(index=False)
        if not result["actions"].empty
        else "No recommended actions available."
    )


    copilot_context = f"""
You are an AI Operations Management Copilot.

Company:
{company_name}

Report:
{report_name}

Operational KPIs:

Productivity:
{productivity:.2f}% | Target: {productivity_target}%

Quality:
{quality:.2f}% | Target: {quality_target}%

SLA:
{sla:.2f}% | Target: {sla_target}%

Average AHT:
{aht:.2f} | Target: {aht_target}

Overall Risk:
{risk_level}

Operational Findings:
{findings_text}

Recommended Actions:
{actions_text}

Manager Question:
{question}

Provide a concise management-level answer.

Your answer must contain:

1. What is happening
2. Possible contributing factors
3. Recommended action
4. Priority
5. Suggested owner
6. Suggested timeline

Do not invent facts that are not supported
by the operational data.

Clearly label assumptions as assumptions.
"""


    # --------------------------------------------------------
    # DISPLAY COPILOT PROMPT
    # --------------------------------------------------------

    st.markdown("### 🧠 Copilot Analysis")

    st.code(
        copilot_context,
        language="text"
    )


    st.info(
        "🤖 Copilot context is ready. "
        "Next step: connect this prompt to your AI model "
        "through the existing n8n workflow."
    )
