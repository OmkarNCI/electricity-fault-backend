# setup_sns.py - AWS SNS Configuration Helper for Electricity Grid Alerts

import argparse
import json
import sys
from datetime import datetime, UTC

try:
    import boto3
    from botocore.exceptions import BotoCoreError, ClientError
except ImportError:
    print("ERROR: boto3 is required. Install with: pip install boto3")
    sys.exit(1)


class SNSConfigHelper:
    """Helper class for SNS configuration and testing."""

    def __init__(self, region="us-east-1"):
        """Initialize SNS client."""
        self.region = region
        try:
            self.sns_client = boto3.client("sns", region_name=region)
            print(f"✓ Connected to SNS in region: {region}")
        except Exception as e:
            print(f"✗ Failed to connect to AWS: {e}")
            print("  Make sure AWS credentials are configured: aws configure")
            sys.exit(1)

    def create_topic(self, topic_name="electricity-area-pole-alerts"):
        """Create SNS topic for alerts."""
        try:
            print(f"\n📌 Creating SNS topic: {topic_name}")
            response = self.sns_client.create_topic(Name=topic_name)
            topic_arn = response["TopicArn"]
            print(f"✓ Topic created successfully")
            print(f"  Topic ARN: {topic_arn}")
            print(f"\n⚠️  Copy this ARN to config/settings.yaml:")
            print(f"  sns_topic_arn: \"{topic_arn}\"")
            return topic_arn
        except ClientError as e:
            if e.response["Error"]["Code"] == "TopicLimitExceeded":
                print("✗ Topic limit exceeded. List existing topics.")
                return None
            raise

    def list_topics(self):
        """List all SNS topics."""
        try:
            print("\n🔍 Listing all SNS topics:")
            response = self.sns_client.list_topics()
            topics = response.get("Topics", [])
            
            if not topics:
                print("  No topics found")
                return []
            
            for topic in topics:
                print(f"  • {topic['TopicArn']}")
            return topics
        except Exception as e:
            print(f"✗ Failed to list topics: {e}")
            return []

    def subscribe_email(self, topic_arn, email):
        """Subscribe email address to SNS topic."""
        try:
            print(f"\n📧 Subscribing email: {email}")
            response = self.sns_client.subscribe(
                TopicArn=topic_arn,
                Protocol="email",
                Endpoint=email,
                Attributes={"FilterPolicy": json.dumps({})}
            )
            subscription_arn = response["SubscriptionArn"]
            print(f"✓ Subscription created")
            print(f"  Subscription ARN: {subscription_arn}")
            print(f"\n⚠️  Check email ({email}) for confirmation link")
            print(f"  Click the link to activate email alerts")
            return subscription_arn
        except ClientError as e:
            print(f"✗ Failed to subscribe: {e}")
            return None

    def list_subscriptions(self, topic_arn=None):
        """List subscriptions for a topic."""
        try:
            print(f"\n👥 Listing subscriptions")
            if topic_arn:
                print(f"  Topic: {topic_arn}")
                response = self.sns_client.list_subscriptions_by_topic(TopicArn=topic_arn)
            else:
                response = self.sns_client.list_subscriptions()
            
            subscriptions = response.get("Subscriptions", [])
            
            if not subscriptions:
                print("  No subscriptions found")
                return subscriptions
            
            for sub in subscriptions:
                status = "✓ Active" if sub["SubscriptionArn"] != "PendingConfirmation" else "⏳ Pending"
                protocol = sub["Protocol"].ljust(10)
                endpoint = sub["Endpoint"][:40].ljust(40)
                print(f"  {status} | {protocol} | {endpoint}")
            
            return subscriptions
        except Exception as e:
            print(f"✗ Failed to list subscriptions: {e}")
            return []

    def get_topic_arn_by_name(self, topic_name):
        """Find topic ARN by name."""
        try:
            topics = self.sns_client.list_topics()["Topics"]
            for topic in topics:
                if topic_name in topic["TopicArn"]:
                    return topic["TopicArn"]
            return None
        except Exception as e:
            print(f"✗ Failed to find topic: {e}")
            return None


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="AWS SNS Configuration Helper for Electricity Grid Alerts",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Create a new SNS topic and subscribe an email address
  python setup_sns.py --create-topic --email ops@example.com
  
  # Display all existing SNS topics in the AWS region
  python setup_sns.py --list-topics
  
  # View all subscriptions for a specific SNS topic
  python setup_sns.py --list-subscriptions --topic-arn arn:aws:sns:us-east-1:123456789:electricity-grid-alerts
  
  # Send a test alert notification to verify SNS connectivity
  python setup_sns.py --test-alert --topic-arn arn:aws:sns:us-east-1:123456789:electricity-grid-alerts
        """
    )
    
    parser.add_argument(
        "--region",
        default="us-east-1",
        help="AWS region (default: us-east-1)"
    )
    parser.add_argument(
        "--create-topic",
        action="store_true",
        help="Create new SNS topic"
    )
    parser.add_argument(
        "--topic-name",
        default="electricity-grid-alerts",
        help="Name for new topic (default: electricity-grid-alerts)"
    )
    parser.add_argument(
        "--email",
        help="Email address to subscribe"
    )
    parser.add_argument(
        "--topic-arn",
        help="SNS Topic ARN (required for subscribe, list-subscriptions, test-alert)"
    )
    parser.add_argument(
        "--list-topics",
        action="store_true",
        help="List all SNS topics"
    )
    parser.add_argument(
        "--list-subscriptions",
        action="store_true",
        help="List subscriptions (requires --topic-arn)"
    )
    parser.add_argument(
        "--area",
        default="AREA_2",
        help="Area ID for test alert (default: AREA_2)"
    )
    parser.add_argument(
        "--pole",
        default="P1",
        help="Pole ID for test alert (default: P1)"
    )
    
    args = parser.parse_args()
    
    # Create the SNS helper instance
    helper = SNSConfigHelper(region=args.region)
    
    # Execute the requested command
    if args.create_topic:
        topic_arn = helper.create_topic(args.topic_name)
        if topic_arn and args.email:
            helper.subscribe_email(topic_arn, args.email)
    
    elif args.list_topics:
        helper.list_topics()
    
    elif args.list_subscriptions:
        if not args.topic_arn:
            print("✗ --topic-arn is required for --list-subscriptions")
            sys.exit(1)
        helper.list_subscriptions(args.topic_arn)
    
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
