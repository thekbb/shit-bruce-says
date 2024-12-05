import unittest
import re
from application import compile_sql_pattern, add_quote_to_table  # Import your functions
import boto3
from unittest.mock import Mock, patch
import datetime


class TestSQLPattern(unittest.TestCase):

    def test_compile_sql_pattern(self):
        pattern = compile_sql_pattern()
        self.assertIsNotNone(pattern)  # Check that the pattern compiles
        self.assertTrue(pattern.search("DELETE"))
        self.assertTrue(pattern.search("d#fffff"))
        self.assertTrue(pattern.search("foo=bar"))
        self.assertTrue(pattern.search("((ddddddd"))
        self.assertTrue(pattern.search("))ddddddd"))
        self.assertTrue(pattern.search("--"))
        self.assertFalse(pattern.search("(testing)"))
        self.assertFalse(pattern.search("testing"))

class TestAddQuote(unittest.TestCase):
    @patch('application.init_dynamodb_table')
    def test_add_quote(self, mock_init_dynamodb_table):

        mock_table = Mock()
        mock_init_dynamodb_table.return_value = mock_table

        quote = "A test quote!"
        add_quote_to_table(quote, mock_table)

        # Check if put_item was called with expected parameters:
        mock_table.put_item.assert_called_once()  # Check put_item called once

        # extract the arguments and perform assertions
        args, kwargs = mock_table.put_item.call_args

        # Assert quote_id and quote match (timestamp will be different)
        self.assertEqual(kwargs['Item']['quote'], quote)

        self.assertIsInstance(kwargs['Item']['quote_id'], int)
        self.assertIsInstance(kwargs['Item']['timestamp'], str)

if __name__ == '__main__':
    unittest.main()
