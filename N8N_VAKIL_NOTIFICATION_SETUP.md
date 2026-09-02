# Vakil WhatsApp and email notification setup

The Streamlit app sends one JSON request to n8n. n8n is responsible for
delivering WhatsApp and email messages, keeping provider credentials outside
the application.

## Workflow 1: send an update from the app

Create and activate an n8n workflow with these nodes:

1. **Webhook**
   - Method: `POST`
   - Path: `vakil-notification`
   - Authentication: Header authentication is recommended for production.
   - Use the production URL containing `/webhook/vakil-notification`.
2. **IF / Switch** for `{{$json.channels}}`
   - WhatsApp branch when the array contains `whatsapp`.
   - Email branch when the array contains `email`.
3. **WhatsApp delivery**
   - Connect Meta WhatsApp Cloud API, Twilio WhatsApp, or another approved
     WhatsApp Business provider.
   - Recipient: `{{$json.whatsapp_number}}`
   - Message: `{{$json.message}}`
   - For proactive WhatsApp messages outside the customer-service window,
     use an approved message template and obtain the client's consent.
4. **Email delivery**
   - Use SMTP, Gmail, Outlook, SendGrid, or another email node.
   - To: `{{$json.email}}`
   - Subject: `Case update: {{$json.case_number}}`
   - Body: `{{$json.message}}`
5. **Respond to Webhook**
   - Return HTTP `200` only after the selected provider branches have accepted
     the message.
   - Example response: `{"accepted": true}`

The incoming JSON includes:

```json
{
  "event": "vakil_case_notification",
  "case_id": "uuid",
  "case_number": "CASE-123",
  "case_title": "Example matter",
  "case_status": "Hearing",
  "court_name": "Example Court",
  "next_hearing_date": "2026-09-15",
  "client_id": "uuid",
  "client_name": "Client Name",
  "whatsapp_number": "+919999999999",
  "email": "client@example.com",
  "channels": ["whatsapp", "email"],
  "message": "The editable message from the app"
}
```

Add the production webhook URL to Streamlit Secrets:

```toml
N8N_VAKIL_NOTIFICATION_WEBHOOK_URL = "https://YOUR-N8N-HOST/webhook/vakil-notification"
```

## Workflow 2: automatic hearing reminders

The app can send messages manually from the **Notifications** tab. For alerts
that run while nobody has the app open, create a second n8n workflow:

1. Add a **Schedule Trigger** that runs daily in the required timezone.
2. Query Supabase `vakil_cases` for open cases whose `next_hearing_date` is
   today, tomorrow, or another chosen reminder window.
3. Join each row to `vakil_clients` using `client_id`.
4. Exclude a recipient when its phone/email is blank.
5. Build a hearing reminder message and send it through the same WhatsApp and
   email branches used above.
6. Insert the result into `vakil_notification_log` so the same case, channel,
   recipient, and reminder date are not sent twice.

Store Supabase and messaging-provider credentials in n8n Credentials, never in
workflow text, GitHub, or browser-visible fields.
