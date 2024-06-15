import customtkinter as ctk
from tkinter import filedialog, messagebox, simpledialog
import os
import shutil
import logging
import receipt_reader
from database import initialize_database, insert_event, insert_event_with_iteration, EventExistsError, EventDateMismatchError
import sqlite3

# Configuration des logs pour affichage dans la console uniquement
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
        self.master.configure(bg="#ebebeb")

        self.center_window(800, 750)  # Augmenter la hauteur de la fenêtre

        self.db_path = './receipts.db'
        initialize_database(self.db_path)

        self.selected_event_id = None

        self.main_frame = ctk.CTkFrame(master)
        self.main_frame.pack(fill="both", expand=True, padx=10, pady=10)

        self.create_ui()

    def center_window(self, width, height):
        screen_width = self.master.winfo_screenwidth()
        screen_height = self.master.winfo_screenheight()
        x = (screen_width - width) // 2
        y = (screen_height - height) // 2
        self.master.geometry(f'{width}x{height}+{x}+{y}')

    def create_ui(self):
        # Create a frame for the left and right sections
        self.top_frame = ctk.CTkFrame(self.main_frame, fg_color="#ebebeb")
        self.top_frame.pack(fill="x", padx=10, pady=10)

        # Left Frame - Add Event Section
        self.left_frame = ctk.CTkFrame(self.top_frame, fg_color="#ebebeb")
        self.left_frame.pack(side="left", fill="both", expand=True, padx=10)

        self.add_section_header(self.left_frame, "AJOUTER EVENEMENT")

        self.event_name_label = ctk.CTkLabel(self.left_frame, text="Nom de l'évènement:", fg_color="#ebebeb")
        self.event_name_label.pack(pady=5)
        self.event_name_entry = ctk.CTkEntry(self.left_frame)
        self.event_name_entry.pack(pady=5)

        self.event_date_label = ctk.CTkLabel(self.left_frame, text="Date prévue:", fg_color="#ebebeb")
        self.event_date_label.pack(pady=5)
        self.event_date_entry = ctk.CTkEntry(self.left_frame)
        self.event_date_entry.pack(pady=5)

        self.add_event_button = ctk.CTkButton(self.left_frame, text="Ajouter l'évènement", command=self.add_event)
        self.add_event_button.pack(pady=10)

        # Right Frame - Select Event Section
        self.right_frame = ctk.CTkFrame(self.top_frame, fg_color="#ebebeb")
        self.right_frame.pack(side="right", fill="both", expand=True, padx=10)

        self.add_section_header(self.right_frame, "SELECTIONNER EVENEMENT")

        self.events_frame = ctk.CTkScrollableFrame(self.right_frame, fg_color="#ebebeb", height=200)
        self.events_frame.pack(pady=10, fill="both", expand=True)
        self.load_events()

        # Bottom Frame - Upload and Process Tickets Section
        self.bottom_frame = ctk.CTkFrame(self.main_frame, fg_color="#ebebeb")
        self.bottom_frame.pack(fill="both", expand=True, pady=10)

        self.add_section_header(self.bottom_frame, "TELECHARGER DES TICKETS")

        self.upload_button = ctk.CTkButton(self.bottom_frame, text="Télécharger les tickets", command=self.upload_tickets)
        self.upload_button.pack(pady=10)

        self.images_frame = ctk.CTkScrollableFrame(self.bottom_frame, fg_color="white", height=200)
        self.images_frame.pack(pady=10, fill="both")

        self.process_tickets_button = ctk.CTkButton(self.bottom_frame, text="Traiter les tickets", command=self.process_tickets)
        self.process_tickets_button.pack(pady=10)

        self.uploaded_images = []

    def add_section_header(self, parent, title):
        frame = ctk.CTkFrame(parent, fg_color="black")
        frame.pack(pady=10, fill='x')

        label = ctk.CTkLabel(frame, text=title, font=("Arial", 14, 'bold'), text_color='white', fg_color="black")
        label.pack(pady=5, padx=5, fill='x', expand=True)

    def show_info(self, info_text):
        messagebox.showinfo("Informations", info_text)

    def add_event(self):
        try:
            event_name = self.event_name_entry.get()
            event_date = self.event_date_entry.get()
            message = insert_event(self.db_path, event_name, event_date)
            self.load_events()
            self.show_info(message)
        except EventExistsError as e:
            logger.error(f"EventExistsError: {e}")
            messagebox.showerror("Erreur", str(e))
        except EventDateMismatchError as e:
            logger.error(f"EventDateMismatchError: {e}")
            result = messagebox.askyesno("Avertissement", f"{str(e)}\nVoulez-vous ajouter un nouvel évènement avec une nouvelle date?")
            if result:
                message = insert_event_with_iteration(self.db_path, event_name, event_date)
                self.load_events()
                self.show_info(message)
        except Exception as e:
            logger.error(f"An error occurred while adding the event: {e}")
            messagebox.showerror("Erreur", f"An unexpected error occurred: {e}")

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
                    self.uploaded_images.append(image_path)
                    image_label = ctk.CTkLabel(self.images_frame, text=os.path.basename(image_path), fg_color="#ebebeb")
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
                messagebox.showwarning("Warning", f"Vous devez séléctionner un évènement dans la section\n SELECTIONNER EVENEMENT")
                return

            source_folder = "./receipt_queue"
            destination_folder = "./receipt_processed"
            db_path = "./receipts.db"
            api_key = receipt_reader.get_api_key()

            if not os.path.exists(destination_folder):
                os.makedirs(destination_folder)

            for image in self.uploaded_images:
                try:
                    receipt_reader.process_image(image, destination_folder, api_key, db_path, self.selected_event_id)
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
