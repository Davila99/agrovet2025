from django.shortcuts import render


def demo_view(request):
	"""Render a minimal demo page used for manual WebSocket testing.

	The page is intentionally simple: paste a DRF token and room id and
	open a WebSocket connection to /ws/chat/<room_id>/?token=<token>
	"""
	return render(request, 'chat/demo.html')


def test_client_view(request):
	"""Render the richer test client used to exercise login, room creation, uploads and WS."""
	return render(request, 'chat/test_client.html')
