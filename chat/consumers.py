"""Consumidores de WebSocket ligeros.

Este archivo expone un `TestConsumer` simple para pruebas y, además,
re-exporta los consumidores existentes para mantener compatibilidad con
el resto del proyecto.

El `TestConsumer` acepta la conexión, responde con {"message": "pong"}
al conectarse y reenvía en un campo "echo" cualquier mensaje JSON que
reciba.
"""

from channels.generic.websocket import AsyncJsonWebsocketConsumer

# Re-export de los consumidores implementados en consumers_impl si existen.
try:
    from .consumers_impl.core import ChatConsumer, PresenceConsumer  # type: ignore
except Exception:
    ChatConsumer = None
    PresenceConsumer = None


class TestConsumer(AsyncJsonWebsocketConsumer):
    """Consumer minimal para pruebas.

    Comportamiento:
    - on connect: acepta y envía {"message": "pong"}
    - on receive JSON: responde con {"echo": <contenido_recibido>}
    """

    async def connect(self):
        await self.accept()
        # Enviar pong al conectar
        await self.send_json({"message": "pong"})

    async def receive_json(self, content, **kwargs):
        # Reenviar el contenido recibido dentro del campo "echo"
        await self.send_json({"echo": content})


__all__ = ["TestConsumer", "ChatConsumer", "PresenceConsumer"]
