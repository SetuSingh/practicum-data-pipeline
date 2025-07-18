"""
Delete ALL Kafka Topics (and their data)
---------------------------------------
This utility connects to the Kafka cluster you specify (default: localhost:9093),
lists every topic currently present, and deletes them **permanently**.  
Deleting a topic also discards **all** messages stored in it, effectively giving
you a clean slate.

Usage
-----
```bash
python delete_all_kafka_topics.py               # deletes all topics on localhost:9093
python delete_all_kafka_topics.py --brokers host1:9092,host2:9092
python delete_all_kafka_topics.py --yes         # skip interactive confirmation
```

⚠️  WARNING  ⚠️
This is irreversible.  All data in every topic will be lost.  Make sure you
really want to wipe the entire cluster before running with `--yes`.
"""

import argparse
import sys
from typing import List

from kafka import KafkaAdminClient
from kafka.errors import UnknownTopicOrPartitionError


def delete_all_topics(brokers: List[str]):
    admin = KafkaAdminClient(bootstrap_servers=brokers, client_id="delete-all-topics")
    existing_topics = admin.list_topics()

    if not existing_topics:
        print("ℹ️  Cluster already has zero topics. Nothing to delete.")
        admin.close()
        return True

    print(f"🗑️  Deleting {len(existing_topics)} topics …")
    try:
        admin.delete_topics(existing_topics, timeout_ms=30000)
        print("✅  Delete request sent to broker. The broker will remove topic data in the background.")
    except UnknownTopicOrPartitionError:
        print("ℹ️  One or more topics vanished while deleting – continue.")
    except Exception as exc:
        print(f"❌  Delete request failed: {exc}")
        admin.close()
        return False

    admin.close()
    return True


def main():
    parser = argparse.ArgumentParser(description="Delete ALL Kafka topics (and their messages)")
    parser.add_argument("--brokers", default="localhost:9093", help="Comma-separated list of Kafka bootstrap servers")
    parser.add_argument("--yes", action="store_true", help="Skip interactive confirmation")
    args = parser.parse_args()

    brokers = [b.strip() for b in args.brokers.split(",") if b.strip()]
    print(f"🔌  Brokers: {brokers}")

    if not args.yes:
        confirm = input("⚠️  This will DELETE ALL TOPICS and their data. Proceed? [y/N]: ").strip().lower()
        if confirm not in {"y", "yes"}:
            print("Cancelled.")
            return

    success = delete_all_topics(brokers)
    if success:
        print("🎉  All topics deletion command executed.")
    else:
        sys.exit(1)


if __name__ == "__main__":
    main() 