# app.py

from flask import Flask, render_template, request, redirect, url_for
import boto3
import datetime

application = Flask(__name__)

dynamodb = boto3.resource('dynamodb', region_name='us-east-2')
table_name = 'bruce-quotes'
table = dynamodb.Table(table_name)

MAX_INPUT_LENGTH = 500

@application.route('/')
def index():
    # Retrieve all quotes from DynamoDB
    response = table.scan()
    quotes = sorted(response.get('Items', []), key=lambda x: x.get('quote_id', 0), reverse=True)
    for quote in quotes:
        if 'timestamp' in quote:
            quote['timestamp'] = datetime.datetime.strptime(quote['timestamp'], '%Y-%m-%d %H:%M:%S.%f')
    return render_template('index.html', quotes=quotes)

@application.route('/add_quote', methods=['POST'])
def add_quote():
    quote = request.form['quote']
    if len(quote) > MAX_INPUT_LENGTH:
        return f"Input length exceeds maximum limit of {MAX_INPUT_LENGTH} characters.", 400
    quote_id = int(datetime.datetime.now().timestamp())
    timestamp = str(datetime.datetime.now())
    table.put_item(Item={'quote_id': quote_id, 'quote': quote, 'timestamp': timestamp})
    return redirect(url_for('index'))

if __name__ == '__main__':
    application.run()
