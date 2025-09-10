#!/usr/bin/env python3
"""
Migration script to normalize existing quotes in DynamoDB.
Removes surrounding quotes from stored quotes to ensure consistent format.

Usage:
    python migrate_quotes.py --dry-run    # Preview changes
    python migrate_quotes.py              # Apply changes
"""

import os
import sys
import argparse
import boto3
from boto3.dynamodb.conditions import Key

# Add the app module to path so we can import the normalize function
sys.path.insert(0, os.path.dirname(__file__))
from app import _normalize_quote, Config

def get_table(endpoint_url=None):
    """Get DynamoDB table reference."""
    session = boto3.Session()

    if endpoint_url:
        # For local development
        dynamodb = session.resource('dynamodb',
                                  endpoint_url=endpoint_url,
                                  region_name=Config.REGION)
    else:
        # For production
        dynamodb = session.resource('dynamodb', region_name=Config.REGION)

    return dynamodb.Table(Config.TABLE_NAME)

def scan_and_migrate_quotes(table, dry_run=True):
    """Scan all quotes and normalize them."""
    print(f"{'DRY RUN: ' if dry_run else ''}Scanning quotes for normalization...")

    response = table.scan(
        FilterExpression=Key('PK').eq('QUOTE'),
        ProjectionExpression='PK, SK, quote'
    )

    items_to_update = []
    total_items = 0

    for item in response['Items']:
        total_items += 1
        original_quote = item['quote']
        normalized_quote = _normalize_quote(original_quote)

        if original_quote != normalized_quote:
            items_to_update.append({
                'SK': item['SK'],
                'original': original_quote,
                'normalized': normalized_quote
            })
            print(f"  Found quote to normalize: {item['SK']}")
            print(f"    Before: {repr(original_quote)}")
            print(f"    After:  {repr(normalized_quote)}")

    # Handle pagination if needed
    while 'LastEvaluatedKey' in response:
        response = table.scan(
            FilterExpression=Key('PK').eq('QUOTE'),
            ProjectionExpression='PK, SK, quote',
            ExclusiveStartKey=response['LastEvaluatedKey']
        )

        for item in response['Items']:
            total_items += 1
            original_quote = item['quote']
            normalized_quote = _normalize_quote(original_quote)

            if original_quote != normalized_quote:
                items_to_update.append({
                    'SK': item['SK'],
                    'original': original_quote,
                    'normalized': normalized_quote
                })
                print(f"  Found quote to normalize: {item['SK']}")
                print(f"    Before: {repr(original_quote)}")
                print(f"    After:  {repr(normalized_quote)}")

    print(f"\nSummary:")
    print(f"  Total quotes scanned: {total_items}")
    print(f"  Quotes needing normalization: {len(items_to_update)}")

    if not dry_run and items_to_update:
        print(f"\nApplying updates...")
        for item in items_to_update:
            try:
                table.update_item(
                    Key={'PK': 'QUOTE', 'SK': item['SK']},
                    UpdateExpression='SET quote = :new_quote',
                    ExpressionAttributeValues={':new_quote': item['normalized']}
                )
                print(f"  ✓ Updated {item['SK']}")
            except Exception as e:
                print(f"  ✗ Failed to update {item['SK']}: {e}")

        print(f"\nMigration complete!")
    elif dry_run and items_to_update:
        print(f"\nDry run complete. Run without --dry-run to apply changes.")
    else:
        print(f"\nNo quotes need normalization.")

def main():
    parser = argparse.ArgumentParser(description='Migrate quotes to normalized format')
    parser.add_argument('--dry-run', action='store_true',
                       help='Preview changes without applying them')
    parser.add_argument('--local', action='store_true',
                       help='Use local DynamoDB (http://localhost:8000)')

    args = parser.parse_args()

    # Set up environment
    if not os.getenv('AWS_REGION'):
        os.environ['AWS_REGION'] = Config.REGION
    if not os.getenv('TABLE_NAME'):
        os.environ['TABLE_NAME'] = Config.TABLE_NAME

    endpoint_url = 'http://localhost:8000' if args.local else None

    try:
        table = get_table(endpoint_url)
        scan_and_migrate_quotes(table, dry_run=args.dry_run)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()
