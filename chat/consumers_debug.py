import json
from channels.generic.websocket import AsyncWebsocketConsumer

class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        # El room_id viene desde la URL /ws/chat/<room_id>/
        self.room_id = self.scope['url_route']['kwargs']['room_id']
        self.group_name = f"chat_{self.room_id}"

        # Agregar al grupo del room
        await self.channel_layer.group_add(
            self.group_name,
            self.channel_name
        )

        await self.accept()

        # 🔹 Log cuando alguien se conecta
        print(f"[WS][CONNECT] ✅ {self.channel_name} conectado al room {self.room_id}")

    async def disconnect(self, close_code):
        # Remover del grupo
        await self.channel_layer.group_discard(
            self.group_name,
            self.channel_name
        )
        print(f"[WS][DISCONNECT] ❌ {self.channel_name} salió del room {self.room_id}")

    async def receive(self, text_data):
        """Cuando el cliente envía un mensaje al WS"""
        try:
            data = json.loads(text_data)
        except Exception:
            print(f"[WS][ERROR] ❗ Mensaje no es JSON válido: {text_data}")
            return

        print(f"[WS][RECEIVE] 📩 Room {self.room_id} recibió de {self.channel_name}: {data}")

        msg_type = data.get("type")

        # Cuando el mensaje es del tipo chat.message
        if msg_type == "chat.message":
            print(f"[WS][MESSAGE] 💬 Mensaje nuevo en room {self.room_id}: {data}")

            # Reenviar (broadcast) a todos los conectados al mismo grupo
            await self.channel_layer.group_send(
                self.group_name,
                {
                    "type": "chat_message",
                    "message": data,
                }
            )

        elif msg_type == "mark_read":
            print(f"[WS][MARK_READ] 👁‍🗨 Mark read recibido en room {self.room_id} de {self.channel_name}")

        else:
            print(f"[WS][UNKNOWN] ❓ Tipo de mensaje desconocido: {msg_type}")

    async def chat_message(self, event):
        """Este método se ejecuta cuando otro cliente recibe el mensaje"""
        message = event["message"]

        print(f"[WS][SEND] 📤 Enviando a cliente {self.channel_name} en room {self.room_id}: {message}")

        await self.send(text_data=json.dumps(message))
