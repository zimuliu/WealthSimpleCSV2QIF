import os
import shutil
import tempfile
import unittest
from unittest.mock import MagicMock, mock_open, patch

import yaml

from app.main import (
    FORMAT_ACTIVITIES_EXPORT,
    FORMAT_MONTHLY_STATEMENT,
    _extract_activities_export_month,
    _get_investment_account_ids,
    convert_activities_row_to_legacy,
    detect_csv_format,
    export_qif_files,
    extract_account_name,
    extract_option_info,
    extract_symbol,
    extract_unit,
    generate_qif_entry,
    map_activities_transaction_type,
    read_config,
    read_csv_files,
)


class TestMain(unittest.TestCase):
    def test_extract_account_name_valid_format(self):
        """Test extract_account_name with valid filename formats"""
        # Test with standard account name format
        filename = "monthly-statement-transactions-HQ8KJW805CAD-2025-07-01.csv"
        result = extract_account_name(filename)
        self.assertEqual(result, "HQ8KJW805CAD")

        # Test with different account name
        filename = "monthly-statement-transactions-AB1234567USD-2024-12-31.csv"
        result = extract_account_name(filename)
        self.assertEqual(result, "AB1234567USD")

        # Test with another valid format
        filename = "monthly-statement-transactions-XY9876543CAD-2023-06-15.csv"
        result = extract_account_name(filename)
        self.assertEqual(result, "XY9876543CAD")

    def test_extract_account_name_different_dates(self):
        """Test extract_account_name with different date formats"""
        # Test with different months
        filename = "monthly-statement-transactions-TEST123456-2025-01-01.csv"
        result = extract_account_name(filename)
        self.assertEqual(result, "TEST123456")

        # Test with leap year date
        filename = "monthly-statement-transactions-LEAP987654-2024-02-29.csv"
        result = extract_account_name(filename)
        self.assertEqual(result, "LEAP987654")

        # Test with end of year date
        filename = "monthly-statement-transactions-YEAR123456-2023-12-31.csv"
        result = extract_account_name(filename)
        self.assertEqual(result, "YEAR123456")

    def test_extract_account_name_invalid_format(self):
        """Test extract_account_name with invalid filename formats"""
        # Test with wrong prefix
        filename = "daily-statement-transactions-HQ8KJW805CAD-2025-07-01.csv"
        result = extract_account_name(filename)
        self.assertIsNone(result)

        # Test with missing date
        filename = "monthly-statement-transactions-HQ8KJW805CAD.csv"
        result = extract_account_name(filename)
        self.assertIsNone(result)

        # Test with wrong file extension
        filename = "monthly-statement-transactions-HQ8KJW805CAD-2025-07-01.txt"
        result = extract_account_name(filename)
        self.assertIsNone(result)

        # Test with malformed date
        filename = "monthly-statement-transactions-HQ8KJW805CAD-25-07-01.csv"
        result = extract_account_name(filename)
        self.assertIsNone(result)

        # Test with invalid date format (wrong separators)
        filename = "monthly-statement-transactions-HQ8KJW805CAD-2025/07/01.csv"
        result = extract_account_name(filename)
        self.assertIsNone(result)

    def test_extract_account_name_edge_cases(self):
        """Test extract_account_name with edge cases"""
        # Test with empty string
        result = extract_account_name("")
        self.assertIsNone(result)

        # Test with completely different filename
        filename = "some-other-file.csv"
        result = extract_account_name(filename)
        self.assertIsNone(result)

        # Test with partial match
        filename = "monthly-statement-transactions-"
        result = extract_account_name(filename)
        self.assertIsNone(result)

    def test_extract_account_name_account_name_variations(self):
        """Test extract_account_name with different account name patterns"""
        # Test with numeric account name
        filename = "monthly-statement-transactions-1234567890-2025-07-01.csv"
        result = extract_account_name(filename)
        self.assertEqual(result, "1234567890")

        # Test with mixed alphanumeric
        filename = "monthly-statement-transactions-ABC123DEF456-2025-07-01.csv"
        result = extract_account_name(filename)
        self.assertEqual(result, "ABC123DEF456")

        # Test with single character account name
        filename = "monthly-statement-transactions-A-2025-07-01.csv"
        result = extract_account_name(filename)
        self.assertEqual(result, "A")

    def test_extract_account_name_special_characters(self):
        """Test extract_account_name with special characters in account names"""
        # The regex pattern uses \w+ which only matches word characters (letters, digits, underscore)
        # Test with underscore (should work)
        filename = "monthly-statement-transactions-TEST_123_CAD-2025-07-01.csv"
        result = extract_account_name(filename)
        self.assertEqual(result, "TEST_123_CAD")

        # Test with hyphen in account name (should not work with current regex)
        filename = "monthly-statement-transactions-TEST-123-CAD-2025-07-01.csv"
        result = extract_account_name(filename)
        # This should return None because the regex stops at the first hyphen
        self.assertIsNone(result)

        # Test with space in account name (should not work)
        filename = "monthly-statement-transactions-TEST 123 CAD-2025-07-01.csv"
        result = extract_account_name(filename)
        self.assertIsNone(result)

    @patch("os.listdir")
    @patch("app.main.read_config")
    @patch(
        "builtins.open",
        new_callable=mock_open,
        read_data="date,transaction,description,amount,currency\n2025-07-01,BUY,AAPL - 10.0 shares,-1500.00,USD\n",
    )
    def test_read_csv_files(self, mock_open_file, mock_read_config, mock_listdir):
        mock_listdir.return_value = [
            "monthly-statement-transactions-TEST123456-2025-07-01.csv"
        ]
        mock_read_config.return_value = {"cdr_symbols": ["TSLA", "DIS", "NVDA", "AAPL"]}
        csv_data, source_files = read_csv_files("input_folder", "dummy_config.yml")
        # Should have 2 accounts (TEST123456-USD and TEST123456-CAD)
        self.assertEqual(len(csv_data), 2)
        # Check that both currency accounts exist
        self.assertIn("TEST123456-USD", csv_data)
        self.assertIn("TEST123456-CAD", csv_data)
        # USD account should have 1 transaction, CAD should be empty
        self.assertEqual(len(csv_data["TEST123456-USD"]), 1)
        self.assertEqual(len(csv_data["TEST123456-CAD"]), 0)
        # Check source files tracking
        self.assertIn("TEST123456-USD", source_files)
        self.assertIn("TEST123456-CAD", source_files)
        self.assertIn(
            "monthly-statement-transactions-TEST123456-2025-07-01.csv",
            source_files["TEST123456-USD"],
        )

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
        description = (
            "SPY 450.00 USD CALL 2025-07-25: Bought 2 contract (executed at 2025-07-23)"
        )
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
        self.assertEqual(
            result, 10.0
        )  # Should still work as regex looks for pattern anywhere

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
        # Test regular symbols with USD - should have no suffix
        result = extract_symbol("AAPL - 10.0 shares", "USD")
        self.assertEqual(result, "AAPL")

        result = extract_symbol("MSFT - 5.0 shares", "USD")
        self.assertEqual(result, "MSFT")

        result = extract_symbol("GOOGL - 2.0 shares", "USD")
        self.assertEqual(result, "GOOGL")

    def test_extract_symbol_standard_symbols_cad(self):
        """Test extract_symbol with standard (non-CDR) symbols in CAD currency"""
        # Test non-CDR symbols with CAD - should get -CT suffix
        cdr_symbols = ["TSLA", "DIS", "NVDA", "AAPL"]
        result = extract_symbol("SHOP - 15.0 shares", "CAD", cdr_symbols)
        self.assertEqual(result, "SHOP-CT")

        result = extract_symbol("RY - 10.0 shares", "CAD", cdr_symbols)
        self.assertEqual(result, "RY-CT")

        result = extract_symbol("TD - 8.0 shares", "CAD", cdr_symbols)
        self.assertEqual(result, "TD-CT")

    def test_extract_symbol_cdr_symbols_cad(self):
        """Test extract_symbol with CDR symbols in CAD currency"""
        # Test CDR symbols (TSLA, DIS, NVDA, AAPL) with CAD - should get -QH suffix
        cdr_symbols = ["TSLA", "DIS", "NVDA", "AAPL"]
        result = extract_symbol("TSLA - 5.0 shares", "CAD", cdr_symbols)
        self.assertEqual(result, "TSLA-QH")

        result = extract_symbol("DIS - 10.0 shares", "CAD", cdr_symbols)
        self.assertEqual(result, "DIS-QH")

        result = extract_symbol("NVDA - 2.0 shares", "CAD", cdr_symbols)
        self.assertEqual(result, "NVDA-QH")

        result = extract_symbol("AAPL - 15.0 shares", "CAD", cdr_symbols)
        self.assertEqual(result, "AAPL-QH")

    def test_extract_symbol_cdr_symbols_usd(self):
        """Test extract_symbol with CDR symbols in USD currency"""
        # CDR symbols with USD should have no suffix
        # Only CDR symbols with CAD currency get -QH suffix
        cdr_symbols = ["TSLA", "DIS", "NVDA", "AAPL"]
        result = extract_symbol("TSLA - 5.0 shares", "USD", cdr_symbols)
        self.assertEqual(result, "TSLA")

        result = extract_symbol("DIS - 10.0 shares", "USD", cdr_symbols)
        self.assertEqual(result, "DIS")

        result = extract_symbol("NVDA - 2.0 shares", "USD", cdr_symbols)
        self.assertEqual(result, "NVDA")

        result = extract_symbol("AAPL - 15.0 shares", "USD", cdr_symbols)
        self.assertEqual(result, "AAPL")

    def test_extract_symbol_case_insensitive_input(self):
        """Test extract_symbol with case-insensitive input - should always return uppercase"""
        cdr_symbols = ["TSLA", "DIS", "NVDA", "AAPL"]
        # Test lowercase symbols - should be converted to uppercase
        result = extract_symbol("aapl - 10.0 shares", "USD", cdr_symbols)
        self.assertEqual(result, "AAPL")

        result = extract_symbol("tsla - 5.0 shares", "CAD", cdr_symbols)
        self.assertEqual(
            result, "TSLA-QH"
        )  # lowercase tsla becomes TSLA and matches CDR

        result = extract_symbol("shop - 15.0 shares", "CAD", cdr_symbols)
        self.assertEqual(result, "SHOP-CT")

        # Test mixed case symbols
        result = extract_symbol("AaPl - 10.0 shares", "CAD", cdr_symbols)
        self.assertEqual(result, "AAPL-QH")

        result = extract_symbol("TsLa - 5.0 shares", "USD", cdr_symbols)
        self.assertEqual(result, "TSLA")

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
        self.assertEqual(result, "SOME")

    def test_extract_symbol_currency_case_sensitivity(self):
        """Test extract_symbol currency case sensitivity"""
        cdr_symbols = ["TSLA", "DIS", "NVDA", "AAPL"]
        # Currency comparison is case-sensitive - lowercase 'cad' is not 'USD',
        # so it falls through to the CAD suffix logic where AAPL is a CDR symbol
        result = extract_symbol("AAPL - 10.0 shares", "cad", cdr_symbols)
        self.assertEqual(result, "AAPL-QH")  # lowercase 'cad' != 'USD', so CDR suffix applies

        result = extract_symbol("aapl - 10.0 shares", "CAD", cdr_symbols)
        self.assertEqual(result, "AAPL-QH")  # uppercase 'CAD' matches

    def test_extract_symbol_period_replacement(self):
        """Test extract_symbol replaces periods with hyphens"""
        cdr_symbols = ["TSLA", "DIS", "NVDA", "AAPL"]
        # Test symbol with period - should be replaced with hyphen
        result = extract_symbol("ETHX.B - 5.0 shares", "CAD", cdr_symbols)
        self.assertEqual(result, "ETHX-B-CT")

        result = extract_symbol("BRK.A - 1.0 shares", "USD", cdr_symbols)
        self.assertEqual(result, "BRK-A")

        result = extract_symbol("brk.b - 2.0 shares", "CAD", cdr_symbols)
        self.assertEqual(result, "BRK-B-CT")

    def test_extract_symbol_without_cdr_symbols(self):
        """Test extract_symbol without CDR symbols list"""
        # Without CDR symbols, all CAD symbols get -CT suffix
        result = extract_symbol("TSLA - 5.0 shares", "CAD")
        self.assertEqual(result, "TSLA-CT")

        result = extract_symbol("AAPL - 10.0 shares", "CAD", [])
        self.assertEqual(result, "AAPL-CT")

        # USD symbols still have no suffix
        result = extract_symbol("AAPL - 10.0 shares", "USD")
        self.assertEqual(result, "AAPL")

    # Tests for generate_qif_entry function
    def test_generate_qif_entry_buy_transaction_usd(self):
        """Test generate_qif_entry with BUY transaction in USD"""
        row = {
            "date": "2025-07-15",
            "transaction": "BUY",
            "description": "AAPL - 10.0 shares",
            "amount": "-1500.00",
            "currency": "USD",
        }
        result = generate_qif_entry(row, "USD")
        expected = "D2025-07-15\nNBuy\nYAAPL\nI150.0\nQ10.0\nT1500.0\nO0.00\nCc\n^"
        self.assertEqual(result, expected)

    def test_generate_qif_entry_buy_transaction_cad(self):
        """Test generate_qif_entry with BUY transaction in CAD"""
        row = {
            "date": "2025-07-16",
            "transaction": "BUY",
            "description": "SHOP - 5.0 shares",
            "amount": "-750.00",
            "currency": "CAD",
        }
        result = generate_qif_entry(row, "CAD")
        expected = "D2025-07-16\nNBuy\nYSHOP-CT\nI150.0\nQ5.0\nT750.0\nO0.00\nCc\n^"
        self.assertEqual(result, expected)

    def test_generate_qif_entry_buy_cdr_symbol_cad(self):
        """Test generate_qif_entry with BUY transaction for CDR symbol in CAD"""
        row = {
            "date": "2025-07-17",
            "transaction": "BUY",
            "description": "TSLA - 2.0 shares",
            "amount": "-500.00",
            "currency": "CAD",
        }
        cdr_symbols = ["TSLA", "DIS", "NVDA", "AAPL"]
        result = generate_qif_entry(row, "CAD", cdr_symbols=cdr_symbols)
        expected = "D2025-07-17\nNBuy\nYTSLA-QH\nI250.0\nQ2.0\nT500.0\nO0.00\nCc\n^"
        self.assertEqual(result, expected)

    def test_generate_qif_entry_sell_transaction_usd(self):
        """Test generate_qif_entry with SELL transaction in USD"""
        row = {
            "date": "2025-07-18",
            "transaction": "SELL",
            "description": "MSFT - 8.0 shares",
            "amount": "2400.00",
            "currency": "USD",
        }
        result = generate_qif_entry(row, "USD")
        expected = "D2025-07-18\nNSell\nYMSFT\nI300.0\nQ8.0\nT2400.0\nO0.00\nCc\n^"
        self.assertEqual(result, expected)

    def test_generate_qif_entry_sell_transaction_cad(self):
        """Test generate_qif_entry with SELL transaction in CAD"""
        row = {
            "date": "2025-07-19",
            "transaction": "SELL",
            "description": "RY - 15.0 shares",
            "amount": "1800.00",
            "currency": "CAD",
        }
        result = generate_qif_entry(row, "CAD")
        expected = "D2025-07-19\nNSell\nYRY-CT\nI120.0\nQ15.0\nT1800.0\nO0.00\nCc\n^"
        self.assertEqual(result, expected)

    def test_generate_qif_entry_buytoopen_options_usd(self):
        """Test generate_qif_entry with BUYTOOPEN options transaction in USD"""
        row = {
            "date": "2025-07-23",
            "transaction": "BUYTOOPEN",
            "description": "SPY 450.00 USD CALL 2025-07-25: Bought 2 contract (executed at 2025-07-23), Fee: $1.50",
            "amount": "-320.50",
            "currency": "USD",
        }
        result = generate_qif_entry(row, "USD")
        expected = "D2025-07-23\nNBuy\nYSPY 450.00 USD CALL 2025-07-25\nI159.5\nQ2\nT320.5\nO1.5\nCc\n^"
        self.assertEqual(result, expected)

    def test_generate_qif_entry_selltoclose_options_usd(self):
        """Test generate_qif_entry with SELLTOCLOSE options transaction in USD"""
        row = {
            "date": "2025-07-25",
            "transaction": "SELLTOCLOSE",
            "description": "AAPL 180.00 USD PUT 2025-07-30: Sold 1 contract (executed at 2025-07-25), Fee: $0.75",
            "amount": "150.25",
            "currency": "USD",
        }
        result = generate_qif_entry(row, "USD")
        expected = "D2025-07-25\nNSell\nYAAPL 180.00 USD PUT 2025-07-30\nI151.0\nQ1\nT150.25\nO0.75\nCc\n^"
        self.assertEqual(result, expected)

    def test_generate_qif_entry_dividend_usd(self):
        """Test generate_qif_entry with DIV transaction in USD"""
        row = {
            "date": "2025-07-20",
            "transaction": "DIV",
            "description": "AAPL - Dividend payment",
            "amount": "25.50",
            "currency": "USD",
        }
        result = generate_qif_entry(row, "USD")
        expected = "D2025-07-20\nNDiv\nYAAPL\nT25.5\nO0.00\nCc\n^"
        self.assertEqual(result, expected)

    def test_generate_qif_entry_dividend_cad(self):
        """Test generate_qif_entry with DIV transaction in CAD"""
        row = {
            "date": "2025-07-21",
            "transaction": "DIV",
            "description": "TD - Dividend payment",
            "amount": "15.75",
            "currency": "CAD",
        }
        result = generate_qif_entry(row, "CAD")
        expected = "D2025-07-21\nNDiv\nYTD-CT\nT15.75\nO0.00\nCc\n^"
        self.assertEqual(result, expected)

    def test_generate_qif_entry_contribution_cad(self):
        """Test generate_qif_entry with CONT transaction in CAD"""
        row = {
            "date": "2025-07-16",
            "transaction": "CONT",
            "description": "Contribution (executed at 2025-07-16)",
            "amount": "1000.0",
            "currency": "CAD",
        }
        result = generate_qif_entry(row, "CAD")
        expected = "D2025-07-16\nNXIn\nT1000.0\nO0.00\nCc\nPContribution\nMContribution (executed at 2025-07-16)\n^"
        self.assertEqual(result, expected)

    def test_generate_qif_entry_contribution_usd(self):
        """Test generate_qif_entry with CONT transaction in USD"""
        row = {
            "date": "2025-07-22",
            "transaction": "CONT",
            "description": "Monthly contribution",
            "amount": "500.0",
            "currency": "USD",
        }
        result = generate_qif_entry(row, "USD")
        expected = "D2025-07-22\nNXIn\nT500.0\nO0.00\nCc\nPContribution\nMMonthly contribution\n^"
        self.assertEqual(result, expected)

    def test_generate_qif_entry_fplint_usd(self):
        """Test generate_qif_entry with FPLINT (stock lending interest) transaction in USD"""
        row = {
            "date": "2025-07-30",
            "transaction": "FPLINT",
            "description": "Stock lending interest payment",
            "amount": "12.50",
            "currency": "USD",
        }
        result = generate_qif_entry(row, "USD")
        expected = "D2025-07-30\nNXIn\nT12.5\nO0.00\nCc\nPInterest\nMStock lending interest payment\n^"
        self.assertEqual(result, expected)

    def test_generate_qif_entry_nrt_usd(self):
        """Test generate_qif_entry with NRT (Non-Resident Tax) transaction in USD"""
        row = {
            "date": "2025-07-31",
            "transaction": "NRT",
            "description": "US Non-Resident Tax Withholding",
            "amount": "5.25",
            "currency": "USD",
        }
        result = generate_qif_entry(row, "USD")
        expected = "D2025-07-31\nNXOut\nT5.25\nO0.00\nCc\nPUS Non-Resident Tax Withholding\nMUS Non-Resident Tax Withholding\n^"
        self.assertEqual(result, expected)

    def test_generate_qif_entry_trfout_transactions(self):
        """Test generate_qif_entry with various outgoing transfer transactions"""
        # Test TRFOUT
        row = {
            "date": "2025-08-01",
            "transaction": "TRFOUT",
            "description": "Transfer to external account",
            "amount": "200.00",
            "currency": "CAD",
        }
        result = generate_qif_entry(row, "CAD")
        expected = "D2025-08-01\nT-200.0\nO0.00\nCc\nPTransfer to external account\n^"
        self.assertEqual(result, expected)

        # Test SPEND
        row = {
            "date": "2025-08-02",
            "transaction": "SPEND",
            "description": "Card purchase",
            "amount": "50.00",
            "currency": "USD",
        }
        result = generate_qif_entry(row, "USD")
        expected = "D2025-08-02\nT-50.0\nO0.00\nCc\nPCard purchase\n^"
        self.assertEqual(result, expected)

        # Test E_TRFOUT
        row = {
            "date": "2025-08-03",
            "transaction": "E_TRFOUT",
            "description": "Electronic transfer out",
            "amount": "100.00",
            "currency": "CAD",
        }
        result = generate_qif_entry(row, "CAD")
        expected = "D2025-08-03\nT-100.0\nO0.00\nCc\nPElectronic transfer out\n^"
        self.assertEqual(result, expected)

        # Test EFTOUT
        row = {
            "date": "2025-08-04",
            "transaction": "EFTOUT",
            "description": "EFT withdrawal",
            "amount": "75.00",
            "currency": "USD",
        }
        result = generate_qif_entry(row, "USD")
        expected = "D2025-08-04\nT-75.0\nO0.00\nCc\nPEFT withdrawal\n^"
        self.assertEqual(result, expected)

        # Test AFT_OUT
        row = {
            "date": "2025-08-05",
            "transaction": "AFT_OUT",
            "description": "Automated transfer out",
            "amount": "125.00",
            "currency": "CAD",
        }
        result = generate_qif_entry(row, "CAD")
        expected = "D2025-08-05\nT-125.0\nO0.00\nCc\nPAutomated transfer out\n^"
        self.assertEqual(result, expected)

    def test_generate_qif_entry_incoming_transactions(self):
        """Test generate_qif_entry with various incoming transactions"""
        # Test CASHBACK
        row = {
            "date": "2025-08-06",
            "transaction": "CASHBACK",
            "description": "Credit card cashback",
            "amount": "15.00",
            "currency": "USD",
        }
        result = generate_qif_entry(row, "USD")
        expected = "D2025-08-06\nT15.0\nO0.00\nCc\nPCredit card cashback\n^"
        self.assertEqual(result, expected)

        # Test EFT
        row = {
            "date": "2025-08-07",
            "transaction": "EFT",
            "description": "Electronic funds transfer",
            "amount": "300.00",
            "currency": "CAD",
        }
        result = generate_qif_entry(row, "CAD")
        expected = "D2025-08-07\nT300.0\nO0.00\nCc\nPElectronic funds transfer\n^"
        self.assertEqual(result, expected)

        # Test INT
        row = {
            "date": "2025-08-08",
            "transaction": "INT",
            "description": "Interest payment",
            "amount": "8.50",
            "currency": "USD",
        }
        result = generate_qif_entry(row, "USD")
        expected = "D2025-08-08\nT8.5\nO0.00\nCc\nPInterest payment\n^"
        self.assertEqual(result, expected)

        # Test TRFIN
        row = {
            "date": "2025-08-09",
            "transaction": "TRFIN",
            "description": "Transfer in from external",
            "amount": "250.00",
            "currency": "CAD",
        }
        result = generate_qif_entry(row, "CAD")
        expected = "D2025-08-09\nT250.0\nO0.00\nCc\nPTransfer in from external\n^"
        self.assertEqual(result, expected)

        # Test TRFINTF
        row = {
            "date": "2025-08-10",
            "transaction": "TRFINTF",
            "description": "Internal transfer fee",
            "amount": "2.00",
            "currency": "USD",
        }
        result = generate_qif_entry(row, "USD")
        expected = "D2025-08-10\nT2.0\nO0.00\nCc\nPInternal transfer fee\n^"
        self.assertEqual(result, expected)

        # Test REFUND
        row = {
            "date": "2025-08-11",
            "transaction": "REFUND",
            "description": "Purchase refund",
            "amount": "45.00",
            "currency": "CAD",
        }
        result = generate_qif_entry(row, "CAD")
        expected = "D2025-08-11\nT45.0\nO0.00\nCc\nPPurchase refund\n^"
        self.assertEqual(result, expected)

    def test_generate_qif_entry_ignored_transactions(self):
        """Test generate_qif_entry with ignored transaction types"""
        ignored_types = ["RECALL", "LOAN", "STKDIS", "STKREORG"]

        for transaction_type in ignored_types:
            row = {
                "date": "2025-08-12",
                "transaction": transaction_type,
                "description": f"{transaction_type} transaction",
                "amount": "100.00",
                "currency": "USD",
            }
            result = generate_qif_entry(row, "USD")
            self.assertIsNone(
                result, f"Transaction type {transaction_type} should return None"
            )

    def test_generate_qif_entry_currency_filtering(self):
        """Test generate_qif_entry currency filtering"""
        # USD transaction with CAD target - should return None
        row = {
            "date": "2025-08-13",
            "transaction": "BUY",
            "description": "AAPL - 5.0 shares",
            "amount": "-750.00",
            "currency": "USD",
        }
        result = generate_qif_entry(row, "CAD")
        self.assertIsNone(result)

        # CAD transaction with USD target - should return None
        row = {
            "date": "2025-08-14",
            "transaction": "BUY",
            "description": "SHOP - 3.0 shares",
            "amount": "-450.00",
            "currency": "CAD",
        }
        result = generate_qif_entry(row, "USD")
        self.assertIsNone(result)

        # Matching currencies should work
        row = {
            "date": "2025-08-15",
            "transaction": "BUY",
            "description": "MSFT - 2.0 shares",
            "amount": "-600.00",
            "currency": "USD",
        }
        result = generate_qif_entry(row, "USD")
        self.assertIsNotNone(result)

    def test_generate_qif_entry_invalid_transaction_type(self):
        """Test generate_qif_entry with invalid transaction type"""
        row = {
            "date": "2025-08-16",
            "transaction": "INVALID_TYPE",
            "description": "Unknown transaction",
            "amount": "100.00",
            "currency": "USD",
        }

        with self.assertRaises(ValueError) as context:
            generate_qif_entry(row, "USD")

        self.assertIn("Invalid transaction type: INVALID_TYPE", str(context.exception))

    def test_generate_qif_entry_fractional_shares_and_amounts(self):
        """Test generate_qif_entry with fractional shares and amounts"""
        # Test fractional shares
        row = {
            "date": "2025-08-17",
            "transaction": "BUY",
            "description": "GOOGL - 2.5 shares",
            "amount": "-6250.75",
            "currency": "USD",
        }
        result = generate_qif_entry(row, "USD")
        expected = "D2025-08-17\nNBuy\nYGOOGL\nI2500.3\nQ2.5\nT6250.75\nO0.00\nCc\n^"
        self.assertEqual(result, expected)

        # Test fractional options contracts and fees
        row = {
            "date": "2025-08-18",
            "transaction": "BUYTOOPEN",
            "description": "NVDA 800.00 USD CALL 2025-09-15: Bought 3 contract (executed at 2025-08-18), Fee: $2.25",
            "amount": "-1502.25",
            "currency": "USD",
        }
        result = generate_qif_entry(row, "USD")
        expected = "D2025-08-18\nNBuy\nYNVDA 800.00 USD CALL 2025-09-15\nI500.0\nQ3\nT1502.25\nO2.25\nCc\n^"
        self.assertEqual(result, expected)

    def test_generate_qif_entry_negative_amounts_handling(self):
        """Test generate_qif_entry handles negative amounts correctly"""
        # BUY transactions typically have negative amounts in CSV
        row = {
            "date": "2025-08-19",
            "transaction": "BUY",
            "description": "AMZN - 1.0 shares",
            "amount": "-3500.00",  # Negative amount
            "currency": "USD",
        }
        result = generate_qif_entry(row, "USD")
        expected = "D2025-08-19\nNBuy\nYAMZN\nI3500.0\nQ1.0\nT3500.0\nO0.00\nCc\n^"
        self.assertEqual(result, expected)

        # SELL transactions typically have positive amounts in CSV
        row = {
            "date": "2025-08-20",
            "transaction": "SELL",
            "description": "AMZN - 1.0 shares",
            "amount": "3600.00",  # Positive amount
            "currency": "USD",
        }
        result = generate_qif_entry(row, "USD")
        expected = "D2025-08-20\nNSell\nYAMZN\nI3600.0\nQ1.0\nT3600.0\nO0.00\nCc\n^"
        self.assertEqual(result, expected)

    # Tests for read_config function
    def test_read_config_valid_yaml_file(self):
        """Test read_config with valid YAML configuration file"""
        # Create a temporary YAML file with valid configuration matching actual format
        config_data = {
            "H12345678CAD-CAD": {"nickname": "My-TFSA", "type": "Investment"},
            "WK23MTV36CAD-CAD": {"nickname": "My-Chequeing", "type": "Checking"},
            "WK5DRT238USD-USD": {"nickname": "My-USD-Saving", "type": "Checking"},
        }

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".yml", delete=False
        ) as temp_file:
            yaml.dump(config_data, temp_file)
            temp_file_path = temp_file.name

        try:
            result = read_config(temp_file_path)
            self.assertEqual(result, config_data)

            # Verify specific account configurations
            self.assertIn("H12345678CAD-CAD", result)
            self.assertEqual(result["H12345678CAD-CAD"]["nickname"], "My-TFSA")
            self.assertEqual(result["H12345678CAD-CAD"]["type"], "Investment")

            self.assertIn("WK23MTV36CAD-CAD", result)
            self.assertEqual(result["WK23MTV36CAD-CAD"]["nickname"], "My-Chequeing")
            self.assertEqual(result["WK23MTV36CAD-CAD"]["type"], "Checking")

            self.assertIn("WK5DRT238USD-USD", result)
            self.assertEqual(result["WK5DRT238USD-USD"]["nickname"], "My-USD-Saving")
            self.assertEqual(result["WK5DRT238USD-USD"]["type"], "Checking")
        finally:
            os.unlink(temp_file_path)

    def test_read_config_empty_yaml_file(self):
        """Test read_config with empty YAML file"""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".yml", delete=False
        ) as temp_file:
            temp_file.write("")  # Empty file
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

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".yml", delete=False
        ) as temp_file:
            temp_file.write(yaml_content)
            temp_file_path = temp_file.name

        try:
            result = read_config(temp_file_path)

            # Comments should be ignored, only data should be parsed
            self.assertEqual(len(result), 2)
            self.assertIn("H12345678CAD-CAD", result)
            self.assertIn("WK23MTV36CAD-CAD", result)
            self.assertEqual(result["H12345678CAD-CAD"]["nickname"], "My-TFSA")
            self.assertEqual(result["WK23MTV36CAD-CAD"]["type"], "Checking")
        finally:
            os.unlink(temp_file_path)

    def test_read_config_multiple_account_types(self):
        """Test read_config with multiple Investment and Checking accounts"""
        config_data = {
            "H16530307CAD-USD": {
                "nickname": "My-Unregistered-USD",
                "type": "Investment",
            },
            "H16530307CAD-CAD": {
                "nickname": "My-Unregistered-CAD",
                "type": "Investment",
            },
            "HQ8KJW805CAD-USD": {"nickname": "My-Option-Trading", "type": "Investment"},
            "WK23MTV36CAD-CAD": {"nickname": "My-Chequeing", "type": "Checking"},
        }

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".yml", delete=False
        ) as temp_file:
            yaml.dump(config_data, temp_file)
            temp_file_path = temp_file.name

        try:
            result = read_config(temp_file_path)
            self.assertEqual(result, config_data)

            # Verify all accounts are loaded correctly
            self.assertEqual(len(result), 4)

            # Check Investment accounts
            investment_accounts = [
                k for k, v in result.items() if v["type"] == "Investment"
            ]
            self.assertEqual(len(investment_accounts), 3)

            # Check Checking accounts
            checking_accounts = [
                k for k, v in result.items() if v["type"] == "Checking"
            ]
            self.assertEqual(len(checking_accounts), 1)
        finally:
            os.unlink(temp_file_path)

    def test_read_config_yaml_with_special_characters_in_nicknames(self):
        """Test read_config with YAML containing special characters in nicknames"""
        config_data = {
            "SPECIAL-ACCOUNT-123": {
                "nickname": "My-Special_Account.Test",
                "type": "Investment",
            },
            "TEST-ACCOUNT-456": {
                "nickname": "Test-Account-With-Dashes",
                "type": "Checking",
            },
        }

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".yml", delete=False, encoding="utf-8"
        ) as temp_file:
            yaml.dump(config_data, temp_file, allow_unicode=True)
            temp_file_path = temp_file.name

        try:
            result = read_config(temp_file_path)
            self.assertEqual(result, config_data)

            # Verify special characters in nicknames are preserved
            self.assertEqual(
                result["SPECIAL-ACCOUNT-123"]["nickname"], "My-Special_Account.Test"
            )
            self.assertEqual(
                result["TEST-ACCOUNT-456"]["nickname"], "Test-Account-With-Dashes"
            )
        finally:
            os.unlink(temp_file_path)

    def test_read_config_file_not_found(self):
        """Test read_config with non-existent file"""
        non_existent_file = "/path/that/does/not/exist/config.yml"

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

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".yml", delete=False
        ) as temp_file:
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
            "INCOMPLETE-ACCOUNT": {
                "nickname": "Missing-Type-Field"
                # Missing 'type' field
            }
        }

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".yml", delete=False
        ) as temp_file:
            yaml.dump(config_data, temp_file)
            temp_file_path = temp_file.name

        try:
            result = read_config(temp_file_path)
            # Function should still return the data, validation happens elsewhere
            self.assertEqual(result, config_data)
            self.assertNotIn("type", result["INCOMPLETE-ACCOUNT"])
        finally:
            os.unlink(temp_file_path)

    def test_read_config_invalid_account_types(self):
        """Test read_config with invalid account types"""
        config_data = {
            "INVALID-TYPE-ACCOUNT": {
                "nickname": "Invalid-Type-Test",
                "type": "InvalidType",  # Should be 'Investment' or 'Checking'
            }
        }

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".yml", delete=False
        ) as temp_file:
            yaml.dump(config_data, temp_file)
            temp_file_path = temp_file.name

        try:
            result = read_config(temp_file_path)
            # Function should still return the data, validation happens elsewhere
            self.assertEqual(result, config_data)
            self.assertEqual(result["INVALID-TYPE-ACCOUNT"]["type"], "InvalidType")
        finally:
            os.unlink(temp_file_path)

    def test_read_config_large_yaml_file(self):
        """Test read_config with a large YAML file"""
        # Generate a large configuration with many accounts
        config_data = {}
        for i in range(50):
            account_id = f"ACCOUNT{i:03d}CAD-CAD"
            config_data[account_id] = {
                "nickname": f"Test-Account-{i}",
                "type": "Investment" if i % 2 == 0 else "Checking",
            }

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".yml", delete=False
        ) as temp_file:
            yaml.dump(config_data, temp_file)
            temp_file_path = temp_file.name

        try:
            result = read_config(temp_file_path)
            self.assertEqual(result, config_data)
            self.assertEqual(len(result), 50)

            # Verify a few random entries
            self.assertEqual(result["ACCOUNT000CAD-CAD"]["nickname"], "Test-Account-0")
            self.assertEqual(result["ACCOUNT000CAD-CAD"]["type"], "Investment")
            self.assertEqual(result["ACCOUNT001CAD-CAD"]["type"], "Checking")
        finally:
            os.unlink(temp_file_path)

    @patch("builtins.open", side_effect=IOError("Disk full"))
    def test_read_config_io_error(self, mock_open):
        """Test read_config with I/O error during file reading"""
        with self.assertRaises(IOError):
            read_config("some_file.yml")

    def test_read_config_actual_accounts_file(self):
        """Test read_config with the actual accounts.yml file if it exists"""
        # This test uses the real accounts.yml file in the project
        if os.path.exists("accounts.yml"):
            result = read_config("accounts.yml")

            # Verify the structure matches expected format
            self.assertIsInstance(result, dict)

            # Check for cdr_symbols configuration
            self.assertIn("cdr_symbols", result)
            self.assertIsInstance(result["cdr_symbols"], list)

            # Check that all accounts have required fields
            for account_id, account_config in result.items():
                # Skip non-account entries like cdr_symbols
                if account_id == "cdr_symbols":
                    continue

                self.assertIn("nickname", account_config)
                self.assertIn("type", account_config)
                self.assertIsInstance(account_config["nickname"], str)
                self.assertIn(account_config["type"], ["Investment", "Checking"])

                # Verify account ID format (should end with -CAD or -USD)
                self.assertTrue(
                    account_id.endswith("-CAD") or account_id.endswith("-USD")
                )

                # Verify only expected fields are present
                expected_fields = {"nickname", "type"}
                actual_fields = set(account_config.keys())
                self.assertEqual(
                    actual_fields,
                    expected_fields,
                    f"Account {account_id} has unexpected fields: {actual_fields - expected_fields}",
                )
        else:
            self.skipTest("accounts.yml file not found in project directory")

    # Tests for read_csv_files function
    @patch("app.main.read_config")
    @patch("os.listdir")
    @patch("builtins.open", new_callable=mock_open)
    def test_read_csv_files_multiple_files(self, mock_open_file, mock_listdir, mock_read_config):
        """Test read_csv_files with multiple CSV files"""
        # Mock directory listing with multiple CSV files
        mock_listdir.return_value = [
            "monthly-statement-transactions-ACCOUNT1-2025-07-01.csv",
            "monthly-statement-transactions-ACCOUNT2-2025-06-30.csv",
            "other-file.txt",  # Should be ignored
        ]

        # Mock CSV content for first file
        csv_content1 = "date,transaction,description,amount,currency\n2025-07-01,BUY,AAPL - 10.0 shares,-1500.00,USD\n2025-07-02,SELL,TSLA - 5.0 shares,1000.00,CAD\n"
        # Mock CSV content for second file
        csv_content2 = "date,transaction,description,amount,currency\n2025-06-30,DIV,MSFT - Dividend payment,25.50,USD\n"

        # Configure mock to return different content based on file path
        def mock_open_side_effect(file_path, mode="r"):
            if "ACCOUNT1" in file_path:
                return mock_open(read_data=csv_content1).return_value
            elif "ACCOUNT2" in file_path:
                return mock_open(read_data=csv_content2).return_value
            else:
                return mock_open(read_data="").return_value

        mock_open_file.side_effect = mock_open_side_effect
        mock_read_config.return_value = {"cdr_symbols": ["TSLA", "DIS", "NVDA", "AAPL"]}

        result, source_files = read_csv_files("test_input_folder", "dummy_config.yml")

        # Should have 4 accounts (2 files × 2 currencies each)
        expected_accounts = [
            "ACCOUNT1-USD",
            "ACCOUNT1-CAD",
            "ACCOUNT2-USD",
            "ACCOUNT2-CAD",
        ]
        self.assertEqual(set(result.keys()), set(expected_accounts))

        # ACCOUNT1-USD should have 1 transaction (AAPL BUY)
        self.assertEqual(len(result["ACCOUNT1-USD"]), 1)
        self.assertIn("AAPL", result["ACCOUNT1-USD"][0])  # USD symbols have no suffix

        # ACCOUNT1-CAD should have 1 transaction (TSLA SELL)
        self.assertEqual(len(result["ACCOUNT1-CAD"]), 1)
        self.assertIn("TSLA-QH", result["ACCOUNT1-CAD"][0])  # TSLA is CDR in CAD

        # ACCOUNT2-USD should have 1 transaction (MSFT DIV)
        self.assertEqual(len(result["ACCOUNT2-USD"]), 1)
        self.assertIn("MSFT", result["ACCOUNT2-USD"][0])  # USD symbols have no suffix

        # ACCOUNT2-CAD should be empty
        self.assertEqual(len(result["ACCOUNT2-CAD"]), 0)

    @patch("app.main.read_config")
    @patch("os.listdir")
    @patch("builtins.open", new_callable=mock_open)
    def test_read_csv_files_empty_directory(self, mock_open_file, mock_listdir, mock_read_config):
        """Test read_csv_files with empty directory"""
        mock_listdir.return_value = []
        mock_read_config.return_value = {"cdr_symbols": []}

        result, source_files = read_csv_files("empty_folder", "dummy_config.yml")

        self.assertEqual(result, {})

    @patch("app.main.read_config")
    @patch("os.listdir")
    @patch("builtins.open", new_callable=mock_open)
    def test_read_csv_files_no_csv_files(self, mock_open_file, mock_listdir, mock_read_config):
        """Test read_csv_files with directory containing no CSV files"""
        mock_listdir.return_value = ["file1.txt", "file2.pdf", "readme.md"]
        mock_read_config.return_value = {"cdr_symbols": []}

        result, source_files = read_csv_files("no_csv_folder", "dummy_config.yml")

        self.assertEqual(result, {})

    @patch("app.main.read_config")
    @patch("os.listdir")
    @patch("builtins.open", new_callable=mock_open)
    def test_read_csv_files_invalid_filename_format(self, mock_open_file, mock_listdir, mock_read_config):
        """Test read_csv_files with CSV files that don't match expected format"""
        mock_listdir.return_value = [
            "invalid-format.csv",
            "monthly-statement-transactions-INVALID.csv",  # Missing date
            "daily-statement-transactions-ACCOUNT1-2025-07-01.csv",  # Wrong prefix
        ]

        mock_read_config.return_value = {"cdr_symbols": []}

        result, source_files = read_csv_files("invalid_folder", "dummy_config.yml")

        # Files that don't match the expected filename pattern are skipped entirely
        self.assertEqual(result, {})

    @patch("app.main.read_config")
    @patch("os.listdir")
    @patch("builtins.open", new_callable=mock_open)
    def test_read_csv_files_mixed_currencies_single_file(
        self, mock_open_file, mock_listdir, mock_read_config
    ):
        """Test read_csv_files with single file containing mixed currency transactions"""
        mock_listdir.return_value = [
            "monthly-statement-transactions-MIXED123-2025-07-01.csv"
        ]

        csv_content = """date,transaction,description,amount,currency
2025-07-01,BUY,AAPL - 10.0 shares,-1500.00,USD
2025-07-02,BUY,SHOP - 5.0 shares,-750.00,CAD
2025-07-03,SELL,MSFT - 8.0 shares,2400.00,USD
2025-07-04,DIV,TD - Dividend payment,15.75,CAD
2025-07-05,CONT,Contribution,1000.0,CAD"""

        # The function reads the same file multiple times (once for each currency)
        # We need to configure the mock to return fresh content each time it's opened
        def mock_open_side_effect(*args, **kwargs):
            return mock_open(read_data=csv_content).return_value

        mock_open_file.side_effect = mock_open_side_effect
        mock_read_config.return_value = {"cdr_symbols": ["TSLA", "DIS", "NVDA", "AAPL"]}

        result, source_files = read_csv_files("mixed_folder", "dummy_config.yml")

        # Should have 2 accounts (USD and CAD)
        self.assertIn("MIXED123-USD", result)
        self.assertIn("MIXED123-CAD", result)

        # USD account should have 2 transactions (AAPL BUY, MSFT SELL)
        self.assertEqual(len(result["MIXED123-USD"]), 2)

        # CAD account should have 3 transactions (SHOP BUY, TD DIV, CONT)
        self.assertEqual(len(result["MIXED123-CAD"]), 3)

    @patch("app.main.read_config")
    @patch("os.listdir")
    @patch("builtins.open", new_callable=mock_open)
    def test_read_csv_files_empty_csv_file(self, mock_open_file, mock_listdir, mock_read_config):
        """Test read_csv_files with empty CSV file"""
        mock_listdir.return_value = [
            "monthly-statement-transactions-EMPTY123-2025-07-01.csv"
        ]

        # CSV with only headers
        csv_content = "date,transaction,description,amount,currency\n"
        mock_open_file.return_value = mock_open(read_data=csv_content).return_value
        mock_read_config.return_value = {"cdr_symbols": []}

        result, source_files = read_csv_files("empty_csv_folder", "dummy_config.yml")

        # Should have both currency accounts but they should be empty
        self.assertIn("EMPTY123-USD", result)
        self.assertIn("EMPTY123-CAD", result)
        self.assertEqual(len(result["EMPTY123-USD"]), 0)
        self.assertEqual(len(result["EMPTY123-CAD"]), 0)

    @patch("app.main.read_config")
    @patch("app.main.detect_csv_format", return_value="monthly_statement")
    @patch("os.listdir")
    @patch("builtins.open", new_callable=mock_open)
    def test_read_csv_files_ignored_transactions(self, mock_open_file, mock_listdir, mock_detect, mock_read_config):
        """Test read_csv_files with transactions that should be ignored"""
        mock_listdir.return_value = [
            "monthly-statement-transactions-IGNORE123-2025-07-01.csv"
        ]

        csv_content = """date,transaction,description,amount,currency
2025-07-01,BUY,AAPL - 10.0 shares,-1500.00,USD
2025-07-02,RECALL,Stock recall transaction,0.00,USD
2025-07-03,LOAN,Stock loan transaction,100.00,USD
2025-07-04,STKDIS,Stock distribution,50.00,USD
2025-07-05,STKREORG,Stock reorganization,0.00,USD
2025-07-06,SELL,MSFT - 5.0 shares,1000.00,USD"""

        mock_open_file.return_value = mock_open(read_data=csv_content).return_value
        mock_read_config.return_value = {"cdr_symbols": ["TSLA", "DIS", "NVDA", "AAPL"]}

        result, source_files = read_csv_files("ignore_folder", "dummy_config.yml")

        # Should only have 2 transactions (BUY and SELL), ignored transactions should not appear
        self.assertEqual(len(result["IGNORE123-USD"]), 2)
        self.assertEqual(len(result["IGNORE123-CAD"]), 0)

        # Verify the transactions are the expected ones
        usd_transactions = result["IGNORE123-USD"]
        self.assertIn("AAPL", usd_transactions[0])  # USD symbols have no suffix
        self.assertIn("MSFT", usd_transactions[1])  # USD symbols have no suffix

    @patch("app.main.read_config")
    @patch("app.main.detect_csv_format", return_value="monthly_statement")
    @patch("os.listdir")
    @patch("builtins.open", new_callable=mock_open)
    def test_read_csv_files_options_transactions(self, mock_open_file, mock_listdir, mock_detect, mock_read_config):
        """Test read_csv_files with options trading transactions"""
        mock_listdir.return_value = [
            "monthly-statement-transactions-OPTIONS123-2025-07-01.csv"
        ]

        csv_content = """date,transaction,description,amount,currency
2025-07-23,BUYTOOPEN,SPY 450.00 USD CALL 2025-07-25: Bought 2 contract (executed at 2025-07-23) Fee: $1.50,-320.50,USD
2025-07-25,SELLTOCLOSE,AAPL 180.00 USD PUT 2025-07-30: Sold 1 contract (executed at 2025-07-25) Fee: $0.75,150.25,USD"""

        mock_open_file.return_value = mock_open(read_data=csv_content).return_value
        mock_read_config.return_value = {"cdr_symbols": ["TSLA", "DIS", "NVDA", "AAPL"]}

        result, source_files = read_csv_files("options_folder", "dummy_config.yml")

        # Should have 2 options transactions in USD account
        self.assertEqual(len(result["OPTIONS123-USD"]), 2)
        self.assertEqual(len(result["OPTIONS123-CAD"]), 0)

        # Verify options symbols are preserved
        usd_transactions = result["OPTIONS123-USD"]
        self.assertIn("SPY 450.00 USD CALL 2025-07-25", usd_transactions[0])
        self.assertIn("AAPL 180.00 USD PUT 2025-07-30", usd_transactions[1])

    @patch("app.main.read_config")
    @patch("app.main.detect_csv_format", return_value="monthly_statement")
    @patch("os.listdir")
    @patch("builtins.open", new_callable=mock_open)
    def test_read_csv_files_various_transaction_types(
        self, mock_open_file, mock_listdir, mock_detect, mock_read_config
    ):
        """Test read_csv_files with various transaction types"""
        mock_listdir.return_value = [
            "monthly-statement-transactions-VARIOUS123-2025-07-01.csv"
        ]

        csv_content = """date,transaction,description,amount,currency
2025-07-01,BUY,AAPL - 10.0 shares,-1500.00,USD
2025-07-02,SELL,MSFT - 5.0 shares,1000.00,USD
2025-07-03,DIV,GOOGL - Dividend payment,25.50,USD
2025-07-04,CONT,Monthly contribution,500.0,USD
2025-07-05,FPLINT,Stock lending interest payment,12.50,USD
2025-07-06,NRT,US Non-Resident Tax Withholding,5.25,USD
2025-07-07,TRFOUT,Transfer to external account,200.00,USD
2025-07-08,CASHBACK,Credit card cashback,15.00,USD
2025-07-09,EFT,Electronic funds transfer,300.00,USD
2025-07-10,INT,Interest payment,8.50,USD"""

        mock_open_file.return_value = mock_open(read_data=csv_content).return_value
        mock_read_config.return_value = {"cdr_symbols": ["TSLA", "DIS", "NVDA", "AAPL"]}

        result, source_files = read_csv_files("various_folder", "dummy_config.yml")

        # Should have 10 transactions in USD account
        self.assertEqual(len(result["VARIOUS123-USD"]), 10)
        self.assertEqual(len(result["VARIOUS123-CAD"]), 0)

        # Verify different transaction types are processed
        usd_transactions = result["VARIOUS123-USD"]
        transaction_text = "\n".join(usd_transactions)

        # Check for different QIF transaction types
        self.assertIn("NBuy", transaction_text)  # BUY
        self.assertIn("NSell", transaction_text)  # SELL
        self.assertIn("NDiv", transaction_text)  # DIV
        self.assertIn("NXIn", transaction_text)  # CONT, FPLINT, CASHBACK, EFT, INT
        self.assertIn("NXOut", transaction_text)  # NRT
        self.assertIn("T-200.0", transaction_text)  # TRFOUT (negative amount)

    @patch("os.listdir")
    def test_read_csv_files_directory_not_found(self, mock_listdir):
        """Test read_csv_files with non-existent directory"""
        mock_listdir.side_effect = FileNotFoundError("Directory not found")

        with self.assertRaises(FileNotFoundError):
            read_csv_files("nonexistent_folder", "dummy_config.yml")

    @patch("os.listdir")
    @patch("builtins.open", new_callable=mock_open)
    def test_read_csv_files_file_read_error(self, mock_open_file, mock_listdir):
        """Test read_csv_files with file read error"""
        mock_listdir.return_value = [
            "monthly-statement-transactions-ERROR123-2025-07-01.csv"
        ]
        mock_open_file.side_effect = IOError("Permission denied")

        with self.assertRaises(IOError):
            read_csv_files("error_folder", "dummy_config.yml")

    @patch("app.main.read_config")
    @patch("os.listdir")
    @patch("builtins.open", new_callable=mock_open)
    def test_read_csv_files_malformed_csv(self, mock_open_file, mock_listdir, mock_read_config):
        """Test read_csv_files with malformed CSV content - missing amount column"""
        mock_listdir.return_value = [
            "monthly-statement-transactions-MALFORMED123-2025-07-01.csv"
        ]

        # CSV with missing 'amount' column - should be handled gracefully
        csv_content = """date,transaction,description,currency
2025-07-01,BUY,AAPL - 10.0 shares,USD"""

        mock_open_file.return_value = mock_open(read_data=csv_content).return_value

        mock_read_config.return_value = {"cdr_symbols": []}

        # Should handle missing 'amount' column gracefully by skipping the row
        result, source_files = read_csv_files("malformed_folder", "dummy_config.yml")

        # Should have both currency accounts but they should be empty
        # since rows with missing/empty amount are skipped
        self.assertIn("MALFORMED123-USD", result)
        self.assertIn("MALFORMED123-CAD", result)
        self.assertEqual(len(result["MALFORMED123-USD"]), 0)
        self.assertEqual(len(result["MALFORMED123-CAD"]), 0)

    @patch("app.main.read_config")
    @patch("os.listdir")
    @patch("builtins.open", new_callable=mock_open)
    def test_read_csv_files_cdr_symbol_handling(self, mock_open_file, mock_listdir, mock_read_config):
        """Test read_csv_files with CDR symbols in different currencies"""
        mock_listdir.return_value = [
            "monthly-statement-transactions-CDR123-2025-07-01.csv"
        ]

        csv_content = """date,transaction,description,amount,currency
2025-07-01,BUY,TSLA - 5.0 shares,-1250.00,CAD
2025-07-02,BUY,TSLA - 3.0 shares,-750.00,USD
2025-07-03,BUY,AAPL - 10.0 shares,-1500.00,CAD
2025-07-04,BUY,SHOP - 8.0 shares,-1200.00,CAD"""

        # The function reads the same file multiple times, so we need to ensure the mock returns fresh content each time
        def mock_open_side_effect(*args, **kwargs):
            return mock_open(read_data=csv_content).return_value

        mock_open_file.side_effect = mock_open_side_effect
        mock_read_config.return_value = {"cdr_symbols": ["TSLA", "DIS", "NVDA", "AAPL"]}

        result, source_files = read_csv_files("cdr_folder", "dummy_config.yml")

        # Verify we have both currency accounts
        self.assertIn("CDR123-CAD", result)
        self.assertIn("CDR123-USD", result)

        # Check that we have the expected number of transactions
        self.assertEqual(len(result["CDR123-CAD"]), 3)  # TSLA, AAPL, SHOP in CAD
        self.assertEqual(len(result["CDR123-USD"]), 1)  # TSLA in USD

        # Check CDR symbol mapping
        cad_transactions = "\n".join(result["CDR123-CAD"])
        usd_transactions = "\n".join(result["CDR123-USD"])

        # TSLA and AAPL in CAD should get -QH suffix (CDR)
        self.assertIn("TSLA-QH", cad_transactions)
        self.assertIn("AAPL-QH", cad_transactions)

        # SHOP in CAD should get -CT suffix (not CDR)
        self.assertIn("SHOP-CT", cad_transactions)

        # TSLA in USD should have no suffix (USD symbols never get suffixes)
        self.assertIn("YTSLA\n", usd_transactions)

    # Tests for export_qif_files function
    def test_export_qif_files_investment_account_basic(self):
        """Test export_qif_files with basic Investment account"""
        # Create test data
        account_data = {
            "TEST123CAD-USD": [
                "D2025-07-15\nNBuy\nYAAPL-CT\nI150.0\nQ10.0\nT1500.0\nO0.00\nCc\n^",
                "D2025-07-16\nNSell\nYMSFT-CT\nI300.0\nQ5.0\nT1500.0\nO0.00\nCc\n^",
            ]
        }

        # Create config data
        config_data = {
            "TEST123CAD-USD": {"nickname": "My-Test-Investment", "type": "Investment"}
        }

        # Mock read_config to return our test config data
        with patch(
            "app.main.read_config", return_value=config_data
        ) as mock_read_config:
            with patch("builtins.open", mock_open()) as mock_file:
                export_qif_files(account_data, "dummy_config.yml")

                # Verify read_config was called
                mock_read_config.assert_called_once_with("dummy_config.yml")

                # Verify file was opened for writing
                mock_file.assert_called_with("output/My-Test-Investment.qif", "w")

                # Verify content written to file
                handle = mock_file.return_value
                written_content = "".join(
                    call.args[0] for call in handle.write.call_args_list
                )

                # Should start with Investment header
                self.assertIn("!Type:Invst", written_content)
                # Should contain the transactions
                self.assertIn("AAPL-CT", written_content)
                self.assertIn("MSFT-CT", written_content)

    def test_export_qif_files_checking_account_basic(self):
        """Test export_qif_files with basic Checking account"""
        # Create test data
        account_data = {
            "WK23MTV36CAD-CAD": [
                "D2025-07-15\nT1000.0\nO0.00\nCc\nPDeposit\n^",
                "D2025-07-16\nT-500.0\nO0.00\nCc\nPWithdrawal\n^",
            ]
        }

        # Create config data
        config_data = {
            "WK23MTV36CAD-CAD": {"nickname": "My-Checking", "type": "Checking"}
        }

        # Mock read_config to return our test config data
        with patch("app.main.read_config", return_value=config_data):
            with patch("builtins.open", mock_open()) as mock_file:
                export_qif_files(account_data, "dummy_config.yml")

                # Verify file was opened for writing
                mock_file.assert_called_with("output/My-Checking.qif", "w")

                # Verify content written to file
                handle = mock_file.return_value
                written_content = "".join(
                    call.args[0] for call in handle.write.call_args_list
                )

                # Should start with Bank header
                self.assertIn("!Type:Bank", written_content)
                # Should contain the transactions
                self.assertIn("T1000.0", written_content)
                self.assertIn("T-500.0", written_content)

    def test_export_qif_files_empty_transactions_skipped(self):
        """Test export_qif_files skips accounts with empty transaction lists"""
        # Create test data with empty transactions
        account_data = {
            "EMPTY123CAD-USD": [],
            "NONEMPTY456CAD-USD": [
                "D2025-07-15\nNBuy\nYAAPL-CT\nI150.0\nQ10.0\nT1500.0\nO0.00\nCc\n^"
            ],
        }

        # Create config data
        config_data = {
            "EMPTY123CAD-USD": {"nickname": "Empty-Account", "type": "Investment"},
            "NONEMPTY456CAD-USD": {
                "nickname": "Non-Empty-Account",
                "type": "Investment",
            },
        }

        # Mock read_config to return our test config data
        with patch("app.main.read_config", return_value=config_data):
            with patch("builtins.open", mock_open()) as mock_file:
                export_qif_files(account_data, "dummy_config.yml")

                # Should only be called once (for non-empty account)
                self.assertEqual(mock_file.call_count, 1)
                mock_file.assert_called_with("output/Non-Empty-Account.qif", "w")

    def test_export_qif_files_unknown_account_error(self):
        """Test export_qif_files raises ValueError for unknown account"""
        # Create test data with account not in config
        account_data = {
            "UNKNOWN123CAD-USD": [
                "D2025-07-15\nNBuy\nYAAPL-CT\nI150.0\nQ10.0\nT1500.0\nO0.00\nCc\n^"
            ]
        }

        # Create temporary config file without the account
        config_data = {
            "DIFFERENT456CAD-USD": {
                "nickname": "Different-Account",
                "type": "Investment",
            }
        }

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".yml", delete=False
        ) as config_file:
            yaml.dump(config_data, config_file)
            config_file_path = config_file.name

        with self.assertRaises(ValueError) as context:
            export_qif_files(account_data, config_file_path)

        self.assertIn("Unknown account", str(context.exception))

        # Clean up
        os.unlink(config_file_path)

    def test_export_qif_files_currency_mismatch_checking_cad(self):
        """Test export_qif_files detects currency mismatch for CAD checking account"""
        # Create test data - CAD base account with USD suffix (mismatch)
        account_data = {
            "WK23MTV36CAD-USD": [  # CAD base account but USD suffix
                "D2025-07-15\nT1000.0\nO0.00\nCc\nPDeposit\n^"
            ]
        }

        # Create temporary config file
        config_data = {
            "WK23MTV36CAD-USD": {"nickname": "Mismatched-Checking", "type": "Checking"}
        }

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".yml", delete=False
        ) as config_file:
            yaml.dump(config_data, config_file)
            config_file_path = config_file.name

        with self.assertRaises(ValueError) as context:
            export_qif_files(account_data, config_file_path)

        error_message = str(context.exception)
        self.assertIn("Currency mismatch", error_message)
        self.assertIn("WK23MTV36CAD-USD", error_message)
        self.assertIn("USD", error_message)
        self.assertIn("CAD", error_message)

        # Clean up
        os.unlink(config_file_path)

    def test_export_qif_files_currency_mismatch_checking_usd(self):
        """Test export_qif_files detects currency mismatch for USD checking account"""
        # Create test data - USD base account with CAD suffix (mismatch)
        account_data = {
            "WK5DRT238USD-CAD": [  # USD base account but CAD suffix
                "D2025-07-15\nT1000.0\nO0.00\nCc\nPDeposit\n^"
            ]
        }

        # Create temporary config file
        config_data = {
            "WK5DRT238USD-CAD": {
                "nickname": "Mismatched-USD-Checking",
                "type": "Checking",
            }
        }

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".yml", delete=False
        ) as config_file:
            yaml.dump(config_data, config_file)
            config_file_path = config_file.name

        with self.assertRaises(ValueError) as context:
            export_qif_files(account_data, config_file_path)

        error_message = str(context.exception)
        self.assertIn("Currency mismatch", error_message)
        self.assertIn("WK5DRT238USD-CAD", error_message)
        self.assertIn("CAD", error_message)
        self.assertIn("USD", error_message)

        # Clean up
        os.unlink(config_file_path)

    def test_export_qif_files_currency_match_checking_accounts(self):
        """Test export_qif_files allows matching currencies for checking accounts"""
        # Create test data with matching currencies
        account_data = {
            "WK23MTV36CAD-CAD": [  # CAD base account with CAD suffix (match)
                "D2025-07-15\nT1000.0\nO0.00\nCc\nPDeposit\n^"
            ],
            "WK5DRT238USD-USD": [  # USD base account with USD suffix (match)
                "D2025-07-16\nT500.0\nO0.00\nCc\nPDeposit\n^"
            ],
        }

        # Create config data
        config_data = {
            "WK23MTV36CAD-CAD": {"nickname": "CAD-Checking", "type": "Checking"},
            "WK5DRT238USD-USD": {"nickname": "USD-Checking", "type": "Checking"},
        }

        # Mock read_config to return our test config data
        with patch("app.main.read_config", return_value=config_data):
            with patch("builtins.open", mock_open()) as mock_file:
                # Should not raise any exceptions
                export_qif_files(account_data, "dummy_config.yml")

                # Should be called twice (once for each account)
                self.assertEqual(mock_file.call_count, 2)

    def test_export_qif_files_investment_accounts_no_currency_validation(self):
        """Test export_qif_files does not validate currency for Investment accounts"""
        # Create test data - Investment accounts should not have currency validation
        account_data = {
            "H16530307CAD-USD": [  # CAD base account with USD suffix (should be OK for Investment)
                "D2025-07-15\nNBuy\nYAAPL-CT\nI150.0\nQ10.0\nT1500.0\nO0.00\nCc\n^"
            ],
            "H16530307CAD-CAD": [  # CAD base account with CAD suffix
                "D2025-07-16\nNBuy\nYSHOP-CT\nI100.0\nQ5.0\nT500.0\nO0.00\nCc\n^"
            ],
        }

        # Create config data
        config_data = {
            "H16530307CAD-USD": {"nickname": "Investment-USD", "type": "Investment"},
            "H16530307CAD-CAD": {"nickname": "Investment-CAD", "type": "Investment"},
        }

        # Mock read_config to return our test config data
        with patch("app.main.read_config", return_value=config_data):
            with patch("builtins.open", mock_open()) as mock_file:
                # Should not raise any exceptions for Investment accounts
                export_qif_files(account_data, "dummy_config.yml")

                # Should be called twice (once for each account)
                self.assertEqual(mock_file.call_count, 2)

    def test_export_qif_files_multiple_mixed_accounts(self):
        """Test export_qif_files with multiple Investment and Checking accounts"""
        # Create test data with mixed account types
        account_data = {
            "H16530307CAD-USD": [
                "D2025-07-15\nNBuy\nYAAPL-CT\nI150.0\nQ10.0\nT1500.0\nO0.00\nCc\n^"
            ],
            "H16530307CAD-CAD": [
                "D2025-07-16\nNBuy\nYTSLA-QH\nI250.0\nQ2.0\nT500.0\nO0.00\nCc\n^"
            ],
            "WK23MTV36CAD-CAD": ["D2025-07-17\nT1000.0\nO0.00\nCc\nPDeposit\n^"],
        }

        # Create config data
        config_data = {
            "H16530307CAD-USD": {"nickname": "Investment-USD", "type": "Investment"},
            "H16530307CAD-CAD": {"nickname": "Investment-CAD", "type": "Investment"},
            "WK23MTV36CAD-CAD": {"nickname": "Checking-CAD", "type": "Checking"},
        }

        # Mock read_config to return our test config data
        with patch("app.main.read_config", return_value=config_data):
            with patch("builtins.open", mock_open()) as mock_file:
                export_qif_files(account_data, "dummy_config.yml")

                # Should be called three times (once for each account)
                self.assertEqual(mock_file.call_count, 3)

                # Verify correct filenames were used
                expected_calls = [
                    ("output/Investment-USD.qif", "w"),
                    ("output/Investment-CAD.qif", "w"),
                    ("output/Checking-CAD.qif", "w"),
                ]
                actual_calls = [call.args for call in mock_file.call_args_list]
                self.assertEqual(set(actual_calls), set(expected_calls))

    def test_export_qif_files_special_characters_in_nicknames(self):
        """Test export_qif_files with special characters in account nicknames"""
        # Create test data
        account_data = {
            "SPECIAL123CAD-USD": [
                "D2025-07-15\nNBuy\nYAAPL-CT\nI150.0\nQ10.0\nT1500.0\nO0.00\nCc\n^"
            ]
        }

        # Create config data with special characters in nickname
        config_data = {
            "SPECIAL123CAD-USD": {
                "nickname": "My-Special_Account.Test",
                "type": "Investment",
            }
        }

        # Mock read_config to return our test config data
        with patch("app.main.read_config", return_value=config_data):
            with patch("builtins.open", mock_open()) as mock_file:
                export_qif_files(account_data, "dummy_config.yml")

                # Verify filename includes special characters
                mock_file.assert_called_with("output/My-Special_Account.Test.qif", "w")

    def test_export_qif_files_config_file_not_found(self):
        """Test export_qif_files with non-existent config file"""
        account_data = {
            "TEST123CAD-USD": [
                "D2025-07-15\nNBuy\nYAAPL-CT\nI150.0\nQ10.0\nT1500.0\nO0.00\nCc\n^"
            ]
        }

        non_existent_config = "/path/that/does/not/exist/config.yml"

        with self.assertRaises(FileNotFoundError):
            export_qif_files(account_data, non_existent_config)

    def test_export_qif_files_invalid_config_file(self):
        """Test export_qif_files with invalid YAML config file"""
        account_data = {
            "TEST123CAD-USD": [
                "D2025-07-15\nNBuy\nYAAPL-CT\nI150.0\nQ10.0\nT1500.0\nO0.00\nCc\n^"
            ]
        }

        # Create invalid YAML file
        invalid_yaml_content = """
TEST123CAD-USD:
  nickname: Test-Account
  type: Investment
    invalid_indentation: true
"""

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".yml", delete=False
        ) as config_file:
            config_file.write(invalid_yaml_content)
            config_file_path = config_file.name

        with self.assertRaises(yaml.YAMLError):
            export_qif_files(account_data, config_file_path)

        # Clean up
        os.unlink(config_file_path)

    def test_export_qif_files_account_without_hyphen(self):
        """Test export_qif_files with account name without hyphen (edge case)"""
        # Create test data with account name without hyphen
        account_data = {"NOHYPHEN": ["D2025-07-15\nT1000.0\nO0.00\nCc\nPDeposit\n^"]}

        # Create config data
        config_data = {
            "NOHYPHEN": {"nickname": "No-Hyphen-Account", "type": "Checking"}
        }

        # Mock read_config to return our test config data
        with patch("app.main.read_config", return_value=config_data):
            with patch("builtins.open", mock_open()) as mock_file:
                # Should not raise exceptions for accounts without hyphens
                export_qif_files(account_data, "dummy_config.yml")

                # Should successfully create the file
                mock_file.assert_called_with("output/No-Hyphen-Account.qif", "w")

    def test_export_qif_files_checking_account_default_currency_cad(self):
        """Test export_qif_files defaults to CAD for unclear checking account base names"""
        # Create test data with unclear base account name
        account_data = {
            "UNCLEAR123-USD": [  # Unclear base name, should default to CAD expectation
                "D2025-07-15\nT1000.0\nO0.00\nCc\nPDeposit\n^"
            ]
        }

        # Create temporary config file
        config_data = {
            "UNCLEAR123-USD": {"nickname": "Unclear-Checking", "type": "Checking"}
        }

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".yml", delete=False
        ) as config_file:
            yaml.dump(config_data, config_file)
            config_file_path = config_file.name

        # Should raise currency mismatch error (defaults to expecting CAD but got USD)
        with self.assertRaises(ValueError) as context:
            export_qif_files(account_data, config_file_path)

        error_message = str(context.exception)
        self.assertIn("Currency mismatch", error_message)

        # Clean up
        os.unlink(config_file_path)

    @patch("builtins.print")  # Mock print to avoid output during tests
    def test_export_qif_files_prints_config_and_account_names(self, mock_print):
        """Test export_qif_files prints config and processes account names"""
        # Create test data
        account_data = {
            "TEST123CAD-USD": [
                "D2025-07-15\nNBuy\nYAAPL-CT\nI150.0\nQ10.0\nT1500.0\nO0.00\nCc\n^"
            ]
        }

        # Create config data
        config_data = {
            "TEST123CAD-USD": {"nickname": "Test-Investment", "type": "Investment"}
        }

        # Mock read_config to return our test config data
        with patch("app.main.read_config", return_value=config_data):
            with patch("builtins.open", mock_open()) as mock_file:
                export_qif_files(account_data, "dummy_config.yml")

                # Verify print statements were called
                self.assertTrue(mock_print.called)

                # Check that config was printed (first call)
                first_call_args = mock_print.call_args_list[0][0]
                self.assertEqual(first_call_args[0], config_data)

                # Check that account name was printed (second call)
                second_call_args = mock_print.call_args_list[1][0]
                self.assertEqual(second_call_args[0], "TEST123CAD-USD")


class TestDetectCsvFormat(unittest.TestCase):
    """Tests for detect_csv_format function"""

    def test_detect_monthly_statement_format(self):
        """Test detection of monthly statement CSV format"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
            f.write("date,transaction,description,amount,balance,currency\n")
            f.write("2025-07-01,BUY,AAPL - 10.0 shares,-1500.00,23500.00,USD\n")
            temp_path = f.name
        try:
            result = detect_csv_format(temp_path)
            self.assertEqual(result, FORMAT_MONTHLY_STATEMENT)
        finally:
            os.unlink(temp_path)

    def test_detect_activities_export_format(self):
        """Test detection of activities export CSV format"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
            f.write("transaction_date,settlement_date,account_id,account_type,activity_type,activity_sub_type,direction,symbol,name,currency,quantity,unit_price,commission,net_cash_amount\n")
            f.write("2026-02-05,,AB123CAD,Chequing,BonusPayment,CASHBACK,,,,CAD,137.5,,,137.5\n")
            temp_path = f.name
        try:
            result = detect_csv_format(temp_path)
            self.assertEqual(result, FORMAT_ACTIVITIES_EXPORT)
        finally:
            os.unlink(temp_path)

    def test_detect_unrecognized_format(self):
        """Test that unrecognized CSV format raises ValueError"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
            f.write("col1,col2,col3\n")
            f.write("val1,val2,val3\n")
            temp_path = f.name
        try:
            with self.assertRaises(ValueError) as ctx:
                detect_csv_format(temp_path)
            self.assertIn("Unrecognized CSV format", str(ctx.exception))
        finally:
            os.unlink(temp_path)

    def test_detect_empty_csv(self):
        """Test that empty CSV file raises ValueError"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
            f.write("")
            temp_path = f.name
        try:
            with self.assertRaises(ValueError) as ctx:
                detect_csv_format(temp_path)
            self.assertIn("Empty CSV file", str(ctx.exception))
        finally:
            os.unlink(temp_path)


class TestMapActivitiesTransactionType(unittest.TestCase):
    """Tests for map_activities_transaction_type function"""

    def test_trade_buy(self):
        """Test Trade/BUY maps to BUY"""
        self.assertEqual(map_activities_transaction_type("Trade", "BUY", -1000), "BUY")

    def test_trade_sell(self):
        """Test Trade/SELL maps to SELL"""
        self.assertEqual(map_activities_transaction_type("Trade", "SELL", 1000), "SELL")

    def test_dividend(self):
        """Test Dividend maps to DIV"""
        self.assertEqual(map_activities_transaction_type("Dividend", "", 50), "DIV")

    def test_interest(self):
        """Test Interest maps to INT"""
        self.assertEqual(map_activities_transaction_type("Interest", "", 10), "INT")

    def test_fee(self):
        """Test Fee maps to FEE"""
        self.assertEqual(map_activities_transaction_type("Fee", "", -5), "FEE")

    def test_bonus_cashback(self):
        """Test BonusPayment/CASHBACK maps to CASHBACK"""
        self.assertEqual(map_activities_transaction_type("BonusPayment", "CASHBACK", 25), "CASHBACK")

    def test_bonus_giveaway(self):
        """Test BonusPayment/GIVEAWAY maps to GIVEAWAY"""
        self.assertEqual(map_activities_transaction_type("BonusPayment", "GIVEAWAY", 33), "GIVEAWAY")

    def test_money_movement_eft_positive(self):
        """Test MoneyMovement/EFT with positive amount maps to EFT"""
        self.assertEqual(map_activities_transaction_type("MoneyMovement", "EFT", 500), "EFT")

    def test_money_movement_eft_negative(self):
        """Test MoneyMovement/EFT with negative amount maps to EFTOUT"""
        self.assertEqual(map_activities_transaction_type("MoneyMovement", "EFT", -500), "EFTOUT")

    def test_money_movement_transfer_positive(self):
        """Test MoneyMovement/TRANSFER with positive amount maps to TRFIN"""
        self.assertEqual(map_activities_transaction_type("MoneyMovement", "TRANSFER", 1000), "TRFIN")

    def test_money_movement_transfer_negative(self):
        """Test MoneyMovement/TRANSFER with negative amount maps to TRFOUT"""
        self.assertEqual(map_activities_transaction_type("MoneyMovement", "TRANSFER", -1000), "TRFOUT")

    def test_money_movement_transfer_tf_positive(self):
        """Test MoneyMovement/TRANSFER_TF with positive amount maps to TRFINTF"""
        self.assertEqual(map_activities_transaction_type("MoneyMovement", "TRANSFER_TF", 500), "TRFINTF")

    def test_money_movement_transfer_tf_negative(self):
        """Test MoneyMovement/TRANSFER_TF with negative amount maps to TRFOUTTF"""
        self.assertEqual(map_activities_transaction_type("MoneyMovement", "TRANSFER_TF", -500), "TRFOUTTF")

    def test_money_movement_e_trfout(self):
        """Test MoneyMovement/E_TRFOUT maps directly"""
        self.assertEqual(map_activities_transaction_type("MoneyMovement", "E_TRFOUT", -100), "E_TRFOUT")

    def test_money_movement_e_trfin(self):
        """Test MoneyMovement/E_TRFIN maps directly"""
        self.assertEqual(map_activities_transaction_type("MoneyMovement", "E_TRFIN", 100), "E_TRFIN")

    def test_money_movement_aft_out(self):
        """Test MoneyMovement/AFT_OUT maps directly"""
        self.assertEqual(map_activities_transaction_type("MoneyMovement", "AFT_OUT", -200), "AFT_OUT")

    def test_money_movement_aft_in(self):
        """Test MoneyMovement/AFT_IN maps directly"""
        self.assertEqual(map_activities_transaction_type("MoneyMovement", "AFT_IN", 200), "AFT_IN")

    def test_money_movement_obp_out(self):
        """Test MoneyMovement/OBP_OUT maps directly"""
        self.assertEqual(map_activities_transaction_type("MoneyMovement", "OBP_OUT", -50), "OBP_OUT")

    def test_money_movement_spend(self):
        """Test MoneyMovement/SPEND maps directly"""
        self.assertEqual(map_activities_transaction_type("MoneyMovement", "SPEND", -30), "SPEND")

    def test_money_movement_unknown_positive(self):
        """Test unknown MoneyMovement sub_type with positive amount falls back to TRFIN"""
        self.assertEqual(map_activities_transaction_type("MoneyMovement", "UNKNOWN_SUB", 100), "TRFIN")

    def test_money_movement_unknown_negative(self):
        """Test unknown MoneyMovement sub_type with negative amount falls back to TRFOUT"""
        self.assertEqual(map_activities_transaction_type("MoneyMovement", "UNKNOWN_SUB", -100), "TRFOUT")

    def test_unknown_activity_type_with_sub(self):
        """Test unknown activity type with sub_type returns combined string"""
        result = map_activities_transaction_type("UnknownType", "UnknownSub", 100)
        self.assertEqual(result, "UnknownType_UnknownSub")

    def test_unknown_activity_type_without_sub(self):
        """Test unknown activity type without sub_type returns activity_type"""
        result = map_activities_transaction_type("UnknownType", "", 100)
        self.assertEqual(result, "UnknownType")


class TestConvertActivitiesRowToLegacy(unittest.TestCase):
    """Tests for convert_activities_row_to_legacy function"""

    def test_trade_buy(self):
        """Test converting a Trade/BUY row to legacy format"""
        row = {
            "transaction_date": "2026-04-01",
            "settlement_date": "2026-04-01",
            "account_id": "AB123CAD",
            "account_type": "Non-registered margin",
            "activity_type": "Trade",
            "activity_sub_type": "BUY",
            "direction": "LONG",
            "symbol": "XDIV",
            "name": "iShares Core MSCI Canadian Quality",
            "currency": "CAD",
            "quantity": "100.5",
            "unit_price": "39.48",
            "commission": "0",
            "net_cash_amount": "-3967.74",
        }
        result = convert_activities_row_to_legacy(row)
        self.assertIsNotNone(result)
        self.assertEqual(result["date"], "2026-04-01")
        self.assertEqual(result["transaction"], "BUY")
        self.assertEqual(result["currency"], "CAD")
        self.assertEqual(result["amount"], "-3967.74")
        self.assertIn("XDIV", result["description"])
        self.assertIn("100.5", result["description"])
        self.assertIn("shares", result["description"])

    def test_trade_sell(self):
        """Test converting a Trade/SELL row to legacy format"""
        row = {
            "transaction_date": "2026-02-13",
            "settlement_date": "2026-02-13",
            "account_id": "CD456CAD",
            "account_type": "Non-registered margin",
            "activity_type": "Trade",
            "activity_sub_type": "SELL",
            "direction": "LONG",
            "symbol": "ZM",
            "name": "Zoom Video Communications Inc",
            "currency": "USD",
            "quantity": "-80",
            "unit_price": "90.04",
            "commission": "0",
            "net_cash_amount": "7203.2",
        }
        result = convert_activities_row_to_legacy(row)
        self.assertIsNotNone(result)
        self.assertEqual(result["transaction"], "SELL")
        self.assertEqual(result["currency"], "USD")
        self.assertIn("ZM", result["description"])
        # Quantity in description should be absolute
        self.assertIn("80.0", result["description"])

    def test_dividend(self):
        """Test converting a Dividend row to legacy format"""
        row = {
            "transaction_date": "2026-01-30",
            "settlement_date": "",
            "account_id": "EF789CAD",
            "account_type": "Non-registered",
            "activity_type": "Dividend",
            "activity_sub_type": "",
            "direction": "",
            "symbol": "XDIV",
            "name": "iShares Core MSCI Canadian Quality",
            "currency": "CAD",
            "quantity": "",
            "unit_price": "",
            "commission": "",
            "net_cash_amount": "137.73",
        }
        result = convert_activities_row_to_legacy(row)
        self.assertIsNotNone(result)
        self.assertEqual(result["transaction"], "DIV")
        self.assertIn("XDIV", result["description"])

    def test_interest(self):
        """Test converting an Interest row to legacy format"""
        row = {
            "transaction_date": "2026-02-01",
            "settlement_date": "",
            "account_id": "GH012CAD",
            "account_type": "Chequing",
            "activity_type": "Interest",
            "activity_sub_type": "",
            "direction": "",
            "symbol": "",
            "name": "",
            "currency": "CAD",
            "quantity": "",
            "unit_price": "",
            "commission": "",
            "net_cash_amount": "34.13",
        }
        result = convert_activities_row_to_legacy(row)
        self.assertIsNotNone(result)
        self.assertEqual(result["transaction"], "INT")
        self.assertEqual(result["description"], "Interest earned")
        self.assertEqual(result["amount"], "34.13")

    def test_fee(self):
        """Test converting a Fee row to legacy format"""
        row = {
            "transaction_date": "2026-01-31",
            "settlement_date": "",
            "account_id": "IJ345CAD",
            "account_type": "Non-registered",
            "activity_type": "Fee",
            "activity_sub_type": "",
            "direction": "",
            "symbol": "",
            "name": "",
            "currency": "CAD",
            "quantity": "",
            "unit_price": "",
            "commission": "",
            "net_cash_amount": "-8.57",
        }
        result = convert_activities_row_to_legacy(row)
        self.assertIsNotNone(result)
        self.assertEqual(result["transaction"], "FEE")
        self.assertEqual(result["description"], "Account fee")

    def test_bonus_cashback(self):
        """Test converting a BonusPayment/CASHBACK row to legacy format"""
        row = {
            "transaction_date": "2026-02-05",
            "settlement_date": "",
            "account_id": "KL678CAD",
            "account_type": "Chequing",
            "activity_type": "BonusPayment",
            "activity_sub_type": "CASHBACK",
            "direction": "",
            "symbol": "",
            "name": "",
            "currency": "CAD",
            "quantity": "137.5",
            "unit_price": "",
            "commission": "",
            "net_cash_amount": "137.5",
        }
        result = convert_activities_row_to_legacy(row)
        self.assertIsNotNone(result)
        self.assertEqual(result["transaction"], "CASHBACK")
        self.assertEqual(result["description"], "Cashback reward")

    def test_bonus_giveaway(self):
        """Test converting a BonusPayment/GIVEAWAY row to legacy format"""
        row = {
            "transaction_date": "2026-01-28",
            "settlement_date": "",
            "account_id": "MN901CAD",
            "account_type": "Chequing",
            "activity_type": "BonusPayment",
            "activity_sub_type": "GIVEAWAY",
            "direction": "",
            "symbol": "",
            "name": "",
            "currency": "CAD",
            "quantity": "",
            "unit_price": "",
            "commission": "",
            "net_cash_amount": "33.29",
        }
        result = convert_activities_row_to_legacy(row)
        self.assertIsNotNone(result)
        self.assertEqual(result["transaction"], "GIVEAWAY")
        self.assertEqual(result["description"], "Giveaway received")

    def test_money_movement_transfer_out(self):
        """Test converting a MoneyMovement/TRANSFER with negative amount"""
        row = {
            "transaction_date": "2026-02-15",
            "settlement_date": "",
            "account_id": "OP234CAD",
            "account_type": "Chequing",
            "activity_type": "MoneyMovement",
            "activity_sub_type": "TRANSFER",
            "direction": "",
            "symbol": "",
            "name": "",
            "currency": "CAD",
            "quantity": "",
            "unit_price": "",
            "commission": "",
            "net_cash_amount": "-3554.58",
        }
        result = convert_activities_row_to_legacy(row)
        self.assertIsNotNone(result)
        self.assertEqual(result["transaction"], "TRFOUT")

    def test_money_movement_transfer_in(self):
        """Test converting a MoneyMovement/TRANSFER with positive amount"""
        row = {
            "transaction_date": "2026-02-15",
            "settlement_date": "",
            "account_id": "OP234CAD",
            "account_type": "Chequing",
            "activity_type": "MoneyMovement",
            "activity_sub_type": "TRANSFER",
            "direction": "",
            "symbol": "",
            "name": "",
            "currency": "CAD",
            "quantity": "",
            "unit_price": "",
            "commission": "",
            "net_cash_amount": "3554.58",
        }
        result = convert_activities_row_to_legacy(row)
        self.assertIsNotNone(result)
        self.assertEqual(result["transaction"], "TRFIN")

    def test_money_movement_obp_out(self):
        """Test converting a MoneyMovement/OBP_OUT"""
        row = {
            "transaction_date": "2026-02-03",
            "settlement_date": "",
            "account_id": "QR567CAD",
            "account_type": "Chequing",
            "activity_type": "MoneyMovement",
            "activity_sub_type": "OBP_OUT",
            "direction": "",
            "symbol": "",
            "name": "",
            "currency": "CAD",
            "quantity": "",
            "unit_price": "",
            "commission": "",
            "net_cash_amount": "-5850",
        }
        result = convert_activities_row_to_legacy(row)
        self.assertIsNotNone(result)
        self.assertEqual(result["transaction"], "OBP_OUT")
        self.assertEqual(result["description"], "Online bill payment")

    def test_money_movement_spend(self):
        """Test converting a MoneyMovement/SPEND"""
        row = {
            "transaction_date": "2026-04-09",
            "settlement_date": "",
            "account_id": "ST890CAD",
            "account_type": "Chequing",
            "activity_type": "MoneyMovement",
            "activity_sub_type": "SPEND",
            "direction": "",
            "symbol": "",
            "name": "",
            "currency": "CAD",
            "quantity": "",
            "unit_price": "",
            "commission": "",
            "net_cash_amount": "-603",
        }
        result = convert_activities_row_to_legacy(row)
        self.assertIsNotNone(result)
        self.assertEqual(result["transaction"], "SPEND")
        self.assertEqual(result["description"], "Spending transaction")

    def test_empty_net_cash_amount_returns_none(self):
        """Test that row with empty net_cash_amount returns None"""
        row = {
            "transaction_date": "2026-02-01",
            "account_id": "TEST123",
            "activity_type": "Interest",
            "activity_sub_type": "",
            "symbol": "",
            "name": "",
            "currency": "CAD",
            "quantity": "",
            "unit_price": "",
            "commission": "",
            "net_cash_amount": "",
        }
        result = convert_activities_row_to_legacy(row)
        self.assertIsNone(result)

    def test_invalid_net_cash_amount_returns_none(self):
        """Test that row with non-numeric net_cash_amount returns None"""
        row = {
            "transaction_date": "2026-02-01",
            "account_id": "TEST123",
            "activity_type": "Interest",
            "activity_sub_type": "",
            "symbol": "",
            "name": "",
            "currency": "CAD",
            "quantity": "",
            "unit_price": "",
            "commission": "",
            "net_cash_amount": "invalid",
        }
        result = convert_activities_row_to_legacy(row)
        self.assertIsNone(result)

    def test_trade_with_period_in_symbol(self):
        """Test converting a Trade row with period in symbol (e.g., DLR.U, ETHX.B)"""
        row = {
            "transaction_date": "2026-04-01",
            "settlement_date": "2026-04-01",
            "account_id": "UV123CAD",
            "account_type": "Non-registered margin",
            "activity_type": "Trade",
            "activity_sub_type": "BUY",
            "direction": "LONG",
            "symbol": "DLR.U",
            "name": "Global X US Dollar Currency ETF",
            "currency": "USD",
            "quantity": "2961.5004",
            "unit_price": "10.13",
            "commission": "0",
            "net_cash_amount": "-30000",
        }
        result = convert_activities_row_to_legacy(row)
        self.assertIsNotNone(result)
        self.assertEqual(result["transaction"], "BUY")
        self.assertIn("DLR.U", result["description"])
        self.assertIn("2961.5004", result["description"])


class TestExtractActivitiesExportMonth(unittest.TestCase):
    """Tests for _extract_activities_export_month function"""

    def test_standard_filename(self):
        self.assertEqual(_extract_activities_export_month("activities-export-2026-04-24.csv"), "2026-04")

    def test_different_date(self):
        self.assertEqual(_extract_activities_export_month("activities-export-2025-12-31.csv"), "2025-12")

    def test_invalid_filename(self):
        self.assertIsNone(_extract_activities_export_month("monthly-statement-transactions-ABC123-2026-04-01.csv"))

    def test_no_date(self):
        self.assertIsNone(_extract_activities_export_month("activities-export.csv"))


class TestGetInvestmentAccountIds(unittest.TestCase):
    """Tests for _get_investment_account_ids function"""

    def test_mixed_accounts(self):
        config = {
            "cdr_symbols": ["TSLA"],
            "H123CAD-CAD": {"nickname": "TFSA", "type": "Investment"},
            "H123CAD-USD": {"nickname": "TFSA-USD", "type": "Investment"},
            "WK456CAD-CAD": {"nickname": "Chequing", "type": "Checking"},
        }
        result = _get_investment_account_ids(config)
        self.assertEqual(result, {"H123CAD"})
        self.assertNotIn("WK456CAD", result)

    def test_no_investment_accounts(self):
        config = {
            "WK456CAD-CAD": {"nickname": "Chequing", "type": "Checking"},
        }
        result = _get_investment_account_ids(config)
        self.assertEqual(result, set())

    def test_multiple_investment_accounts(self):
        config = {
            "H123CAD-CAD": {"nickname": "TFSA-CAD", "type": "Investment"},
            "H123CAD-USD": {"nickname": "TFSA-USD", "type": "Investment"},
            "H456CAD-CAD": {"nickname": "RRSP-CAD", "type": "Investment"},
        }
        result = _get_investment_account_ids(config)
        self.assertEqual(result, {"H123CAD", "H456CAD"})


class TestActivitiesExportIntegration(unittest.TestCase):
    """Integration tests for activities export format with full pipeline.

    Activities export files are only used for Investment accounts in the
    current (incomplete) month. The current month is derived from the filename date.
    """

    def setUp(self):
        """Create temp directories for input and config"""
        self.test_dir = tempfile.mkdtemp()
        self.input_dir = os.path.join(self.test_dir, "input")
        os.makedirs(self.input_dir)

    def tearDown(self):
        """Clean up temp directories"""
        shutil.rmtree(self.test_dir)

    def _create_config(self, config_data):
        """Helper to create a config file"""
        config_path = os.path.join(self.test_dir, "accounts.yml")
        with open(config_path, "w") as f:
            yaml.dump(config_data, f)
        return config_path

    def _create_activities_csv(self, filename, rows):
        """Helper to create an activities export CSV file with anonymized data"""
        headers = "transaction_date,settlement_date,account_id,account_type,activity_type,activity_sub_type,direction,symbol,name,currency,quantity,unit_price,commission,net_cash_amount"
        filepath = os.path.join(self.input_dir, filename)
        with open(filepath, "w") as f:
            f.write(headers + "\n")
            for row in rows:
                f.write(row + "\n")
        return filepath

    def test_activities_export_trade_buy_cad(self):
        """Test processing a CAD stock buy from activities export"""
        self._create_activities_csv("activities-export-2026-04-01.csv", [
            "2026-04-06,2026-04-06,TEST1CAD,Non-registered,Trade,BUY,LONG,XDIV,iShares Core MSCI Quality,CAD,8.7639,39.48,0,-346",
        ])
        config_path = self._create_config({
            "cdr_symbols": ["TSLA", "DIS", "NVDA", "AAPL"],
            "TEST1CAD-CAD": {"nickname": "Test-NonReg-CAD", "type": "Investment"},
            "TEST1CAD-USD": {"nickname": "Test-NonReg-USD", "type": "Investment"},
        })

        result, source_files = read_csv_files(self.input_dir, config_path)

        self.assertIn("TEST1CAD-CAD", result)
        self.assertEqual(len(result["TEST1CAD-CAD"]), 1)
        qif = result["TEST1CAD-CAD"][0]
        self.assertIn("NBuy", qif)
        self.assertIn("XDIV-CT", qif)
        self.assertIn("T346.0", qif)

    def test_activities_export_trade_sell_usd(self):
        """Test processing a USD stock sell from activities export (current month only)"""
        self._create_activities_csv("activities-export-2026-04-01.csv", [
            "2026-04-13,2026-04-13,TEST2CAD,Non-registered margin,Trade,SELL,LONG,ZM,Zoom Video,USD,-80,90.04,0,7203.2",
        ])
        config_path = self._create_config({
            "cdr_symbols": [],
            "TEST2CAD-CAD": {"nickname": "Test-Margin-CAD", "type": "Investment"},
            "TEST2CAD-USD": {"nickname": "Test-Margin-USD", "type": "Investment"},
        })

        result, _ = read_csv_files(self.input_dir, config_path)

        self.assertIn("TEST2CAD-USD", result)
        self.assertEqual(len(result["TEST2CAD-USD"]), 1)
        qif = result["TEST2CAD-USD"][0]
        self.assertIn("NSell", qif)
        self.assertIn("ZM", qif)

    def test_activities_export_dividend_skipped(self):
        """Test that Dividend transactions are skipped from activities export (only Trade is processed)"""
        self._create_activities_csv("activities-export-2026-04-01.csv", [
            "2026-04-09,,TEST3CAD,Non-registered,Dividend,,,XDIV,iShares Core MSCI Quality,CAD,137.73,,,137.73",
        ])
        config_path = self._create_config({
            "cdr_symbols": [],
            "TEST3CAD-CAD": {"nickname": "Test-Div-CAD", "type": "Investment"},
            "TEST3CAD-USD": {"nickname": "Test-Div-USD", "type": "Investment"},
        })

        result, _ = read_csv_files(self.input_dir, config_path)

        # Dividend is not Trade, so it should be skipped
        self.assertEqual(len(result.get("TEST3CAD-CAD", [])), 0)

    def test_activities_export_non_trade_skipped(self):
        """Test that non-Trade transactions (Interest, Dividend, Fee, etc.) are skipped from activities export"""
        self._create_activities_csv("activities-export-2026-04-01.csv", [
            "2026-04-15,,TEST4CAD,TFSA,Interest,,,,,CAD,34.13,,,34.13",
            "2026-04-09,,TEST4CAD,TFSA,Dividend,,,XDIV,iShares,CAD,5.00,,,5.00",
            "2026-04-15,,TEST4CAD,TFSA,Fee,,,,,CAD,-6.8,,,-6.8",
            "2026-04-10,,TEST4CAD,TFSA,MoneyMovement,EFT,,,,CAD,1000,,,1000",
            "2026-04-06,2026-04-06,TEST4CAD,TFSA,Trade,BUY,LONG,XDIV,iShares,CAD,10,39.48,0,-394.8",
        ])
        config_path = self._create_config({
            "cdr_symbols": [],
            "TEST4CAD-CAD": {"nickname": "Test-TFSA", "type": "Investment"},
            "TEST4CAD-USD": {"nickname": "Test-TFSA-USD", "type": "Investment"},
        })

        result, _ = read_csv_files(self.input_dir, config_path)

        # Only the Trade/BUY should be processed; Interest, Dividend, Fee, MoneyMovement are skipped
        self.assertEqual(len(result["TEST4CAD-CAD"]), 1)
        self.assertIn("NBuy", result["TEST4CAD-CAD"][0])
        self.assertIn("XDIV", result["TEST4CAD-CAD"][0])

    def test_activities_export_checking_account_skipped(self):
        """Test that Checking accounts are skipped from activities export"""
        self._create_activities_csv("activities-export-2026-04-01.csv", [
            "2026-04-01,,CHKACCTCAD,Chequing,Interest,,,,,CAD,34.13,,,34.13",
        ])
        config_path = self._create_config({
            "cdr_symbols": [],
            "CHKACCTCAD-CAD": {"nickname": "Test-Checking", "type": "Checking"},
            "CHKACCTCAD-USD": {"nickname": "Test-Checking-USD", "type": "Checking"},
        })

        result, _ = read_csv_files(self.input_dir, config_path)

        # Checking accounts should not be processed from activities export
        self.assertEqual(len(result.get("CHKACCTCAD-CAD", [])), 0)

    def test_activities_export_old_month_skipped(self):
        """Test that Trade transactions from previous months are skipped"""
        self._create_activities_csv("activities-export-2026-04-01.csv", [
            "2026-02-01,2026-02-01,OLDMONTHCAD,TFSA,Trade,BUY,LONG,SHOP,Shopify,CAD,5,100,0,-500",
            "2026-03-15,2026-03-15,OLDMONTHCAD,TFSA,Trade,BUY,LONG,RY,Royal Bank,CAD,10,80,0,-800",
            "2026-04-01,2026-04-01,OLDMONTHCAD,TFSA,Trade,BUY,LONG,ENB,Enbridge,CAD,20,50,0,-1000",
        ])
        config_path = self._create_config({
            "cdr_symbols": [],
            "OLDMONTHCAD-CAD": {"nickname": "Test-TFSA", "type": "Investment"},
            "OLDMONTHCAD-USD": {"nickname": "Test-TFSA-USD", "type": "Investment"},
        })

        result, _ = read_csv_files(self.input_dir, config_path)

        # Only April (current month) Trade should be processed
        self.assertEqual(len(result["OLDMONTHCAD-CAD"]), 1)
        self.assertIn("ENB-CT", result["OLDMONTHCAD-CAD"][0])

    def test_activities_export_fee_skipped(self):
        """Test that Fee transactions are skipped from activities export (only Trade is processed)"""
        self._create_activities_csv("activities-export-2026-04-01.csv", [
            "2026-04-15,,TEST5CAD,TFSA,Fee,,,,,CAD,-6.8,,,-6.8",
        ])
        config_path = self._create_config({
            "cdr_symbols": [],
            "TEST5CAD-CAD": {"nickname": "Test-TFSA-CAD", "type": "Investment"},
            "TEST5CAD-USD": {"nickname": "Test-TFSA-USD", "type": "Investment"},
        })

        result, _ = read_csv_files(self.input_dir, config_path)

        # Fee is not Trade, so it should be skipped
        self.assertEqual(len(result.get("TEST5CAD-CAD", [])), 0)

    def test_activities_export_multiple_investment_accounts_trade_only(self):
        """Test that only Trade transactions are processed across multiple accounts"""
        self._create_activities_csv("activities-export-2026-04-01.csv", [
            "2026-04-15,,ACCT1CAD,TFSA,Interest,,,,,CAD,25.09,,,25.09",
            "2026-04-15,,ACCT2CAD,Non-registered,Interest,,,,,USD,56.28,,,56.28",
            "2026-04-06,2026-04-06,ACCT3CAD,Non-registered,Trade,BUY,LONG,ENB,Enbridge Inc,CAD,177.7887,71,0,-12623",
            "2026-04-10,2026-04-10,ACCT1CAD,TFSA,Trade,BUY,LONG,SHOP,Shopify Inc,CAD,5,120,0,-600",
        ])
        config_path = self._create_config({
            "cdr_symbols": [],
            "ACCT1CAD-CAD": {"nickname": "Acct1-CAD", "type": "Investment"},
            "ACCT1CAD-USD": {"nickname": "Acct1-USD", "type": "Investment"},
            "ACCT2CAD-CAD": {"nickname": "Acct2-CAD", "type": "Investment"},
            "ACCT2CAD-USD": {"nickname": "Acct2-USD", "type": "Investment"},
            "ACCT3CAD-CAD": {"nickname": "Acct3-CAD", "type": "Investment"},
            "ACCT3CAD-USD": {"nickname": "Acct3-USD", "type": "Investment"},
        })

        result, _ = read_csv_files(self.input_dir, config_path)

        # ACCT1 should have 1 Trade/BUY (Interest is skipped)
        self.assertEqual(len(result["ACCT1CAD-CAD"]), 1)
        self.assertIn("SHOP-CT", result["ACCT1CAD-CAD"][0])

        # ACCT2 should have nothing (Interest only, no Trade)
        self.assertEqual(len(result.get("ACCT2CAD-USD", [])), 0)

        # ACCT3 should have 1 Trade/BUY
        self.assertEqual(len(result["ACCT3CAD-CAD"]), 1)
        self.assertIn("ENB-CT", result["ACCT3CAD-CAD"][0])

    def test_activities_export_mixed_with_monthly_statement(self):
        """Test processing both activities export and monthly statement files together.
        Activities export only processes Trade transactions for Investment accounts in the current month.
        Monthly statements process all accounts and transaction types as before."""
        # Create activities export file with Trade for Investment account in current month
        self._create_activities_csv("activities-export-2026-04-01.csv", [
            "2026-04-15,2026-04-15,NEWACCTCAD,TFSA,Trade,BUY,LONG,SHOP,Shopify,CAD,5,100,0,-500",
        ])

        # Create monthly statement file (processes all accounts regardless)
        monthly_path = os.path.join(self.input_dir, "monthly-statement-transactions-OLDACCTCAD-2026-01-01.csv")
        with open(monthly_path, "w") as f:
            f.write("date,transaction,description,amount,balance,currency\n")
            f.write("2026-01-01,INT,Interest earned,2.37,894.39,CAD\n")

        config_path = self._create_config({
            "cdr_symbols": [],
            "NEWACCTCAD-CAD": {"nickname": "New-Acct-CAD", "type": "Investment"},
            "NEWACCTCAD-USD": {"nickname": "New-Acct-USD", "type": "Investment"},
            "OLDACCTCAD-CAD": {"nickname": "Old-Acct-CAD", "type": "Checking"},
            "OLDACCTCAD-USD": {"nickname": "Old-Acct-USD", "type": "Checking"},
        })

        result, source_files = read_csv_files(self.input_dir, config_path)

        # New account from activities export (Trade only)
        self.assertIn("NEWACCTCAD-CAD", result)
        self.assertEqual(len(result["NEWACCTCAD-CAD"]), 1)
        self.assertIn("NBuy", result["NEWACCTCAD-CAD"][0])

        # Old account from monthly statement (all transaction types)
        self.assertIn("OLDACCTCAD-CAD", result)
        self.assertEqual(len(result["OLDACCTCAD-CAD"]), 1)

        # Source files tracking
        self.assertIn("activities-export-2026-04-01.csv", source_files["NEWACCTCAD-CAD"])
        self.assertIn("monthly-statement-transactions-OLDACCTCAD-2026-01-01.csv", source_files["OLDACCTCAD-CAD"])

    def test_activities_export_cdr_symbol_trade(self):
        """Test CDR symbol handling for activities export Trade transaction"""
        self._create_activities_csv("activities-export-2026-04-01.csv", [
            "2026-04-09,2026-04-09,TEST6CAD,Non-registered margin,Trade,BUY,LONG,NVDA,Nvidia CDR,CAD,10,50,0,-500",
        ])
        config_path = self._create_config({
            "cdr_symbols": ["TSLA", "DIS", "NVDA", "AAPL"],
            "TEST6CAD-CAD": {"nickname": "Test-CDR-CAD", "type": "Investment"},
            "TEST6CAD-USD": {"nickname": "Test-CDR-USD", "type": "Investment"},
        })

        result, _ = read_csv_files(self.input_dir, config_path)

        self.assertEqual(len(result["TEST6CAD-CAD"]), 1)
        qif = result["TEST6CAD-CAD"][0]
        self.assertIn("NBuy", qif)
        # NVDA in CAD should get -QH suffix (CDR symbol)
        self.assertIn("NVDA-QH", qif)

    def test_activities_export_money_movement_skipped(self):
        """Test that MoneyMovement transactions are skipped from activities export (only Trade is processed)"""
        self._create_activities_csv("activities-export-2026-04-01.csv", [
            "2026-04-01,,TEST7CAD,Non-registered,MoneyMovement,E_TRFOUT,,,,CAD,-70,,,-70",
            "2026-04-02,,TEST7CAD,Non-registered,MoneyMovement,AFT_OUT,,,,CAD,-410.19,,,-410.19",
            "2026-04-03,,TEST7CAD,Non-registered,MoneyMovement,AFT_IN,,,,CAD,5313.12,,,5313.12",
        ])
        config_path = self._create_config({
            "cdr_symbols": [],
            "TEST7CAD-CAD": {"nickname": "Test-Movement-CAD", "type": "Investment"},
            "TEST7CAD-USD": {"nickname": "Test-Movement-USD", "type": "Investment"},
        })

        result, _ = read_csv_files(self.input_dir, config_path)

        # MoneyMovement is not Trade, so all should be skipped
        self.assertEqual(len(result.get("TEST7CAD-CAD", [])), 0)

    def test_activities_export_usd_trade_only(self):
        """Test that only Trade transactions are processed for USD Investment accounts"""
        self._create_activities_csv("activities-export-2026-04-01.csv", [
            "2026-04-01,,TEST8CAD,Non-registered,Interest,,,,,USD,56.28,,,56.28",
            "2026-04-12,,TEST8CAD,Non-registered,MoneyMovement,EFT,,,,USD,11103,,,11103",
            "2026-04-06,2026-04-06,TEST8CAD,Non-registered,Trade,BUY,LONG,AAPL,Apple Inc,USD,5,200,0,-1000",
        ])
        config_path = self._create_config({
            "cdr_symbols": [],
            "TEST8CAD-CAD": {"nickname": "Test-NonReg-CAD", "type": "Investment"},
            "TEST8CAD-USD": {"nickname": "Test-NonReg-USD", "type": "Investment"},
        })

        result, _ = read_csv_files(self.input_dir, config_path)

        # Only Trade/BUY should be processed (Interest and MoneyMovement are skipped)
        self.assertEqual(len(result["TEST8CAD-USD"]), 1)
        self.assertIn("NBuy", result["TEST8CAD-USD"][0])
        self.assertIn("AAPL", result["TEST8CAD-USD"][0])

    def test_activities_export_symbol_with_period(self):
        """Test that symbols with periods (e.g., ETHX.B, DLR.U) are handled correctly"""
        self._create_activities_csv("activities-export-2026-04-01.csv", [
            "2026-04-06,2026-04-06,TEST9CAD,RRSP,Trade,BUY,LONG,ETHX.B,CI Galaxy Ethereum ETF,CAD,926.6135,9.1803,0,-8506.59",
        ])
        config_path = self._create_config({
            "cdr_symbols": [],
            "TEST9CAD-CAD": {"nickname": "Test-RRSP-CAD", "type": "Investment"},
            "TEST9CAD-USD": {"nickname": "Test-RRSP-USD", "type": "Investment"},
        })

        result, _ = read_csv_files(self.input_dir, config_path)

        self.assertEqual(len(result["TEST9CAD-CAD"]), 1)
        qif = result["TEST9CAD-CAD"][0]
        self.assertIn("NBuy", qif)
        # ETHX.B should become ETHX-B-CT (period replaced with hyphen)
        self.assertIn("ETHX-B-CT", qif)

    def test_activities_export_source_files_tracking(self):
        """Test that source files are properly tracked for activities export"""
        self._create_activities_csv("activities-export-2026-04-24.csv", [
            "2026-04-15,2026-04-15,SRCTEST1CAD,TFSA,Trade,BUY,LONG,SHOP,Shopify,CAD,5,100,0,-500",
            "2026-04-15,2026-04-15,SRCTEST2CAD,RRSP,Trade,BUY,LONG,AAPL,Apple,USD,3,200,0,-600",
        ])
        config_path = self._create_config({
            "cdr_symbols": [],
            "SRCTEST1CAD-CAD": {"nickname": "Src1-CAD", "type": "Investment"},
            "SRCTEST1CAD-USD": {"nickname": "Src1-USD", "type": "Investment"},
            "SRCTEST2CAD-CAD": {"nickname": "Src2-CAD", "type": "Investment"},
            "SRCTEST2CAD-USD": {"nickname": "Src2-USD", "type": "Investment"},
        })

        _, source_files = read_csv_files(self.input_dir, config_path)

        # Both accounts should reference the activities export file
        self.assertIn("activities-export-2026-04-24.csv", source_files["SRCTEST1CAD-CAD"])
        self.assertIn("activities-export-2026-04-24.csv", source_files["SRCTEST2CAD-USD"])

    def test_activities_export_all_transactions_flag(self):
        """Test --all-transactions flag enables all transaction types from activities export"""
        self._create_activities_csv("activities-export-2026-04-01.csv", [
            "2026-04-15,,ALLFLAGCAD,TFSA,Interest,,,,,CAD,34.13,,,34.13",
            "2026-04-09,,ALLFLAGCAD,TFSA,Dividend,,,XDIV,iShares,CAD,5.00,,,5.00",
            "2026-04-06,2026-04-06,ALLFLAGCAD,TFSA,Trade,BUY,LONG,SHOP,Shopify,CAD,5,100,0,-500",
            "2026-04-10,,ALLFLAGCAD,TFSA,MoneyMovement,EFT,,,,CAD,1000,,,1000",
        ])
        config_path = self._create_config({
            "cdr_symbols": [],
            "ALLFLAGCAD-CAD": {"nickname": "AllFlag-CAD", "type": "Investment"},
            "ALLFLAGCAD-USD": {"nickname": "AllFlag-USD", "type": "Investment"},
        })

        # Without flag: only Trade
        result_default, _ = read_csv_files(self.input_dir, config_path)
        self.assertEqual(len(result_default["ALLFLAGCAD-CAD"]), 1)

        # With flag: all 4 transactions
        result_all, _ = read_csv_files(self.input_dir, config_path, all_transactions=True)
        self.assertEqual(len(result_all["ALLFLAGCAD-CAD"]), 4)

    def test_activities_export_all_accounts_flag(self):
        """Test --all-accounts flag enables all accounts from activities export"""
        self._create_activities_csv("activities-export-2026-04-01.csv", [
            "2026-04-06,2026-04-06,INVACCTCAD,TFSA,Trade,BUY,LONG,SHOP,Shopify,CAD,5,100,0,-500",
            "2026-04-06,2026-04-06,CHKACCTCAD,Chequing,Trade,BUY,LONG,RY,Royal Bank,CAD,10,80,0,-800",
        ])
        config_path = self._create_config({
            "cdr_symbols": [],
            "INVACCTCAD-CAD": {"nickname": "Inv-CAD", "type": "Investment"},
            "INVACCTCAD-USD": {"nickname": "Inv-USD", "type": "Investment"},
            "CHKACCTCAD-CAD": {"nickname": "Chk-CAD", "type": "Checking"},
            "CHKACCTCAD-USD": {"nickname": "Chk-USD", "type": "Checking"},
        })

        # Without flag: only Investment
        result_default, _ = read_csv_files(self.input_dir, config_path)
        self.assertEqual(len(result_default.get("INVACCTCAD-CAD", [])), 1)
        self.assertEqual(len(result_default.get("CHKACCTCAD-CAD", [])), 0)

        # With flag: all accounts
        result_all, _ = read_csv_files(self.input_dir, config_path, all_accounts=True)
        self.assertEqual(len(result_all["INVACCTCAD-CAD"]), 1)
        self.assertEqual(len(result_all["CHKACCTCAD-CAD"]), 1)

    def test_activities_export_both_flags(self):
        """Test both --all-transactions and --all-accounts flags together"""
        self._create_activities_csv("activities-export-2026-04-01.csv", [
            "2026-04-15,,CHKBOTHCAD,Chequing,Interest,,,,,CAD,10.50,,,10.50",
            "2026-04-06,2026-04-06,CHKBOTHCAD,Chequing,Trade,BUY,LONG,RY,Royal Bank,CAD,10,80,0,-800",
        ])
        config_path = self._create_config({
            "cdr_symbols": [],
            "CHKBOTHCAD-CAD": {"nickname": "ChkBoth-CAD", "type": "Checking"},
            "CHKBOTHCAD-USD": {"nickname": "ChkBoth-USD", "type": "Checking"},
        })

        # Without flags: nothing (Checking + non-Trade)
        result_default, _ = read_csv_files(self.input_dir, config_path)
        self.assertEqual(len(result_default.get("CHKBOTHCAD-CAD", [])), 0)

        # With both flags: both transactions from Checking account
        result_all, _ = read_csv_files(self.input_dir, config_path, all_transactions=True, all_accounts=True)
        self.assertEqual(len(result_all["CHKBOTHCAD-CAD"]), 2)

    def test_activities_export_empty_trade_rows_skipped(self):
        """Test that Trade rows with empty amounts are skipped"""
        self._create_activities_csv("activities-export-2026-04-01.csv", [
            "2026-04-01,2026-04-01,EMPTY1CAD,TFSA,Trade,BUY,LONG,SHOP,Shopify,CAD,5,100,0,-500",
            "2026-04-02,2026-04-02,EMPTY1CAD,TFSA,Trade,BUY,LONG,RY,Royal Bank,CAD,,,,",
        ])
        config_path = self._create_config({
            "cdr_symbols": [],
            "EMPTY1CAD-CAD": {"nickname": "Empty-Test-CAD", "type": "Investment"},
            "EMPTY1CAD-USD": {"nickname": "Empty-Test-USD", "type": "Investment"},
        })

        result, _ = read_csv_files(self.input_dir, config_path)

        # Only the first Trade row should be processed (second has empty amount)
        self.assertEqual(len(result["EMPTY1CAD-CAD"]), 1)
        self.assertIn("SHOP-CT", result["EMPTY1CAD-CAD"][0])


if __name__ == "__main__":
    unittest.main()
