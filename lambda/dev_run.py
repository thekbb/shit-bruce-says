import os, json
import app

os.environ.setdefault("AWS_REGION", "us-east-2")
os.environ.setdefault("TABLE_NAME", "bruce-quotes")
os.environ.setdefault("DYNAMODB_ENDPOINT", "http://localhost:8000")
os.environ.setdefault("AWS_ACCESS_KEY_ID", "fake")
os.environ.setdefault("AWS_SECRET_ACCESS_KEY", "fake")

def main():
    post_event = {
        "requestContext": {"http": {"method": "POST", "path": "/quotes"}},
        "body": json.dumps({"quote": "Hello from dev_run.py!"}),
    }
    print(app.handler(post_event, None))

    get_event = {
        "requestContext": {"http": {"method": "GET", "path": "/quotes"}},
        "queryStringParameters": {"limit": "10"},
    }
    print(app.handler(get_event, None))

if __name__ == "__main__":
    main()
