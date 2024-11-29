# Shit Bruce Says

Bruce says some shit. This Python Flask app allows the world to
contribute new quotes, storing them in AWS Dynamo DB.

## Running

Auth to AWS on the CLI to access the DDB table.

```shell
export AWS_ACCESS_KEY_ID="<redacted>"
export AWS_SECRET_ACCESS_KEY="<redacted>"
```

Create a virtual env named `virt`

```shell
virtualenv virt
source virt/bin/activate
```

Install dependencies

```shell
pip install -r requirements.txt
```

Run the app

```shell
python app.py
```

## Running in Docker
```shell
docker build -t shitbrucesays .
docker run -it --rm -p 8080:5000 shitbrucesays
```

View the site on http://localhost:8080 on the host machine.
