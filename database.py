import sqlite3
import logging

class EventExistsError(Exception):
    pass

class EventDateMismatchError(Exception):
    pass

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
    except Exception as e:
        logging.error(f"Error initializing database: {e}")
    finally:
        conn.close()

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
    except Exception as e:
        logging.error(f"Error inserting data into database: {e}")
    finally:
        conn.close()

def insert_event(db_path, event_name, event_date):
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Check if an event with the same or similar name already exists
        cursor.execute('''
            SELECT event_name, event_date FROM event WHERE event_name LIKE ?
        ''', (f'%{event_name}%',))
        existing_events = cursor.fetchall()

        if existing_events:
            for existing_event in existing_events:
                if existing_event[1] != event_date:
                    logging.warning(f"Event with a similar name but different date already exists: {existing_event}")
                    raise EventDateMismatchError(f"L'évènement existe déjà avec une date différente:\n {existing_event}")
            logging.error(f"Event with a similar name already exists: {existing_events}")
            raise EventExistsError(f"L'évènement existe déjà:\n {existing_events}")

        cursor.execute('''
            INSERT INTO event (event_name, event_date)
            VALUES (?, ?)
        ''', (event_name, event_date))

        conn.commit()
        logging.info(f"Event '{event_name}' added successfully.")
        return f"Event '{event_name}' added successfully."
    except EventExistsError as e:
        raise e
    except EventDateMismatchError as e:
        raise e
    except Exception as e:
        logging.error(f"Error inserting event into database: {e}")
        return f"Error inserting event into database: {e}"
    finally:
        if conn:
            conn.close()

def insert_event_with_iteration(db_path, event_name, event_date):
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Count existing events with the same name or similar
        cursor.execute('''
            SELECT COUNT(*) FROM event WHERE event_name LIKE ?
        ''', (f'%{event_name}%',))
        count = cursor.fetchone()[0]

        new_event_name = f"{event_name} ({count + 1})"

        cursor.execute('''
            INSERT INTO event (event_name, event_date)
            VALUES (?, ?)
        ''', (new_event_name, event_date))

        conn.commit()
        logging.info(f"Event '{new_event_name}' added successfully.")
        return f"Event '{new_event_name}' added successfully."
    except Exception as e:
        logging.error(f"Error inserting event with iteration into database: {e}")
        return f"Error inserting event with iteration into database: {e}"
    finally:
        if conn:
            conn.close()
