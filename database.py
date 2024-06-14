import sqlite3
import logging


# Function to initialize the database
def initialize_database(db_path):
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Create tables if they don't exist
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS receipts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT,
                fournisseur TEXT,
                localisation TEXT,
                categorie TEXT
            )
        ''')
        logging.info("Table 'receipts' initialized or already exists.")

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS articles (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                receipt_id INTEGER,
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


# Function to insert receipt data
def insert_receipt_data(db_path, receipt_data):
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        cursor.execute('''
            INSERT INTO receipts (date, fournisseur, localisation, categorie)
            VALUES (?, ?, ?, ?)
        ''', (
        receipt_data['date'], receipt_data['fournisseur'], receipt_data['localisation'], receipt_data['categorie']))

        receipt_id = cursor.lastrowid
        logging.info(
            f"Inserted receipt with ID {receipt_id}: Date: {receipt_data['date']}, Fournisseur: {receipt_data['fournisseur']}, Localisation: {receipt_data['localisation']}, Catégorie: {receipt_data['categorie']}")

        for article in receipt_data['articles']:
            cursor.execute('''
                INSERT INTO articles (receipt_id, nom, prix_unitaire, quantite, prix_total)
                VALUES (?, ?, ?, ?, ?)
            ''', (
                receipt_id,
                article['nom'],
                float(article['prix_unitaire']),
                float(article['quantite']),
                float(article['prix_total'])
            ))
            logging.info(
                f"Inserted article for receipt ID {receipt_id}: Nom: {article['nom']}, Prix unitaire: {article['prix_unitaire']}, Quantité: {article['quantite']}, Prix total: {article['prix_total']}")

        conn.commit()
        conn.close()
        logging.info("Data inserted successfully.")
    except Exception as e:
        logging.error(f"Error inserting data into database: {e}")
