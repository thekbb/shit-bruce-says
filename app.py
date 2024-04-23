# app.py

from flask import Flask, render_template, request, redirect, url_for
import boto3
import datetime

# Flask app configuration
app = Flask(__name__)

# Initialize DynamoDB client
dynamodb = boto3.resource('dynamodb', region_name='us-east-2')

# DynamoDB table name
table_name = 'bruce-quotes'  # Update with your DynamoDB table name

# Get reference to DynamoDB table
table = dynamodb.Table(table_name)

# Route to display form for entering quotes
@app.route('/')
def index():
    # Retrieve all quotes from DynamoDB
    response = table.scan()
    quotes = sorted(response.get('Items', []), key=lambda x: x.get('quote_id', 0), reverse=True)

    # Convert timestamp strings to datetime objects
    for quote in quotes:
        if 'timestamp' in quote:
            quote['timestamp'] = datetime.datetime.strptime(quote['timestamp'], '%Y-%m-%d %H:%M:%S.%f')

    return render_template('index.html', quotes=quotes)

# Route to handle form submission and store quotes in DynamoDB
@app.route('/add_quote', methods=['POST'])
def add_quote():
    quote = request.form['quote']
    quote_id = int(datetime.datetime.now().timestamp())
    timestamp = str(datetime.datetime.now())

    # Insert quote into DynamoDB
    table.put_item(Item={'quote_id': quote_id, 'quote': quote, 'timestamp': timestamp})

    # Redirect back to the index page
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run()
