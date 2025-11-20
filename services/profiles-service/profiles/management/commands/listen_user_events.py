"""
Management command to listen for user.created events from Auth Service
and automatically create profiles based on user role.
"""
from django.core.management.base import BaseCommand
import sys
import os
import logging

# Add common to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../../../..'))

from common.events.kafka_consumer import KafkaEventConsumer
from profiles.models import SpecialistProfile, BusinessmanProfile, ConsumerProfile

logger = logging.getLogger(__name__)


def handle_user_created(data):
    """Handle user.created event from Auth Service."""
    user_id = data.get('user_id')
    role = data.get('role', '').lower()
    
    if not user_id:
        logger.warning("user.created event missing user_id")
        return
    
    logger.info(f"Processing user.created event: user_id={user_id}, role={role}")
    
    try:
        # Crear perfil según el role
        if role in ['specialist', 'specialista']:
            SpecialistProfile.objects.get_or_create(user_id=user_id)
            logger.info(f"Created SpecialistProfile for user_id={user_id}")
        elif role in ['businessman', 'business', 'business_owner']:
            BusinessmanProfile.objects.get_or_create(user_id=user_id)
            logger.info(f"Created BusinessmanProfile for user_id={user_id}")
        elif role in ['consumer', 'client']:
            ConsumerProfile.objects.get_or_create(user_id=user_id)
            logger.info(f"Created ConsumerProfile for user_id={user_id}")
        else:
            logger.info(f"No profile created for role={role}")
    except Exception as e:
        logger.error(f"Failed to create profile for user_id={user_id}: {e}")


class Command(BaseCommand):
    help = 'Listen for user events from Auth Service and create profiles automatically'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Starting Kafka consumer for user events...'))
        
        consumer = KafkaEventConsumer(
            group_id='profiles-service-user-consumer',
            topics=['user.events']
        )
        
        # Register handler
        consumer.register_handler('user.created', handle_user_created)
        
        # Start consuming (blocking)
        self.stdout.write(self.style.SUCCESS('Listening for user.created events...'))
        consumer.start()

