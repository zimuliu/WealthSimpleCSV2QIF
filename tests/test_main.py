import unittest
import tempfile
import os
import yaml

from unittest.mock import patch, mock_open
from app.main import read_csv_files, extract_account_name, read_config, extract_option_info, extract_unit, extract_symbol, generate_qif_entry

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

    def test_extract_unit_valid_descriptions(self):
        """Test extract_unit with valid stock transaction descriptions"""
        # Test with standard format - integer shares
        description = "AAPL - 10.0 shares"
        result = extract_unit(description)
        self.assertEqual(result, 10.0)

        # Test with fractional shares
        description = "TSLA - 5.5 shares"
        result = extract_unit(description)
        self.assertEqual(result, 5.5)

        # Test with single share
        description = "SHOP - 1.0 shares"
        result = extract_unit(description)
        self.assertEqual(result, 1.0)

        # Test with large number of shares
        description = "NVDA - 100.0 shares"
        result = extract_unit(description)
        self.assertEqual(result, 100.0)

        # Test with high precision fractional shares
        description = "GOOGL - 2.25 shares"
        result = extract_unit(description)
        self.assertEqual(result, 2.25)

    def test_extract_unit_different_decimal_formats(self):
        """Test extract_unit with different decimal formats"""
        # Test with multiple decimal places
        description = "AAPL - 15.123 shares"
        result = extract_unit(description)
        self.assertEqual(result, 15.123)

        # Test with many decimal places
        description = "MSFT - 7.123456 shares"
        result = extract_unit(description)
        self.assertEqual(result, 7.123456)

        # Test with zero decimal
        description = "AMZN - 3.0 shares"
        result = extract_unit(description)
        self.assertEqual(result, 3.0)

        # Test with small fractional amount
        description = "BRK.B - 0.5 shares"
        result = extract_unit(description)
        self.assertEqual(result, 0.5)

        # Test with very small fractional amount
        description = "EXPENSIVE - 0.001 shares"
        result = extract_unit(description)
        self.assertEqual(result, 0.001)

    def test_extract_unit_different_symbols(self):
        """Test extract_unit with different stock symbols"""
        # Test with simple symbol
        description = "A - 5.0 shares"
        result = extract_unit(description)
        self.assertEqual(result, 5.0)

        # Test with symbol containing dots
        description = "BRK.B - 2.5 shares"
        result = extract_unit(description)
        self.assertEqual(result, 2.5)

        # Test with longer symbol
        description = "BERKSHIRE - 1.0 shares"
        result = extract_unit(description)
        self.assertEqual(result, 1.0)

        # Test with numeric-like symbol
        description = "3M - 8.0 shares"
        result = extract_unit(description)
        self.assertEqual(result, 8.0)

    def test_extract_unit_whitespace_variations(self):
        """Test extract_unit with various whitespace scenarios"""
        # Test with extra spaces around dash
        description = "AAPL  -  10.0 shares"
        result = extract_unit(description)
        self.assertEqual(result, 10.0)

        # Test with leading/trailing whitespace
        description = "  TSLA - 5.0 shares  "
        result = extract_unit(description)
        self.assertEqual(result, 5.0)

        # Test with extra spaces before shares
        description = "NVDA - 15.0  shares"
        result = extract_unit(description)
        self.assertEqual(result, 15.0)

        # Test with tabs or other whitespace
        description = "SHOP\t-\t3.0\tshares"
        result = extract_unit(description)
        self.assertEqual(result, 3.0)

    def test_extract_unit_edge_cases(self):
        """Test extract_unit with edge cases and invalid inputs"""
        # Test with None input - this will raise TypeError as the function doesn't handle None
        with self.assertRaises(TypeError):
            extract_unit(None)

        # Test with empty string
        result = extract_unit("")
        self.assertIsNone(result)

        # Test with string that doesn't contain shares pattern
        description = "AAPL - some other text"
        result = extract_unit(description)
        self.assertIsNone(result)

        # Test with shares word but no number
        description = "AAPL - shares"
        result = extract_unit(description)
        self.assertIsNone(result)

        # Test with number but no shares word
        description = "AAPL - 10.0 contracts"
        result = extract_unit(description)
        self.assertIsNone(result)

    def test_extract_unit_malformed_descriptions(self):
        """Test extract_unit with malformed descriptions"""
        # Test with integer instead of decimal format
        description = "AAPL - 10 shares"
        result = extract_unit(description)
        self.assertIsNone(result)  # Function expects decimal format (e.g., 10.0)

        # Test with missing dash
        description = "AAPL 10.0 shares"
        result = extract_unit(description)
        self.assertEqual(result, 10.0)  # Should still work as regex looks for pattern anywhere


        # Test with shares in different case
        description = "AAPL - 10.0 SHARES"
        result = extract_unit(description)
        self.assertIsNone(result)  # Function is case-sensitive

        # Test with plural vs singular
        description = "AAPL - 1.0 share"
        result = extract_unit(description)
        self.assertIsNone(result)  # Function expects "shares" not "share"

    def test_extract_unit_complex_descriptions(self):
        """Test extract_unit with complex transaction descriptions"""
        # Test with additional text before shares
        description = "AAPL - Purchase of 10.0 shares at market price"
        result = extract_unit(description)
        self.assertEqual(result, 10.0)

        # Test with additional text after shares
        description = "TSLA - 5.0 shares (executed at 2025-07-15)"
        result = extract_unit(description)
        self.assertEqual(result, 5.0)

        # Test with currency information
        description = "SHOP - 15.0 shares in CAD"
        result = extract_unit(description)
        self.assertEqual(result, 15.0)

        # Test with price information
        description = "NVDA - 2.5 shares at $500.00 per share"
        result = extract_unit(description)
        self.assertEqual(result, 2.5)

    def test_extract_unit_boundary_values(self):
        """Test extract_unit with boundary and extreme values"""
        # Test with very large number
        description = "PENNY - 999999.0 shares"
        result = extract_unit(description)
        self.assertEqual(result, 999999.0)

        # Test with very small number
        description = "EXPENSIVE - 0.000001 shares"
        result = extract_unit(description)
        self.assertEqual(result, 0.000001)

        # Test with zero shares (edge case)
        description = "TEST - 0.0 shares"
        result = extract_unit(description)
        self.assertEqual(result, 0.0)

        # Test with single digit decimal
        description = "SIMPLE - 9.0 shares"
        result = extract_unit(description)
        self.assertEqual(result, 9.0)

    def test_extract_unit_special_characters_in_symbol(self):
        """Test extract_unit with special characters in stock symbols"""
        # Test with dot in symbol
        description = "BRK.A - 1.0 shares"
        result = extract_unit(description)
        self.assertEqual(result, 1.0)

        # Test with hyphen in symbol (though this might be rare)
        description = "SOME-STOCK - 5.0 shares"
        result = extract_unit(description)
        self.assertEqual(result, 5.0)

        # Test with numbers in symbol
        description = "STOCK123 - 10.0 shares"
        result = extract_unit(description)
        self.assertEqual(result, 10.0)

        # Test with underscore in symbol
        description = "STOCK_A - 7.5 shares"
        result = extract_unit(description)
        self.assertEqual(result, 7.5)

    def test_extract_symbol_standard_symbols_usd(self):
        """Test extract_symbol with standard symbols in USD currency"""
        # Test regular symbols with USD - should get -CT suffix
        result = extract_symbol("AAPL - 10.0 shares", "USD")
        self.assertEqual(result, "AAPL-CT")

        result = extract_symbol("MSFT - 5.0 shares", "USD")
        self.assertEqual(result, "MSFT-CT")

        result = extract_symbol("GOOGL - 2.0 shares", "USD")
        self.assertEqual(result, "GOOGL-CT")

    def test_extract_symbol_standard_symbols_cad(self):
        """Test extract_symbol with standard (non-CDR) symbols in CAD currency"""
        # Test non-CDR symbols with CAD - should get -CT suffix
        result = extract_symbol("SHOP - 15.0 shares", "CAD")
        self.assertEqual(result, "SHOP-CT")

        result = extract_symbol("RY - 10.0 shares", "CAD")
        self.assertEqual(result, "RY-CT")

        result = extract_symbol("TD - 8.0 shares", "CAD")
        self.assertEqual(result, "TD-CT")

    def test_extract_symbol_cdr_symbols_cad(self):
        """Test extract_symbol with CDR symbols in CAD currency"""
        # Test CDR symbols (TSLA, DIS, NVDA, AAPL) with CAD - should get -QH suffix
        result = extract_symbol("TSLA - 5.0 shares", "CAD")
        self.assertEqual(result, "TSLA-QH")

        result = extract_symbol("DIS - 10.0 shares", "CAD")
        self.assertEqual(result, "DIS-QH")

        result = extract_symbol("NVDA - 2.0 shares", "CAD")
        self.assertEqual(result, "NVDA-QH")

        result = extract_symbol("AAPL - 15.0 shares", "CAD")
        self.assertEqual(result, "AAPL-QH")

    def test_extract_symbol_cdr_symbols_usd(self):
        """Test extract_symbol with CDR symbols in USD currency"""
        # CDR symbols with USD should get -CT suffix (not -QH)
        # Only CDR symbols with CAD currency get -QH suffix
        result = extract_symbol("TSLA - 5.0 shares", "USD")
        self.assertEqual(result, "TSLA-CT")

        result = extract_symbol("DIS - 10.0 shares", "USD")
        self.assertEqual(result, "DIS-CT")

        result = extract_symbol("NVDA - 2.0 shares", "USD")
        self.assertEqual(result, "NVDA-CT")

        result = extract_symbol("AAPL - 15.0 shares", "USD")
        self.assertEqual(result, "AAPL-CT")

    def test_extract_symbol_case_insensitive_input(self):
        """Test extract_symbol with case-insensitive input - should always return uppercase"""
        # Test lowercase symbols - should be converted to uppercase
        result = extract_symbol("aapl - 10.0 shares", "USD")
        self.assertEqual(result, "AAPL-CT")

        result = extract_symbol("tsla - 5.0 shares", "CAD")
        self.assertEqual(result, "TSLA-QH")  # lowercase tsla becomes TSLA and matches CDR

        result = extract_symbol("shop - 15.0 shares", "CAD")
        self.assertEqual(result, "SHOP-CT")

        # Test mixed case symbols
        result = extract_symbol("AaPl - 10.0 shares", "CAD")
        self.assertEqual(result, "AAPL-QH")

        result = extract_symbol("TsLa - 5.0 shares", "USD")
        self.assertEqual(result, "TSLA-CT")

    def test_extract_symbol_edge_cases(self):
        """Test extract_symbol with edge cases and invalid inputs"""
        # Test with missing dash
        result = extract_symbol("AAPL 10.0 shares", "USD")
        self.assertIsNone(result)

        # Test with empty string
        result = extract_symbol("", "USD")
        self.assertIsNone(result)

        # Test with multiple dashes - should extract everything before first dash
        result = extract_symbol("some-stock - 5.0 shares", "USD")
        self.assertEqual(result, "SOME-CT")

    def test_extract_symbol_currency_case_sensitivity(self):
        """Test extract_symbol currency case sensitivity"""
        # Currency comparison is case-sensitive
        result = extract_symbol("AAPL - 10.0 shares", "cad")
        self.assertEqual(result, "AAPL-CT")  # lowercase 'cad' != 'CAD'

        result = extract_symbol("aapl - 10.0 shares", "CAD")
        self.assertEqual(result, "AAPL-QH")  # uppercase 'CAD' matches

    # Tests for generate_qif_entry function
    def test_generate_qif_entry_buy_transaction_usd(self):
        """Test generate_qif_entry with BUY transaction in USD"""
        row = {
            'date': '2025-07-15',
            'transaction': 'BUY',
            'description': 'AAPL - 10.0 shares',
            'amount': '-1500.00',
            'currency': 'USD'
        }
        result = generate_qif_entry(row, 'USD')
        expected = 'D2025-07-15\nNBuy\nYAAPL-CT\nI150.0\nQ10.0\nT1500.0\nO0.00\nCc\n^'
        self.assertEqual(result, expected)

    def test_generate_qif_entry_buy_transaction_cad(self):
        """Test generate_qif_entry with BUY transaction in CAD"""
        row = {
            'date': '2025-07-16',
            'transaction': 'BUY',
            'description': 'SHOP - 5.0 shares',
            'amount': '-750.00',
            'currency': 'CAD'
        }
        result = generate_qif_entry(row, 'CAD')
        expected = 'D2025-07-16\nNBuy\nYSHOP-CT\nI150.0\nQ5.0\nT750.0\nO0.00\nCc\n^'
        self.assertEqual(result, expected)

    def test_generate_qif_entry_buy_cdr_symbol_cad(self):
        """Test generate_qif_entry with BUY transaction for CDR symbol in CAD"""
        row = {
            'date': '2025-07-17',
            'transaction': 'BUY',
            'description': 'TSLA - 2.0 shares',
            'amount': '-500.00',
            'currency': 'CAD'
        }
        result = generate_qif_entry(row, 'CAD')
        expected = 'D2025-07-17\nNBuy\nYTSLA-QH\nI250.0\nQ2.0\nT500.0\nO0.00\nCc\n^'
        self.assertEqual(result, expected)

    def test_generate_qif_entry_sell_transaction_usd(self):
        """Test generate_qif_entry with SELL transaction in USD"""
        row = {
            'date': '2025-07-18',
            'transaction': 'SELL',
            'description': 'MSFT - 8.0 shares',
            'amount': '2400.00',
            'currency': 'USD'
        }
        result = generate_qif_entry(row, 'USD')
        expected = 'D2025-07-18\nNSell\nYMSFT-CT\nI300.0\nQ8.0\nT2400.0\nO0.00\nCc\n^'
        self.assertEqual(result, expected)

    def test_generate_qif_entry_sell_transaction_cad(self):
        """Test generate_qif_entry with SELL transaction in CAD"""
        row = {
            'date': '2025-07-19',
            'transaction': 'SELL',
            'description': 'RY - 15.0 shares',
            'amount': '1800.00',
            'currency': 'CAD'
        }
        result = generate_qif_entry(row, 'CAD')
        expected = 'D2025-07-19\nNSell\nYRY-CT\nI120.0\nQ15.0\nT1800.0\nO0.00\nCc\n^'
        self.assertEqual(result, expected)

    def test_generate_qif_entry_buytoopen_options_usd(self):
        """Test generate_qif_entry with BUYTOOPEN options transaction in USD"""
        row = {
            'date': '2025-07-23',
            'transaction': 'BUYTOOPEN',
            'description': 'SPY 450.00 USD CALL 2025-07-25: Bought 2 contract (executed at 2025-07-23), Fee: $1.50',
            'amount': '-320.50',
            'currency': 'USD'
        }
        result = generate_qif_entry(row, 'USD')
        expected = 'D2025-07-23\nNBuy\nYSPY 450.00 USD CALL 2025-07-25\nI159.5\nQ2\nT320.5\nO1.5\nCc\n^'
        self.assertEqual(result, expected)

    def test_generate_qif_entry_selltoclose_options_usd(self):
        """Test generate_qif_entry with SELLTOCLOSE options transaction in USD"""
        row = {
            'date': '2025-07-25',
            'transaction': 'SELLTOCLOSE',
            'description': 'AAPL 180.00 USD PUT 2025-07-30: Sold 1 contract (executed at 2025-07-25), Fee: $0.75',
            'amount': '150.25',
            'currency': 'USD'
        }
        result = generate_qif_entry(row, 'USD')
        expected = 'D2025-07-25\nNSell\nYAAPL 180.00 USD PUT 2025-07-30\nI151.0\nQ1\nT150.25\nO0.75\nCc\n^'
        self.assertEqual(result, expected)

    def test_generate_qif_entry_dividend_usd(self):
        """Test generate_qif_entry with DIV transaction in USD"""
        row = {
            'date': '2025-07-20',
            'transaction': 'DIV',
            'description': 'AAPL - Dividend payment',
            'amount': '25.50',
            'currency': 'USD'
        }
        result = generate_qif_entry(row, 'USD')
        expected = 'D2025-07-20\nNDiv\nYAAPL-CT\nT25.5\nO0.00\nCc\n^'
        self.assertEqual(result, expected)

    def test_generate_qif_entry_dividend_cad(self):
        """Test generate_qif_entry with DIV transaction in CAD"""
        row = {
            'date': '2025-07-21',
            'transaction': 'DIV',
            'description': 'TD - Dividend payment',
            'amount': '15.75',
            'currency': 'CAD'
        }
        result = generate_qif_entry(row, 'CAD')
        expected = 'D2025-07-21\nNDiv\nYTD-CT\nT15.75\nO0.00\nCc\n^'
        self.assertEqual(result, expected)

    def test_generate_qif_entry_contribution_cad(self):
        """Test generate_qif_entry with CONT transaction in CAD"""
        row = {
            'date': '2025-07-16',
            'transaction': 'CONT',
            'description': 'Contribution (executed at 2025-07-16)',
            'amount': '1000.0',
            'currency': 'CAD'
        }
        result = generate_qif_entry(row, 'CAD')
        expected = 'D2025-07-16\nNXIn\nT1000.0\nO0.00\nCc\nPContribution\nMContribution (executed at 2025-07-16)\n^'
        self.assertEqual(result, expected)

    def test_generate_qif_entry_contribution_usd(self):
        """Test generate_qif_entry with CONT transaction in USD"""
        row = {
            'date': '2025-07-22',
            'transaction': 'CONT',
            'description': 'Monthly contribution',
            'amount': '500.0',
            'currency': 'USD'
        }
        result = generate_qif_entry(row, 'USD')
        expected = 'D2025-07-22\nNXIn\nT500.0\nO0.00\nCc\nPContribution\nMMonthly contribution\n^'
        self.assertEqual(result, expected)

    def test_generate_qif_entry_fplint_usd(self):
        """Test generate_qif_entry with FPLINT (stock lending interest) transaction in USD"""
        row = {
            'date': '2025-07-30',
            'transaction': 'FPLINT',
            'description': 'Stock lending interest payment',
            'amount': '12.50',
            'currency': 'USD'
        }
        result = generate_qif_entry(row, 'USD')
        expected = 'D2025-07-30\nNXIn\nT12.5\nO0.00\nCc\nPInterest\nMStock lending interest payment\n^'
        self.assertEqual(result, expected)

    def test_generate_qif_entry_nrt_usd(self):
        """Test generate_qif_entry with NRT (Non-Resident Tax) transaction in USD"""
        row = {
            'date': '2025-07-31',
            'transaction': 'NRT',
            'description': 'US Non-Resident Tax Withholding',
            'amount': '5.25',
            'currency': 'USD'
        }
        result = generate_qif_entry(row, 'USD')
        expected = 'D2025-07-31\nNXOut\nT5.25\nO0.00\nCc\nPUS Non-Resident Tax Withholding\nMUS Non-Resident Tax Withholding\n^'
        self.assertEqual(result, expected)

    def test_generate_qif_entry_trfout_transactions(self):
        """Test generate_qif_entry with various outgoing transfer transactions"""
        # Test TRFOUT
        row = {
            'date': '2025-08-01',
            'transaction': 'TRFOUT',
            'description': 'Transfer to external account',
            'amount': '200.00',
            'currency': 'CAD'
        }
        result = generate_qif_entry(row, 'CAD')
        expected = 'D2025-08-01\nT-200.0\nO0.00\nCc\nPTransfer to external account\n^'
        self.assertEqual(result, expected)

        # Test SPEND
        row = {
            'date': '2025-08-02',
            'transaction': 'SPEND',
            'description': 'Card purchase',
            'amount': '50.00',
            'currency': 'USD'
        }
        result = generate_qif_entry(row, 'USD')
        expected = 'D2025-08-02\nT-50.0\nO0.00\nCc\nPCard purchase\n^'
        self.assertEqual(result, expected)

        # Test E_TRFOUT
        row = {
            'date': '2025-08-03',
            'transaction': 'E_TRFOUT',
            'description': 'Electronic transfer out',
            'amount': '100.00',
            'currency': 'CAD'
        }
        result = generate_qif_entry(row, 'CAD')
        expected = 'D2025-08-03\nT-100.0\nO0.00\nCc\nPElectronic transfer out\n^'
        self.assertEqual(result, expected)

        # Test EFTOUT
        row = {
            'date': '2025-08-04',
            'transaction': 'EFTOUT',
            'description': 'EFT withdrawal',
            'amount': '75.00',
            'currency': 'USD'
        }
        result = generate_qif_entry(row, 'USD')
        expected = 'D2025-08-04\nT-75.0\nO0.00\nCc\nPEFT withdrawal\n^'
        self.assertEqual(result, expected)

        # Test AFT_OUT
        row = {
            'date': '2025-08-05',
            'transaction': 'AFT_OUT',
            'description': 'Automated transfer out',
            'amount': '125.00',
            'currency': 'CAD'
        }
        result = generate_qif_entry(row, 'CAD')
        expected = 'D2025-08-05\nT-125.0\nO0.00\nCc\nPAutomated transfer out\n^'
        self.assertEqual(result, expected)

    def test_generate_qif_entry_incoming_transactions(self):
        """Test generate_qif_entry with various incoming transactions"""
        # Test CASHBACK
        row = {
            'date': '2025-08-06',
            'transaction': 'CASHBACK',
            'description': 'Credit card cashback',
            'amount': '15.00',
            'currency': 'USD'
        }
        result = generate_qif_entry(row, 'USD')
        expected = 'D2025-08-06\nT15.0\nO0.00\nCc\nPCredit card cashback\n^'
        self.assertEqual(result, expected)

        # Test EFT
        row = {
            'date': '2025-08-07',
            'transaction': 'EFT',
            'description': 'Electronic funds transfer',
            'amount': '300.00',
            'currency': 'CAD'
        }
        result = generate_qif_entry(row, 'CAD')
        expected = 'D2025-08-07\nT300.0\nO0.00\nCc\nPElectronic funds transfer\n^'
        self.assertEqual(result, expected)

        # Test INT
        row = {
            'date': '2025-08-08',
            'transaction': 'INT',
            'description': 'Interest payment',
            'amount': '8.50',
            'currency': 'USD'
        }
        result = generate_qif_entry(row, 'USD')
        expected = 'D2025-08-08\nT8.5\nO0.00\nCc\nPInterest payment\n^'
        self.assertEqual(result, expected)

        # Test TRFIN
        row = {
            'date': '2025-08-09',
            'transaction': 'TRFIN',
            'description': 'Transfer in from external',
            'amount': '250.00',
            'currency': 'CAD'
        }
        result = generate_qif_entry(row, 'CAD')
        expected = 'D2025-08-09\nT250.0\nO0.00\nCc\nPTransfer in from external\n^'
        self.assertEqual(result, expected)

        # Test TRFINTF
        row = {
            'date': '2025-08-10',
            'transaction': 'TRFINTF',
            'description': 'Internal transfer fee',
            'amount': '2.00',
            'currency': 'USD'
        }
        result = generate_qif_entry(row, 'USD')
        expected = 'D2025-08-10\nT2.0\nO0.00\nCc\nPInternal transfer fee\n^'
        self.assertEqual(result, expected)

        # Test REFUND
        row = {
            'date': '2025-08-11',
            'transaction': 'REFUND',
            'description': 'Purchase refund',
            'amount': '45.00',
            'currency': 'CAD'
        }
        result = generate_qif_entry(row, 'CAD')
        expected = 'D2025-08-11\nT45.0\nO0.00\nCc\nPPurchase refund\n^'
        self.assertEqual(result, expected)

    def test_generate_qif_entry_ignored_transactions(self):
        """Test generate_qif_entry with ignored transaction types"""
        ignored_types = ['RECALL', 'LOAN', 'STKDIS', 'STKREORG']

        for transaction_type in ignored_types:
            row = {
                'date': '2025-08-12',
                'transaction': transaction_type,
                'description': f'{transaction_type} transaction',
                'amount': '100.00',
                'currency': 'USD'
            }
            result = generate_qif_entry(row, 'USD')
            self.assertIsNone(result, f"Transaction type {transaction_type} should return None")

    def test_generate_qif_entry_currency_filtering(self):
        """Test generate_qif_entry currency filtering"""
        # USD transaction with CAD target - should return None
        row = {
            'date': '2025-08-13',
            'transaction': 'BUY',
            'description': 'AAPL - 5.0 shares',
            'amount': '-750.00',
            'currency': 'USD'
        }
        result = generate_qif_entry(row, 'CAD')
        self.assertIsNone(result)

        # CAD transaction with USD target - should return None
        row = {
            'date': '2025-08-14',
            'transaction': 'BUY',
            'description': 'SHOP - 3.0 shares',
            'amount': '-450.00',
            'currency': 'CAD'
        }
        result = generate_qif_entry(row, 'USD')
        self.assertIsNone(result)

        # Matching currencies should work
        row = {
            'date': '2025-08-15',
            'transaction': 'BUY',
            'description': 'MSFT - 2.0 shares',
            'amount': '-600.00',
            'currency': 'USD'
        }
        result = generate_qif_entry(row, 'USD')
        self.assertIsNotNone(result)

    def test_generate_qif_entry_invalid_transaction_type(self):
        """Test generate_qif_entry with invalid transaction type"""
        row = {
            'date': '2025-08-16',
            'transaction': 'INVALID_TYPE',
            'description': 'Unknown transaction',
            'amount': '100.00',
            'currency': 'USD'
        }

        with self.assertRaises(ValueError) as context:
            generate_qif_entry(row, 'USD')

        self.assertIn('Invalid transaction type: INVALID_TYPE', str(context.exception))

    def test_generate_qif_entry_fractional_shares_and_amounts(self):
        """Test generate_qif_entry with fractional shares and amounts"""
        # Test fractional shares
        row = {
            'date': '2025-08-17',
            'transaction': 'BUY',
            'description': 'GOOGL - 2.5 shares',
            'amount': '-6250.75',
            'currency': 'USD'
        }
        result = generate_qif_entry(row, 'USD')
        expected = 'D2025-08-17\nNBuy\nYGOOGL-CT\nI2500.3\nQ2.5\nT6250.75\nO0.00\nCc\n^'
        self.assertEqual(result, expected)

        # Test fractional options contracts and fees
        row = {
            'date': '2025-08-18',
            'transaction': 'BUYTOOPEN',
            'description': 'NVDA 800.00 USD CALL 2025-09-15: Bought 3 contract (executed at 2025-08-18), Fee: $2.25',
            'amount': '-1502.25',
            'currency': 'USD'
        }
        result = generate_qif_entry(row, 'USD')
        expected = 'D2025-08-18\nNBuy\nYNVDA 800.00 USD CALL 2025-09-15\nI500.0\nQ3\nT1502.25\nO2.25\nCc\n^'
        self.assertEqual(result, expected)

    def test_generate_qif_entry_negative_amounts_handling(self):
        """Test generate_qif_entry handles negative amounts correctly"""
        # BUY transactions typically have negative amounts in CSV
        row = {
            'date': '2025-08-19',
            'transaction': 'BUY',
            'description': 'AMZN - 1.0 shares',
            'amount': '-3500.00',  # Negative amount
            'currency': 'USD'
        }
        result = generate_qif_entry(row, 'USD')
        expected = 'D2025-08-19\nNBuy\nYAMZN-CT\nI3500.0\nQ1.0\nT3500.0\nO0.00\nCc\n^'
        self.assertEqual(result, expected)

        # SELL transactions typically have positive amounts in CSV
        row = {
            'date': '2025-08-20',
            'transaction': 'SELL',
            'description': 'AMZN - 1.0 shares',
            'amount': '3600.00',  # Positive amount
            'currency': 'USD'
        }
        result = generate_qif_entry(row, 'USD')
        expected = 'D2025-08-20\nNSell\nYAMZN-CT\nI3600.0\nQ1.0\nT3600.0\nO0.00\nCc\n^'
        self.assertEqual(result, expected)

    # Tests for read_config function
    def test_read_config_valid_yaml_file(self):
        """Test read_config with valid YAML configuration file"""
        # Create a temporary YAML file with valid configuration matching actual format
        config_data = {
            'H12345678CAD-CAD': {
                'nickname': 'My-TFSA',
                'type': 'Investment'
            },
            'WK23MTV36CAD-CAD': {
                'nickname': 'My-Chequeing',
                'type': 'Checking'
            },
            'WK5DRT238USD-USD': {
                'nickname': 'My-USD-Saving',
                'type': 'Checking'
            }
        }

        with tempfile.NamedTemporaryFile(mode='w', suffix='.yml', delete=False) as temp_file:
            yaml.dump(config_data, temp_file)
            temp_file_path = temp_file.name

        try:
            result = read_config(temp_file_path)
            self.assertEqual(result, config_data)

            # Verify specific account configurations
            self.assertIn('H12345678CAD-CAD', result)
            self.assertEqual(result['H12345678CAD-CAD']['nickname'], 'My-TFSA')
            self.assertEqual(result['H12345678CAD-CAD']['type'], 'Investment')

            self.assertIn('WK23MTV36CAD-CAD', result)
            self.assertEqual(result['WK23MTV36CAD-CAD']['nickname'], 'My-Chequeing')
            self.assertEqual(result['WK23MTV36CAD-CAD']['type'], 'Checking')

            self.assertIn('WK5DRT238USD-USD', result)
            self.assertEqual(result['WK5DRT238USD-USD']['nickname'], 'My-USD-Saving')
            self.assertEqual(result['WK5DRT238USD-USD']['type'], 'Checking')
        finally:
            os.unlink(temp_file_path)

    def test_read_config_empty_yaml_file(self):
        """Test read_config with empty YAML file"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yml', delete=False) as temp_file:
            temp_file.write('')  # Empty file
            temp_file_path = temp_file.name

        try:
            result = read_config(temp_file_path)
            self.assertIsNone(result)  # Empty YAML file returns None
        finally:
            os.unlink(temp_file_path)

    def test_read_config_yaml_with_comments(self):
        """Test read_config with YAML file containing comments"""
        yaml_content = """
# Account configuration file
# Investment accounts
H12345678CAD-CAD:
  nickname: My-TFSA  # Tax-Free Savings Account
  type: Investment

# Checking accounts
WK23MTV36CAD-CAD:
  nickname: My-Chequeing
  type: Checking
"""

        with tempfile.NamedTemporaryFile(mode='w', suffix='.yml', delete=False) as temp_file:
            temp_file.write(yaml_content)
            temp_file_path = temp_file.name

        try:
            result = read_config(temp_file_path)

            # Comments should be ignored, only data should be parsed
            self.assertEqual(len(result), 2)
            self.assertIn('H12345678CAD-CAD', result)
            self.assertIn('WK23MTV36CAD-CAD', result)
            self.assertEqual(result['H12345678CAD-CAD']['nickname'], 'My-TFSA')
            self.assertEqual(result['WK23MTV36CAD-CAD']['type'], 'Checking')
        finally:
            os.unlink(temp_file_path)

    def test_read_config_multiple_account_types(self):
        """Test read_config with multiple Investment and Checking accounts"""
        config_data = {
            'H16530307CAD-USD': {
                'nickname': 'My-Unregistered-USD',
                'type': 'Investment'
            },
            'H16530307CAD-CAD': {
                'nickname': 'My-Unregistered-CAD',
                'type': 'Investment'
            },
            'HQ8KJW805CAD-USD': {
                'nickname': 'My-Option-Trading',
                'type': 'Investment'
            },
            'WK23MTV36CAD-CAD': {
                'nickname': 'My-Chequeing',
                'type': 'Checking'
            }
        }

        with tempfile.NamedTemporaryFile(mode='w', suffix='.yml', delete=False) as temp_file:
            yaml.dump(config_data, temp_file)
            temp_file_path = temp_file.name

        try:
            result = read_config(temp_file_path)
            self.assertEqual(result, config_data)

            # Verify all accounts are loaded correctly
            self.assertEqual(len(result), 4)

            # Check Investment accounts
            investment_accounts = [k for k, v in result.items() if v['type'] == 'Investment']
            self.assertEqual(len(investment_accounts), 3)

            # Check Checking accounts
            checking_accounts = [k for k, v in result.items() if v['type'] == 'Checking']
            self.assertEqual(len(checking_accounts), 1)
        finally:
            os.unlink(temp_file_path)

    def test_read_config_yaml_with_special_characters_in_nicknames(self):
        """Test read_config with YAML containing special characters in nicknames"""
        config_data = {
            'SPECIAL-ACCOUNT-123': {
                'nickname': 'My-Special_Account.Test',
                'type': 'Investment'
            },
            'TEST-ACCOUNT-456': {
                'nickname': 'Test-Account-With-Dashes',
                'type': 'Checking'
            }
        }

        with tempfile.NamedTemporaryFile(mode='w', suffix='.yml', delete=False, encoding='utf-8') as temp_file:
            yaml.dump(config_data, temp_file, allow_unicode=True)
            temp_file_path = temp_file.name

        try:
            result = read_config(temp_file_path)
            self.assertEqual(result, config_data)

            # Verify special characters in nicknames are preserved
            self.assertEqual(result['SPECIAL-ACCOUNT-123']['nickname'], 'My-Special_Account.Test')
            self.assertEqual(result['TEST-ACCOUNT-456']['nickname'], 'Test-Account-With-Dashes')
        finally:
            os.unlink(temp_file_path)

    def test_read_config_file_not_found(self):
        """Test read_config with non-existent file"""
        non_existent_file = '/path/that/does/not/exist/config.yml'

        with self.assertRaises(FileNotFoundError):
            read_config(non_existent_file)

    def test_read_config_invalid_yaml_syntax(self):
        """Test read_config with invalid YAML syntax"""
        invalid_yaml_content = """
H12345678CAD-CAD:
  nickname: My-TFSA
  type: Investment
    invalid_indentation: true
WK23MTV36CAD-CAD
  missing_colon_here
    nickname: My-Chequeing
"""

        with tempfile.NamedTemporaryFile(mode='w', suffix='.yml', delete=False) as temp_file:
            temp_file.write(invalid_yaml_content)
            temp_file_path = temp_file.name

        try:
            with self.assertRaises(yaml.YAMLError):
                read_config(temp_file_path)
        finally:
            os.unlink(temp_file_path)

    def test_read_config_missing_required_fields(self):
        """Test read_config with YAML missing required fields"""
        # Test with missing 'type' field
        config_data = {
            'INCOMPLETE-ACCOUNT': {
                'nickname': 'Missing-Type-Field'
                # Missing 'type' field
            }
        }

        with tempfile.NamedTemporaryFile(mode='w', suffix='.yml', delete=False) as temp_file:
            yaml.dump(config_data, temp_file)
            temp_file_path = temp_file.name

        try:
            result = read_config(temp_file_path)
            # Function should still return the data, validation happens elsewhere
            self.assertEqual(result, config_data)
            self.assertNotIn('type', result['INCOMPLETE-ACCOUNT'])
        finally:
            os.unlink(temp_file_path)

    def test_read_config_invalid_account_types(self):
        """Test read_config with invalid account types"""
        config_data = {
            'INVALID-TYPE-ACCOUNT': {
                'nickname': 'Invalid-Type-Test',
                'type': 'InvalidType'  # Should be 'Investment' or 'Checking'
            }
        }

        with tempfile.NamedTemporaryFile(mode='w', suffix='.yml', delete=False) as temp_file:
            yaml.dump(config_data, temp_file)
            temp_file_path = temp_file.name

        try:
            result = read_config(temp_file_path)
            # Function should still return the data, validation happens elsewhere
            self.assertEqual(result, config_data)
            self.assertEqual(result['INVALID-TYPE-ACCOUNT']['type'], 'InvalidType')
        finally:
            os.unlink(temp_file_path)

    def test_read_config_large_yaml_file(self):
        """Test read_config with a large YAML file"""
        # Generate a large configuration with many accounts
        config_data = {}
        for i in range(50):
            account_id = f'ACCOUNT{i:03d}CAD-CAD'
            config_data[account_id] = {
                'nickname': f'Test-Account-{i}',
                'type': 'Investment' if i % 2 == 0 else 'Checking'
            }

        with tempfile.NamedTemporaryFile(mode='w', suffix='.yml', delete=False) as temp_file:
            yaml.dump(config_data, temp_file)
            temp_file_path = temp_file.name

        try:
            result = read_config(temp_file_path)
            self.assertEqual(result, config_data)
            self.assertEqual(len(result), 50)

            # Verify a few random entries
            self.assertEqual(result['ACCOUNT000CAD-CAD']['nickname'], 'Test-Account-0')
            self.assertEqual(result['ACCOUNT000CAD-CAD']['type'], 'Investment')
            self.assertEqual(result['ACCOUNT001CAD-CAD']['type'], 'Checking')
        finally:
            os.unlink(temp_file_path)

    @patch('builtins.open', side_effect=IOError("Disk full"))
    def test_read_config_io_error(self, mock_open):
        """Test read_config with I/O error during file reading"""
        with self.assertRaises(IOError):
            read_config('some_file.yml')

    def test_read_config_actual_accounts_file(self):
        """Test read_config with the actual accounts.yml file if it exists"""
        # This test uses the real accounts.yml file in the project
        if os.path.exists('accounts.yml'):
            result = read_config('accounts.yml')

            # Verify the structure matches expected format
            self.assertIsInstance(result, dict)

            # Check that all accounts have required fields
            for account_id, account_config in result.items():
                self.assertIn('nickname', account_config)
                self.assertIn('type', account_config)
                self.assertIsInstance(account_config['nickname'], str)
                self.assertIn(account_config['type'], ['Investment', 'Checking'])

                # Verify account ID format (should end with -CAD or -USD)
                self.assertTrue(account_id.endswith('-CAD') or account_id.endswith('-USD'))

                # Verify only expected fields are present
                expected_fields = {'nickname', 'type'}
                actual_fields = set(account_config.keys())
                self.assertEqual(actual_fields, expected_fields,
                               f"Account {account_id} has unexpected fields: {actual_fields - expected_fields}")
        else:
            self.skipTest("accounts.yml file not found in project directory")

if __name__ == '__main__':
    unittest.main()
