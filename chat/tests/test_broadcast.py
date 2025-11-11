import pytest
from channels.layers import get_channel_layer
from chat.utils.broadcast import safe_group_send_sync
from chat.models import BroadcastRetry


@pytest.mark.django_db
def test_safe_group_send_persists_retry(monkeypatch):
    class DummyLayer:
        def group_send(self, group_name, payload):
            raise ConnectionRefusedError('simulated connection refused')

    monkeypatch.setattr('chat.utils.broadcast.get_channel_layer', lambda: DummyLayer())

    # Ensure no retries before
    assert BroadcastRetry.objects.count() == 0

    result = safe_group_send_sync('chat_1', {'type': 'chat.message', 'text': 'hi'})
    assert result is False
    # Now a BroadcastRetry should be created
    assert BroadcastRetry.objects.count() == 1
    br = BroadcastRetry.objects.first()
    assert br.group_name == 'chat_1'
    assert isinstance(br.payload, dict)
*** End Patch