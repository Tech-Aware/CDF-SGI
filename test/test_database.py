import unittest
from unittest.mock import patch, MagicMock, call
import sqlite3
import logging
from database import initialize_database, insert_receipt_data, insert_event


class TestDatabaseFunctions(unittest.TestCase):

    @patch('database.sqlite3.connect')
    def test_initialize_database(self, mock_connect):
        mock_conn = MagicMock()
        mock_connect.return_value = mock_conn
        mock_cursor = mock_conn.cursor.return_value

        initialize_database('test.db')

        mock_connect.assert_called_once_with('test.db')
        self.assertEqual(mock_cursor.execute.call_count, 3)
        mock_conn.commit.assert_called_once()
        mock_conn.close.assert_called_once()

    @patch('database.sqlite3.connect')
    def test_insert_event(self, mock_connect):
        mock_conn = MagicMock()
        mock_connect.return_value = mock_conn
        mock_cursor = mock_conn.cursor.return_value

        insert_event('test.db', 'Test Event', '2024-01-01')

        mock_connect.assert_called_once_with('test.db')
        mock_cursor.execute.assert_called_once_with('''
            INSERT INTO event (event_name, event_date)
            VALUES (?, ?)
        ''', ('Test Event', '2024-01-01'))
        mock_conn.commit.assert_called_once()
        mock_conn.close.assert_called_once()

    @patch('database.sqlite3.connect')
    def test_insert_receipt_data(self, mock_connect):
        mock_conn = MagicMock()
        mock_connect.return_value = mock_conn
        mock_cursor = mock_conn.cursor.return_value

        receipt_data = {
            'date': '2024-01-01',
            'fournisseur': 'Test Supplier',
            'localisation': 'Test Location',
            'articles': [
                {
                    'famille': 'Food',
                    'sous_famille': 'Fruit',
                    'nom': 'Apple',
                    'prix_unitaire': 0.5,
                    'quantite': 10,
                    'prix_total': 5.0
                },
                {
                    'famille': 'Drink',
                    'sous_famille': 'Juice',
                    'nom': 'Orange Juice',
                    'prix_unitaire': 1.5,
                    'quantite': 5,
                    'prix_total': 7.5
                }
            ]
        }

        mock_cursor.lastrowid = 1

        logging.info("Before insert_receipt_data")
        insert_receipt_data('test.db', receipt_data, 1)
        logging.info("After insert_receipt_data")

        for call in mock_cursor.execute.call_args_list:
            logging.info(f"Call made to execute: {call}")

        expected_receipt_call = call('''
            INSERT INTO receipts (event_id, date, fournisseur, localisation)
            VALUES (?, ?, ?, ?)
        ''', (1, '2024-01-01', 'Test Supplier', 'Test Location'))

        expected_article_calls = [
            call('''
                INSERT INTO articles (receipt_id, famille, sous_famille, nom, prix_unitaire, quantite, prix_total)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (1, 'Food', 'Fruit', 'Apple', 0.5, 10, 5.0)),
            call('''
                INSERT INTO articles (receipt_id, famille, sous_famille, nom, prix_unitaire, quantite, prix_total)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (1, 'Drink', 'Juice', 'Orange Juice', 1.5, 5, 7.5))
        ]

        mock_connect.assert_called_once_with('test.db')

        try:
            self.assertIn(expected_receipt_call, mock_cursor.execute.call_args_list)
        except AssertionError as e:
            logging.error(f"Receipt insertion assertion failed: {e}")
            raise

        try:
            for expected_call in expected_article_calls:
                self.assertIn(expected_call, mock_cursor.execute.call_args_list)
        except AssertionError as e:
            logging.error(f"Article insertion assertion failed: {e}")
            raise

        mock_conn.commit.assert_called_once()
        mock_conn.close.assert_called_once()


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    unittest.main()
