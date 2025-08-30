"""
MatchBoxAIEngine.Query: (Query Parsing Service)
Supports PDF, Docx, Voice, Text, LLMRESP.

Developed and maintained by Aditya Gaur / @xdityagr at Github / adityagaur.home@gmail.com
© 2025 MatchBox AI. All rights reserved.
"""
import os
import requests
from dotenv import load_dotenv
import pdfplumber
# from docx import Document
# import fitz
import json

from TruptiEngine.DataDefinitions import *
import json
from json import JSONDecodeError
import re

load_dotenv(override=True)


def llm_campaign_info_from_raw(raw_text:str):
    raw_text = raw_text.lstrip("```json").replace('```', '')
    try:
        json_data = json.loads(raw_text)

        creator_reqs = [
            CreatorRequirement(**req) for req in json_data.get("creator_requirements", [])
        ]

        # Convert deliverables
        deliverables = [
            Deliverable(**d) for d in json_data.get("deliverables", [])
        ]

        # Build CampaignInfo object
        campaign_info = CampaignInfo(
            category=json_data.get("category"),
            products_services=json_data.get("products_services", []),
            creator_requirements=creator_reqs,
            budget_per_creator=json_data.get("budget_per_creator"),
            budget_total=json_data.get("budget_total"),
            deliverables=deliverables,
            genre=json_data.get("genre"),
            followers_open=json_data.get("followers_open", True),
            location=json_data.get("location"),
            tat=json_data.get("tat"),
            notes=json_data.get("notes"),
            num_creators_target=json_data.get("num_creators_target", {}),
            platforms=json_data.get("platforms", [])
        )

        return campaign_info, {}

    except JSONDecodeError as e:
        return None, {'error':str(e)}
    
def llm_fromJSON(raw_text):
    raw_text = raw_text.lstrip("```json").replace('```', '')
    try:
        json_data = json.loads(raw_text)
        return json_data
    except Exception as e: 
        print(f'[Error] {e}')
        return None
    
def parse_audio(filepath):
    API_URL = "https://router.huggingface.co/hf-inference/models/openai/whisper-large-v3"
    headers = {
        "Authorization": f"Bearer {os.environ['HF_API_KEY']}",
    }

    try:
        with open(filepath, "rb") as f:
            data = f.read()
        response = requests.post(API_URL, headers={"Content-Type": "audio/mpeg", **headers}, data=data)
        resp_js = response.json()
        if response.status_code == 200:
            return resp_js['text'], {}
        else:
            return None, {'error':response}
        
    except Exception as e: 
        return None, {'error': e}
    


def parse_audio_from_bytes(audio_bytes):
    API_URL = "https://router.huggingface.co/hf-inference/models/openai/whisper-large-v3"
    headers = {
        "Authorization": f"Bearer {os.environ.get('HF_API_KEY')}",
        "Content-Type": "audio/mpeg"
    }

    try:
        response = requests.post(API_URL, headers=headers, data=audio_bytes)

        if response.status_code != 200:
            return None, {'error': f'Status {response.status_code}: {response.text}'}

        resp_js = response.json()
        text_output = resp_js.get('text')
        if text_output:
            return text_output, {}
        else:
            return None, {'error': f"No 'text' key in API response: {resp_js}"}

    except Exception as e:
        return None, {'error': str(e)}


# def parse_pdf(file_path):
#     try:
#         text = ""
#         pdf_document = fitz.open(file_path)
#         for page_num in range(len(pdf_document)):
#             page = pdf_document[page_num]
#             text += page.get_text() + "\n"
#         text = text.strip()
#         return text, {}
    
#     except Exception as e: 
#         return None, {'error':str(e)}

# def parse_docx(filepath):
#     try:
#         doc = Document(filepath)
#         content = "\n".join([para.text for para in doc.paragraphs]).strip()
#         return content, {}

#     except Exception as e: 
#         return None, {'error':str(e)}

def parse_txt(file_path):
    with open(file_path, "r", encoding="utf-8") as f:
        return f.read()
    
