import requests
import json
from pels.env import config
def make_openAI_request(prompt,model,temperature):
    OPENAI_SECRET_KEY = config("OPENAI_SECRET_KEY",default='none')
    OPENAI_ENDPOINT = config("OPENAI_ENDPOINT",default='none')
    message =[{"role": "user", "content" : prompt}]

    headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {OPENAI_SECRET_KEY}",
        }

    data = {
            "model": model,
            "messages": message,
            "temperature": temperature,
        }

    response = requests.post(OPENAI_ENDPOINT, headers=headers, data=json.dumps(data))

    if response.status_code == 200:      
         return response.json()
    else:
            raise Exception(f"Error {response.status_code}: {response.text}")