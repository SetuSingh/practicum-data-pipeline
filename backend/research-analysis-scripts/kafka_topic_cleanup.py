"""
Kafka Topic Cleanup Utility
Clears messages from all topics used in the optimized stream processing analysis

This utility provides methods to:
- Delete and recreate topics (full cleanup)
- Clear messages from topics without deleting them
- Reset consumer group offsets
- Manage topic lifecycle for research experiments

Usage:
    python kafka_topic_cleanup.py [--delete-topics] [--reset-offsets] [--recreate-topics]
"""

import sys
import os
import time
import argparse
from typing import Dict, List, Any, Optional
from kafka import KafkaAdminClient, KafkaConsumer, KafkaProducer
from kafka.admin import NewTopic, ConfigResource, ConfigResourceType
from kafka.errors import TopicAlreadyExistsError, UnknownTopicOrPartitionError
from kafka.structs import TopicPartition, OffsetAndMetadata

# Add paths for imports
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

class KafkaTopicCleanup:
    """Utility for cleaning up Kafka topics used in stream processing research"""
    
    def __init__(self, kafka_servers: List[str] = None):
        self.kafka_servers = kafka_servers or ['localhost:9093']
        self.predefined_topics = self._generate_predefined_topics()
        self.consumer_groups = self._generate_consumer_groups()
        
        print(f"🔧 Kafka Topic Cleanup Utility")
        print(f"🔌 Kafka servers: {self.kafka_servers}")
        print(f"📝 Managing {len(self.predefined_topics)} topics")
        print(f"👥 Managing {len(self.consumer_groups)} consumer groups")
    
    def _generate_predefined_topics(self) -> List[str]:
        """Generate list of all predefined topics"""
        topics = []
        dataset_types = ['healthcare', 'financial']
        dataset_sizes = [500, 1000, 2500, 5000, 10000]
        
        for data_type in dataset_types:
            for size in dataset_sizes:
                topics.append(f"{data_type}_{size}")
        
        return topics
    
    def _generate_consumer_groups(self) -> List[str]:
        """Generate list of all consumer groups"""
        consumer_groups = []
        
        # Configuration suffixes
        config_suffixes = [
            'k_3', 'k_5', 'k_10', 'k_15',  # K-anonymity
            'dp_0_1', 'dp_0_5', 'dp_1_0', 'dp_2_0',  # Differential privacy
            'token_128', 'token_256', 'token_512'  # Tokenization
        ]
        
        dataset_types = ['healthcare', 'financial']
        dataset_sizes = [500, 1000, 2500, 5000, 10000]
        
        for config_suffix in config_suffixes:
            for data_type in dataset_types:
                for size in dataset_sizes:
                    consumer_groups.append(f"{config_suffix}_{data_type}_{size}")
        
        return consumer_groups
    
    def check_kafka_connectivity(self) -> bool:
        """Check if Kafka is accessible"""
        try:
            admin_client = KafkaAdminClient(
                bootstrap_servers=self.kafka_servers,
                client_id="cleanup-connectivity-test",
                request_timeout_ms=10000
            )
            
            # Try to list topics to verify connectivity
            existing_topics = admin_client.list_topics()
            admin_client.close()
            
            print("✅ Kafka connectivity verified")
            return True
            
        except Exception as e:
            print(f"❌ Kafka connectivity failed: {str(e)}")
            return False
    
    def list_existing_topics(self) -> List[str]:
        """List all existing topics in Kafka"""
        try:
            admin_client = KafkaAdminClient(
                bootstrap_servers=self.kafka_servers,
                client_id="topic-lister"
            )
            
            # Get topic metadata
            existing_topics = admin_client.list_topics()
            admin_client.close()
            
            # Filter for our research topics
            research_topics = [topic for topic in existing_topics if topic in self.predefined_topics]
            
            print(f"📋 Found {len(research_topics)} research topics out of {len(existing_topics)} total topics")
            return research_topics
            
        except Exception as e:
            print(f"❌ Failed to list topics: {str(e)}")
            return []
    
    def delete_topics(self, topics: List[str] = None) -> bool:
        """Delete specified topics or all predefined topics"""
        topics_to_delete = topics or self.predefined_topics
        
        print(f"🗑️  Deleting {len(topics_to_delete)} topics...")
        
        try:
            admin_client = KafkaAdminClient(
                bootstrap_servers=self.kafka_servers,
                client_id="topic-deleter"
            )
            
            # kafka-python >=2 returns DeleteTopicsResponse, not dict of futures
            try:
                admin_client.delete_topics(topics_to_delete, timeout_ms=30000)
                print("✅ Delete request sent to broker")
            except UnknownTopicOrPartitionError:
                print("ℹ️  One or more topics already absent – continuing")
            except Exception as req_err:
                print(f"❌ Delete request failed: {req_err}")
                admin_client.close()
                return False
            
            admin_client.close()
            print("✅ Topic deletion completed")
            return True
            
        except Exception as e:
            print(f"❌ Failed to delete topics: {str(e)}")
            return False
    
    def create_topics(self, topics: List[str] = None) -> bool:
        """Create specified topics or all predefined topics"""
        topics_to_create = topics or self.predefined_topics
        
        print(f"📝 Creating {len(topics_to_create)} topics...")
        
        try:
            admin_client = KafkaAdminClient(
                bootstrap_servers=self.kafka_servers,
                client_id="topic-creator"
            )
            
            new_topics = [NewTopic(name=t, num_partitions=1, replication_factor=1) for t in topics_to_create]
            try:
                admin_client.create_topics(new_topics, timeout_ms=30000)
                print("✅ Topic creation request sent to broker")
            except TopicAlreadyExistsError:
                print("ℹ️  Some topics already exist – skipping duplicates")
            except Exception as req_err:
                print(f"❌ Topic creation failed: {req_err}")
                admin_client.close()
                return False
            
            admin_client.close()
            print("✅ Topic creation completed")
            return True
            
        except Exception as e:
            print(f"❌ Failed to create topics: {str(e)}")
            return False
    
    def recreate_topics(self, topics: List[str] = None) -> bool:
        """Delete and recreate topics (full cleanup)"""
        topics_to_recreate = topics or self.predefined_topics
        
        print(f"🔄 Recreating {len(topics_to_recreate)} topics...")
        
        # Delete topics first
        if self.delete_topics(topics_to_recreate):
            # Wait a moment for deletion to propagate
            time.sleep(5)
            
            # Create topics again
            return self.create_topics(topics_to_recreate)
        
        return False
    
    def clear_topic_messages(self, topic: str) -> bool:
        """Clear all messages from a specific topic by consuming all messages"""
        print(f"🧹 Clearing messages from topic: {topic}")
        
        try:
            # Create consumer to consume all messages
            consumer = KafkaConsumer(
                topic,
                bootstrap_servers=self.kafka_servers,
                auto_offset_reset='earliest',
                enable_auto_commit=True,
                group_id=f"cleanup-{topic}-{int(time.time())}",
                consumer_timeout_ms=10000  # 10 second timeout
            )
            
            message_count = 0
            for message in consumer:
                message_count += 1
                if message_count % 1000 == 0:
                    print(f"  📤 Consumed {message_count} messages...")
            
            consumer.close()
            print(f"  ✅ Cleared {message_count} messages from {topic}")
            return True
            
        except Exception as e:
            print(f"  ❌ Failed to clear messages from {topic}: {str(e)}")
            return False
    
    def clear_all_topic_messages(self) -> bool:
        """Clear messages from all predefined topics"""
        print(f"🧹 Clearing messages from all {len(self.predefined_topics)} topics...")
        
        success_count = 0
        for topic in self.predefined_topics:
            if self.clear_topic_messages(topic):
                success_count += 1
        
        print(f"✅ Successfully cleared {success_count}/{len(self.predefined_topics)} topics")
        return success_count == len(self.predefined_topics)
    
    def reset_consumer_group_offsets(self, consumer_group: str, topics: List[str] = None) -> bool:
        """Reset consumer group offsets to earliest for specified topics"""
        topics_to_reset = topics or self.predefined_topics
        
        print(f"🔄 Resetting consumer group '{consumer_group}' offsets for {len(topics_to_reset)} topics...")
        
        try:
            admin_client = KafkaAdminClient(
                bootstrap_servers=self.kafka_servers,
                client_id="offset-resetter"
            )
            
            # Create consumer to reset offsets
            consumer = KafkaConsumer(
                *topics_to_reset,
                bootstrap_servers=self.kafka_servers,
                group_id=consumer_group,
                auto_offset_reset='earliest',
                enable_auto_commit=False
            )
            
            # Get topic partitions
            partitions = []
            for topic in topics_to_reset:
                topic_partitions = consumer.partitions_for_topic(topic)
                if topic_partitions:
                    for partition in topic_partitions:
                        partitions.append(TopicPartition(topic, partition))
            
            # Reset offsets to earliest
            consumer.seek_to_beginning(*partitions)
            
            # Commit the reset offsets
            offset_dict = {}
            for partition in partitions:
                offset_dict[partition] = OffsetAndMetadata(0, None)
            
            consumer.commit(offset_dict)
            consumer.close()
            admin_client.close()
            
            print(f"  ✅ Reset offsets for consumer group: {consumer_group}")
            return True
            
        except Exception as e:
            print(f"  ❌ Failed to reset offsets for {consumer_group}: {str(e)}")
            return False
    
    def reset_all_consumer_group_offsets(self) -> bool:
        """Reset all consumer group offsets"""
        print(f"🔄 Resetting all {len(self.consumer_groups)} consumer group offsets...")
        
        success_count = 0
        for consumer_group in self.consumer_groups:
            if self.reset_consumer_group_offsets(consumer_group):
                success_count += 1
        
        print(f"✅ Successfully reset {success_count}/{len(self.consumer_groups)} consumer groups")
        return success_count == len(self.consumer_groups)
    
    def full_cleanup(self) -> bool:
        """Perform full cleanup: recreate topics and reset consumer group offsets"""
        print("\n🧹 PERFORMING FULL CLEANUP")
        print("="*40)
        
        # Step 1: Recreate topics (deletes all messages)
        if not self.recreate_topics():
            print("❌ Failed to recreate topics")
            return False
        
        # Step 2: Reset consumer group offsets (optional, since topics were recreated)
        print("\n🔄 Resetting consumer group offsets...")
        self.reset_all_consumer_group_offsets()
        
        print("\n✅ Full cleanup completed successfully!")
        return True
    
    def light_cleanup(self) -> bool:
        """Perform light cleanup: clear messages without recreating topics"""
        print("\n🧹 PERFORMING LIGHT CLEANUP")
        print("="*40)
        
        # Step 1: Clear messages from all topics
        if not self.clear_all_topic_messages():
            print("❌ Failed to clear topic messages")
            return False
        
        # Step 2: Reset consumer group offsets
        if not self.reset_all_consumer_group_offsets():
            print("❌ Failed to reset consumer group offsets")
            return False
        
        print("\n✅ Light cleanup completed successfully!")
        return True
    
    def get_cleanup_status(self) -> Dict[str, Any]:
        """Get current cleanup status"""
        existing_topics = self.list_existing_topics()
        
        return {
            'predefined_topics': self.predefined_topics,
            'existing_topics': existing_topics,
            'missing_topics': [t for t in self.predefined_topics if t not in existing_topics],
            'consumer_groups': self.consumer_groups,
            'topics_count': len(self.predefined_topics),
            'existing_topics_count': len(existing_topics),
            'consumer_groups_count': len(self.consumer_groups)
        }


def main():
    """Main function for Kafka topic cleanup utility"""
    parser = argparse.ArgumentParser(description='Kafka Topic Cleanup Utility for Stream Processing Research')
    parser.add_argument('--delete-topics', action='store_true', help='Delete all research topics')
    parser.add_argument('--create-topics', action='store_true', help='Create all research topics')
    parser.add_argument('--recreate-topics', action='store_true', help='Delete and recreate all topics')
    parser.add_argument('--clear-messages', action='store_true', help='Clear messages from all topics')
    parser.add_argument('--reset-offsets', action='store_true', help='Reset consumer group offsets')
    parser.add_argument('--full-cleanup', action='store_true', help='Perform full cleanup (recreate topics + reset offsets)')
    parser.add_argument('--light-cleanup', action='store_true', help='Perform light cleanup (clear messages + reset offsets)')
    parser.add_argument('--status', action='store_true', help='Show cleanup status')
    parser.add_argument('--list-topics', action='store_true', help='List existing topics')
    parser.add_argument('--kafka-servers', default='localhost:9093', help='Kafka server addresses')
    
    args = parser.parse_args()
    
    # Parse Kafka servers
    kafka_servers = [server.strip() for server in args.kafka_servers.split(',')]
    
    # Initialize cleanup utility
    cleanup = KafkaTopicCleanup(kafka_servers)
    
    # Check Kafka connectivity
    if not cleanup.check_kafka_connectivity():
        print("❌ Cannot connect to Kafka. Please ensure Kafka is running.")
        return
    
    # Execute requested actions
    if args.status:
        status = cleanup.get_cleanup_status()
        print(f"\n📊 CLEANUP STATUS")
        print(f"  • Predefined topics: {status['topics_count']}")
        print(f"  • Existing topics: {status['existing_topics_count']}")
        print(f"  • Missing topics: {len(status['missing_topics'])}")
        print(f"  • Consumer groups: {status['consumer_groups_count']}")
        if status['missing_topics']:
            print(f"  • Missing: {status['missing_topics']}")
    
    elif args.list_topics:
        existing_topics = cleanup.list_existing_topics()
        print(f"\n📋 EXISTING RESEARCH TOPICS ({len(existing_topics)}):")
        for topic in existing_topics:
            print(f"  • {topic}")
    
    elif args.delete_topics:
        cleanup.delete_topics()
    
    elif args.create_topics:
        cleanup.create_topics()
    
    elif args.recreate_topics:
        cleanup.recreate_topics()
    
    elif args.clear_messages:
        cleanup.clear_all_topic_messages()
    
    elif args.reset_offsets:
        cleanup.reset_all_consumer_group_offsets()
    
    elif args.full_cleanup:
        cleanup.full_cleanup()
    
    elif args.light_cleanup:
        cleanup.light_cleanup()
    
    else:
        print("ℹ️  No action specified. Use --help for available options.")
        print("\nQuick actions:")
        print("  • --status              : Show current status")
        print("  • --full-cleanup        : Complete cleanup (recreate topics + reset offsets)")
        print("  • --light-cleanup       : Light cleanup (clear messages + reset offsets)")
        print("  • --list-topics         : List existing topics")


if __name__ == "__main__":
    main() 