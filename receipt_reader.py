import base64
import requests
import os
import shutil
import time
import logging

import ui
from database import initialize_database, insert_receipt_data  # Importing the database functions
from datetime import datetime

# Configuration des logs pour affichage dans la console uniquement
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levellevelname)s - %(message)s - [%(filename)s:%(lineno)d] - %(funcName)s()',
    datefmt='%Y-%m-%d %H:%M:%S',
    handlers=[logging.StreamHandler()]
)

logger = logging.getLogger(__name__)


# Function to get the OpenAI API Key
def get_api_key():
    try:
        api_key = os.getenv('OPENAI_API_KEY')
        if not api_key:
            raise ValueError("OpenAI API Key not found. Please set the 'OPENAI_API_KEY' environment variable.")
        return api_key
    except Exception as e:
        logger.error(f"Error getting API Key: {e}")
        raise


# Function to encode the image
def encode_image(image_path):
    try:
        with open(image_path, "rb") as image_file:
            return base64.b64encode(image_file.read()).decode('utf-8')
    except FileNotFoundError:
        logger.error(f"Image file not found: {image_path}")
        raise
    except Exception as e:
        logger.error(f"Error encoding image: {e}")
        raise

articles_list = [
    "Alimentation",
    "Boissons",
    "Transports",
    "Services",
]
sub_articles_list = [
    "Snacking",
    "Alcoolisées",
    "Non Alcoolisées",
    "Crèmerie",
    "Charcuterie",
    "Viande",
    "Boulangerie",
    "Surgelés",
    "Vêtements et Accessoires",
    "Électronique et Informatique",
    "Maison et Jardin",
    "Loisirs et Divertissements",
    "Hygiène et Santé"
]

# Function to create the payload
def create_payload(base64_image):
    try:
        prompt = (
            "Veuillez analyser l'image du reçu joint. Lire méticuleusement le tickets joints et fournir les informations au format suivant :\n"
            "date, fournisseur, localisation (seulement la ville)\n"
            "famille, sous_famille, article, prix unitaire, quantité, prix total\n"
            "famille, sous_famille, article, prix unitaire, quantité, prix total\n"
            "famille, sous_famille, article, prix unitaire, quantité, prix total\n"
            "famille, sous_famille, article, prix unitaire, quantité, prix total\n"
            "famille, sous_famille, article, prix unitaire, quantité, prix total\n"
            "..., ..., ..., ..., ..., ...\n"
            "INSTRUCTION IMPORTANTE:\n"
            "Veille à fournir les informations demandées et seulement ces informations\n"
            "Pour les famille et les sous famille priorise avant tous les listes suivantes:\n"
            "Pour les famille d'article, utilise les informations ci-dessous:\n"
            "L'article, ses quantité, son prix unitaire et total se trouve strictement sur la même ligne"
            "Ne pas arrondir, ni les quantité, ni les montants"
            "SI la colonne du prix unitaire est HT, ALORS calculer le prix TTC en ajoutant le pourcentage de TVA indiqué"
            "SI la ligne se nomme total, ALORS ne pas la prendre en compte"
            "SI les quantité correspondent à la ligne 'Total' ALORS ne pas tenir compte de cette quantité"
            f"{articles_list}\n"
            f"Et pour les sous-famille les informations ci-dessous:\n"
            f"{sub_articles_list}"
            f"SI L'IMAGE n'est pas un ticket de caisse ou une facture répondre 'NO RECEIPT PROVIDED'\n"
            f"SI c'est du Gaz, de l'essence, de l'électricité, du bois, ou tout autre carburant, ALORS la famille est Energie\n"
            "SI c'est quelque chose qui se mange ou qui se boit pour un être vivant, ALORS la famille est Alimentation\n"
            "SI ce n'est pas quelque chose qui se mange, ALORS c'est soit une Fourniture, soit de la logistique\n"
            "Fait des recherches sur le web pour t'assurer que tu as bien définit les familles et sous familles\n"
            "EXEMPLE DE SORTIE ATTENDUE N°1:\n"
            "31/08/2023, Intermarché, Foix\n"
            "ALIMENTATION\n"
            "Alimentation, snacking, Vico Chips Class.Nat, 3.56, 1, 3.56\n"
            "Alimentation, crèmerie, Pat. Emmental Rape 3, 3.01, 1, 3.01\n"
            "Alimentation, crèmerie, Pat Beurre Moule DX, 4.63, 1, 4.63"
            "EXEMPLE DE SORTIE ATTENDUE N°2:\n"
            "31/08/2023, Intermarché, Foix\n"
            "Fournitures, équipement, Tente de spectacle, 437, 1, 427\n"
            "Energie, carburant, Essence au litre, 1,72, 40, 68.80\n"
            "Alimentation, charcuterie, Paté de campagne, 4.63, 1, 4.63"
        )

        return {
            "model": "gpt-4o",
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": prompt
                        },
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{base64_image}"
                            }
                        }
                    ]
                }
            ],
            "max_tokens": 1000
        }
    except Exception as e:
        logger.error(f"Error creating payload: {e}")
        raise


# Function to send the request to the OpenAI API
def send_request(api_key, payload):
    try:
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}"
        }

        response = requests.post("https://api.openai.com/v1/chat/completions", headers=headers, json=payload)

        if response.status_code != 200:
            raise Exception(f"Request failed: {response.status_code} {response.text}")

        return response.json()
    except requests.exceptions.RequestException as e:
        logger.error(f"Error sending request: {e}")
        raise
    except Exception as e:
        logger.error(f"General error: {e}")
        raise


def parse_response(response):
    try:
        if "choices" in response and len(response["choices"]) > 0:
            output = response["choices"][0]["message"]["content"]
            output_lines = output.split("\n")

            if len(output_lines) < 2:
                logger.warning("Unexpected response format: Not enough lines in output.")
                return None, True  # Indiquer que le format est incorrect

            date_fournisseur_localisation = output_lines[0].split(",")
            if len(date_fournisseur_localisation) < 3:
                logger.warning("Unexpected response format: Not enough elements in date_fournisseur_localisation.")
                return None, True  # Indiquer que le format est incorrect

            date_str = date_fournisseur_localisation[0].strip()
            try:
                date = datetime.strptime(date_str, "%d/%m/%Y").date()
            except ValueError as e:
                logger.error(f"Error parsing date: {e}")
                return None, True  # Indiquer que le format est incorrect

            fournisseur = date_fournisseur_localisation[1].strip()
            localisation = date_fournisseur_localisation[2].strip()

            articles = output_lines[1:]
            parsed_articles = []
            for article in articles:
                if article.strip() == "":
                    logger.warning("Skipping empty line in article list.")
                    continue  # Ignorer les lignes vides mais ne pas arrêter le traitement

                article_parts = article.split(",")
                if len(article_parts) < 6:
                    logger.warning(f"Unexpected response format: Not enough elements in article '{article}'.")
                    return None, True  # Indiquer que le format est incorrect

                try:
                    parsed_articles.append({
                        "famille": article_parts[0].strip(),
                        "sous_famille": article_parts[1].strip(),
                        "nom": article_parts[2].strip(),
                        "prix_unitaire": float(article_parts[3].strip()),
                        "quantite": float(article_parts[4].strip()),
                        "prix_total": float(article_parts[5].strip())
                    })
                except ValueError as e:
                    logger.error(f"Error parsing article data: {e}")
                    return None, True  # Indiquer que le format est incorrect

            return {
                "date": date,
                "fournisseur": fournisseur,
                "localisation": localisation,
                "articles": parsed_articles
            }, False  # Indiquer que le parsing a réussi sans problème
        else:
            logger.warning("No relevant content found in the response.")
            return None, True  # Indiquer que le format est incorrect
    except Exception as e:
        logger.error(f"Error parsing response: {e}")
        return None, True  # Indiquer que le format est incorrect


# Function to process a single image
def process_image(image_path, destination_folder, api_key, db_path, event_id, retry=False):
    try:
        logger.info(f"Processing image: {image_path}")
        base64_image = encode_image(image_path)
        payload = create_payload(base64_image)
        response = send_request(api_key, payload)

        parsed_data, parse_error = parse_response(response)
        if parsed_data:
            # Afficher les informations avant l'insertion
            print(f"Date: {parsed_data['date']}, Fournisseur: {parsed_data['fournisseur']}, Localisation: {parsed_data['localisation']}")
            for article in parsed_data["articles"]:
                print(f"Famille: {article['famille']}, Sous Famille: {article['sous_famille']}, Nom: {article['nom']}, Prix unitaire: {article['prix_unitaire']}, Quantité: {article['quantite']}, Prix total: {article['prix_total']}")

            # Insérer les données dans la base de données
            insert_receipt_data(db_path, parsed_data, event_id)

            # Déplacer l'image traitée dans le dossier de destination
            try:
                shutil.move(image_path, os.path.join(destination_folder, os.path.basename(image_path)))
                logger.info(f"Moved processed image to: {destination_folder}")
            except FileNotFoundError as e:
                logger.error(f"Error moving file: {e}")
            except Exception as e:
                logger.error(f"Unexpected error moving file: {e}")
        else:
            if not retry:
                logger.warning("Data parsing incomplete or error encountered. Retrying...")
                process_image(image_path, destination_folder, api_key, db_path, event_id, retry=True)
            else:
                logger.error("Parsed data is empty or incorrect after retry. Skipping this image.")
                ui.messagebox.showwarning("Warning", "Les données extraites sont incorrectes après réessai. Image ignorée.")
    except Exception as e:
        logger.error(f"Error processing image {os.path.basename(image_path)}: {e}")
        if not retry:
            logger.info("Retrying the process for the image.")
            process_image(image_path, destination_folder, api_key, db_path, event_id, retry=True)
        else:
            logger.error(f"Failed after retrying. Skipping image {os.path.basename(image_path)}")
            ui.messagebox.showwarning("Warning", f"Erreur dans le traitement de l'image {os.path.basename(image_path)} après réessai. Image ignorée.")


# Path to your source and destination folders
source_folder = "./receipt_queue"
destination_folder = "./receipt_processed"

# Ensure the destination folder exists
os.makedirs(destination_folder, exist_ok=True)
