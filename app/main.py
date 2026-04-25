import argparse
import csv
import os
import re

import yaml

# Constants for CSV format types
FORMAT_MONTHLY_STATEMENT = "monthly_statement"
FORMAT_ACTIVITIES_EXPORT = "activities_export"

# Activities export column names
ACTIVITIES_COLUMNS = [
    "transaction_date", "settlement_date", "account_id", "account_type",
    "activity_type", "activity_sub_type", "direction", "symbol", "name",
    "currency", "quantity", "unit_price", "commission", "net_cash_amount"
]


def detect_csv_format(filepath):
    """
    Detect the format of a CSV file by examining its headers.

    Args:
        filepath (str): Path to the CSV file.

    Returns:
        str: FORMAT_MONTHLY_STATEMENT or FORMAT_ACTIVITIES_EXPORT

    Raises:
        ValueError: If the CSV format is not recognized.
    """
    with open(filepath, "r") as f:
        reader = csv.reader(f)
        try:
            headers = next(reader)
        except StopIteration:
            raise ValueError(f"Empty CSV file: {filepath}")

    # Strip whitespace and BOM from headers
    headers = [h.strip().strip("\ufeff") for h in headers]

    if "transaction_date" in headers and "activity_type" in headers:
        return FORMAT_ACTIVITIES_EXPORT
    elif "date" in headers and "transaction" in headers:
        return FORMAT_MONTHLY_STATEMENT
    else:
        raise ValueError(
            f"Unrecognized CSV format in '{filepath}'. "
            f"Headers: {headers}"
        )


def map_activities_transaction_type(activity_type, activity_sub_type, net_cash_amount):
    """
    Map activities export activity_type and activity_sub_type to the legacy transaction type.

    Args:
        activity_type (str): The activity_type from the new format (e.g., 'Trade', 'MoneyMovement').
        activity_sub_type (str): The activity_sub_type from the new format (e.g., 'BUY', 'TRANSFER').
        net_cash_amount (float): The net cash amount (used to determine direction for some types).

    Returns:
        str: The legacy transaction type string (e.g., 'BUY', 'SELL', 'EFT', 'INT').
    """
    if activity_type == "Trade":
        if activity_sub_type == "BUY":
            return "BUY"
        elif activity_sub_type == "SELL":
            return "SELL"
        else:
            return activity_sub_type

    elif activity_type == "Dividend":
        return "DIV"

    elif activity_type == "Interest":
        return "INT"

    elif activity_type == "Fee":
        return "FEE"

    elif activity_type == "BonusPayment":
        if activity_sub_type == "CASHBACK":
            return "CASHBACK"
        elif activity_sub_type == "GIVEAWAY":
            return "GIVEAWAY"
        else:
            return activity_sub_type

    elif activity_type == "MoneyMovement":
        sub = activity_sub_type.upper() if activity_sub_type else ""
        if sub == "EFT":
            if net_cash_amount < 0:
                return "EFTOUT"
            else:
                return "EFT"
        elif sub == "TRANSFER":
            if net_cash_amount < 0:
                return "TRFOUT"
            else:
                return "TRFIN"
        elif sub == "TRANSFER_TF":
            if net_cash_amount < 0:
                return "TRFOUTTF"
            else:
                return "TRFINTF"
        elif sub in ("E_TRFOUT", "EFTOUT", "AFT_OUT", "OBP_OUT", "SPEND"):
            return sub
        elif sub in ("E_TRFIN", "AFT_IN"):
            return sub
        else:
            # Fallback: determine by amount sign
            if net_cash_amount < 0:
                return "TRFOUT"
            else:
                return "TRFIN"

    else:
        return f"{activity_type}_{activity_sub_type}" if activity_sub_type else activity_type


def convert_activities_row_to_legacy(row):
    """
    Convert an activities export CSV row to the legacy format expected by generate_qif_entry.

    The new format has structured columns for symbol, quantity, unit_price, commission,
    while the old format encodes this information in the 'description' field.

    Args:
        row (dict): A row from the activities export CSV with keys matching ACTIVITIES_COLUMNS.

    Returns:
        dict: A row in the legacy format with keys: 'date', 'transaction', 'description',
              'amount', 'currency'. Returns None if the row should be skipped.
    """
    net_cash_str = (row.get("net_cash_amount") or "").strip()
    if not net_cash_str:
        return None

    try:
        net_cash_amount = float(net_cash_str)
    except ValueError:
        return None

    activity_type = (row.get("activity_type") or "").strip()
    activity_sub_type = (row.get("activity_sub_type") or "").strip()
    symbol = (row.get("symbol") or "").strip()
    name = (row.get("name") or "").strip()
    quantity_str = (row.get("quantity") or "").strip()
    unit_price_str = (row.get("unit_price") or "").strip()
    commission_str = (row.get("commission") or "").strip()
    currency = (row.get("currency") or "").strip()
    date = (row.get("transaction_date") or "").strip()

    transaction_type = map_activities_transaction_type(
        activity_type, activity_sub_type, net_cash_amount
    )

    # Build description based on transaction type
    if activity_type == "Trade":
        # For trade transactions, build the "SYMBOL - QUANTITY shares" description
        quantity = float(quantity_str) if quantity_str else 0
        # Use absolute value for quantity in description
        abs_quantity = abs(quantity)
        description = f"{symbol} - {abs_quantity} shares"
    elif activity_type == "Dividend":
        description = f"{symbol} - {name}" if name else f"{symbol} - Dividend"
    elif activity_type == "Interest":
        description = "Interest earned"
    elif activity_type == "Fee":
        description = "Account fee"
    elif activity_type == "BonusPayment":
        if activity_sub_type == "CASHBACK":
            description = "Cashback reward"
        elif activity_sub_type == "GIVEAWAY":
            description = "Giveaway received"
        else:
            description = f"{activity_type} {activity_sub_type}"
    elif activity_type == "MoneyMovement":
        sub_desc_map = {
            "TRANSFER": "Transfer",
            "TRANSFER_TF": "Transfer",
            "EFT": "Electronic funds transfer",
            "E_TRFOUT": "e-Transfer out",
            "E_TRFIN": "e-Transfer in",
            "AFT_OUT": "Automated transfer out",
            "AFT_IN": "Automated transfer in",
            "OBP_OUT": "Online bill payment",
            "SPEND": "Spending transaction",
        }
        description = sub_desc_map.get(activity_sub_type, f"{activity_type} {activity_sub_type}")
    else:
        description = f"{activity_type} {activity_sub_type}".strip()

    return {
        "date": date,
        "transaction": transaction_type,
        "description": description,
        "amount": str(net_cash_amount),
        "currency": currency,
    }


def read_config(config_file):
    """
    Read the configuration from the specified YAML file.

    Args:
        config_file (str): The path to the YAML configuration file.

    Returns:
        dict: The configuration data as a dictionary.
    """
    with open(config_file, "r") as file:
        config = yaml.safe_load(file)
    return config


def extract_account_name(filename):
    """
    Extract the account name from the given CSV filename.

    The expected filename format is:
    'monthly-statement-transactions-{ACCOUNT_NAME}-{DATE}.csv'

    Args:
        filename (str): The CSV filename.

    Returns:
        str: The extracted account name.
    """
    pattern = r"monthly-statement-transactions-(\w+)-\d{4}-\d{2}-\d{2}.csv"
    match = re.search(pattern, filename)
    if match:
        return match.group(1)
    else:
        return None


def extract_option_info(description):
    """
    Extract the option name, number of contracts, and fees from the given description.

    Parses WealthSimple options trading descriptions to extract key information needed
    for QIF conversion. Handles both BUYTOOPEN and SELLTOCLOSE transactions.

    Args:
        description (str): The description string containing option details.

    Examples:
        "SPY 450.00 USD CALL 2025-07-25: Bought 2 contract (executed at 2025-07-23), Fee: $1.50"
        "AAPL 180.00 USD PUT 2025-07-30: Sold 1 contract (executed at 2025-07-25), Fee: $0.75"
        "TSLA 250.00 USD CALL 2025-08-15: Bought 5 contract (executed at 2025-08-10), Fee: $3.75"

    Returns:
        tuple: (option_name, contracts, fee) where:
            - option_name (str): Full option symbol (e.g., "SPY 450.00 USD CALL 2025-07-25")
            - contracts (int): Number of contracts traded (e.g., 2)
            - fee (float): Trading fee in dollars (e.g., 1.50)
            Returns (None, None, None) if parsing fails.
    """
    if not description or not isinstance(description, str):
        return None, None, None

    colon_index = description.find(":")
    if colon_index == -1:
        return None, None, None

    option_name = description[:colon_index].strip()
    after_colon = description[colon_index + 1 :]

    contracts_match = re.search(r"(\d+)\s+contract", after_colon)
    contracts = int(contracts_match.group(1)) if contracts_match else None

    fee_match = re.search(r"Fee:\s*\$([\d.]+)", after_colon)
    fee = float(fee_match.group(1)) if fee_match else None

    return option_name, contracts, fee


def extract_symbol(description, currency, cdr_symbols=None):
    """
    Extract the stock symbol from the given description and apply appropriate suffix.

    Handles both regular stocks and Canadian Depositary Receipts (CDRs) with proper
    symbol mapping for QIF compatibility. Symbol extraction is case-insensitive and
    always returns uppercase symbols. Periods in symbols are replaced with hyphens
    for QIF compatibility (e.g., ETHX.B becomes ETHX-B).

    Args:
        description (str): The transaction description containing the symbol.
        currency (str): The transaction currency ("USD" or "CAD").
        cdr_symbols (list, optional): List of CDR symbols that get "-QH" suffix in CAD.
                                      Defaults to empty list if not provided.

    Examples:
        Input: "AAPL - 10.0 shares", currency="USD" → Output: "AAPL" (no suffix for USD)
        Input: "tsla - 5.0 shares", currency="CAD" → Output: "TSLA-QH" (CDR mapping)
        Input: "shop - 15.0 shares", currency="CAD" → Output: "SHOP-CT"
        Input: "nvda - 8.0 shares", currency="CAD" → Output: "NVDA-QH" (CDR mapping)
        Input: "ETHX.B - 5.0 shares", currency="CAD" → Output: "ETHX-B-CT"

    Returns:
        str: The extracted symbol with appropriate suffix:
            - USD symbols get no suffix
            - CDR symbols in CAD get "-QH" suffix
            - All other CAD symbols get "-CT" suffix
            - Periods in symbols are replaced with hyphens
            - Symbol is always returned in uppercase
            - Returns None if symbol extraction fails
    """
    if cdr_symbols is None:
        cdr_symbols = []

    dash_index = description.find("-")
    if dash_index == -1:
        return None
    else:
        symbol = description[:dash_index].strip().upper()
        # Replace periods with hyphens for QIF compatibility (e.g., ETHX.B -> ETHX-B)
        symbol = symbol.replace(".", "-")

        # USD symbols have no suffix
        if currency == "USD":
            return symbol

        # CAD symbols get appropriate suffix
        # Convert cdr_symbols to uppercase for case-insensitive comparison
        cdr_symbols_upper = [s.upper() for s in cdr_symbols]
        if symbol in cdr_symbols_upper:
            return f"{symbol}-QH"
        else:
            return f"{symbol}-CT"


def extract_unit(input_string):
    """
    Extract the number of shares from the given input string.

    Parses WealthSimple stock transaction descriptions to extract share quantities
    for QIF conversion.

    Args:
        input_string (str): The transaction description containing share information.

    Examples:
        "AAPL - 10.0 shares" → Returns: 10.0
        "TSLA - 5.0 shares" → Returns: 5.0
        "SHOP - 15.0 shares" → Returns: 15.0
        "NVDA - 2.5 shares" → Returns: 2.5

    Returns:
        float: The extracted number of shares, or None if parsing fails.

    Note:
        Expected format is '{SYMBOL} - {NUMBER} shares'
    """
    pattern = r"(\d+\.\d+)\s+shares"
    match = re.search(pattern, input_string)
    if match:
        return float(match.group(1))
    else:
        return None


def generate_qif_entry(row, target_currency, filename=None, cdr_symbols=None):
    """
    Generate a QIF entry from a CSV transaction row for the specified currency.

    Converts WealthSimple CSV transaction data into QIF format entries. Handles
    multiple transaction types including stocks, options, dividends, contributions,
    and various cash transactions. Only processes transactions matching the target currency.

    Args:
        row (dict): CSV row containing transaction data with keys:
            - 'date': Transaction date (YYYY-MM-DD format)
            - 'transaction': Transaction type (BUY, SELL, BUYTOOPEN, etc.)
            - 'description': Transaction description
            - 'amount': Transaction amount (string, can be negative)
            - 'currency': Transaction currency (USD or CAD)
        target_currency (str): Currency to filter for ("USD" or "CAD")
        filename (str, optional): Source filename for error reporting
        cdr_symbols (list, optional): List of CDR symbols that get "-QH" suffix in CAD.

    Examples:
        Stock Purchase:
        Input: {'date': '2025-07-15', 'transaction': 'BUY', 'description': 'AAPL - 10.0 shares',
                'amount': '-1500.00', 'currency': 'USD'}
        Output: 'D07/15/2025\nNBuy\nYAAPL-CT\nI150.00\nQ10\nT1500.00\nO0.00\nCc\n^'

        Options Trading:
        Input: {'date': '2025-07-23', 'transaction': 'BUYTOOPEN',
                'description': 'SPY 450.00 USD CALL 2025-07-25: Bought 2 contract (executed at 2025-07-23), Fee: $1.50',
                'amount': '-320.50', 'currency': 'USD'}
        Output: 'D07/23/2025\nNBuy\nYSPY 450.00 USD CALL 2025-07-25\nI159.50\nQ2\nT320.50\nO1.50\nCc\n^'

        Contribution:
        Input: {'date': '2025-07-16', 'transaction': 'CONT',
                'description': 'Contribution (executed at 2025-07-16)', 'amount': '1000.0', 'currency': 'CAD'}
        Output: 'D07/16/2025\nNXIn\nT1000.0\nO0.00\nCc\nPContribution\nMContribution (executed at 2025-07-16)\n^'

    Returns:
        str: Formatted QIF entry string, or None if:
            - Currency doesn't match target_currency
            - Transaction type is in the ignored list (RECALL, LOAN, STKDIS, STKREORG)
            - Amount is empty or invalid (warning printed)

    Raises:
        ValueError: If transaction type is not recognized
    """
    transaction_type = row["transaction"]

    # Skip rows with empty or invalid amount values
    amount_str = row.get("amount", "").strip()
    if not amount_str:
        file_info = f" in file '{filename}'" if filename else ""
        print(f"WARNING: Skipping row with empty amount{file_info}")
        print(f"  Row data: {dict(row)}")
        return None

    try:
        total = abs(float(amount_str))
    except ValueError:
        file_info = f" in file '{filename}'" if filename else ""
        print(f"WARNING: Skipping row with invalid amount '{amount_str}'{file_info}")
        print(f"  Row data: {dict(row)}")
        return None

    currency = row["currency"]

    if currency != target_currency:
        return None

    if transaction_type == "BUY":
        symbol = extract_symbol(row["description"], currency, cdr_symbols)
        unit = extract_unit(row["description"])
        price = total / unit
        return f'D{row["date"]}\nNBuy\nY{symbol}\nI{price}\nQ{unit}\nT{total}\nO0.00\nCc\n^'
    elif transaction_type == "SELL":
        symbol = extract_symbol(row["description"], currency, cdr_symbols)
        unit = extract_unit(row["description"])
        price = total / unit
        return f'D{row["date"]}\nNSell\nY{symbol}\nI{price}\nQ{unit}\nT{total}\nO0.00\nCc\n^'
    elif transaction_type == "BUYTOOPEN":
        option_name, unit, fee = extract_option_info(row["description"])
        option_total = total - fee
        price = option_total / unit
        return f'D{row["date"]}\nNBuy\nY{option_name}\nI{price}\nQ{unit}\nT{total}\nO{fee}\nCc\n^'
    elif transaction_type == "SELLTOCLOSE":
        option_name, unit, fee = extract_option_info(row["description"])
        option_total = total + fee
        price = option_total / unit
        return f'D{row["date"]}\nNSell\nY{option_name}\nI{price}\nQ{unit}\nT{total}\nO{fee}\nCc\n^'
    elif transaction_type == "DIV":
        symbol = extract_symbol(row["description"], currency, cdr_symbols)
        return f'D{row["date"]}\nNDiv\nY{symbol}\nT{total}\nO0.00\nCc\n^'
    elif transaction_type == "CONT":
        return f'D{row["date"]}\nNXIn\nT{total}\nO0.00\nCc\nPContribution\nM{row["description"]}\n^'
    elif transaction_type == "FPLINT":  # Stock lending monthly interest payment
        return f'D{row["date"]}\nNXIn\nT{total}\nO0.00\nCc\nPInterest\nM{row["description"]}\n^'
    elif transaction_type == "NRT":
        return f'D{row["date"]}\nNXOut\nT{total}\nO0.00\nCc\nPUS Non-Resident Tax Withholding\nM{row["description"]}\n^'
    elif transaction_type in ("TRFOUT", "SPEND", "E_TRFOUT", "EFTOUT", "AFT_OUT", "FEE", "TRFOUTTF", "WD", "OBP_OUT"):
        return f'D{row["date"]}\nT-{total}\nO0.00\nCc\nP{row["description"]}\n^'
    elif transaction_type in ("CASHBACK", "EFT", "INT", "TRFIN", "TRFINTF", "REFUND", "E_TRFIN", "GIVEAWAY", "AFT_IN"):
        return f'D{row["date"]}\nT{total}\nO0.00\nCc\nP{row["description"]}\n^'
    elif transaction_type in ("RECALL", "LOAN", "STKDIS", "STKREORG"):
        return None
    else:
        raise ValueError(f"Invalid transaction type: {transaction_type}")


def _read_monthly_statement_file(file_path, filename, account_name, cdr_symbols,
                                  transactions_by_account, source_files_by_account):
    """
    Read a monthly statement CSV file and add transactions to the account dictionaries.

    Args:
        file_path (str): Full path to the CSV file.
        filename (str): Just the filename (for error reporting and source tracking).
        account_name (str): The extracted account name from the filename.
        cdr_symbols (list): List of CDR symbols for symbol suffix handling.
        transactions_by_account (dict): Dict to populate with QIF entries by account-currency.
        source_files_by_account (dict): Dict to track source files by account-currency.
    """
    for target_currency in ["USD", "CAD"]:
        per_currency_account_name = f"{account_name}-{target_currency}"
        transactions_by_account.setdefault(per_currency_account_name, [])
        source_files_by_account.setdefault(per_currency_account_name, set())
        source_files_by_account[per_currency_account_name].add(filename)

        with open(file_path, "r") as csv_file:
            reader = csv.DictReader(csv_file)
            for row in reader:
                qif = generate_qif_entry(
                    row, target_currency, filename, cdr_symbols
                )
                if qif:
                    transactions_by_account[per_currency_account_name].append(qif)


def _extract_activities_export_month(filename):
    """
    Extract the year-month from an activities export filename.

    Args:
        filename (str): The filename (e.g., 'activities-export-2026-04-24.csv').

    Returns:
        str: The year-month string (e.g., '2026-04'), or None if extraction fails.
    """
    pattern = r"activities-export-(\d{4}-\d{2})-\d{2}\.csv"
    match = re.search(pattern, filename)
    if match:
        return match.group(1)
    return None


def _get_investment_account_ids(config):
    """
    Extract the set of account IDs that are configured as Investment accounts.

    Args:
        config (dict): The configuration dictionary from accounts.yml.

    Returns:
        set: Set of base account IDs (without currency suffix) that are Investment type.
    """
    investment_ids = set()
    for key, value in config.items():
        if isinstance(value, dict) and value.get("type") == "Investment":
            # Strip the currency suffix (e.g., 'H16530307CAD-USD' -> 'H16530307CAD')
            if "-" in key:
                base_id = key.rsplit("-", 1)[0]
                investment_ids.add(base_id)
            else:
                investment_ids.add(key)
    return investment_ids


def _read_activities_export_file(file_path, filename, cdr_symbols, config,
                                  transactions_by_account, source_files_by_account,
                                  all_transactions=False, all_accounts=False):
    """
    Read an activities export CSV file and add transactions to the account dictionaries.

    By default, the activities export format is only used for Trade transactions from
    Investment accounts in the current (incomplete) month. The current month is
    determined from the filename date. Completed months will be re-exported by
    WealthSimple in the legacy monthly statement format with richer info.

    Args:
        file_path (str): Full path to the CSV file.
        filename (str): Just the filename (for error reporting and source tracking).
        cdr_symbols (list): List of CDR symbols for symbol suffix handling.
        config (dict): The full configuration dictionary (used to determine Investment accounts).
        transactions_by_account (dict): Dict to populate with QIF entries by account-currency.
        source_files_by_account (dict): Dict to track source files by account-currency.
        all_transactions (bool): If True, process all transaction types (not just Trade).
        all_accounts (bool): If True, process all accounts (not just Investment).
    """
    # Extract the current month from the filename
    current_month = _extract_activities_export_month(filename)
    if current_month is None:
        print(
            f"WARNING: Could not extract month from activities export filename '{filename}'. "
            f"Expected format: 'activities-export-YYYY-MM-DD.csv'"
        )
        return

    # Get the set of investment account IDs from config
    investment_account_ids = _get_investment_account_ids(config)

    with open(file_path, "r") as csv_file:
        reader = csv.DictReader(csv_file)
        for row in reader:
            account_id = (row.get("account_id") or "").strip()
            if not account_id:
                continue

            # Only process investment accounts (unless --all-accounts is set)
            if not all_accounts and account_id not in investment_account_ids:
                continue

            # Only process transactions from the current (incomplete) month
            transaction_date = (row.get("transaction_date") or "").strip()
            if not transaction_date or not transaction_date.startswith(current_month):
                continue

            # Only process Trade transactions (BUY/SELL) from activities export
            # unless --all-transactions is set. Other transaction types
            # (Interest, Dividend, Fee, MoneyMovement, etc.) will normally be
            # re-exported in the legacy monthly statement format with richer info
            if not all_transactions:
                activity_type = (row.get("activity_type") or "").strip()
                if activity_type != "Trade":
                    continue

            # Convert activities row to legacy format
            legacy_row = convert_activities_row_to_legacy(row)
            if legacy_row is None:
                continue

            currency = legacy_row["currency"]
            if not currency:
                continue

            # Process for the matching currency only
            for target_currency in ["USD", "CAD"]:
                per_currency_account_name = f"{account_id}-{target_currency}"
                transactions_by_account.setdefault(per_currency_account_name, [])
                source_files_by_account.setdefault(per_currency_account_name, set())
                source_files_by_account[per_currency_account_name].add(filename)

            per_currency_account_name = f"{account_id}-{currency}"
            qif = generate_qif_entry(
                legacy_row, currency, filename, cdr_symbols
            )
            if qif:
                transactions_by_account[per_currency_account_name].append(qif)


def read_csv_files(input_folder, config_filename, all_transactions=False, all_accounts=False):
    """
    Read all CSV files from the input folder and organize transactions by account and currency.

    Processes WealthSimple CSV exports in both the legacy monthly statement format and the
    new activities export format. Separates transactions by currency for each account.
    Creates separate account entries for USD and CAD transactions to enable proper multi-currency
    accounting in QIF format.

    Supported formats:
        - Monthly statement: 'monthly-statement-transactions-{ACCOUNT_ID}-{DATE}.csv'
          Account ID is extracted from the filename.
        - Activities export: 'activities-export-{DATE}.csv'
          Account ID is extracted from the 'account_id' column in the CSV data.

    Args:
        input_folder (str): Path to folder containing WealthSimple CSV files.
        config_filename (str): Path to YAML configuration file containing CDR symbols and account mappings.
        all_transactions (bool): If True, process all transaction types from activities export (not just Trade).
        all_accounts (bool): If True, process all accounts from activities export (not just Investment).

    Returns:
        tuple: (transactions_by_account, source_files_by_account) where:
            - transactions_by_account (dict): Keys are account names with currency suffixes
              (e.g., 'AB1234567CAD-USD') and values are lists of QIF entry strings.
            - source_files_by_account (dict): Keys are account names with currency suffixes
              and values are sets of source filenames.

    Note:
        - Automatically creates both USD and CAD variants for each account
        - Empty lists are created even if no transactions exist for a currency
        - CDR symbols are loaded from config file for proper symbol suffix handling
        - Format detection is done by examining CSV headers
    """
    # Load config to get CDR symbols
    config = read_config(config_filename)
    cdr_symbols = config.get("cdr_symbols", [])

    transactions_by_account = {}
    source_files_by_account = {}

    for filename in os.listdir(input_folder):
        if not filename.endswith(".csv"):
            continue

        file_path = os.path.join(input_folder, filename)

        try:
            csv_format = detect_csv_format(file_path)
        except ValueError as e:
            print(f"WARNING: {e}")
            continue

        if csv_format == FORMAT_MONTHLY_STATEMENT:
            account_name = extract_account_name(filename)
            if account_name is None:
                print(
                    f"WARNING: Skipping '{filename}' - does not match expected "
                    f"filename pattern 'monthly-statement-transactions-{{ACCOUNT_NAME}}-{{DATE}}.csv'"
                )
                continue
            _read_monthly_statement_file(
                file_path, filename, account_name, cdr_symbols,
                transactions_by_account, source_files_by_account
            )
        elif csv_format == FORMAT_ACTIVITIES_EXPORT:
            _read_activities_export_file(
                file_path, filename, cdr_symbols, config,
                transactions_by_account, source_files_by_account,
                all_transactions=all_transactions, all_accounts=all_accounts
            )

    return transactions_by_account, source_files_by_account


def export_qif_files(account_data, config_filename, source_files_by_account=None):
    """
    Export individual QIF files for each account in the account data dictionary.

    Creates separate QIF files for each configured account, applying the appropriate
    QIF format header based on account type (Investment vs Checking).

    Args:
        account_data (dict): Dictionary where keys are account names with currency suffixes
                           (e.g., 'AB1234567CAD-USD') and values are lists of QIF entry strings.
        config_filename (str): Path to YAML configuration file containing account mappings with currency suffixes.

    Configuration Example:
        accounts.yml:
        ```yaml
        AB1234567CAD-CAD:
          nickname: My-Investment-CAD
          type: Investment
        AB1234567CAD-USD:
          nickname: My-Investment-USD
          type: Investment
        CD9876543USD-USD:
          nickname: My-US-Saving
          type: Checking
        EF5555555CAD-CAD:
          nickname: My-Chequeing
          type: Checking
        ```

    Output Files:
        - output/My-Investment-CAD.qif (Investment account format - CAD transactions)
        - output/My-Investment-USD.qif (Investment account format - USD transactions)
        - output/My-US-Saving.qif (Bank account format - USD only)
        - output/My-Chequeing.qif (Bank account format - CAD only)

    Processing Flow:
        1. Tool reads account names with currency suffixes from accounts.yml (e.g., 'AB1234567CAD-CAD')
        2. Processes currency-suffixed accounts directly (e.g., 'AB1234567CAD-USD')
        3. Each account entry corresponds to one output QIF file
        4. Output files use the configured nickname

    QIF Headers:
        - Investment accounts: '!Type:Invst'
        - Checking accounts: '!Type:Bank'

    Raises:
        ValueError: If account name from CSV is not found in configuration file, or if there's a currency mismatch for chequing accounts.

    Note:
        - Skips accounts with no transactions (empty lists)
        - Creates output directory if it doesn't exist
        - Overwrites existing QIF files with same names
        - For chequing accounts, validates that the account currency suffix matches the expected currency
    """

    config = read_config(config_filename)
    print(config)

    for account_name, transactions in account_data.items():
        if len(transactions) == 0:
            continue

        print(account_name)
        if account_name not in config:
            source_files = sorted(source_files_by_account.get(account_name, set())) if source_files_by_account else []
            files_info = "\n  Related CSV files:\n" + "\n".join(f"    - {f}" for f in source_files) if source_files else ""
            raise ValueError(
                f"Unknown account: {account_name}\n"
                f"  Please add this account to your accounts config file.{files_info}"
            )

        account_config = config[account_name]
        account_type = account_config["type"]

        # For chequing accounts, validate currency mismatch
        if account_type == "Checking":
            # Extract currency suffix from account name (e.g., 'WK23MTV36CAD-CAD' -> 'CAD')
            if "-" in account_name:
                account_currency_suffix = account_name.split("-")[-1]
                # Extract base account name (e.g., 'WK23MTV36CAD-CAD' -> 'WK23MTV36CAD')
                base_account_name = account_name.rsplit("-", 1)[0]

                # Determine expected currency from base account name
                # If base account ends with 'CAD', expect CAD; if ends with 'USD', expect USD
                if base_account_name.endswith("CAD"):
                    expected_currency = "CAD"
                elif base_account_name.endswith("USD"):
                    expected_currency = "USD"
                else:
                    # Default to CAD if unclear
                    expected_currency = "CAD"

                # Check for currency mismatch
                if account_currency_suffix != expected_currency:
                    raise ValueError(
                        f"Currency mismatch for chequing account '{account_name}': "
                        f"account suffix indicates '{account_currency_suffix}' but expected '{expected_currency}' "
                        f"based on account base name '{base_account_name}'"
                    )

            transactions.insert(0, "!Type:Bank")
        else:
            transactions.insert(0, "!Type:Invst")

        qif_content = "\n".join(transactions) + "\n"

        filename = f"output/{config[account_name]['nickname']}.qif"
        with open(filename, "w") as file:
            file.write(qif_content)
        print(f"Exported {filename}")


def main():
    parser = argparse.ArgumentParser(
        description="WealthSimple CSV to QIF Conversion CLI App"
    )
    parser.add_argument(
        "--input-folder",
        type=str,
        help="Path to the input folder containing CSV files, default to `input`",
        default="input",
    )
    parser.add_argument(
        "--account-config",
        type=str,
        help="Path to the config for accounts, default to `accounts.yml`",
        default="accounts.yml",
    )
    parser.add_argument(
        "--all-transactions",
        action="store_true",
        help="Process all transaction types from activities export (default: Trade only)",
        default=False,
    )
    parser.add_argument(
        "--all-accounts",
        action="store_true",
        help="Process all accounts from activities export (default: Investment only)",
        default=False,
    )
    args = parser.parse_args()

    csv_data, source_files = read_csv_files(
        args.input_folder, args.account_config,
        all_transactions=args.all_transactions, all_accounts=args.all_accounts
    )
    export_qif_files(csv_data, args.account_config, source_files)


if __name__ == "__main__":
    main()
