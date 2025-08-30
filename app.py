
"""
Project Trupti 
an innovative AI-powered irrigation assistant designed to empower farmers with smart, 
ata-driven farming solutions. Leveraging real-time weather data, crop requirements, 
and soil conditions, Trupti delivers personalized irrigation plans to optimize water usage and enhance crop yields. 

To run use : 
uvicorn app:app --port 5000
ngrok http 5000

Developed and maintained by Aditya Gaur / @xdityagr at Github / adityagaur.home@gmail.com
"""


from fastapi import FastAPI, Request, Query
from fastapi.responses import PlainTextResponse
import uvicorn
from dotenv import load_dotenv
import os
import json
import requests
from TruptiEngine.Model import ModelHandler
import time
from weatherEngine import WeatherMonitor

from TruptiEngine.Query.parser import *
from TruptiEngine.Outreach.callingEngine import VapiClient


load_dotenv(override=True) 

app = FastAPI()

VERIFY_TOKEN = os.getenv("WEBHOOK_TOKEN")
ACCESS_TOKEN = os.getenv("GRAPH_ACCESS_TOKEN")
PHONE_ID = os.getenv("GRAPH_PHONE_ID")
OPENWEATHER_API_KEY = os.getenv("OPENWEATHER_API_KEY")

print(VERIFY_TOKEN)
print(ACCESS_TOKEN)
print(PHONE_ID)

WELCOME_MESSAGE = """नमस्ते {} जी! 👋  
*Project Trupti* 🌱💧 में आपका स्वागत है।  
यह आपका स्मार्ट सिंचाई सहायक है।  

कृपया ये जानकारी हमें भेजें (आप चाहें तो लिखकर या आवाज़ में भेज सकते हैं 🎤✍️):  

1️⃣ आपकी फ़सल (जैसे गेहूँ, धान, मक्का) 🌾  
2️⃣ मिट्टी का प्रकार (रेतीली, दोमट, चिकनी) 🏞️  
3️⃣ आपका स्थान (गाँव/ज़िला) 📍  
4️⃣ सिंचाई का तरीका (टपक/स्प्रिंकलर/नहर) 🚜  

👉 इसके आधार पर हम आपको सही सिंचाई योजना बताएँगे ✅  

मदद चाहिए तो लिखें `मदद` 🤖  


"""

active_conversations = {} # later redis will be used.
WP_SYSTEM_PROMPT = """
You are **Trupti**, an AI assistant on WhatsApp designed to help farmers with smart irrigation planning and farming advice.  
You provide clear, step-by-step guidance for watering crops using real-time weather, soil conditions, and crop-specific water needs.  
Your tone must always be friendly, simple, and respectful (always addressing the farmer as "<name> जी" or "<name> garu" depending on language conventions).  
User's Name is : %s
---

🌟 Interaction Workflow:

1. Greetings & Language Preference:  
- If the first message is a greeting (e.g. "नमस्ते", "हेलो", "हाय", "Hi", "Hello", etc.), reply with:  

  "Hello <name> ji! 👋  
  Welcome to *Project Trupti* 🌱💧.  
  Which language would you like to continue in? (You may reply Hindi, English, Telugu, Kannada, Marathi, Tamil, Bengali, or any other language you prefer.)"  

- Detect the farmer’s response and continue the full conversation in **that language**.  
- Always stick to the chosen language unless the farmer explicitly switches.  

---

2. Welcome Template (Translated to Farmer’s Language):  
After detecting language, send the following in that language (examples shown for Hindi/English — dynamically adapt for other languages using translation):  

Hindi Example:  
"नमस्ते <name> जी! 👋  
*Project Trupti* 🌱💧 में आपका स्वागत है।  
यह आपका स्मार्ट सिंचाई सहायक है।  

कृपया ये जानकारी हमें भेजें (आप चाहें तो लिखकर या आवाज़ में भेज सकते हैं 🎤✍️):  

1️⃣ आपकी फ़सल (जैसे गेहूँ, धान, मक्का) 🌾  
2️⃣ मिट्टी का प्रकार (रेतीली, दोमट, चिकनी) 🏞️  
3️⃣ आपका स्थान (गाँव/ज़िला) 📍  
4️⃣ सिंचाई का तरीका (टपक/स्प्रिंकलर/नहर) 🚜  

👉 इसके आधार पर हम आपको सही सिंचाई योजना बताएँगे ✅  

मदद चाहिए तो लिखें `मदद` 🤖  
"

English Example:  
"Hello <name> ji! 👋  
Welcome to *Project Trupti* 🌱💧.  
This is your smart irrigation assistant.  

Please share these details (you can type or send by voice 🎤✍️):  

1️⃣ Your Crop (e.g., Wheat, Rice, Maize) 🌾  
2️⃣ Soil Type (Sandy, Loamy, Clay) 🏞️  
3️⃣ Location (Village/District) 📍  
4️⃣ Irrigation Method (Drip/Sprinkler/Canal) 🚜  

👉 Based on this, we will suggest the best irrigation plan ✅  

For help, type `Help` 🤖  
"

---

3. Information Collection:  
- Ask ONE question at a time in the selected language until you have all:  
  - Crop type 🌾  
  - Soil type 🏞️  
  - Location 📍  (Should be a city in India, Make sure it is a city/state)
  - Irrigation method 🚜  
  - User selected language to talk in
- If the farmer skips or gives incomplete answer, politely ask again.  

---

4. JSON Data Return:  
- Once all details are collected, return the structured input in pure JSON format like mentioned. Strictly, no other text should be mentioned, just the json info. No text after or before it.

{{
  "crop_type": "Wheat",
  "soil_type": "Loamy",
  "location": "Jaipur",
  "irrigation_method": "Drip",
  "language":"Hindi"
}} 
  

---

6. Help Mode:  
If farmer types "Help", "मदद", or the equivalent in their chosen language:  
- Explain how Trupti works.  
- Show example usage.  
- Encourage them to provide crop/soil/location details.  

---

7. General Rules:  
- Answer only **farming and agriculture related queries** (irrigation, soil, fertilizer, crop care).  
- If query is irrelevant, politely guide back to farming context.  
- Always continue in the farmer’s selected language.  
- Keep answers short, simple, caring, and practical.  

---
"""
active_weather_monitors = {}

def get_media_url(media_id):
    url = f"https://graph.facebook.com/v19.0/{media_id}"

    headers = {
        "Authorization": f"Bearer {ACCESS_TOKEN}"
    }
    response = requests.get(url, headers=headers)
    print(json.dumps(response.json(), indent=4))
    media_url = response.json()["url"]
    return media_url

def download_media_file(media_url, save_as):
    headers = {
        "Authorization": f"Bearer {ACCESS_TOKEN}"
    }
    response = requests.get(media_url, headers=headers)
    with open(save_as, "wb") as f:
        f.write(response.content)
    print(f"📥 Downloaded file as {save_as}")


def send_reply_text(phone, message_text):
    url = f"https://graph.facebook.com/v19.0/{PHONE_ID}/messages"
    headers = {
        "Authorization": f"Bearer {ACCESS_TOKEN}",
        "Content-Type": "application/json"
    }
    payload = {
        "messaging_product": "whatsapp",
        "to": phone,
        "type": "text",
        "text": {
            "body": message_text
        }
    }

    response = requests.post(url, headers=headers, json=payload)

    print("Reply status:", response.status_code)
    print("Response:", response.json())


recent_messages = set()

def get_weather_info(city, country_code="IN", api_key=None):
    """
    Fetch basic weather parameters for a given city.
    
    Args:
        city (str): Name of the city (e.g., "Jaipur")
        country_code (str): Country code (default: "IN" for India)
        api_key (str): OpenWeather API key (defaults to env variable OPENWEATHER_API_KEY)
    
    Returns:
        dict: Basic weather info or error message
    """
    if not api_key:
        api_key = os.getenv("OPENWEATHER_API_KEY")
    if not api_key:
        return {"error": "No API key provided"}

    url = "http://api.openweathermap.org/data/2.5/weather"
    params = {
        "q": f"{city},{country_code}",
        "appid": api_key, 
        "units": "metric"
    }
    print('GETTING WEATHER INFO')
    
    try:
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        
        # Parse JSON response
        try:
            data = response.json()
        except ValueError as json_err:
            return {"error": f"Invalid JSON response: {str(json_err)}"}
        

        if isinstance(data, dict) and "cod" in data and data["cod"] != 200:
            return {"error": f"API error: {data.get('message', 'Unknown error')}"}
        
        # Ensure the expected keys exist
        if not isinstance(data, dict) or "main" not in data or "weather" not in data:
            return {"error": "Unexpected API response format"}
        
        # Extract weather data with safe access
        weather_info = {
            "city": city,
            "temperature_c": data["main"]["temp"],
            "humidity_percent": data["main"]["humidity"],
            "pressure_hpa": data["main"]["pressure"],
            "weather_main": data["weather"][0]["main"],
            "weather_description": data["weather"][0]["description"],
            "clouds_percent": data["clouds"]["all"],
            "timestamp": data["dt"]
        }
        print(weather_info)

        if "wind" in data and "speed" in data["wind"]:
            weather_info["wind_speed_ms"] = data["wind"]["speed"]
        
        if "rain" in data and "1h" in data["rain"]:
            weather_info["rain_1h_mm"] = data["rain"]["1h"]
        else:
            weather_info["rain_1h_mm"] = 0
            
        return weather_info
        

    except Exception as e:
        return {"error": f"Unexpected error: {str(e)}"}
    
def irrigation_callback(user_info, from_number):
    location = user_info['location']
    crop = user_info['crop_type']
    soil = user_info['soil_type']
    language = user_info['language']
    irrigation_method = user_info['irrigation_method']
    weather_data = get_weather_info(location, 'IN')
    print('got weather data')
    
    if "error" in weather_data:
        print(f"Weather data error: {weather_data['error']}")
        send_reply_text(from_number, f"Sorry, couldn't fetch weather data: {weather_data['error']}")
        return
    
    # Check for bad weather conditions from the single weather data point
    is_bad_weather = False
    
    # Check for heavy rain (more than 20mm in last hour)
    if weather_data.get("rain_1h_mm", 0) > 20:
        is_bad_weather = True
    
    # Check for severe weather conditions
    weather_main = weather_data.get("weather_main", "").lower()
    severe_weather_conditions = ["storm", "thunderstorm", "hurricane", "tornado"]
    if weather_main in severe_weather_conditions:
        is_bad_weather = True

    wind_speed = weather_data.get("wind_speed_ms", 0)
    if wind_speed > 10:  # High wind speed 
        is_bad_weather = True

    mh = ModelHandler()
    system_prompt = f"""
You must use the language specified: {language}.  
Respond only in this language, with no translations to other languages.  

Available Information:  
- Location: {location}  
- Crop: {crop}  
- Soil Type: {soil}  
- Irrigation Method: {irrigation_method}  
- Current Weather Conditions: {json.dumps(weather_data, indent=2)}  

Instructions:  
1. Analyze the weather (rain, temperature, humidity, wind) and the needs of the crop and soil to determine how much irrigation is required and when it should be done.  
2. Provide suggestions to the farmer in simple, short sentences in the specified language ({language}).  
3. If severe weather conditions like heavy rain or hail are detected, include a warning.  
4. Specify the amount of water (liters per acre or mm) and the time of day (morning/evening) for irrigation.  
5. Provide a complete irrigation plan, including the interval (how many days apart), amount, and timing.  
    """

    report = mh.instant_chat(system_ctx=system_prompt, user_input="कृपया सिंचाई रिपोर्ट तैयार करें। /Prepare irrigation report.")
    send_reply_text(from_number, report)

    if is_bad_weather:
        vapi = VapiClient()
        bad_weather_prompt = f"""
        You are Trupti, an AI assistant calling to warn the farmer about bad weather conditions. 
        
        User's Name: {user_info.get('name', 'Farmer')} जी
        Location: {location}
        Crop: {crop}
        Soil: {soil}
        Irrigation Method: {irrigation_method}
        Current Weather: {json.dumps(weather_data, indent=2)}
        Language you should use during the conversation : {language}
        
        Instructions:
        - Greet politely in the mentioned language.
        - Warn about the specific bad weather (e.g., heavy rain, storm, high winds).
        - Give practical advice on protecting the crop (e.g., cover fields, delay irrigation).
        - Suggest emergency measures if needed.
        - Keep the call short, caring, and informative.
        - End by offering more help via WhatsApp.
        """
        # Update the assistant's system prompt for this call scenario
        vapi.update_system_prompt(bad_weather_prompt)  
        
        # Initiate the call (add + prefix to phone number)
        customer_number = f"+{from_number}"
        vapi.initiate_call(customer_number, firstMessage="नमस्ते, यह Trupti है। मौसम के बारे में महत्वपूर्ण चेतावनी है।")

@app.api_route("/webhook", methods=["GET", "POST"])
async def whatsapp_webhook(request: Request,
    hub_mode: str = Query(None, alias="hub.mode"),
    hub_challenge: str = Query(None, alias="hub.challenge"),
    hub_verify_token: str = Query(None, alias="hub.verify_token")
):

    if request.method == "GET":
        if hub_mode == "subscribe" and hub_verify_token == VERIFY_TOKEN:
            return PlainTextResponse(hub_challenge)
        else:
            print('here2')

            return PlainTextResponse("Verification failed", status_code=403)

    elif request.method == "POST":
        try:
            try:
                data = await request.json()
            except Exception:
                form = await request.form()
                data = dict(form)

            print(json.dumps(data, indent=2))

            if "entry" not in data:
                print("⚠️ No 'entry' in webhook data")
                return {"status": "no_entry"}

            # Check for incoming messages
            entry = data.get("entry", [])[0]
            changes = entry.get("changes", [])[0]
            value = changes.get("value", {})
            if "messages" not in value:
                print("📭 Ignored non-message webhook (status/update):", json.dumps(value, indent=2))
                return {"status": "ignored"}

            reciever_name = value.get('contacts', [{'profile':{'name':'User'}}])[0]['profile']['name']
            messages = value.get("messages", [])

            if messages:
                msg = messages[0]
                message_id = msg.get("id")

                if message_id in recent_messages:
                    print("Duplicate webhook call ignored.")
                    return {"status": "duplicate"}


                recent_messages.add(message_id)

                if len(recent_messages) > 1000:
                    recent_messages.clear()


                from_number = msg.get("from")
                msg_type = msg.get("type")
                
                text_message = None
                parsed_text = None
                parsed_from = None

                if msg_type in ('media', 'image', 'document', 'audio'):
                    media_id = msg[msg_type]["id"]
                    fname = msg[msg_type].get('filename', None)            

                    extension = ''
                    if fname : 
                        extension = fname
                        
                    url = get_media_url(media_id)

                    if msg_type == 'audio':
                        extension = '.mp3'
                        parsed_from = 'Voice message audio (mp3)'
                        storage_id = f'storage_{msg_type}_{media_id}_{extension}'
                        audio_response = requests.get(url, headers={"Authorization": f"Bearer {ACCESS_TOKEN}"})
                        audio_bytes = audio_response.content
                        print(f"Audio bytes size: {len(audio_bytes)}")

                        resp, error = parse_audio_from_bytes(audio_bytes)
                        print("Parsed text:", resp)
                        print("Error:", error)
                
                        if error.get('error', None) is None and resp is not None:
                            parsed_text = resp
                            # send_reply_text(from_number, f"Did you say? : {parsed_text}")
                        else:
                            send_reply_text(from_number, f"We couldn't parse your audio file, Please try again.")
                            

                    elif msg_type == 'image':
                        extension='.jpeg'

                elif msg_type == "text":
                    text_message = msg["text"]["body"]

                print(f'Parsed Text : {parsed_text}')
                if from_number not in active_conversations:                
                    # init model only once per user
    
                    mlh = ModelHandler()
                    conv, err = mlh.persist_chat_init(WP_SYSTEM_PROMPT % reciever_name)

                    if not err.get('error', None):
                        active_conversations[from_number] = conv
                    else:
                        pass
                
                conv = active_conversations[from_number]

                input = text_message if text_message else f"Parsed Text (from {parsed_from}) : {parsed_text}"
                response = conv.run(input=input)
                response.strip()

                if response.startswith('```'):
                    if 'json' in response:
                        raw_text = response.lstrip("```json").replace('```', '')
                        print(raw_text.strip())
                        user_info = json.loads(raw_text)
                        print(user_info)

                        irrigation_callback(user_info, from_number)

                else:
                    print(response)
                    send_reply_text(from_number, response)

                print(f"📩 From {from_number}: {text_message}")
        
        except Exception as e:
            print(f"Webhook processing error: {e}")


        return {"status": "received"} 

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)


