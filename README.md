# WealthSimpleCSV2QIF

[![License: GPL v3](https://img.shields.io/badge/License-GPLv3-blue.svg)](LICENSE)
[![Python 3.6+](https://img.shields.io/badge/python-3.6+-blue.svg)](https://www.python.org/downloads/)
[![PyYAML](https://img.shields.io/badge/dependency-PyYAML-green.svg)](https://pyyaml.org/)
[![Tests](https://github.com/zimuliu/WealthSimpleCSV2QIF/workflows/Tests%20and%20Coverage/badge.svg)](https://github.com/zimuliu/WealthSimpleCSV2QIF/actions)
[![codecov](https://codecov.io/gh/zimuliu/WealthSimpleCSV2QIF/branch/main/graph/badge.svg)](https://codecov.io/gh/zimuliu/WealthSimpleCSV2QIF)
[![Coverage Status](https://coveralls.io/repos/github/zimuliu/WealthSimpleCSV2QIF/badge.svg?branch=main)](https://coveralls.io/github/zimuliu/WealthSimpleCSV2QIF?branch=main)

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
# Multi-currency account example (most common scenario)
# Single WealthSimple account with both USD and CAD transactions
AB1234567CAD-CAD:
  nickname: My-TFSA-CAD          # Output filename will be "My-TFSA-CAD.qif"
  type: Investment               # QIF account type: Investment or Checking
AB1234567CAD-USD:
  nickname: My-TFSA-USD          # Output filename will be "My-TFSA-USD.qif"
  type: Investment

# Cash account example (USD only - matches account currency)
CD9876543USD-USD:
  nickname: My-US-Saving         # Output filename will be "My-US-Saving.qif"
  type: Checking

# CAD cash account example
EF5555555CAD-CAD:
  nickname: My-Chequeing          # Output filename will be "My-Chequeing.qif"
  type: Checking

# Investment account example (processes both currencies)
GH7777777CAD-CAD:
  nickname: My-Trading-CAD        # Output filename will be "My-Trading-CAD.qif"
  type: Investment
GH7777777CAD-USD:
  nickname: My-Trading-USD        # Output filename will be "My-Trading-USD.qif"
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

Examples:
monthly-statement-transactions-AB1234567CAD-2025-07-01.csv → Account ID: AB1234567CAD
monthly-statement-transactions-CD9876543USD-2025-06-30.csv → Account ID: CD9876543USD
```

**Important Multi-Currency Note**: You need to configure each currency variant separately in your `accounts.yml`:

- Configure: `AB1234567CAD-CAD` and `AB1234567CAD-USD` (with currency suffixes)
- Output files: `My-TFSA-CAD.qif` and `My-TFSA-USD.qif` (using configured nicknames)

**Important for Checking Accounts:** Checking (cash) accounts only process transactions matching the account's currency suffix. For example:
- `CD9876543USD-USD` (Checking) → Only processes USD transactions → `My-US-Saving.qif`
- `EF5555555CAD-CAD` (Checking) → Only processes CAD transactions → `My-Chequeing.qif`
- Investment accounts can process both currencies if configured for both

This allows proper separation of currencies into different QIF files for accurate accounting.

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
- `monthly-statement-transactions-AB1234567CAD-2025-07-01.csv`
- `monthly-statement-transactions-CD9876543USD-2025-06-30.csv`
- `monthly-statement-transactions-EF5555555CAD-2025-08-15.csv`
- `monthly-statement-transactions-GH7777777CAD-2025-09-01.csv`

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
2025-07-18,CONT,"Contribution (executed at 2025-07-18)",1000.0,24775.50,USD
2025-07-19,BUYTOOPEN,"SPY 450.00 USD CALL 2025-07-25: Bought 2 contract (executed at 2025-07-19), Fee: $1.50",-320.50,24455.00,USD
2025-07-20,SELLTOCLOSE,"SPY 450.00 USD CALL 2025-07-25: Sold 2 contract (executed at 2025-07-20), Fee: $1.50",385.50,24840.50,USD
2025-07-21,BUY,SHOP - 15.0 shares,-825.00,24015.50,CAD
2025-07-22,EFT,"Electronic Transfer In",500.0,24515.50,CAD
```

## Output Format

### QIF File Structure

The tool generates QIF files in the `output/` directory with names based on your account configuration:

```
output/
├── My-TFSA.qif
├── My-US-Saving.qif
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
2025-07-23,BUYTOOPEN,"SPY 450.00 USD CALL 2025-07-25: Bought 2 contract (executed at 2025-07-23), Fee: $1.50",-320.50,8204.25,USD
2025-07-24,SELLTOCLOSE,"SPY 450.00 USD CALL 2025-07-25: Sold 2 contract (executed at 2025-07-24), Fee: $1.50",385.50,8589.75,USD
2025-07-25,BUYTOOPEN,"AAPL 180.00 USD PUT 2025-07-30: Bought 1 contract (executed at 2025-07-25), Fee: $0.75",-245.75,8344.00,USD
```

**Output QIF:**
```
!Type:Invst
D07/23/2025
NBuy
YSPY 450.00 USD CALL 2025-07-25
I159.50
Q2
T320.50
O1.50
Cc
^
D07/24/2025
NSell
YSPY 450.00 USD CALL 2025-07-25
I192.00
Q2
T385.50
O1.50
Cc
^
D07/25/2025
NBuy
YAAPL 180.00 USD PUT 2025-07-30
I245.00
Q1
T245.75
O0.75
Cc
^
```

### Example 3: Cash Account Transactions

**Input CSV:**
```csv
date,transaction,description,amount,balance,currency
2025-07-15,CONT,"Contribution (executed at 2025-07-15)",1000.0,15000.0,CAD
2025-07-16,EFT,"Electronic Transfer In",500.0,15500.0,CAD
2025-07-17,SPEND,"Coffee Shop Purchase",-4.50,15495.50,CAD
2025-07-18,INT,"Interest Payment",2.25,15497.75,CAD
2025-07-19,NRT,"US Non-Resident Tax Withholding",-15.00,15482.75,USD
```

**Output QIF (Checking Account):**
```
!Type:Bank
D07/15/2025
NXIn
T1000.0
O0.00
Cc
PContribution
MContribution (executed at 2025-07-15)
^
D07/16/2025
T500.0
O0.00
Cc
PElectronic Transfer In
^
D07/17/2025
T-4.50
O0.00
Cc
PCoffee Shop Purchase
^
D07/18/2025
T2.25
O0.00
Cc
PInterest Payment
^
D07/19/2025
NXOut
T15.00
O0.00
Cc
PUS Non-Resident Tax Withholding
MUS Non-Resident Tax Withholding
^
```

### Example 4: Multi-Currency Account (Complete Workflow)

This is the most common scenario: a single WealthSimple account containing both USD and CAD transactions.

**Input CSV (monthly-statement-transactions-AB1234567CAD-2025-07-01.csv):**
```csv
date,transaction,description,amount,balance,currency
2025-07-15,BUY,AAPL - 10.0 shares,-1500.00,23500.00,USD
2025-07-16,CONT,"Contribution (executed at 2025-07-16)",2000.0,25500.00,CAD
2025-07-17,BUY,SHOP - 15.0 shares,-825.00,24675.00,CAD
2025-07-18,DIV,AAPL - Dividend,25.50,23525.50,USD
2025-07-19,BUYTOOPEN,"SPY 450.00 USD CALL 2025-07-25: Bought 1 contract (executed at 2025-07-19), Fee: $0.75",-160.75,23364.75,USD
```

**accounts.yml Configuration:**
```yaml
AB1234567CAD-CAD:
  nickname: My-Investment-CAD
  type: Investment
AB1234567CAD-USD:
  nickname: My-Investment-USD
  type: Investment
```

**Generated Output Files:**

**My-Investment-USD.qif (USD transactions only):**
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
D07/18/2025
NDiv
YAAPL-CT
T25.50
O0.00
Cc
^
D07/19/2025
NBuy
YSPY 450.00 USD CALL 2025-07-25
I160.00
Q1
T160.75
O0.75
Cc
^
```

**My-Investment-CAD.qif (CAD transactions only):**
```
!Type:Invst
D07/16/2025
NXIn
T2000.0
O0.00
Cc
PContribution
MContribution (executed at 2025-07-16)
^
D07/17/2025
NBuy
YSHOP-CT
I55.00
Q15
T825.00
O0.00
Cc
^
```

**Key Multi-Currency Features:**
- **Automatic Separation**: One CSV file becomes two QIF files based on currency
- **Currency Suffix**: Tool adds `-USD` and `-CAD` to account IDs automatically
- **Independent Processing**: Each currency is processed separately for accurate accounting
- **Symbol Mapping**: CDR symbols get `-QH` suffix for CAD accounts, others get `-CT`

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
pip install -r requirements-dev.txt
```

## Testing

### Quick Start

```bash
# Activate virtual environment (required)
source .venv/bin/activate  # or source venv/bin/activate

# Install test dependencies
make install

# Run tests with coverage
make coverage

# Generate HTML coverage report
make coverage-html

# View coverage report in browser
make coverage-report
```

**Important**: Always activate your virtual environment before running tests to ensure the correct Python interpreter and dependencies are used.

### Test Commands

#### Using Make (Recommended)

```bash
# Run all tests
make test

# Run tests with verbose output
make test-verbose

# Run tests with coverage report
make coverage

# Generate HTML coverage report
make coverage-html

# Open coverage report in browser
make coverage-report

# Run all quality checks (tests, linting, formatting)
make all-checks

# Clean up generated files
make clean
```

#### Using pytest directly

```bash
# Run all tests
python -m pytest

# Run tests with coverage
python -m pytest --cov=app

# Run tests with HTML coverage report
python -m pytest --cov=app --cov-report=html

# Run specific test file
python -m pytest tests/test_main.py

# Run specific test method
python -m pytest tests/test_main.py::TestMain::test_extract_account_name_valid_format

# Run tests with verbose output
python -m pytest -v

# Run tests and stop on first failure
python -m pytest -x
```

#### Using unittest (Legacy)

```bash
# Run all tests
python -m unittest discover tests

# Run specific test
python -m unittest tests.test_main

# Run with verbose output
python -m unittest discover tests -v
```

### Test Coverage

The project uses `pytest-cov` for test coverage reporting. Coverage configuration is defined in `.coveragerc`.

#### Coverage Targets
- **Minimum Coverage**: 80% (configured in `pytest.ini`)
- **Source Code**: `app/` directory
- **Excluded**: Test files, setup files, virtual environments

#### Coverage Reports

**Terminal Report:**
```bash
make coverage
```

**HTML Report:**
```bash
make coverage-html
# Opens htmlcov/index.html
```

**XML Report (for CI/CD):**
```bash
python -m pytest --cov=app --cov-report=xml
# Generates coverage.xml
```

### Test Structure

```
tests/
├── __init__.py
└── test_main.py          # Comprehensive unit tests
```

#### Test Categories

The test suite includes:

- **Unit Tests**: Test individual functions and methods
- **Integration Tests**: Test component interactions
- **Edge Case Tests**: Test boundary conditions and error handling
- **Data Validation Tests**: Test CSV parsing and QIF generation

#### Key Test Areas

1. **CSV File Processing**
   - File name parsing
   - CSV content reading
   - Multi-currency handling

2. **Transaction Processing**
   - Stock transactions (BUY/SELL)
   - Options trading (BUYTOOPEN/SELLTOCLOSE)
   - Cash transactions (deposits, withdrawals)
   - Dividend payments

3. **QIF Generation**
   - Investment account format
   - Checking account format
   - Symbol mapping (CDR vs regular)
   - Currency separation

4. **Configuration Management**
   - YAML file parsing
   - Account mapping validation
   - Error handling

### Code Quality

#### Linting and Formatting

```bash
# Check code style
make lint

# Format code
make format

# Check formatting without changes
make check-format

# Run type checking (if mypy installed)
make type-check
```

#### Pre-commit Hooks

Install pre-commit hooks for automatic code quality checks:

```bash
# Install pre-commit
pip install pre-commit

# Install hooks
pre-commit install

# Run hooks manually
pre-commit run --all-files
```

### Continuous Integration

The project is configured for CI/CD with automated testing and coverage reporting on GitHub.

#### GitHub Actions Workflow

The project includes a comprehensive GitHub Actions workflow (`.github/workflows/test.yml`) that:

- **Multi-Python Testing**: Tests across Python 3.8, 3.9, 3.10, 3.11, and 3.12
- **Automated Linting**: Runs flake8 code quality checks
- **Coverage Reporting**: Generates and uploads coverage reports
- **Pull Request Comments**: Adds coverage comments to pull requests

#### Coverage Integration

The workflow automatically uploads coverage reports to multiple services:

1. **Codecov**: Provides detailed coverage analysis and trends
2. **Coveralls**: Alternative coverage reporting service
3. **GitHub Comments**: Adds coverage summaries to pull requests

#### Configuration Files

- `pytest.ini`: Test configuration and coverage settings
- `.coveragerc`: Coverage measurement configuration
- `requirements-dev.txt`: Development dependencies
- `Makefile`: Local automation commands
- `.github/workflows/test.yml`: GitHub Actions CI/CD pipeline

#### Setting Up Coverage Services

To enable coverage reporting on your fork:

1. **Codecov Setup**:
   - Visit [codecov.io](https://codecov.io) and sign in with GitHub
   - Add your repository to enable coverage reporting
   - No additional configuration needed (uses GitHub Actions integration)

2. **Coveralls Setup**:
   - Visit [coveralls.io](https://coveralls.io) and sign in with GitHub
   - Add your repository to enable coverage reporting
   - No additional configuration needed (uses GitHub token)

#### Viewing Coverage Reports

- **GitHub Actions**: View test results and coverage in the Actions tab
- **Codecov**: Detailed coverage reports at `https://codecov.io/gh/username/WealthSimpleCSV2QIF`
- **Coveralls**: Coverage trends at `https://coveralls.io/github/username/WealthSimpleCSV2QIF`
- **Pull Requests**: Automatic coverage comments on PRs showing changes

#### Local CI Testing

Test the CI pipeline locally:

```bash
# Run the same checks as CI
make all-checks

# Generate coverage report
make coverage-html

# View coverage report
make coverage-report
```

### Running Tests in Different Environments

#### Using tox (Multi-Python Testing)

```bash
# Install tox
pip install tox

# Run tests across multiple Python versions
tox

# Run tests for specific Python version
tox -e py39
```

#### Using Docker

```bash
# Build test image
docker build -t ws-csv-to-qif-test .

# Run tests in container
docker run --rm ws-csv-to-qif-test make test
```

### Troubleshooting Tests

#### Common Issues

**Import Errors:**
```bash
# Ensure app is in Python path
pip install -e .
```

**Coverage Not Working:**
```bash
# Reinstall coverage tools
pip install --upgrade pytest-cov coverage
```

**Tests Not Found:**
```bash
# Check test discovery
python -m pytest --collect-only
```

#### Debug Mode

```bash
# Run tests with debug output
python -m pytest -s -vv

# Run specific test with pdb
python -m pytest --pdb tests/test_main.py::TestMain::test_specific_function
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

This project is licensed under the GNU General Public License v3.0 - see the [LICENSE](LICENSE) file for details.

### GPL-3.0 License Summary

- ✅ Commercial use
- ✅ Modification
- ✅ Distribution
- ✅ Private use
- ✅ Patent use
- ❌ Liability
- ❌ Warranty
- ⚠️ **Copyleft**: Derivative works must also be licensed under GPL-3.0
- ⚠️ **Source code**: Must provide source code when distributing
- ⚠️ **License notice**: Must include license and copyright notice
- ⚠️ **State changes**: Must document significant changes made to the code

### Important GPL-3.0 Requirements

If you distribute this software or create derivative works:

1. **Include License**: You must include the GPL-3.0 license text
2. **Provide Source**: You must make the source code available
3. **Same License**: Derivative works must also be GPL-3.0 licensed
4. **Document Changes**: You must clearly mark any modifications you make

For more information about GPL-3.0, visit: https://www.gnu.org/licenses/gpl-3.0.html

---

**Made with ❤️ for the WealthSimple community**

*If this tool helps you manage your finances better, consider giving it a ⭐ on GitHub!*
