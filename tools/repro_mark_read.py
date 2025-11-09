import os
import django
import sys

# Ensure project root is on sys.path so Django settings can be imported
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

# Set up Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'consultveterinarias.settings')
django.setup()

from django.contrib.auth import get_user_model
from chat.models import ChatRoom, ChatMessage, ChatMessageReceipt, get_or_create_private_chat
from chat.consumers_impl.chat_consumer import ChatConsumer
from django.utils import timezone

User = get_user_model()

# Utility: print receipts for a message

def print_receipts(msg):
    receipts = list(ChatMessageReceipt.objects.filter(message=msg))
    print(f"Message id={msg.id} content={msg.content!r}")
    for r in receipts:
        print(f"  Receipt id={r.id} user_id={r.user_id} delivered={r.delivered} delivered_at={r.delivered_at} read={r.read} read_at={r.read_at}")


# Find or create two users
users = list(User.objects.all()[:2])
if len(users) < 2:
    print('Need at least 2 users in DB to run this repro')
    sys.exit(1)

u1, u2 = users[0], users[1]
print(f"Using users: sender={u1.id} recipient={u2.id}")

# Create or get a private room
room, created = get_or_create_private_chat(u1, u2)
print(f"Room id={room.id} created={created}")

# Create a message from u1
msg = ChatMessage.objects.create(room=room, sender=u1, content='Repro test message')
print('Created message')

# Ensure receipts exist
for p in room.participants.all():
    if p.id == u1.id:
        continue
    ChatMessageReceipt.objects.get_or_create(message=msg, user=p, defaults={'delivered': False, 'read': False})

print('Receipts before mark_read:')
print_receipts(msg)

# Call consumer helper to mark all read as user u2
print('\nCalling ChatConsumer._mark_all_read as recipient user to simulate mark_read...')
affected = ChatConsumer._mark_all_read(None, room.id, u2)
print('Affected message ids returned by helper:', affected)

print('\nReceipts after mark_read:')
print_receipts(msg)

# Check aggregated ChatMessage flags
msg.refresh_from_db()
print('\nAggregated ChatMessage flags: read=%s seen=%s read_at=%s' % (msg.read, msg.seen, msg.read_at))

print('\nDone')
