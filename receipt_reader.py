import base64
import requests
import os
import shutil
import time
import logging
from database import initialize_database, insert_receipt_data  # Importing the database functions
from datetime import datetime


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


# Function to create the payload
def create_payload(base64_image):
    try:
        prompt = (
            "Veuillez analyser l'image du reçu suivante et fournir les informations au format suivant :\n"
            "date, fournisseur, localisation (seulement la ville)\n"
            "famille d'articles (tu détermineras la famille en fonction de l'article concerné parmi les catégories suivantes ALIMENTATION, ANIMATION, ENERGIE, ALCOOL, LOGISTIQUE, MATERIEL)\n"
            "nom de l'article de la sous-famille, prix unitaire, quantité, prix total\n"
            "nom de l'article de la sous-famille, prix unitaire, quantité, prix total\n"
            "nom de l'article de la sous-famille, prix unitaire, quantité, prix total\n"
            "..., ..., ..., ..., ...\n"
            "famille d'articles (tu détermineras la famille en fonction de l'article concerné parmi les catégories suivantes ALIMENTATION, ANIMATION, ENERGIE, ALCOOL, LOGISTIQUE, MATERIEL)\n"
            "nom de l'article de la sous-famille, prix unitaire, quantité, prix total\n"
            "nom de l'article de la sous-famille, prix unitaire, quantité, prix total\n"
            "nom de l'article de la sous-famille, prix unitaire, quantité, prix total\n"
            "..., ..., ..., ..., ...\n"
            "..., ..., ..., ..., ...\n"
            "INSTRUCTION IMPORTANTE:\n"
            "Veille à fournir les informations demandées et seulement ces informations\n"
            "EXEMPLE DE SORTIE ATTENDUE N°1:\n"
            "31/08/2023, Intermarché, Foix\n"
            "ALIMENTATION\n"
            "Vico Chips Class.Nat, 3.56, 1, 3.56\n"
            "Pat. Emmental Rape 3, 3.01, 1, 3.01\n"
            "Pat Beurre Moule DX, 4.63, 1, 4.63"
            "EXEMPLE DE SORTIE ATTENDUE N°2:\n"
            "31/08/2023, Intermarché, Foix\n"
            "MATERIEL\n"
            "Tente de spectacle, 437, 1, 427\n"
            "ENERGIE\n"
            "Essence au litre, 1,72, 40, 68.80\n"
            "ALIMENTATION\n"
            "Paté de campagne, 4.63, 1, 4.63"
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
            "max_tokens": 300
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
            output = output.split("\n")

            if len(output) < 3:
                logger.warning("Unexpected response format: Not enough lines in output.")
                return None

            date_fournisseur_localisation = output[0].split(",")
            if len(date_fournisseur_localisation) < 3:
                logger.warning("Unexpected response format: Not enough elements in date_fournisseur_localisation.")
                return None

            # Format the date
            date_str = date_fournisseur_localisation[0].strip()
            try:
                date = datetime.strptime(date_str, "%d/%m/%Y").date()
            except ValueError as e:
                logger.error(f"Error parsing date: {e}")
                return None

            fournisseur = date_fournisseur_localisation[1].strip()
            localisation = date_fournisseur_localisation[2].strip()

            categorie = output[1].split(",")[0].strip()

            articles = output[2:]
            parsed_articles = []
            for article in articles:
                article_parts = article.split(",")
                if len(article_parts) < 4:
                    logger.warning(f"Unexpected response format: Not enough elements in article '{article}'.")
                    continue

                try:
                    parsed_articles.append({
                        "nom": article_parts[0].strip(),
                        "prix_unitaire": float(article_parts[1].strip()),
                        "quantite": float(article_parts[2].strip()),
                        "prix_total": float(article_parts[3].strip())
                    })
                except ValueError as e:
                    logger.error(f"Error parsing article data: {e}")
                    continue

            return {
                "date": date,
                "fournisseur": fournisseur,
                "localisation": localisation,
                "categorie": categorie,
                "articles": parsed_articles
            }
        else:
            logger.warning("No relevant content found in the response.")
            return None
    except Exception as e:
        logger.error(f"Error parsing response: {e}")
        return None



# Function to process a single image
def process_image(image_path, destination_folder, api_key, db_path):
    try:
        logger.info(f"Processing image: {image_path}")
        base64_image = encode_image(image_path)
        payload = create_payload(base64_image)
        response = send_request(api_key, payload)

        parsed_data = parse_response(response)
        if parsed_data:
            print(f"Date: {parsed_data['date']}, Fournisseur: {parsed_data['fournisseur']}, Localisation: {parsed_data['localisation']}")
            print(f"Catégorie: {parsed_data['categorie']}")

            for article in parsed_data["articles"]:
                print(f"Nom: {article['nom']}, Prix unitaire: {article['prix_unitaire']}, Quantité: {article['quantite']}, Prix total: {article['prix_total']}")

            # Insert data into database
            insert_receipt_data(db_path, parsed_data)
        else:
            logger.warning("Parsed data is empty.")

    except Exception as e:
        logger.error(f"Error processing image {os.path.basename(image_path)}: {e}")


# Main function to monitor the source folder and process images one by one
def main(source_folder, destination_folder):
    try:
        api_key = get_api_key()
        no_image_count = 0

        while True:
            images = [f for f in os.listdir(source_folder) if os.path.isfile(os.path.join(source_folder, f))]
            if images:
                no_image_count = 0
                image_path = os.path.join(source_folder, images[0])
                process_image(image_path, destination_folder, api_key)
                # Move processed image to destination folder
                try:
                    shutil.move(image_path, os.path.join(destination_folder, os.path.basename(image_path)))
                    logger.info(f"Moved processed image to: {destination_folder}")
                except FileNotFoundError as e:
                    logger.error(f"Error moving file: {e}")
                except Exception as e:
                    logger.error(f"Unexpected error moving file: {e}")
            else:
                no_image_count += 1
                logger.info(f"No images to process. Attempt {no_image_count}/3.")
                if no_image_count >= 3:
                    logger.info("No images to process for 3 consecutive attempts. Exiting.")
                    break
                time.sleep(5)  # Wait for 5 seconds before checking again

    except Exception as e:
        logger.error(f"Error in main function: {e}")

# Path to your source and destination folders
source_folder = "./receipt_queue"
destination_folder = "./receipt_processed"

# Ensure the destination folder exists
os.makedirs(destination_folder, exist_ok=True)

if __name__ == "__main__":
    # Configuration des logs pour affichage dans la console uniquement
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s - %(levelname)s - %(message)s - [%(filename)s:%(lineno)d] - %(funcName)s()',
        datefmt='%Y-%m-%d %H:%M:%S',
        handlers=[logging.StreamHandler()]
    )

    logger = logging.getLogger(__name__)

    # Path to your source and destination folders
    source_folder = "./receipt_queue"
    destination_folder = "./receipt_processed"
    db_path = "./receipts.db"

    # Ensure the destination folder exists
    os.makedirs(destination_folder, exist_ok=True)

    # Initialize the database
    initialize_database(db_path)

    # Process images
    for image_filename in os.listdir(source_folder):
        image_path = os.path.join(source_folder, image_filename)
        if os.path.isfile(image_path):
            process_image(image_path, destination_folder, get_api_key(), db_path)

