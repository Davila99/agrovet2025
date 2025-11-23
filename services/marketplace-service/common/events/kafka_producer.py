"""
Kafka producer for publishing events between microservices.
"""
import json
import logging
import os
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

# Try to import confluent_kafka, fallback to mock if not available
try:
    from confluent_kafka import Producer
    KAFKA_AVAILABLE = True
except ImportError:
    logger.warning("confluent_kafka not installed. Events will be logged only.")
    KAFKA_AVAILABLE = False
    Producer = None


class KafkaEventProducer:
    """
    Producer for publishing events to Kafka topics.
    Falls back to logging if Kafka is not configured.
    """
    
    def __init__(self):
        self.bootstrap_servers = os.getenv('KAFKA_BOOTSTRAP_SERVERS', 'localhost:9092')
        self.producer = None
        
        if KAFKA_AVAILABLE and self.bootstrap_servers:
            try:
                self.producer = Producer({
                    'bootstrap.servers': self.bootstrap_servers,
                    'client.id': 'agrovet-producer',
                    'acks': 'all',  # Wait for all replicas
                    'retries': 3,
                })
                logger.info(f"Kafka producer initialized: {self.bootstrap_servers}")
            except Exception as e:
                logger.error(f"Failed to initialize Kafka producer: {e}")
                self.producer = None
    
    def publish(self, topic: str, event_type: str, data: Dict[str, Any], key: Optional[str] = None):
        """
        Publish an event to a Kafka topic.
        
        Args:
            topic: Kafka topic name (e.g., 'user.events', 'marketplace.events')
            event_type: Type of event (e.g., 'user.created', 'order.placed')
            data: Event payload
            key: Optional partition key
        """
        event = {
            'type': event_type,
            'timestamp': self._get_timestamp(),
            'data': data
        }
        
        message = json.dumps(event).encode('utf-8')
        
        if self.producer:
            try:
                self.producer.produce(
                    topic,
                    message,
                    key=key.encode('utf-8') if key else None,
                    callback=self._delivery_callback
                )
                self.producer.poll(0)  # Trigger delivery callbacks
                logger.info(f"Published event {event_type} to {topic}")
            except Exception as e:
                logger.error(f"Failed to publish event to {topic}: {e}")
        else:
            # Fallback: log the event
            logger.info(f"[KAFKA MOCK] Would publish to {topic}: {event_type} - {json.dumps(data)}")
    
    def _delivery_callback(self, err, msg):
        """Callback for message delivery confirmation."""
        if err:
            logger.error(f"Message delivery failed: {err}")
        else:
            logger.debug(f"Message delivered to {msg.topic()} [{msg.partition()}]")
    
    def _get_timestamp(self):
        """Get current timestamp in ISO format."""
        from datetime import datetime
        return datetime.utcnow().isoformat() + 'Z'
    
    def flush(self):
        """Flush pending messages."""
        if self.producer:
            self.producer.flush()


# Global producer instance
_producer_instance = None


def get_producer() -> KafkaEventProducer:
    """Get or create the global Kafka producer instance."""
    global _producer_instance
    if _producer_instance is None:
        _producer_instance = KafkaEventProducer()
    return _producer_instance


# Convenience functions for common events
def publish_user_event(event_type: str, user_id: int, data: Dict[str, Any]):
    """Publish a user-related event."""
    get_producer().publish('user.events', event_type, {'user_id': user_id, **data}, key=str(user_id))


def publish_marketplace_event(event_type: str, data: Dict[str, Any]):
    """Publish a marketplace-related event."""
    get_producer().publish('marketplace.events', event_type, data)


def publish_media_event(event_type: str, media_id: int, data: Dict[str, Any]):
    """Publish a media-related event."""
    get_producer().publish('media.events', event_type, {'media_id': media_id, **data}, key=str(media_id))


def publish_chat_event(event_type: str, data: Dict[str, Any]):
    """Publish a chat-related event."""
    get_producer().publish('chat.events', event_type, data)


def publish_foro_event(event_type: str, data: Dict[str, Any]):
    """Publish a foro-related event."""
    get_producer().publish('foro.events', event_type, data)

