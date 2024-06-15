import unittest
from unittest.mock import patch, mock_open, MagicMock
import receipt_reader
import base64
import requests
import os
from datetime import date

class TestReceiptReader(unittest.TestCase):

    @patch("builtins.open", new_callable=mock_open, read_data=b"image data")
    def test_encode_image(self, mock_file):
        encoded_image = receipt_reader.encode_image("test.jpg")
        self.assertEqual(encoded_image, base64.b64encode(b"image data").decode('utf-8'))
        mock_file.assert_called_once_with("test.jpg", "rb")

    def test_create_payload(self):
        base64_image = base64.b64encode(b"image data").decode('utf-8')
        payload = receipt_reader.create_payload(base64_image)
        self.assertIn("model", payload)
        self.assertIn("messages", payload)
        self.assertEqual(payload["messages"][0]["content"][1]["image_url"]["url"], f"data:image/jpeg;base64,{base64_image}")

    @patch("requests.post")
    def test_send_request(self, mock_post):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"choices": [{"message": {"content": "response"}}]}
        mock_post.return_value = mock_response

        api_key = "test_api_key"
        payload = {"test": "data"}
        response = receipt_reader.send_request(api_key, payload)

        self.assertEqual(response, {"choices": [{"message": {"content": "response"}}]})
        mock_post.assert_called_once_with(
            "https://api.openai.com/v1/chat/completions",
            headers={"Content-Type": "application/json", "Authorization": f"Bearer {api_key}"},
            json=payload
        )

    def test_parse_response(self):
        response = {
            "choices": [
                {
                    "message": {
                        "content": "31/08/2023, Intermarché, Foix\n"
                                   "Food, Fruit, Apple, 0.5, 10, 5.0\n"
                                   "Drink, Juice, Orange Juice, 1.5, 5, 7.5\n"
                    }
                }
            ]
        }
        parsed_data = receipt_reader.parse_response(response)
        self.assertIsNotNone(parsed_data)
        self.assertEqual(parsed_data["date"], date(2023, 8, 31))  # Correction ici
        self.assertEqual(parsed_data["fournisseur"], "Intermarché")
        self.assertEqual(parsed_data["localisation"], "Foix")
        self.assertEqual(len(parsed_data["articles"]), 2)

    @patch("shutil.move")
    @patch("receipt_reader.insert_receipt_data")
    @patch("receipt_reader.send_request")
    @patch("receipt_reader.encode_image")
    @patch("os.makedirs")
    def test_process_image(self, mock_makedirs, mock_encode_image, mock_send_request, mock_insert_receipt_data, mock_shutil_move):
        mock_encode_image.return_value = "encoded_image"
        mock_send_request.return_value = {
            "choices": [
                {
                    "message": {
                        "content": "31/08/2023, Intermarché, Foix\n"
                                   "Food, Fruit, Apple, 0.5, 10, 5.0\n"
                                   "Drink, Juice, Orange Juice, 1.5, 5, 7.5\n"
                    }
                }
            ]
        }

        receipt_reader.process_image("test.jpg", "destination_folder", "test_api_key", "test_db_path", 1)

        mock_encode_image.assert_called_once_with("test.jpg")
        mock_send_request.assert_called_once()
        mock_insert_receipt_data.assert_called_once()
        mock_shutil_move.assert_called_once_with("test.jpg", os.path.join("destination_folder", "test.jpg"))

if __name__ == "__main__":
    unittest.main()
