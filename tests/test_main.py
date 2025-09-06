import unittest

from unittest.mock import patch, mock_open
from app.main import read_csv_files, extract_account_name, read_config, extract_option_info

class TestMain(unittest.TestCase):
    def test_extract_account_name_valid_format(self):
        """Test extract_account_name with valid filename formats"""
        # Test with standard account name format
        filename = 'monthly-statement-transactions-HQ8KJW805CAD-2025-07-01.csv'
        result = extract_account_name(filename)
        self.assertEqual(result, 'HQ8KJW805CAD')

        # Test with different account name
        filename = 'monthly-statement-transactions-AB1234567USD-2024-12-31.csv'
        result = extract_account_name(filename)
        self.assertEqual(result, 'AB1234567USD')

        # Test with another valid format
        filename = 'monthly-statement-transactions-XY9876543CAD-2023-06-15.csv'
        result = extract_account_name(filename)
        self.assertEqual(result, 'XY9876543CAD')

    def test_extract_account_name_different_dates(self):
        """Test extract_account_name with different date formats"""
        # Test with different months
        filename = 'monthly-statement-transactions-TEST123456-2025-01-01.csv'
        result = extract_account_name(filename)
        self.assertEqual(result, 'TEST123456')

        # Test with leap year date
        filename = 'monthly-statement-transactions-LEAP987654-2024-02-29.csv'
        result = extract_account_name(filename)
        self.assertEqual(result, 'LEAP987654')

        # Test with end of year date
        filename = 'monthly-statement-transactions-YEAR123456-2023-12-31.csv'
        result = extract_account_name(filename)
        self.assertEqual(result, 'YEAR123456')

    def test_extract_account_name_invalid_format(self):
        """Test extract_account_name with invalid filename formats"""
        # Test with wrong prefix
        filename = 'daily-statement-transactions-HQ8KJW805CAD-2025-07-01.csv'
        result = extract_account_name(filename)
        self.assertIsNone(result)

        # Test with missing date
        filename = 'monthly-statement-transactions-HQ8KJW805CAD.csv'
        result = extract_account_name(filename)
        self.assertIsNone(result)

        # Test with wrong file extension
        filename = 'monthly-statement-transactions-HQ8KJW805CAD-2025-07-01.txt'
        result = extract_account_name(filename)
        self.assertIsNone(result)

        # Test with malformed date
        filename = 'monthly-statement-transactions-HQ8KJW805CAD-25-07-01.csv'
        result = extract_account_name(filename)
        self.assertIsNone(result)

        # Test with invalid date format (wrong separators)
        filename = 'monthly-statement-transactions-HQ8KJW805CAD-2025/07/01.csv'
        result = extract_account_name(filename)
        self.assertIsNone(result)

    def test_extract_account_name_edge_cases(self):
        """Test extract_account_name with edge cases"""
        # Test with empty string
        result = extract_account_name('')
        self.assertIsNone(result)

        # Test with None input
        result = extract_account_name(None)
        self.assertIsNone(result)

        # Test with completely different filename
        filename = 'some-other-file.csv'
        result = extract_account_name(filename)
        self.assertIsNone(result)

        # Test with partial match
        filename = 'monthly-statement-transactions-'
        result = extract_account_name(filename)
        self.assertIsNone(result)

    def test_extract_account_name_account_name_variations(self):
        """Test extract_account_name with different account name patterns"""
        # Test with numeric account name
        filename = 'monthly-statement-transactions-1234567890-2025-07-01.csv'
        result = extract_account_name(filename)
        self.assertEqual(result, '1234567890')

        # Test with mixed alphanumeric
        filename = 'monthly-statement-transactions-ABC123DEF456-2025-07-01.csv'
        result = extract_account_name(filename)
        self.assertEqual(result, 'ABC123DEF456')

        # Test with single character account name
        filename = 'monthly-statement-transactions-A-2025-07-01.csv'
        result = extract_account_name(filename)
        self.assertEqual(result, 'A')

    def test_extract_account_name_special_characters(self):
        """Test extract_account_name with special characters in account names"""
        # The regex pattern uses \w+ which only matches word characters (letters, digits, underscore)
        # Test with underscore (should work)
        filename = 'monthly-statement-transactions-TEST_123_CAD-2025-07-01.csv'
        result = extract_account_name(filename)
        self.assertEqual(result, 'TEST_123_CAD')

        # Test with hyphen in account name (should not work with current regex)
        filename = 'monthly-statement-transactions-TEST-123-CAD-2025-07-01.csv'
        result = extract_account_name(filename)
        # This should return None because the regex stops at the first hyphen
        self.assertIsNone(result)

        # Test with space in account name (should not work)
        filename = 'monthly-statement-transactions-TEST 123 CAD-2025-07-01.csv'
        result = extract_account_name(filename)
        self.assertIsNone(result)

    @patch('os.listdir')
    @patch('builtins.open', new_callable=mock_open, read_data='date,transaction,description,amount,currency\n2025-07-01,BUY,AAPL - 10.0 shares,-1500.00,USD\n')
    def test_read_csv_files(self, mock_open_file, mock_listdir):
        mock_listdir.return_value = ['monthly-statement-transactions-TEST123456-2025-07-01.csv']
        csv_data = read_csv_files('input_folder')
        # Should have 2 accounts (TEST123456-USD and TEST123456-CAD)
        self.assertEqual(len(csv_data), 2)
        # Check that both currency accounts exist
        self.assertIn('TEST123456-USD', csv_data)
        self.assertIn('TEST123456-CAD', csv_data)
        # USD account should have 1 transaction, CAD should be empty
        self.assertEqual(len(csv_data['TEST123456-USD']), 1)
        self.assertEqual(len(csv_data['TEST123456-CAD']), 0)

    def test_extract_option_info_valid_descriptions(self):
        """Test extract_option_info with valid option descriptions"""
        # Test CALL option with standard format
        description = "SPY 450.00 USD CALL 2025-07-25: Bought 2 contract (executed at 2025-07-23), Fee: $1.50"
        option_name, contracts, fee = extract_option_info(description)
        self.assertEqual(option_name, "SPY 450.00 USD CALL 2025-07-25")
        self.assertEqual(contracts, 2)
        self.assertEqual(fee, 1.50)

        # Test PUT option
        description = "AAPL 180.00 USD PUT 2025-07-30: Sold 1 contract (executed at 2025-07-25), Fee: $0.75"
        option_name, contracts, fee = extract_option_info(description)
        self.assertEqual(option_name, "AAPL 180.00 USD PUT 2025-07-30")
        self.assertEqual(contracts, 1)
        self.assertEqual(fee, 0.75)

        # Test with multiple contracts
        description = "TSLA 250.00 USD CALL 2025-08-15: Bought 5 contract (executed at 2025-08-10), Fee: $3.75"
        option_name, contracts, fee = extract_option_info(description)
        self.assertEqual(option_name, "TSLA 250.00 USD CALL 2025-08-15")
        self.assertEqual(contracts, 5)
        self.assertEqual(fee, 3.75)

        # Test with different strike price format
        description = "NVDA 500.50 USD CALL 2025-09-20: Bought 3 contract (executed at 2025-09-15), Fee: $2.25"
        option_name, contracts, fee = extract_option_info(description)
        self.assertEqual(option_name, "NVDA 500.50 USD CALL 2025-09-20")
        self.assertEqual(contracts, 3)
        self.assertEqual(fee, 2.25)

    def test_extract_option_info_different_fee_formats(self):
        """Test extract_option_info with different fee formats"""
        # Test with zero fee
        description = "SPY 450.00 USD CALL 2025-07-25: Bought 2 contract (executed at 2025-07-23), Fee: $0.00"
        option_name, contracts, fee = extract_option_info(description)
        self.assertEqual(option_name, "SPY 450.00 USD CALL 2025-07-25")
        self.assertEqual(contracts, 2)
        self.assertEqual(fee, 0.00)

        # Test with high precision fee
        description = "AAPL 180.00 USD PUT 2025-07-30: Sold 1 contract (executed at 2025-07-25), Fee: $1.2345"
        option_name, contracts, fee = extract_option_info(description)
        self.assertEqual(option_name, "AAPL 180.00 USD PUT 2025-07-30")
        self.assertEqual(contracts, 1)
        self.assertEqual(fee, 1.2345)

        # Test with integer fee
        description = "TSLA 250.00 USD CALL 2025-08-15: Bought 5 contract (executed at 2025-08-10), Fee: $5"
        option_name, contracts, fee = extract_option_info(description)
        self.assertEqual(option_name, "TSLA 250.00 USD CALL 2025-08-15")
        self.assertEqual(contracts, 5)
        self.assertEqual(fee, 5.0)

    def test_extract_option_info_different_contract_counts(self):
        """Test extract_option_info with different contract counts"""
        # Test with single digit contracts
        description = "SPY 450.00 USD CALL 2025-07-25: Bought 1 contract (executed at 2025-07-23), Fee: $1.50"
        option_name, contracts, fee = extract_option_info(description)
        self.assertEqual(contracts, 1)

        # Test with double digit contracts
        description = "SPY 450.00 USD CALL 2025-07-25: Bought 15 contract (executed at 2025-07-23), Fee: $1.50"
        option_name, contracts, fee = extract_option_info(description)
        self.assertEqual(contracts, 15)

        # Test with triple digit contracts
        description = "SPY 450.00 USD CALL 2025-07-25: Bought 100 contract (executed at 2025-07-23), Fee: $1.50"
        option_name, contracts, fee = extract_option_info(description)
        self.assertEqual(contracts, 100)

    def test_extract_option_info_edge_cases(self):
        """Test extract_option_info with edge cases and invalid inputs"""
        # Test with None input
        option_name, contracts, fee = extract_option_info(None)
        self.assertIsNone(option_name)
        self.assertIsNone(contracts)
        self.assertIsNone(fee)

        # Test with empty string
        option_name, contracts, fee = extract_option_info("")
        self.assertIsNone(option_name)
        self.assertIsNone(contracts)
        self.assertIsNone(fee)

        # Test with non-string input
        option_name, contracts, fee = extract_option_info(123)
        self.assertIsNone(option_name)
        self.assertIsNone(contracts)
        self.assertIsNone(fee)

        # Test with string without colon
        description = "SPY 450.00 USD CALL 2025-07-25 Bought 2 contract executed at 2025-07-23 Fee 1.50"
        option_name, contracts, fee = extract_option_info(description)
        self.assertIsNone(option_name)
        self.assertIsNone(contracts)
        self.assertIsNone(fee)

    def test_extract_option_info_missing_components(self):
        """Test extract_option_info with missing components in description"""
        # Test with missing contract information
        description = "SPY 450.00 USD CALL 2025-07-25: Bought (executed at 2025-07-23), Fee: $1.50"
        option_name, contracts, fee = extract_option_info(description)
        self.assertEqual(option_name, "SPY 450.00 USD CALL 2025-07-25")
        self.assertIsNone(contracts)
        self.assertEqual(fee, 1.50)

        # Test with missing fee information
        description = "SPY 450.00 USD CALL 2025-07-25: Bought 2 contract (executed at 2025-07-23)"
        option_name, contracts, fee = extract_option_info(description)
        self.assertEqual(option_name, "SPY 450.00 USD CALL 2025-07-25")
        self.assertEqual(contracts, 2)
        self.assertIsNone(fee)

        # Test with missing both contract and fee information
        description = "SPY 450.00 USD CALL 2025-07-25: Bought (executed at 2025-07-23)"
        option_name, contracts, fee = extract_option_info(description)
        self.assertEqual(option_name, "SPY 450.00 USD CALL 2025-07-25")
        self.assertIsNone(contracts)
        self.assertIsNone(fee)

    def test_extract_option_info_malformed_descriptions(self):
        """Test extract_option_info with malformed descriptions"""
        # Test with colon but no proper format after
        description = "SPY 450.00 USD CALL 2025-07-25: invalid format"
        option_name, contracts, fee = extract_option_info(description)
        self.assertEqual(option_name, "SPY 450.00 USD CALL 2025-07-25")
        self.assertIsNone(contracts)
        self.assertIsNone(fee)

        # Test with multiple colons
        description = "SPY 450.00 USD CALL 2025-07-25: Bought 2 contract: Fee: $1.50"
        option_name, contracts, fee = extract_option_info(description)
        self.assertEqual(option_name, "SPY 450.00 USD CALL 2025-07-25")
        self.assertEqual(contracts, 2)
        self.assertEqual(fee, 1.50)

        # Test with contract word but no number
        description = "SPY 450.00 USD CALL 2025-07-25: Bought contract (executed at 2025-07-23), Fee: $1.50"
        option_name, contracts, fee = extract_option_info(description)
        self.assertEqual(option_name, "SPY 450.00 USD CALL 2025-07-25")
        self.assertIsNone(contracts)
        self.assertEqual(fee, 1.50)

        # Test with Fee word but no amount
        description = "SPY 450.00 USD CALL 2025-07-25: Bought 2 contract (executed at 2025-07-23), Fee:"
        option_name, contracts, fee = extract_option_info(description)
        self.assertEqual(option_name, "SPY 450.00 USD CALL 2025-07-25")
        self.assertEqual(contracts, 2)
        self.assertIsNone(fee)

    def test_extract_option_info_whitespace_handling(self):
        """Test extract_option_info with various whitespace scenarios"""
        # Test with extra whitespace around colon
        description = "SPY 450.00 USD CALL 2025-07-25  :  Bought 2 contract (executed at 2025-07-23), Fee: $1.50"
        option_name, contracts, fee = extract_option_info(description)
        self.assertEqual(option_name, "SPY 450.00 USD CALL 2025-07-25")
        self.assertEqual(contracts, 2)
        self.assertEqual(fee, 1.50)

        # Test with leading/trailing whitespace
        description = "  SPY 450.00 USD CALL 2025-07-25: Bought 2 contract (executed at 2025-07-23), Fee: $1.50  "
        option_name, contracts, fee = extract_option_info(description)
        self.assertEqual(option_name, "SPY 450.00 USD CALL 2025-07-25")
        self.assertEqual(contracts, 2)
        self.assertEqual(fee, 1.50)

        # Test with extra spaces in contract description
        description = "SPY 450.00 USD CALL 2025-07-25: Bought  2  contract (executed at 2025-07-23), Fee: $1.50"
        option_name, contracts, fee = extract_option_info(description)
        self.assertEqual(option_name, "SPY 450.00 USD CALL 2025-07-25")
        self.assertEqual(contracts, 2)
        self.assertEqual(fee, 1.50)

    def test_extract_option_info_different_action_words(self):
        """Test extract_option_info with different action words (Bought/Sold)"""
        # Test with "Sold" action
        description = "SPY 450.00 USD CALL 2025-07-25: Sold 3 contract (executed at 2025-07-23), Fee: $2.25"
        option_name, contracts, fee = extract_option_info(description)
        self.assertEqual(option_name, "SPY 450.00 USD CALL 2025-07-25")
        self.assertEqual(contracts, 3)
        self.assertEqual(fee, 2.25)

        # Test with "Bought" action
        description = "AAPL 180.00 USD PUT 2025-07-30: Bought 1 contract (executed at 2025-07-25), Fee: $0.75"
        option_name, contracts, fee = extract_option_info(description)
        self.assertEqual(option_name, "AAPL 180.00 USD PUT 2025-07-30")
        self.assertEqual(contracts, 1)
        self.assertEqual(fee, 0.75)

if __name__ == '__main__':
    unittest.main()
