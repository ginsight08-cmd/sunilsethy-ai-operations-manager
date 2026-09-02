"""Persistent, login-scoped Vakil client and legal case management UI."""

from datetime import date, datetime, time, timezone

import pandas as pd
import requests
import streamlit as st


CASE_STATUSES = ["Consultation", "Drafting", "Filed", "Pending", "Hearing", "Order Reserved", "Disposed", "Closed"]
CASE_PRIORITIES = ["Urgent", "High", "Normal", "Low"]


def _rows(response):
    return list(getattr(response, "data", None) or [])


def _date_value(value, fallback=None):
    parsed = pd.to_datetime(value, errors="coerce")
    return fallback or date.today() if pd.isna(parsed) else parsed.date()


def _iso_date(value):
    return value.isoformat() if value else None


def _load_records(db, user_id):
    clients = _rows(
        db.table("vakil_clients").select("*").eq("user_id", user_id).order("client_name").execute()
    )
    cases = _rows(
        db.table("vakil_cases").select("*").eq("user_id", user_id).order("updated_at", desc=True).execute()
    )
    return clients, cases


def _client_label(client):
    contact = client.get("phone") or client.get("email") or "No contact"
    return f"{client.get('client_name', 'Unnamed')} · {contact}"


def _render_dashboard(cases, clients):
    today = date.today()
    open_cases = [row for row in cases if row.get("status") not in {"Disposed", "Closed"}]
    upcoming = []
    overdue = []
    for row in open_cases:
        hearing = pd.to_datetime(row.get("next_hearing_date"), errors="coerce")
        if pd.isna(hearing):
            continue
        hearing_date = hearing.date()
        if hearing_date < today:
            overdue.append(row)
        elif (hearing_date - today).days <= 30:
            upcoming.append(row)

    metrics = st.columns(5)
    metrics[0].metric("Clients", len(clients))
    metrics[1].metric("Total cases", len(cases))
    metrics[2].metric("Open cases", len(open_cases))
    metrics[3].metric("Hearings ≤30 days", len(upcoming))
    metrics[4].metric("Past hearing date", len(overdue))

    if cases:
        frame = pd.DataFrame(cases)
        display_columns = [
            "case_number", "case_title", "client_name", "court_name", "case_type",
            "status", "priority", "next_hearing_date", "advocate_name", "updated_at",
        ]
        frame = frame[[column for column in display_columns if column in frame.columns]]
        st.subheader("📋 Case register")
        search = st.text_input("Search cases", placeholder="Case number, client, court, party, or title")
        if search.strip():
            mask = frame.astype(str).apply(
                lambda column: column.str.contains(search.strip(), case=False, na=False)
            ).any(axis=1)
            frame = frame[mask]
        st.dataframe(frame, use_container_width=True, hide_index=True)
    else:
        st.info("No legal cases saved yet. Add a client, then create the first case.")


def _render_clients(db, user_id, clients):
    st.subheader("👥 Client master")
    with st.expander("➕ Add a client", expanded=not clients):
        with st.form("vakil_add_client", clear_on_submit=True):
            c1, c2 = st.columns(2)
            name = c1.text_input("Client name *")
            client_type = c2.selectbox("Client type", ["Individual", "Company", "Trust", "Government", "Other"])
            c3, c4 = st.columns(2)
            phone = c3.text_input("Phone")
            email = c4.text_input("Email")
            address = st.text_area("Address")
            identity_reference = st.text_input("Identity/reference number", help="Store only information you are authorized to retain.")
            notes = st.text_area("Client notes")
            submitted = st.form_submit_button("Save client", type="primary")
        if submitted:
            if not name.strip():
                st.error("Client name is required.")
            else:
                db.table("vakil_clients").insert({
                    "user_id": user_id, "client_name": name.strip(), "client_type": client_type,
                    "phone": phone.strip(), "email": email.strip().lower(), "address": address.strip(),
                    "identity_reference": identity_reference.strip(), "notes": notes.strip(),
                }).execute()
                st.success("Client saved.")
                st.rerun()

    if not clients:
        return

    selected_id = st.selectbox(
        "Select client to view or edit",
        options=[row["id"] for row in clients],
        format_func=lambda value: _client_label(next(row for row in clients if row["id"] == value)),
        key="vakil_client_selector",
    )
    selected = next(row for row in clients if row["id"] == selected_id)
    with st.form("vakil_edit_client"):
        c1, c2 = st.columns(2)
        name = c1.text_input("Client name *", value=selected.get("client_name") or "")
        types = ["Individual", "Company", "Trust", "Government", "Other"]
        current_type = selected.get("client_type") or "Individual"
        client_type = c2.selectbox("Client type", types, index=types.index(current_type) if current_type in types else 0)
        c3, c4 = st.columns(2)
        phone = c3.text_input("Phone", value=selected.get("phone") or "")
        email = c4.text_input("Email", value=selected.get("email") or "")
        address = st.text_area("Address", value=selected.get("address") or "")
        identity_reference = st.text_input("Identity/reference number", value=selected.get("identity_reference") or "")
        notes = st.text_area("Client notes", value=selected.get("notes") or "")
        save = st.form_submit_button("Update client", type="primary")
    if save:
        if not name.strip():
            st.error("Client name is required.")
        else:
            db.table("vakil_clients").update({
                "client_name": name.strip(), "client_type": client_type, "phone": phone.strip(),
                "email": email.strip().lower(), "address": address.strip(),
                "identity_reference": identity_reference.strip(), "notes": notes.strip(),
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }).eq("id", selected_id).eq("user_id", user_id).execute()
            db.table("vakil_cases").update({
                "client_name": name.strip(), "updated_at": datetime.now(timezone.utc).isoformat(),
            }).eq("client_id", selected_id).eq("user_id", user_id).execute()
            st.success("Client updated.")
            st.rerun()

    with st.expander("🗑️ Delete this client"):
        st.warning("A client cannot be deleted while linked cases exist.")
        confirm = st.checkbox("I understand and want to delete this client", key="vakil_delete_client_confirm")
        if st.button("Delete client", disabled=not confirm, key="vakil_delete_client"):
            try:
                db.table("vakil_clients").delete().eq("id", selected_id).eq("user_id", user_id).execute()
                st.success("Client deleted.")
                st.rerun()
            except Exception as exc:
                st.error(f"Client could not be deleted. Remove or reassign linked cases first. {exc}")


def _case_form_values(prefix, clients, record=None):
    record = record or {}
    client_ids = [row["id"] for row in clients]
    current_client = record.get("client_id")
    client_index = client_ids.index(current_client) if current_client in client_ids else 0
    client_id = st.selectbox(
        "Client *", client_ids, index=client_index,
        format_func=lambda value: _client_label(next(row for row in clients if row["id"] == value)),
        key=f"{prefix}_client",
    )
    c1, c2 = st.columns(2)
    case_number = c1.text_input("Case number *", value=record.get("case_number") or "", key=f"{prefix}_number")
    case_title = c2.text_input("Case title", value=record.get("case_title") or "", key=f"{prefix}_title")
    c3, c4 = st.columns(2)
    court_name = c3.text_input("Court / tribunal", value=record.get("court_name") or "", key=f"{prefix}_court")
    case_type = c4.text_input("Case type", value=record.get("case_type") or "", key=f"{prefix}_type")
    c5, c6 = st.columns(2)
    filing_number = c5.text_input("Filing/CNR number", value=record.get("filing_number") or "", key=f"{prefix}_filing")
    opposing_party = c6.text_input("Opposing party", value=record.get("opposing_party") or "", key=f"{prefix}_opponent")
    c7, c8, c9 = st.columns(3)
    status_value = record.get("status") or "Consultation"
    status = c7.selectbox("Status", CASE_STATUSES, index=CASE_STATUSES.index(status_value) if status_value in CASE_STATUSES else 0, key=f"{prefix}_status")
    priority_value = record.get("priority") or "Normal"
    priority = c8.selectbox("Priority", CASE_PRIORITIES, index=CASE_PRIORITIES.index(priority_value) if priority_value in CASE_PRIORITIES else 2, key=f"{prefix}_priority")
    advocate = c9.text_input("Advocate/owner", value=record.get("advocate_name") or "", key=f"{prefix}_advocate")
    c10, c11 = st.columns(2)
    filing_date = c10.date_input("Filing date", value=_date_value(record.get("filing_date")), key=f"{prefix}_filing_date")
    has_hearing = c11.checkbox("Next hearing scheduled", value=bool(record.get("next_hearing_date")), key=f"{prefix}_has_hearing")
    hearing_date = c11.date_input("Next hearing date", value=_date_value(record.get("next_hearing_date")), disabled=not has_hearing, key=f"{prefix}_hearing")
    description = st.text_area("Case facts / description", value=record.get("description") or "", key=f"{prefix}_description")
    notes = st.text_area("Latest notes / next action", value=record.get("notes") or "", key=f"{prefix}_notes")
    client = next(row for row in clients if row["id"] == client_id)
    return {
        "client_id": client_id, "client_name": client.get("client_name") or "", "case_number": case_number.strip(),
        "case_title": case_title.strip(), "court_name": court_name.strip(), "case_type": case_type.strip(),
        "filing_number": filing_number.strip(), "opposing_party": opposing_party.strip(), "status": status,
        "priority": priority, "advocate_name": advocate.strip(), "filing_date": _iso_date(filing_date),
        "next_hearing_date": _iso_date(hearing_date) if has_hearing else None,
        "description": description.strip(), "notes": notes.strip(),
    }


def _render_cases(db, user_id, clients, cases):
    st.subheader("⚖️ Legal cases")
    if not clients:
        st.warning("Add a client before creating a case.")
        return

    with st.expander("➕ Create a case", expanded=not cases):
        with st.form("vakil_add_case", clear_on_submit=False):
            payload = _case_form_values("vakil_add", clients)
            create = st.form_submit_button("Save case", type="primary")
        if create:
            if not payload["case_number"]:
                st.error("Case number is required.")
            else:
                payload["user_id"] = user_id
                try:
                    db.table("vakil_cases").insert(payload).execute()
                    st.success("Case saved.")
                    st.rerun()
                except Exception as exc:
                    st.error(f"Case could not be saved. Check that the case number is unique. {exc}")

    if not cases:
        return

    selected_id = st.selectbox(
        "Select case to view or edit", options=[row["id"] for row in cases],
        format_func=lambda value: next(
            f"{row.get('case_number')} · {row.get('client_name')} · {row.get('status')}"
            for row in cases if row["id"] == value
        ), key="vakil_case_selector",
    )
    selected = next(row for row in cases if row["id"] == selected_id)
    with st.form("vakil_edit_case"):
        payload = _case_form_values("vakil_edit", clients, selected)
        save = st.form_submit_button("Update case", type="primary")
    if save:
        if not payload["case_number"]:
            st.error("Case number is required.")
        else:
            payload["updated_at"] = datetime.now(timezone.utc).isoformat()
            try:
                db.table("vakil_cases").update(payload).eq("id", selected_id).eq("user_id", user_id).execute()
                st.success("Case updated.")
                st.rerun()
            except Exception as exc:
                st.error(f"Case could not be updated. {exc}")

    with st.expander("🗑️ Delete this case"):
        confirm = st.checkbox("I understand and want to permanently delete this case", key="vakil_delete_case_confirm")
        if st.button("Delete case", disabled=not confirm, key="vakil_delete_case"):
            db.table("vakil_cases").delete().eq("id", selected_id).eq("user_id", user_id).execute()
            st.success("Case deleted.")
            st.rerun()


def _default_notification_message(case, client):
    hearing = case.get("next_hearing_date") or "not scheduled"
    return (
        f"Dear {client.get('client_name', 'Client')}, update for case "
        f"{case.get('case_number', '')} ({case.get('case_title') or 'Legal matter'}): "
        f"current status is {case.get('status', '')}. Next hearing: {hearing}. "
        f"Court: {case.get('court_name') or 'not specified'}. "
        "Please contact your advocate if you need clarification."
    )


def _render_notifications(db, user_id, clients, cases, webhook_url, sender_email):
    st.subheader("🔔 Hearing and case notifications")
    st.caption("Send a tracked case update to the client's WhatsApp number, email address, or both.")
    if not cases:
        st.info("Create a case before sending notifications.")
        return
    if not webhook_url:
        st.warning("Add N8N_VAKIL_NOTIFICATION_WEBHOOK_URL to Streamlit Secrets before sending.")

    case_id = st.selectbox(
        "Case", [row["id"] for row in cases],
        format_func=lambda value: next(
            f"{row.get('case_number')} · {row.get('client_name')} · {row.get('status')}"
            for row in cases if row["id"] == value
        ), key="vakil_notification_case",
    )
    selected_case = next(row for row in cases if row["id"] == case_id)
    client = next((row for row in clients if row["id"] == selected_case.get("client_id")), {})

    c1, c2 = st.columns(2)
    send_whatsapp = c1.checkbox("WhatsApp", value=bool(client.get("phone")))
    send_email = c2.checkbox("Email", value=bool(client.get("email")))
    c1.caption(f"Number: {client.get('phone') or 'not available'}")
    c2.caption(f"Address: {client.get('email') or 'not available'}")
    message = st.text_area(
        "Notification message", value=_default_notification_message(selected_case, client), height=150,
        key=f"vakil_notification_message_{case_id}",
    )

    disabled = not webhook_url or not message.strip() or not (send_whatsapp or send_email)
    if st.button("Send and record notification", type="primary", disabled=disabled):
        if send_whatsapp and not client.get("phone"):
            st.error("Add the client's WhatsApp phone number first.")
            return
        if send_email and not client.get("email"):
            st.error("Add the client's email address first.")
            return

        channels = [name for name, enabled in (("whatsapp", send_whatsapp), ("email", send_email)) if enabled]
        payload = {
            "event": "vakil_case_notification",
            "user_id": user_id,
            "case_id": selected_case["id"],
            "case_number": selected_case.get("case_number"),
            "case_title": selected_case.get("case_title"),
            "case_status": selected_case.get("status"),
            "court_name": selected_case.get("court_name"),
            "next_hearing_date": selected_case.get("next_hearing_date"),
            "client_id": client.get("id"),
            "client_name": client.get("client_name"),
            "whatsapp_number": client.get("phone") if send_whatsapp else "",
            "email": client.get("email") if send_email else "",
            "channels": channels,
            "message": message.strip(),
            "sender_email": sender_email,
        }
        delivery_status = "failed"
        response_detail = ""
        try:
            response = requests.post(webhook_url, json=payload, timeout=60)
            response_detail = (response.text or "")[:1000]
            response.raise_for_status()
            delivery_status = "queued"
            st.success("Notification accepted by n8n and recorded.")
        except requests.exceptions.RequestException as exc:
            response_detail = str(exc)[:1000]
            st.error(f"Notification delivery failed: {exc}")
        finally:
            try:
                db.table("vakil_notification_log").insert({
                    "user_id": user_id, "case_id": selected_case["id"], "client_id": client.get("id"),
                    "channels": channels, "recipient_email": client.get("email") if send_email else "",
                    "recipient_phone": client.get("phone") if send_whatsapp else "", "message": message.strip(),
                    "delivery_status": delivery_status, "provider_response": response_detail,
                }).execute()
            except Exception as exc:
                st.warning(f"Delivery ran, but its audit record could not be saved: {exc}")

    try:
        logs = _rows(
            db.table("vakil_notification_log").select(
                "created_at,delivery_status,channels,recipient_email,recipient_phone,message"
            ).eq("user_id", user_id).order("created_at", desc=True).limit(100).execute()
        )
        if logs:
            st.markdown("#### Recent notification history")
            st.dataframe(pd.DataFrame(logs), use_container_width=True, hide_index=True)
    except Exception:
        pass


def render(db, user_id, notification_webhook_url="", sender_email=""):
    """Render the persistent case-management workspace."""
    st.markdown('<div class="main-title">Vakil Case Management</div>', unsafe_allow_html=True)
    st.caption("Persistent client records, legal matters, hearings, ownership, status, and follow-up tracking.")
    try:
        clients, cases = _load_records(db, user_id)
    except Exception as exc:
        st.error("The Vakil database is not configured yet. Run supabase_vakil_schema.sql in Supabase SQL Editor.")
        st.code(str(exc), language="text")
        return

    dashboard, client_tab, case_tab, notification_tab = st.tabs(
        ["📊 Dashboard", "👥 Clients", "⚖️ Cases", "🔔 Notifications"]
    )
    with dashboard:
        _render_dashboard(cases, clients)
    with client_tab:
        _render_clients(db, user_id, clients)
    with case_tab:
        _render_cases(db, user_id, clients, cases)
    with notification_tab:
        _render_notifications(db, user_id, clients, cases, notification_webhook_url, sender_email)
