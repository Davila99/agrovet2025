import json
from unittest import mock
from rest_framework import status
from rest_framework.test import APIRequestFactory
from .api.views import AddViewSet
from .models import Add, Category

def create_category():
    return Category.objects.create(name="Test Category")

class AddViewSetTests(unittest.TestCase):
    def setUp(self):
        self.factory = APIRequestFactory()
        self.category = create_category()
        self.payload = {
            "title": "Test Add",
            "description": "Descripción del anuncio",
            "price": 100,
            "category": self.category.id,
            "condition": "new",
            "status": "active",
            "latitude": -34.6037,
            "longitude": -58.3816,
        }
        self.fake_token = "fake-token-123"

    @mock.patch("common.http_clients.auth_client.get_auth_client")
    @mock.patch("common.events.kafka_producer.get_producer")
    def test_create_add_with_valid_token(self, mock_producer, mock_auth_client):
        # Mock auth client
        mock_auth_instance = mock.Mock()
        mock_auth_instance.verify_token.return_value = {"id": 42, "username": "testuser"}
        mock_auth_client.return_value = mock_auth_instance
        # Mock producer
        mock_producer_instance = mock.Mock()
        mock_producer.return_value = mock_producer_instance
        # Build request (use direct path to avoid reverse issues)
        request = self.factory.post(
            "/adds/",
            data=json.dumps(self.payload),
            content_type="application/json",
        )
        request.META["HTTP_AUTHORIZATION"] = f"Token {self.fake_token}"
        # Call view
        view = AddViewSet.as_view({"post": "create"})
        response = view(request)
        # Assertions
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        add_obj = Add.objects.get(title="Test Add")
        self.assertEqual(add_obj.publisher_id, 42)
        mock_auth_instance.verify_token.assert_called_once_with(self.fake_token)
        mock_producer_instance.publish.assert_called_once()
        args, kwargs = mock_producer_instance.publish.call_args
        self.assertEqual(args[0], "marketplace.events")
        self.assertEqual(args[1], "add.created")
        self.assertIn("add_id", args[2])
        self.assertIn("publisher_id", args[2])
        self.assertIn("title", args[2])
