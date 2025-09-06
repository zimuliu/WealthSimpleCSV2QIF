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

    Args:
        description (str): The description string containing option details.
        Example: "SPY 631.00 USD PUT 2025-07-23: Bought 3 contract (executed at 2025-07-23), Fee: $2.2500"

    Returns:
        tuple: (option_name, contracts, fee) or (None, None, None) if no match found.
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


def extract_symbol(description):
    """
    Extract the symbol from the given description.

    Args:
        description (str): The description.

    Returns:
        str: The extracted symbol.
    """
    dash_index = description.find('-')
    if dash_index == -1:
        return None
    else:
        symbol = description[:dash_index].strip()
        CDR_SYMBOLS = ["TSLA", "DIS", "NVDA", "AAPL"]
        if symbol in CDR_SYMBOLS:
            return f'{symbol}-QH'
        else:
            return f'{symbol}-CT'

def extract_unit(input_string):
    """
    Extract the unit from the given input string.

    The expected format of the input string is:
    '{NUMBER} shares'

    Args:
        input_string (str): The input string.

    Returns:
        float: The extracted number.
    """
    pattern = r'(\d+\.\d+) shares'
    match = re.search(pattern, input_string)
    if match:
        return float(match.group(1))
    else:
        return None

def generate_qif_entry(row, target_currency):
    transaction_type = row['transaction']
    total = abs(float(row['amount']))
    currency = row['currency']

    if currency != target_currency:
        return None

    if transaction_type == 'BUY':
        symbol = extract_symbol(row['description'])
        unit = extract_unit(row['description'])
        price = total / unit
        return f'D{row["date"]}\nNBuy\nY{symbol}\nI{price}\nQ{unit}\nT{total}\nO0.00\nCc\n^'
    elif transaction_type == 'SELL':
        symbol = extract_symbol(row['description'])
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
        symbol = extract_symbol(row['description'])
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

    Args:
        account_data (dict): A dictionary where the keys are account names and the values are lists of strings.
    """

    config = read_config(config_filename)
    print(config)

    for account_name, transactions in account_data.items():
        if len(transactions) == 0:
            continue

        print(account_name)
        if account_name not in config:
            raise ValueError("Unknown account")

        if config[account_name]['type'] == "Checking":
            transactions.insert(0, '!Type:Bank');
        else:
            transactions.insert(0, '!Type:Invst');

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
