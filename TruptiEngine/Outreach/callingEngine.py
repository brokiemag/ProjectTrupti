"""
ProjectTrupti.Outreach.callingEngine: (Call placement engine)

Developed and maintained by Aditya Gaur / @xdityagr at Github / adityagaur.home@gmail.com
© 2025 Trupti AI. All rights reserved.
"""
import requests
import json
import os

from dotenv import load_dotenv
load_dotenv(override=True) 

import requests
import json

class VapiClient:

    BASE_URL = "https://api.vapi.ai"

    def __init__(self):
        self._api_key = os.getenv("CALLING_API")
        self._assistant_id  = os.getenv("ASSISTANT_ID")
        self._phone_id = os.getenv("PHONE_ID")

        self.headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json"
        }

    def _make_request(self, method: str, endpoint: str, data: dict = None) -> dict:

        url = f"{self.BASE_URL}{endpoint}"
        try:
            if method == "POST":
                response = requests.post(url, headers=self.headers, json=data)
            elif method == "PATCH":
                response = requests.patch(url, headers=self.headers, json=data)
            elif method == "GET":
                response = requests.get(url, headers=self.headers)
            else:
                raise ValueError(f"Unsupported HTTP method: {method}")

            response.raise_for_status()  # Raises HTTPError for bad responses (4xx or 5xx)
            return response.json()
        
        except requests.exceptions.HTTPError as http_err:
            print(f"❌ HTTP error occurred: {http_err}")
            print(f"Response: {json.dumps(response.json(), indent=4)}")
            raise
        except requests.exceptions.ConnectionError as conn_err:
            print(f"❌ Connection error occurred: {conn_err}")
            raise
        except requests.exceptions.Timeout as timeout_err:
            print(f"❌ Timeout error occurred: {timeout_err}")
            raise
        except requests.exceptions.RequestException as req_err:
            print(f"❌ An unknown error occurred: {req_err}")
            raise

    def update_system_prompt(self, prompt: str) -> dict:
        new_system_prompt = prompt

           
        print(f"🔄 Attempting to update system prompt for assistant ID: {self._assistant_id}...")
        payload = {
            "model": {

                "provider": "openai",
                "model": "gpt-4o", 
                "systemPrompt": new_system_prompt
                }}
        try:
            updated_assistant = self._make_request(
                method="PATCH",
                endpoint=f"/assistant/{self._assistant_id}",
                data=payload
            )
            print(f"✅ Assistant '{self._assistant_id}' system prompt updated successfully!")
            print(f"New prompt: '{updated_assistant['model']['systemPrompt']}'")
            return updated_assistant
        except Exception as e:
            print(f"❌ Failed to update assistant prompt: {e}")
            raise

    def initiate_call(self, customer_number: str, firstMessage:str) -> dict:
        print(f"📞 Attempting to initiate call to {customer_number} using assistant {self._assistant_id} & phone id {self._phone_id}...")
        payload = {
            "assistantId": self._assistant_id,
            "customer": {
                "number": customer_number
            },
            "phoneNumberId": self._phone_id
        }
        try:
            call_data = self._make_request(
                method="POST",
                endpoint="/call",
                data=payload
            )
            print("✅ Call initiated successfully!")
            print("Call ID:", call_data.get("id"))
            print("Listen URL (WebSocket):", call_data.get("monitor", {}).get("listenUrl"))
            print("Control URL:", call_data.get("monitor", {}).get("controlUrl"))
            return call_data
        except Exception as e:
            print(f"❌ Failed to initiate call: {e}")
            raise
