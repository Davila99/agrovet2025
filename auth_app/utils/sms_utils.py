from django.conf import settings


def send_sms_code(phone_number, code):
    """Enviar un SMS con Twilio si está disponible y configurado.

    Fallback de desarrollo: si Twilio no está instalado o faltan credenciales,
    imprime el código en la consola y devuelve 'DEBUG'. Esto evita errores
    en import-time cuando la librería no está presente.
    """
    account_sid = getattr(settings, 'TWILIO_ACCOUNT_SID', None)
    auth_token = getattr(settings, 'TWILIO_AUTH_TOKEN', None)
    from_number = getattr(settings, 'TWILIO_PHONE_NUMBER', None)

    # Si no están las credenciales, modo debug: imprimir y no intentar enviar
    if not all([account_sid, auth_token, from_number]):
        try:
            print(f"[DEBUG SMS] to={phone_number} code={code}")
        except Exception:
            pass
        return 'DEBUG'

    # Intentar import dinámico de Twilio para evitar fallo en import-time
    try:
        from twilio.rest import Client
    except Exception as exc:
        # Si Twilio no está instalado, caer a modo debug
        try:
            print(f"[DEBUG SMS - twilio missing] to={phone_number} code={code}")
        except Exception:
            pass
        return 'DEBUG'

    client = Client(account_sid, auth_token)
    message = client.messages.create(
        body=f"Tu código de recuperación es {code}",
        from_=from_number,
        to=phone_number
    )
    return getattr(message, 'sid', None)
