import re
import smtplib
import requests
from django.core.mail import EmailMessage
from django.conf import settings


def enviar_correo(asunto, mensaje, destinatario, proveedor='gmail'):
    """Envía correo usando el backend configurado; fallback SMTP si falla."""
    if proveedor == 'gmail':
        config = settings.EMAIL_GMAIL
    elif proveedor == 'outlook':
        config = settings.EMAIL_OUTLOOK
    elif proveedor == 'brevo':
        config = None
    else:
        raise ValueError("Proveedor no soportado")

    default_from = getattr(settings, 'DEFAULT_FROM_EMAIL', None) or (config.get('USERNAME') if config else None)

    email = EmailMessage(
        subject=asunto,
        body=mensaje,
        from_email=default_from,
        to=[destinatario],
    )
    email.content_subtype = "plain"

    try:
        if proveedor == 'brevo':
            api_key = getattr(settings, 'BREVO_API_KEY', '')
            if api_key:
                from_email_raw = getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@example.com')
                email_match = re.search(r'<(.+?)>', from_email_raw)
                sender_email = email_match.group(1) if email_match else from_email_raw
                name_match = re.match(r'^(.+?)\s*<', from_email_raw)
                sender_name = name_match.group(1).strip() if name_match else "Burbujitas de Colores"

                payload = {
                    "sender": {"name": sender_name, "email": sender_email},
                    "to": [{"email": destinatario}],
                    "subject": asunto,
                    "textContent": mensaje,
                }
                headers = {'api-key': api_key, 'Content-Type': 'application/json'}
                resp = requests.post('https://api.sendinblue.com/v3/smtp/email', json=payload, headers=headers, timeout=10)
                if resp.status_code >= 400:
                    raise RuntimeError(f'Brevo API error: {resp.status_code} {resp.text}')
                return

        email.send(fail_silently=False)
    except Exception:
        if proveedor == 'brevo':
            raise
        try:
            with smtplib.SMTP(config['HOST'], config['PORT']) as server:
                if config.get('USE_TLS'):
                    server.starttls()
                server.login(config['USERNAME'], config['PASSWORD'])
                server.sendmail(config['USERNAME'], [destinatario], email.message().as_string())
        except Exception:
            raise
