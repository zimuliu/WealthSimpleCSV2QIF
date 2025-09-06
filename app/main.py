import os
import csv
import argparse
import re
import yaml

def read_config(config_file):
    """
    Read the configuration from the specified YAML file.

    Args:
        config_file (str): The path to the YAML configuration file.

    Returns:
        dict: The configuration data as a dictionary.
    """
    with open(config_file, 'r') as file:
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
    pattern = r'monthly-statement-transactions-(\w+)-\d{4}-\d{2}-\d{2}.csv'
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

    colon_index = description.find(':')
    if colon_index == -1:
        return None, None, None

    option_name = description[:colon_index].strip()
    after_colon = description[colon_index + 1:]

    contracts_match = re.search(r'(\d+)\s+contract', after_colon)
    contracts = int(contracts_match.group(1)) if contracts_match else None

    fee_match = re.search(r'Fee:\s*\$([\d.]+)', after_colon)
    fee = float(fee_match.group(1)) if fee_match else None

    return option_name, contracts, fee


def extract_symbol(description, currency):
    """
    Extract the stock symbol from the given description and apply appropriate suffix.

    Handles both regular stocks and Canadian Depositary Receipts (CDRs) with proper
    symbol mapping for QIF compatibility.

    Args:
        description (str): The transaction description containing the symbol.
        currency (str): The transaction currency ("USD" or "CAD").

    Examples:
        Input: "AAPL - 10.0 shares", currency="USD" → Output: "AAPL-CT"
        Input: "TSLA - 5.0 shares", currency="CAD" → Output: "TSLA-QH" (CDR mapping)
        Input: "SHOP - 15.0 shares", currency="CAD" → Output: "SHOP-CT"
        Input: "NVDA - 8.0 shares", currency="CAD" → Output: "NVDA-QH" (CDR mapping)

    Returns:
        str: The extracted symbol with appropriate suffix:
            - CDR symbols (TSLA, DIS, NVDA, AAPL) in CAD get "-QH" suffix
            - All other symbols get "-CT" suffix
            - Returns None if symbol extraction fails
    """
    dash_index = description.find('-')
    if dash_index == -1:
        return None
    else:
        symbol = description[:dash_index].strip()
        CDR_SYMBOLS = ["TSLA", "DIS", "NVDA", "AAPL"]
        if symbol in CDR_SYMBOLS and currency == "CAD":
            return f'{symbol}-QH'
        else:
            return f'{symbol}-CT'

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
    pattern = r'(\d+\.\d+) shares'
    match = re.search(pattern, input_string)
    if match:
        return float(match.group(1))
    else:
        return None

def generate_qif_entry(row, target_currency):
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

    Raises:
        ValueError: If transaction type is not recognized
    """
    transaction_type = row['transaction']
    total = abs(float(row['amount']))
    currency = row['currency']

    if currency != target_currency:
        return None

    if transaction_type == 'BUY':
        symbol = extract_symbol(row['description'], currency)
        unit = extract_unit(row['description'])
        price = total / unit
        return f'D{row["date"]}\nNBuy\nY{symbol}\nI{price}\nQ{unit}\nT{total}\nO0.00\nCc\n^'
    elif transaction_type == 'SELL':
        symbol = extract_symbol(row['description'], currency)
        unit = extract_unit(row['description'])
        price = total / unit
        return f'D{row["date"]}\nNSell\nY{symbol}\nI{price}\nQ{unit}\nT{total}\nO0.00\nCc\n^'
    elif transaction_type == 'BUYTOOPEN':
        option_name, unit, fee = extract_option_info(row['description'])
        option_total = total - fee
        price = option_total / unit
        return f'D{row["date"]}\nNBuy\nY{option_name}\nI{price}\nQ{unit}\nT{total}\nO{fee}\nCc\n^'
    elif transaction_type == 'SELLTOCLOSE':
        option_name, unit, fee = extract_option_info(row['description'])
        option_total = total + fee
        price = option_total / unit
        return f'D{row["date"]}\nNSell\nY{option_name}\nI{price}\nQ{unit}\nT{total}\nO{fee}\nCc\n^'
    elif transaction_type == 'DIV':
        symbol = extract_symbol(row['description'], currency)
        return f'D{row["date"]}\nNDiv\nY{symbol}\nT{total}\nO0.00\nCc\n^'
    elif transaction_type == 'CONT':
        return f'D{row["date"]}\nNXIn\nT{total}\nO0.00\nCc\nPContribution\nM{row["description"]}\n^'
    elif transaction_type == 'FPLINT': #Stock lending monthly interest payment
        return f'D{row["date"]}\nNXIn\nT{total}\nO0.00\nCc\nPInterest\nM{row["description"]}\n^'
    elif transaction_type == 'NRT':
        return f'D{row["date"]}\nNXOut\nT{total}\nO0.00\nCc\nPUS Non-Resident Tax Withholding\nM{row["description"]}\n^'
    elif transaction_type in ('TRFOUT', 'SPEND', 'E_TRFOUT', 'EFTOUT', 'AFT_OUT'):
        return f'D{row["date"]}\nT-{total}\nO0.00\nCc\nP{row["description"]}\n^'
    elif transaction_type in ('CASHBACK', 'EFT', 'INT', 'TRFIN', 'TRFINTF', 'REFUND'):
        return f'D{row["date"]}\nT{total}\nO0.00\nCc\nP{row["description"]}\n^'
    elif transaction_type in ('RECALL', 'LOAN', 'STKDIS', 'STKREORG'):
        return None
    else:
        raise ValueError(f'Invalid transaction type: {transaction_type}')

def read_csv_files(input_folder):
    """
    Read all CSV files from the input folder and organize transactions by account and currency.

    Processes WealthSimple CSV exports and separates transactions by currency for each account.
    Creates separate account entries for USD and CAD transactions to enable proper multi-currency
    accounting in QIF format.

    Args:
        input_folder (str): Path to folder containing WealthSimple CSV files.
                           Expected filename format: 'monthly-statement-transactions-{ACCOUNT_ID}-{DATE}.csv'

    Examples:
        Input files:
        - monthly-statement-transactions-AB1234567CAD-2025-07-01.csv
        - monthly-statement-transactions-CD9876543USD-2025-06-30.csv

        Output structure:
        {
            'AB1234567CAD-USD': [list of USD QIF entries],
            'AB1234567CAD-CAD': [list of CAD QIF entries],
            'CD9876543USD-USD': [list of USD QIF entries],
            'CD9876543USD-CAD': [list of CAD QIF entries]  # May be empty
        }

    Returns:
        dict: Dictionary where keys are account names with currency suffixes (e.g., 'AB1234567CAD-USD')
              and values are lists of QIF entry strings for that account/currency combination.

    Note:
        - Automatically creates both USD and CAD variants for each account
        - Empty lists are created even if no transactions exist for a currency
        - Account ID is extracted from filename using regex pattern
    """
    transactions_by_account = {}

    for filename in os.listdir(input_folder):
        if filename.endswith('.csv'):
            account_name = extract_account_name(filename)
            for target_currency in ['USD', 'CAD']:
                per_currency_account_name = f'{account_name}-{target_currency}'
                transactions_by_account.setdefault(per_currency_account_name, [])

                file_path = os.path.join(input_folder, filename)
                with open(file_path, 'r') as csv_file:
                    reader = csv.DictReader(csv_file)
                    for row in reader:
                        qif = generate_qif_entry(row, target_currency)
                        if qif:
                            transactions_by_account[per_currency_account_name].append(qif)
    return transactions_by_account

def export_qif_files(account_data, config_filename):
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
            raise ValueError("Unknown account")

        account_config = config[account_name]
        account_type = account_config['type']

        # For chequing accounts, validate currency mismatch
        if account_type == "Checking":
            # Extract currency suffix from account name (e.g., 'WK23MTV36CAD-CAD' -> 'CAD')
            if '-' in account_name:
                account_currency_suffix = account_name.split('-')[-1]
                # Extract base account name (e.g., 'WK23MTV36CAD-CAD' -> 'WK23MTV36CAD')
                base_account_name = account_name.rsplit('-', 1)[0]

                # Determine expected currency from base account name
                # If base account ends with 'CAD', expect CAD; if ends with 'USD', expect USD
                if base_account_name.endswith('CAD'):
                    expected_currency = 'CAD'
                elif base_account_name.endswith('USD'):
                    expected_currency = 'USD'
                else:
                    # Default to CAD if unclear
                    expected_currency = 'CAD'

                # Check for currency mismatch
                if account_currency_suffix != expected_currency:
                    raise ValueError(f"Currency mismatch for chequing account '{account_name}': "
                                   f"account suffix indicates '{account_currency_suffix}' but expected '{expected_currency}' "
                                   f"based on account base name '{base_account_name}'")

            transactions.insert(0, '!Type:Bank')
        else:
            transactions.insert(0, '!Type:Invst')

        qif_content = '\n'.join(transactions) + '\n'

        filename = f"output/{config[account_name]['nickname']}.qif"
        with open(filename, 'w') as file:
            file.write(qif_content)
        print(f"Exported {filename}")

def main():
    parser = argparse.ArgumentParser(description='WealthSimple CSV to QIF Conversion CLI App')
    parser.add_argument('--input-folder', type=str, help='Path to the input folder containing CSV files, default to `input`', default='input')
    parser.add_argument('--account-config', type=str, help='Path to the config for accounts, default to `accounts.yml`', default='accounts.yml')
    args = parser.parse_args()

    csv_data = read_csv_files(args.input_folder)
    export_qif_files(csv_data, args.account_config)

if __name__ == "__main__":
    main()
