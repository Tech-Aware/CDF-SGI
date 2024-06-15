import customtkinter as ctk
from tkinter import filedialog
import os
import shutil
import logging
import receipt_reader
from database import initialize_database, insert_event
import sqlite3

# Configuration des logs pour affpipichage dans la console uniquement
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s - [%(filename)s:%(lineno)d] - %(funcName)s()',
    datefmt='%Y-%m-%d %H:%M:%S',
    handlers=[logging.StreamHandler()]
)

logger = logging.getLogger(__name__)

class TicketApp:
    def __init__(self, master):
        self.master = master
        self.master.title("Ticket Management System")

        self.db_path = './receipts.db'
        initialize_database(self.db_path)

        self.selected_event_id = None

        # Add Event Section
        self.event_name_label = ctk.CTkLabel(master, text="Event Name")
        self.event_name_label.pack(pady=5)
        self.event_name_entry = ctk.CTkEntry(master)
        self.event_name_entry.pack(pady=5)

        self.event_date_label = ctk.CTkLabel(master, text="Event Date")
        self.event_date_label.pack(pady=5)
        self.event_date_entry = ctk.CTkEntry(master)
        self.event_date_entry.pack(pady=5)

        self.add_event_button = ctk.CTkButton(master, text="Add Event", command=self.add_event)
        self.add_event_button.pack(pady=10)

        # Existing Events Section
        self.events_frame = ctk.CTkFrame(master)
        self.events_frame.pack(pady=10)
        self.load_events()

        # Upload Images Section
        self.upload_button = ctk.CTkButton(master, text="Upload Tickets", command=self.upload_tickets)
        self.upload_button.pack(pady=10)

        self.images_frame = ctk.CTkFrame(master)
        self.images_frame.pack(pady=10)

        self.process_tickets_button = ctk.CTkButton(master, text="Process Tickets", command=self.process_tickets)
        self.process_tickets_button.pack(pady=10)

        self.uploaded_images = []

    def add_event(self):
        try:
            event_name = self.event_name_entry.get()
            event_date = self.event_date_entry.get()
            insert_event(self.db_path, event_name, event_date)
            self.load_events()
        except Exception as e:
            logger.error(f"An error occurred while adding the event: {e}")
            raise

    def load_events(self):
        try:
            for widget in self.events_frame.winfo_children():
                widget.destroy()

            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("SELECT id, event_name, event_date FROM event")
            events = cursor.fetchall()
            conn.close()

            for event in events:
                event_button = ctk.CTkButton(self.events_frame, text=f"{event[1]} ({event[2]})",
                                             command=lambda e=event[0]: self.select_event(e))
                event_button.pack(pady=5)
        except sqlite3.Error as e:
            logger.error(f"Database error: {e}")
            raise
        except Exception as e:
            logger.error(f"An error occurred while loading events: {e}")
            raise

    def select_event(self, event_id):
        try:
            self.selected_event_id = event_id
            logger.info(f"Selected Event ID: {event_id}")
        except Exception as e:
            logger.error(f"An error occurred while selecting the event: {e}")
            raise

    def upload_tickets(self):
        try:
            image_paths = filedialog.askopenfilenames(filetypes=[("Image Files", "*.png;*.jpg;*.jpeg")])
            if not os.path.exists("./receipt_queue"):
                os.makedirs("./receipt_queue")

            for image_path in image_paths:
                try:
                    # shutil.copy(image_path, "./receipt_queue")
                    self.uploaded_images.append(image_path)
                    image_label = ctk.CTkLabel(self.images_frame, text=os.path.basename(image_path))
                    image_label.pack(pady=2)
                except PermissionError as e:
                    logger.error(f"Permission error: {e}")
                except Exception as e:
                    logger.error(f"An error occurred while uploading tickets: {e}")
                    raise
        except Exception as e:
            logger.error(f"An error occurred while selecting tickets to upload: {e}")
            raise

    def process_tickets(self):
        try:
            if self.selected_event_id is None:
                logger.warning("No event selected")
                return

            source_folder = "./receipt_queue"
            destination_folder = "./receipt_processed"
            db_path = "./receipts.db"
            api_key = receipt_reader.get_api_key()

            if not os.path.exists(destination_folder):
                os.makedirs(destination_folder)

            for image in self.uploaded_images:
                try:
                    # shutil.copy(image, source_folder)
                    # logger.info(f"Copied {image} to {source_folder}")
                    receipt_reader.process_image(image, destination_folder, api_key, db_path,
                                                 self.selected_event_id)
                except PermissionError as e:
                    logger.error(f"Permission error: {e}")
                except Exception as e:
                    logger.error(f"An error occurred while processing tickets: {e}")
                    raise

            self.uploaded_images = []
            for widget in self.images_frame.winfo_children():
                widget.destroy()
            logger.info("All tickets processed")
        except Exception as e:
            logger.error(f"An error occurred while processing tickets: {e}")
            raise


if __name__ == "__main__":
    try:
        root = ctk.CTk()
        app = TicketApp(root)
        root.mainloop()
    except Exception as e:
        logger.critical(f"An error occurred in the main application: {e}")
        raise
