import sqlite3
import logging

def initialize_database(db_path):
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS event (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                event_name TEXT,
                event_date TEXT
            )
        ''')
        logging.info("Table 'event' initialized or already exists.")

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS receipts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                event_id INTEGER,
                date TEXT,
                fournisseur TEXT,
                localisation TEXT,
                FOREIGN KEY (event_id) REFERENCES event(id)
            )
        ''')
        logging.info("Table 'receipts' initialized or already exists.")

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS articles (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                receipt_id INTEGER,
                famille TEXT,
                sous_famille TEXT,
                nom TEXT,
                prix_unitaire REAL,
                quantite REAL,
                prix_total REAL,
                FOREIGN KEY (receipt_id) REFERENCES receipts (id)
            )
        ''')
        logging.info("Table 'articles' initialized or already exists.")

        conn.commit()
        conn.close()
        logging.info("Database initialized successfully.")
    except Exception as e:
        logging.error(f"Error initializing database: {e}")

def insert_receipt_data(db_path, receipt_data, event_id):
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        cursor.execute('''
            INSERT INTO receipts (event_id, date, fournisseur, localisation)
            VALUES (?, ?, ?, ?)
        ''', (
        event_id, receipt_data['date'], receipt_data['fournisseur'], receipt_data['localisation']))

        receipt_id = cursor.lastrowid
        logging.info(
            f"Inserted receipt with ID {receipt_id}: Date: {receipt_data['date']}, Fournisseur: {receipt_data['fournisseur']}, Localisation: {receipt_data['localisation']}")

        for article in receipt_data['articles']:
            cursor.execute('''
                INSERT INTO articles (receipt_id, famille, sous_famille, nom, prix_unitaire, quantite, prix_total)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                receipt_id,
                article['famille'],
                article['sous_famille'],
                article['nom'],
                float(article['prix_unitaire']),
                float(article['quantite']),
                float(article['prix_total'])
            ))
            logging.info(
                f"Inserted article for receipt ID {receipt_id}: Famille: {article['famille']}, Sous famille: {article['sous_famille']}, Nom: {article['nom']}, Prix unitaire: {article['prix_unitaire']}, Quantité: {article['quantite']}, Prix total: {article['prix_total']}")
        conn.commit()
        conn.close()
        logging.info("Data inserted successfully.")
    except Exception as e:
        logging.error(f"Error inserting data into database: {e}")

def insert_event(db_path, event_name, event_date):
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO event (event_name, event_date)
            VALUES (?, ?)
        ''', (event_name, event_date))
        conn.commit()
        conn.close()
        logging.info(f"Event '{event_name}' added successfully.")
    except Exception as e:
        logging.error(f"Error inserting event into database: {e}")
