# WealthSimpleCSV2QIF

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python 3.6+](https://img.shields.io/badge/python-3.6+-blue.svg)](https://www.python.org/downloads/)
[![PyYAML](https://img.shields.io/badge/dependency-PyYAML-green.svg)](https://pyyaml.org/)

Convert WealthSimple Trade/Cash CSV exports to QIF format for seamless import into financial software like Quicken, GnuCash, or other accounting applications.

## Table of Contents

- [Why Use This Tool?](#why-use-this-tool)
- [Quick Start](#quick-start)
- [Features](#features)
- [Installation](#installation)
- [Configuration](#configuration)
- [Usage](#usage)
- [Input Format](#input-format)
- [Output Format](#output-format)
- [Supported Transactions](#supported-transactions)
- [Examples](#examples)
- [Technical Details](#technical-details)
- [FAQ](#faq)
- [Troubleshooting](#troubleshooting)
- [Development](#development)
- [Contributing](#contributing)
- [License](#license)

## Why Use This Tool?

WealthSimple provides CSV exports, but most accounting software requires QIF format. This tool bridges that gap with:

- **Intelligent Parsing**: Handles complex options trading descriptions and extracts fees automatically
- **Multi-Currency Support**: Separates USD and CAD transactions for proper accounting
- **Account Flexibility**: Maps WealthSimple account IDs to your preferred naming scheme
- **QIF Compliance**: Generates properly formatted QIF files that import cleanly into financial software

## Quick Start

```bash
# 1. Clone and install
git clone https://github.com/zimuliu/WealthSimpleCSV2QIF.git
cd WealthSimpleCSV2QIF
pip install .

# 2. Configure accounts
cp accounts-sample.yml accounts.yml
# Edit accounts.yml with your account details

# 3. Convert files
ws-csv-to-qif
```

## Features

### Core Functionality
- **Multi-Currency Support**: Handles both USD and CAD transactions separately
- **Comprehensive Transaction Types**: Supports stocks, options, dividends, contributions, transfers, and more
- **Options Trading**: Advanced parsing of complex options transactions including fees and contract details
- **Account Configuration**: Flexible YAML-based account mapping system
- **QIF Format Compliance**: Generates properly formatted QIF files for different account types

### Advanced Features
- **Automatic Fee Extraction**: Separates trading fees from transaction amounts for accurate accounting
- **Currency Separation**: Creates separate account entries for multi-currency accounts
- **CDR Symbol Mapping**: Handles Canadian Depositary Receipts with proper symbol conversion
- **Flexible File Organization**: Configurable input/output directories
- **Error Handling**: Comprehensive validation and error reporting

## Installation

### Prerequisites
- Python 3.6 or higher
- pip (Python package installer)

### Method 1: Standard Installation (Recommended)

```bash
# Clone the repository
git clone https://github.com/zimuliu/WealthSimpleCSV2QIF.git
cd WealthSimpleCSV2QIF

# Create and activate virtual environment (recommended)
python -m venv venv

# Activate virtual environment
# On Windows:
venv\Scripts\activate
# On macOS/Linux:
source venv/bin/activate

# Install the application
pip install .
```

### Method 2: Development Installation

```bash
# For development with editable installation
pip install -e .

# Install development dependencies
pip install -r requirements.txt
```

### Method 3: Direct from Git

```bash
pip install git+https://github.com/zimuliu/WealthSimpleCSV2QIF.git
```

### Verification

Test your installation:
```bash
ws-csv-to-qif --help
```

## Configuration

### Account Configuration File

Create an `accounts.yml` file that maps WealthSimple account IDs to friendly names and account types:

```bash
cp accounts-sample.yml accounts.yml
```

### Configuration Format

```yaml
# WealthSimple Account ID (from CSV filename)
H12345678CAD:
  nickname: My-TFSA           # Output filename will be "My-TFSA.qif"
  type: Investment            # QIF account type: Investment or Checking

WK1234567CAD:
  nickname: My-Cash-Account
  type: Checking

# USD account example
H12345678USD:
  nickname: My-USD-Trading
  type: Investment
```

### Configuration Parameters

| Parameter | Description | Valid Values |
|-----------|-------------|--------------|
| `nickname` | Friendly name for output QIF file | Any string (avoid special characters) |
| `type` | QIF account type | `Investment` or `Checking` |

### Finding Your Account IDs

Account IDs are found in your WealthSimple CSV filenames:
```
monthly-statement-transactions-[ACCOUNT_ID]-[DATE].csv
                               ^^^^^^^^^^^^
                               This is your Account ID
```

## Usage

### Basic Usage

1. **Prepare your files**: Place WealthSimple CSV files in the `input/` directory
2. **Configure accounts**: Ensure `accounts.yml` contains all your account mappings
3. **Run conversion**:
   ```bash
   ws-csv-to-qif
   ```
4. **Find output**: QIF files will be created in the `output/` directory

### Advanced Usage

#### Custom Directories
```bash
ws-csv-to-qif --input-folder /path/to/csv/files --account-config /path/to/accounts.yml
```

#### Processing Specific Files
```bash
# Process files from a specific month
ws-csv-to-qif --input-folder ~/Downloads/WealthSimple/2024-01/
```

### Command Line Options

| Option | Description | Default |
|--------|-------------|---------|
| `--input-folder` | Path to folder containing CSV files | `input` |
| `--account-config` | Path to account configuration YAML file | `accounts.yml` |
| `--help` | Show help message and exit | - |

## Input Format

### Expected CSV File Naming
```
monthly-statement-transactions-{ACCOUNT_ID}-{YYYY-MM-DD}.csv
```

**Examples:**
- `monthly-statement-transactions-HQ8ABC123CAD-2025-07-01.csv`
- `monthly-statement-transactions-WK9876543USD-2025-06-30.csv`

### Required CSV Columns

| Column | Description | Example |
|--------|-------------|---------|
| `date` | Transaction date | `2025-07-15` |
| `transaction` | Transaction type | `BUY`, `SELL`, `DIV` |
| `description` | Transaction description | `AAPL - 10.0 shares` |
| `amount` | Transaction amount | `1500.00` |
| `balance` | Account balance after transaction | `25000.00` |
| `currency` | Transaction currency | `USD`, `CAD` |

### Sample CSV Content
```csv
date,transaction,description,amount,balance,currency
2025-07-15,BUY,AAPL - 10.0 shares,-1500.00,23500.00,USD
2025-07-16,DIV,AAPL - Dividend,25.50,23525.50,USD
2025-07-17,SELL,AAPL - 5.0 shares,750.00,24275.50,USD
```

## Output Format

### QIF File Structure

The tool generates QIF files in the `output/` directory with names based on your account configuration:

```
output/
├── My-TFSA.qif
├── My-Cash-Account.qif
└── My-USD-Trading.qif
```

### QIF Content Example

**Investment Account (type: Investment):**
```
!Type:Invst
D07/15/2025
NBuy
YAAPL-CT
I150.00
Q10
T1500.00
O0.00
Cc
^
```

**Cash Account (type: Checking):**
```
!Type:Bank
D07/16/2025
T25.50
O0.00
Cc
PAAPL - Dividend
^
```

## Supported Transactions

### Investment Transactions

| WealthSimple Type | Description | QIF Mapping |
|-------------------|-------------|-------------|
| `BUY` | Stock purchase | Buy transaction with symbol, price, quantity |
| `SELL` | Stock sale | Sell transaction with symbol, price, quantity |
| `BUYTOOPEN` | Options purchase | Buy with option symbol, contracts, fees |
| `SELLTOCLOSE` | Options sale | Sell with option symbol, contracts, fees |
| `DIV` | Dividend payment | Dividend income |

### Cash Transactions

| WealthSimple Type | Description | QIF Mapping |
|-------------------|-------------|-------------|
| `CONT` | Account contribution | Transfer in (XIn) |
| `FPLINT` | Stock lending interest | Interest income (XIn) |
| `INT` | Interest payment | Interest income |
| `NRT` | US tax withholding | Tax withholding (XOut) |
| `TRFIN/TRFOUT` | Transfers | Transfer in/out |
| `EFT/EFTOUT` | Electronic transfers | Transfer in/out |
| `CASHBACK` | Cashback rewards | Income |
| `REFUND` | Refunds | Income |
| `SPEND` | Spending transactions | Expense |

### Ignored Transactions

These transaction types are ignored (not converted):
- `RECALL` - Stock recalls
- `LOAN` - Margin loans
- `STKDIS` - Stock distributions
- `STKREORG` - Stock reorganizations

## Examples

### Example 1: Basic Stock Trading

**Input CSV:**
```csv
date,transaction,description,amount,balance,currency
2025-07-15,BUY,TSLA - 5.0 shares,-850.00,9150.00,USD
2025-07-20,SELL,TSLA - 5.0 shares,900.00,10050.00,USD
```

**Output QIF:**
```
!Type:Invst
D07/15/2025
NBuy
YTSLA-QH
I170.00
Q5
T850.00
O0.00
Cc
^
D07/20/2025
NSell
YTSLA-QH
I180.00
Q5
T900.00
O0.00
Cc
^
```

### Example 2: Options Trading

**Input CSV:**
```csv
date,transaction,description,amount,balance,currency
2025-07-15,BUYTOOPEN,"SPY 631.00 USD PUT 2025-07-23: Bought 3 contract (executed at 2025-07-23), Fee: $2.25",-945.75,8204.25,USD
```

**Output QIF:**
```
!Type:Invst
D07/15/2025
NBuy
YSPY 631.00 USD PUT 2025-07-23
I314.50
Q3
T945.75
O2.25
Cc
^
```

### Example 3: Multi-Currency Account

For account `HQ8KJW805CAD` with both USD and CAD transactions, the tool creates separate entries:
- `HQ8KJW805CAD-USD` for USD transactions
- `HQ8KJW805CAD-CAD` for CAD transactions

## Technical Details

### Currency Handling

The application processes each account's transactions separately by currency:

1. **Account Separation**: Each WealthSimple account is split into currency-specific sub-accounts
2. **Currency Filtering**: Only transactions matching the target currency are included in each QIF file
3. **Symbol Mapping**: CDR symbols are automatically converted (e.g., `TSLA` → `TSLA-QH`)

### Symbol Processing

#### CDR (Canadian Depositary Receipt) Mapping
- **CDR Symbols**: `TSLA`, `DIS`, `NVDA`, `AAPL` → Suffix `-QH`
- **Other Symbols**: All others → Suffix `-CT`

#### Options Symbol Extraction
Options descriptions are parsed to extract:
- Underlying symbol
- Strike price
- Option type (PUT/CALL)
- Expiration date
- Number of contracts
- Trading fees

### QIF Format Specifications

The tool generates QIF files compliant with the Quicken Interchange Format:

#### Investment Account Fields
- `D` - Date
- `N` - Action (Buy, Sell, Div, etc.)
- `Y` - Security symbol
- `I` - Price per share
- `Q` - Quantity
- `T` - Total amount
- `O` - Commission/fees
- `C` - Cleared status
- `^` - End of entry

#### Bank Account Fields
- `D` - Date
- `T` - Amount
- `P` - Payee/description
- `M` - Memo
- `C` - Cleared status
- `^` - End of entry

## FAQ

### General Questions

**Q: What versions of Python are supported?**
A: Python 3.6 and higher are supported.

**Q: Can I process multiple months of data at once?**
A: Yes, place all CSV files in the input directory and run the tool once.

**Q: Does the tool modify my original CSV files?**
A: No, the tool only reads CSV files and creates new QIF files.

### Configuration Questions

**Q: How do I find my WealthSimple account ID?**
A: The account ID is in your CSV filename: `monthly-statement-transactions-[ACCOUNT_ID]-[DATE].csv`

**Q: Can I use the same nickname for multiple accounts?**
A: No, each account should have a unique nickname to avoid overwriting QIF files.

**Q: What's the difference between Investment and Checking account types?**
A: Investment accounts use QIF investment format with stock symbols and quantities. Checking accounts use bank format for cash transactions.

### Usage Questions

**Q: Why are my QIF files empty?**
A: Check that your account configuration matches the account IDs in your CSV filenames, and ensure transactions exist for the specified currency.

**Q: Can I process files from different directories?**
A: Yes, use the `--input-folder` option to specify a different directory.

**Q: How do I handle accounts with both USD and CAD transactions?**
A: The tool automatically creates separate QIF entries for each currency. Configure both currency variants in your accounts.yml file.

## Troubleshooting

### Common Errors

#### "Unknown account" Error
```
ValueError: Unknown account
```

**Cause**: Account ID in CSV filename not found in `accounts.yml`

**Solution**:
1. Check the account ID in your CSV filename
2. Add the missing account to `accounts.yml`
3. Ensure the account ID matches exactly (including currency suffix)

#### Empty QIF Files

**Possible Causes**:
1. No transactions for the specified currency
2. Account configuration mismatch
3. Malformed CSV files

**Solutions**:
1. Verify transactions exist in your CSV for both USD and CAD
2. Check account ID mapping in `accounts.yml`
3. Validate CSV file format and required columns

#### Options Parsing Issues

**Cause**: Non-standard options description format

**Solution**: Ensure options descriptions follow WealthSimple's format:
```
"SYMBOL STRIKE CURRENCY TYPE EXPIRY: Action X contract (executed at DATE), Fee: $X.XX"
```

#### Installation Issues

**Python not found**:
```bash
# Install Python 3.6+ from python.org
# Or use package manager:
# macOS: brew install python
# Ubuntu: sudo apt install python3 python3-pip
```

**Permission errors**:
```bash
# Use virtual environment (recommended)
python -m venv venv
source venv/bin/activate  # or venv\Scripts\activate on Windows
pip install .
```

### Debug Mode

For detailed error information, you can modify the main.py to add debug output:

```python
# Add this to see detailed processing information
import logging
logging.basicConfig(level=logging.DEBUG)
```

### Getting Help

If you encounter issues not covered here:

1. Check the [Issues](https://github.com/zimuliu/WealthSimpleCSV2QIF/issues) page
2. Create a new issue with:
   - Error message
   - Sample CSV data (anonymized)
   - Your accounts.yml configuration (anonymized)
   - Python version and operating system

## Development

### Setting Up Development Environment

```bash
# Clone repository
git clone https://github.com/zimuliu/WealthSimpleCSV2QIF.git
cd WealthSimpleCSV2QIF

# Create virtual environment
python -m venv venv
source venv/bin/activate  # or venv\Scripts\activate on Windows

# Install in development mode
pip install -e .

# Install development dependencies
pip install -r requirements.txt
```

### Running Tests

```bash
# Run all tests
python -m unittest discover tests

# Run specific test
python -m unittest tests.test_main

# Run with verbose output
python -m unittest discover tests -v
```

### Code Structure

```
WealthSimpleCSV2QIF/
├── app/
│   ├── __init__.py
│   └── main.py              # Core application logic
├── tests/
│   ├── __init__.py
│   └── test_main.py         # Unit tests
├── input/                   # Default input directory
├── output/                  # Default output directory
├── accounts-sample.yml      # Sample configuration
├── requirements.txt         # Dependencies
├── setup.py                # Package configuration
└── README.md               # This file
```

### Adding New Transaction Types

To add support for new WealthSimple transaction types:

1. Add the transaction type to `generate_qif_entry()` function
2. Implement the QIF formatting logic
3. Add test cases in `tests/test_main.py`
4. Update documentation

### Code Style

- Follow PEP 8 style guidelines
- Use descriptive variable names
- Add docstrings to all functions
- Include type hints where appropriate

## Contributing

We welcome contributions! Here's how to get started:

### Quick Contribution Guide

1. **Fork** the repository
2. **Create** a feature branch: `git checkout -b feature-name`
3. **Make** your changes
4. **Add** tests for new functionality
5. **Run** tests: `python -m unittest discover tests`
6. **Commit** changes: `git commit -am 'Add feature'`
7. **Push** to branch: `git push origin feature-name`
8. **Submit** a pull request

### Contribution Areas

- **New Transaction Types**: Add support for additional WealthSimple transaction types
- **Output Formats**: Support for other financial formats (OFX, CSV, etc.)
- **Error Handling**: Improve validation and error messages
- **Documentation**: Improve examples, add tutorials
- **Testing**: Increase test coverage, add integration tests
- **Performance**: Optimize processing for large files

### Code Review Process

1. All contributions require code review
2. Tests must pass
3. Documentation must be updated for new features
4. Follow existing code style and conventions

### Reporting Issues

When reporting bugs, please include:

- **Description**: Clear description of the issue
- **Steps to Reproduce**: Exact steps to reproduce the problem
- **Expected Behavior**: What you expected to happen
- **Actual Behavior**: What actually happened
- **Environment**: Python version, OS, etc.
- **Sample Data**: Anonymized CSV data if relevant

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

### MIT License Summary

- ✅ Commercial use
- ✅ Modification
- ✅ Distribution
- ✅ Private use
- ❌ Liability
- ❌ Warranty

---

**Made with ❤️ for the WealthSimple community**

*If this tool helps you manage your finances better, consider giving it a ⭐ on GitHub!*
