from django.conf import settings


def send_sms_code(phone_number, code):
    """Enviar un SMS con Twilio si está disponible y configurado."""
    account_sid = getattr(settings, 'TWILIO_ACCOUNT_SID', None)
    auth_token = getattr(settings, 'TWILIO_AUTH_TOKEN', None)
    from_number = getattr(settings, 'TWILIO_PHONE_NUMBER', None)

    if not all([account_sid, auth_token, from_number]):
        print(f"[DEBUG SMS] to={phone_number} code={code}")
        return 'DEBUG'

    try:
        from twilio.rest import Client
    except Exception:
        print(f"[DEBUG SMS - twilio missing] to={phone_number} code={code}")
        return 'DEBUG'

    client = Client(account_sid, auth_token)
    message = client.messages.create(
        body=f"Tu código de recuperación es {code}",
        from_=from_number,
        to=phone_number
    )
    return getattr(message, 'sid', None)


def send_whatsapp_code(phone_number, code):
    """Enviar un mensaje de WhatsApp con Twilio (usa sandbox o número verificado)."""
    account_sid = getattr(settings, 'TWILIO_ACCOUNT_SID', None)
    auth_token = getattr(settings, 'TWILIO_AUTH_TOKEN', None)
    from_whatsapp = getattr(settings, 'TWILIO_WHATSAPP_FROM', 'whatsapp:+14155238886')  # Sandbox por defecto

    if not all([account_sid, auth_token]):
        print(f"[DEBUG WhatsApp] to={phone_number} code={code}")
        return 'DEBUG'

    try:
        from twilio.rest import Client
    except Exception:
        print(f"[DEBUG WhatsApp - twilio missing] to={phone_number} code={code}")
        return 'DEBUG'

    client = Client(account_sid, auth_token)
    message = client.messages.create(
        body=f"Tu código de verificación es {code}",
        from_=from_whatsapp,
        to=f"whatsapp:{phone_number}"
    )
    return getattr(message, 'sid', None)
