import boto3
from botocore.config import Config

# Hard-wire to DynamoDB Local; no env needed
DDB_ENDPOINT = "http://localhost:8000"
REGION = "us-east-2"

# Fake creds required even for local. seriously - you need this fake stuff.
session = boto3.Session(
    aws_access_key_id="fake",
    aws_secret_access_key="fake",
    region_name=REGION,
)

# Disable retries to fail fast if endpoint is wrong
cfg = Config(retries={"max_attempts": 1, "mode": "standard"})

dynamodb = session.resource("dynamodb", endpoint_url=DDB_ENDPOINT, config=cfg)

def main():
    table = dynamodb.create_table(
        TableName="bruce-quotes",
        BillingMode="PAY_PER_REQUEST",
        KeySchema=[
            {"AttributeName": "PK", "KeyType": "HASH"},
            {"AttributeName": "SK", "KeyType": "RANGE"},
        ],
        AttributeDefinitions=[
            {"AttributeName": "PK", "AttributeType": "S"},
            {"AttributeName": "SK", "AttributeType": "S"},
        ],
    )
    print("Created table:", table.table_name)

if __name__ == "__main__":
    # Quick connectivity check—will raise if Local isn’t reachable
    try:
        list(dynamodb.tables.all())
    except Exception as e:
        raise SystemExit(
            f"Could not reach DynamoDB Local at {DDB_ENDPOINT}. "
            f"Is the container running and port mapped? Original error: {e}"
        )
    main()
