import os
import resend

SENDER_EMAIL = os.getenv("RESEND_SENDER_EMAIL", "bridge-no-reply@icu.584743.xyz")


def send_email(to: list[str], subject: str, html: str):
    if not to:
        return
    api_key = os.getenv("RESEND_API_KEY")
    if not api_key:
        raise RuntimeError("RESEND_API_KEY not configured")
    resend.api_key = api_key
    resend.Emails.send({
        "from": SENDER_EMAIL,
        "to": to,
        "subject": subject,
        "html": html,
    })
