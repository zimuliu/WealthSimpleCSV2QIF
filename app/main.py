import os
import csv
import argparse

def read_csv_files(input_folder):
    csv_data = []
    for filename in os.listdir(input_folder):
        if filename.endswith('.csv'):
            file_path = os.path.join(input_folder, filename)
            with open(file_path, 'r') as csv_file:
                reader = csv.DictReader(csv_file)
                for row in reader:
                    csv_data.append(row)
    return csv_data

def main():
    parser = argparse.ArgumentParser(description='My Python CSV CLI App')
    parser.add_argument('--input-folder', type=str, required=True, help='Path to the input folder containing CSV files')
    args = parser.parse_args()

    csv_data = read_csv_files(args.input_folder)
    for row in csv_data:
        print(row)

if __name__ == "__main__":
    main()
