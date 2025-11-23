"""
Kafka consumer for subscribing to events from other microservices.
"""
import json
import logging
import os
from typing import Callable, Dict, Any

logger = logging.getLogger(__name__)

# Try to import confluent_kafka
try:
    from confluent_kafka import Consumer, KafkaError
    KAFKA_AVAILABLE = True
except ImportError:
    logger.warning("confluent_kafka not installed. Consumer will not work.")
    KAFKA_AVAILABLE = False
    Consumer = None
    KafkaError = None


class KafkaEventConsumer:
    """
    Consumer for subscribing to Kafka topics and processing events.
    """
    
    def __init__(self, group_id: str, topics: list):
        self.bootstrap_servers = os.getenv('KAFKA_BOOTSTRAP_SERVERS', 'localhost:9092')
        self.group_id = group_id
        self.topics = topics
        self.consumer = None
        self.handlers: Dict[str, Callable] = {}
        
        if KAFKA_AVAILABLE and self.bootstrap_servers:
            try:
                self.consumer = Consumer({
                    'bootstrap.servers': self.bootstrap_servers,
                    'group.id': group_id,
                    'auto.offset.reset': 'earliest',
                    'enable.auto.commit': True,
                })
                self.consumer.subscribe(topics)
                logger.info(f"Kafka consumer initialized: group={group_id}, topics={topics}")
            except Exception as e:
                logger.error(f"Failed to initialize Kafka consumer: {e}")
                self.consumer = None
    
    def register_handler(self, event_type: str, handler: Callable[[Dict[str, Any]], None]):
        """
        Register a handler function for a specific event type.
        
        Args:
            event_type: Event type to handle (e.g., 'user.created')
            handler: Function that takes event data and processes it
        """
        self.handlers[event_type] = handler
        logger.info(f"Registered handler for event type: {event_type}")
    
    def start(self, timeout: float = 1.0):
        """
        Start consuming messages. This is a blocking call.
        Should be run in a separate thread or process.
        
        Args:
            timeout: Timeout in seconds for polling
        """
        if not self.consumer:
            logger.error("Consumer not initialized. Cannot start.")
            return
        
        logger.info(f"Starting consumer for topics: {self.topics}")
        
        try:
            while True:
                msg = self.consumer.poll(timeout)
                
                if msg is None:
                    continue
                
                if msg.error():
                    if msg.error().code() == KafkaError._PARTITION_EOF:
                        logger.debug(f"Reached end of partition {msg.partition()}")
                    else:
                        logger.error(f"Consumer error: {msg.error()}")
                    continue
                
                try:
                    # Parse message
                    event = json.loads(msg.value().decode('utf-8'))
                    event_type = event.get('type')
                    data = event.get('data', {})
                    
                    # Find and call handler
                    if event_type in self.handlers:
                        logger.info(f"Processing event: {event_type}")
                        self.handlers[event_type](data)
                    else:
                        logger.warning(f"No handler registered for event type: {event_type}")
                
                except json.JSONDecodeError as e:
                    logger.error(f"Failed to parse message: {e}")
                except Exception as e:
                    logger.error(f"Error processing message: {e}")
        
        except KeyboardInterrupt:
            logger.info("Consumer interrupted by user")
        finally:
            self.close()
    
    def close(self):
        """Close the consumer."""
        if self.consumer:
            self.consumer.close()
            logger.info("Consumer closed")

