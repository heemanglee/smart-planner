"""DynamoDB client and table management."""

import boto3
from botocore.exceptions import ClientError

from app.config import settings


def get_dynamodb_client():
    """Get DynamoDB client."""
    return boto3.client(
        "dynamodb",
        endpoint_url=settings.dynamodb_endpoint_url,
        region_name=settings.aws_region,
        aws_access_key_id=settings.aws_access_key_id,
        aws_secret_access_key=settings.aws_secret_access_key,
    )


def get_dynamodb_resource():
    """Get DynamoDB resource."""
    return boto3.resource(
        "dynamodb",
        endpoint_url=settings.dynamodb_endpoint_url,
        region_name=settings.aws_region,
        aws_access_key_id=settings.aws_access_key_id,
        aws_secret_access_key=settings.aws_secret_access_key,
    )


def create_sessions_table() -> bool:
    """Create sessions table if not exists.

    Returns:
        True if table was created or already exists, False on error.
    """
    client = get_dynamodb_client()
    table_name = settings.dynamodb_table_name

    try:
        client.describe_table(TableName=table_name)
        return True
    except ClientError as e:
        if e.response["Error"]["Code"] != "ResourceNotFoundException":
            return False

    try:
        client.create_table(
            TableName=table_name,
            KeySchema=[
                {"AttributeName": "id", "KeyType": "HASH"},
            ],
            AttributeDefinitions=[
                {"AttributeName": "id", "AttributeType": "S"},
            ],
            BillingMode="PAY_PER_REQUEST",
        )
        waiter = client.get_waiter("table_exists")
        waiter.wait(TableName=table_name)
        return True
    except ClientError:
        return False


def test_connection() -> bool:
    """Test DynamoDB connection.

    Returns:
        True if connection is successful, False otherwise.
    """
    try:
        client = get_dynamodb_client()
        client.list_tables()
        return True
    except Exception:
        return False


def get_table():
    """Get sessions table resource."""
    resource = get_dynamodb_resource()
    return resource.Table(settings.dynamodb_table_name)