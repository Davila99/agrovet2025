#!/usr/bin/env python3
"""
Script to create Kafka topics for event-driven architecture.
Run this after starting Kafka in docker-compose.
"""
import os
import subprocess
import sys

KAFKA_BOOTSTRAP_SERVERS = os.getenv('KAFKA_BOOTSTRAP_SERVERS', 'localhost:9092')

# Topics to create
TOPICS = [
    {
        'name': 'user.events',
        'partitions': 3,
        'replication_factor': 1,
        'description': 'User lifecycle events (created, updated, deleted)'
    },
    {
        'name': 'marketplace.events',
        'partitions': 3,
        'replication_factor': 1,
        'description': 'Marketplace events (add created, order placed, etc.)'
    },
    {
        'name': 'media.events',
        'partitions': 3,
        'replication_factor': 1,
        'description': 'Media upload/delete events'
    },
    {
        'name': 'chat.events',
        'partitions': 3,
        'replication_factor': 1,
        'description': 'Chat events (message sent, room created, etc.)'
    },
    {
        'name': 'foro.events',
        'partitions': 3,
        'replication_factor': 1,
        'description': 'Foro events (post created, comment added, etc.)'
    },
    {
        'name': 'profiles.events',
        'partitions': 3,
        'replication_factor': 1,
        'description': 'Profile events (profile created, updated)'
    },
]

def create_topic(name, partitions, replication_factor):
    """Create a Kafka topic."""
    cmd = [
        'kafka-topics',
        '--create',
        '--bootstrap-server', KAFKA_BOOTSTRAP_SERVERS,
        '--topic', name,
        '--partitions', str(partitions),
        '--replication-factor', str(replication_factor),
        '--if-not-exists'
    ]
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        print(f"✅ Created topic: {name}")
        return True
    except subprocess.CalledProcessError as e:
        if "already exists" in e.stderr.lower():
            print(f"ℹ️  Topic already exists: {name}")
            return True
        else:
            print(f"❌ Failed to create topic {name}: {e.stderr}")
            return False
    except FileNotFoundError:
        print("❌ kafka-topics command not found. Make sure Kafka is installed or run this inside Kafka container.")
        print(f"   To run inside container: docker exec -it kafka-agrovet kafka-topics --create ...")
        return False

def list_topics():
    """List all existing topics."""
    cmd = [
        'kafka-topics',
        '--list',
        '--bootstrap-server', KAFKA_BOOTSTRAP_SERVERS
    ]
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        topics = [t.strip() for t in result.stdout.strip().split('\n') if t.strip()]
        return topics
    except Exception as e:
        print(f"⚠️  Could not list topics: {e}")
        return []

def main():
    print("🚀 Creating Kafka topics for Agrovet microservices...")
    print(f"   Bootstrap servers: {KAFKA_BOOTSTRAP_SERVERS}\n")
    
    # List existing topics
    existing = list_topics()
    if existing:
        print(f"📋 Existing topics: {', '.join(existing)}\n")
    
    # Create topics
    success_count = 0
    for topic in TOPICS:
        if create_topic(topic['name'], topic['partitions'], topic['replication_factor']):
            success_count += 1
    
    print(f"\n✅ Created/verified {success_count}/{len(TOPICS)} topics")
    print("\n📝 Topics created:")
    for topic in TOPICS:
        print(f"   - {topic['name']}: {topic['description']}")

if __name__ == '__main__':
    main()

