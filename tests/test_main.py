import unittest
from unittest.mock import patch, mock_open
from app.main import read_csv_files

class TestMain(unittest.TestCase):
    @patch('os.listdir')
    @patch('builtins.open', new_callable=mock_open, read_data='Timestamp,Sensor1,Sensor2,Sensor3\n1,2.3,4.5,6.7\n')
    def test_read_csv_files(self, mock_open_file, mock_listdir):
        mock_listdir.return_value = ['file1.csv', 'file2.csv']
        csv_data = read_csv_files('input_folder')
        self.assertEqual(len(csv_data), 1)
        self.assertDictEqual(csv_data[0], {'Timestamp': '1', 'Sensor1': '2.3', 'Sensor2': '4.5', 'Sensor3': '6.7'})

if __name__ == '__main__':
    unittest.main()
