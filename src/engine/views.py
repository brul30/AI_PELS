from rest_framework.response import Response
from rest_framework.decorators import api_view
from bs4 import BeautifulSoup as bs
import re
import json
import requests

from .serializers import WordSerializer
from .models import Word

import requests
import json

from pels.env import config

from rest_framework import status

@api_view(['POST'])
def search(request):

    word_data = request.data.get('search')

    #print(word_data)
    
    # Validate that word_data exists and is a string (this is a simple validation example)
    if not word_data or not isinstance(word_data, str):
        return Response({'error': 'Invalid data'}, status=status.HTTP_400_BAD_REQUEST)

    # Check if the word exists
    if Word.objects.filter(word=word_data).exists():

        serializer = WordSerializer(Word.objects.get(word=word_data))

        return Response({'info': "word was found in database",
                         **serializer.data})
    
    else:
        
        laymans = get_laymans(word_data)
        #print(laymans)
        create_word(word_data, laymans)
        return search_word(word_data)

def search_word(word):

    if not word or not isinstance(word, str):

        return Response({'error': 'Invalid data'}, status=status.HTTP_400_BAD_REQUEST)

    # Check if the word exists
    if Word.objects.filter(word=word).exists():

        serializer = WordSerializer(Word.objects.get(word=word))

        return Response({'info': "word was not found in database, created new word",
                         **serializer.data})
    
    else:
        
        return Response({'error': "word was not found in database"})
   
# def get_laymans(word):

#     #print("laymans reached", word)

#     message =[{"role": "user", "content" : f"generate english layman pronunciation of {word} in the format: abc-def-ghi. no extra symbols"}]

#     key = config("OPENAI_SECRET_KEY", default='none')
#     endpoint = config("OPENAI_ENDPOINT", default='none')

#     headers = {

#         "Content-Type": "application/json",
#         "Authorization": f"Bearer {key}",
#     }

#     data = {

#         "model": "gpt-4-0613",
#         "messages": message,
#         "temperature": 0,
#     }

#     response = requests.post(endpoint, headers=headers, data=json.dumps(data))

#     if response.status_code == 200:

#         laymans = response.json()['choices'][0]['message']['content']
#         #laymans_list = re.split('-', laymans)
#         laymans_list = laymans.split('-')
#         #print(laymans_list)
#         return laymans_list
        
#     else:
#         return Exception(f"Error {response.status_code}: {response.text}")

def get_laymans_gpt4(word):


    prompt = f"layman pronunciation of word \"{word}\". only use letters and hyphens. format '^[a-zA-Z\-]+$'"

    message =[{"role": "user", "content" : prompt}]

    key = config("OPENAI_SECRET_KEY", default='none')
    endpoint = config("OPENAI_ENDPOINT", default='none')

    model="gpt-4-0613"

    temperature=0

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {key}",
    }

    data = {
        "model": model,
        "messages": message,
        "temperature": temperature,
    }

    response = requests.post(endpoint, headers=headers, data=json.dumps(data))

    if response.status_code == 200:      
        #print(response.json())
        return response.json()["choices"][0]["message"]["content"]
    else:
        raise Exception(f"Error {response.status_code}: {response.text}")

def get_laymans_webscrape(word):
        
    link = config("LINK", default='none')
    url = f'{link}{word}'
    response = requests.get(url)
    soup = bs(response.content, "html.parser")
    pronunciation_spans = soup.find('p', id='SyllableContentContainer')
    #print(pronunciation_spans)
    if "How to pronounce" in pronunciation_spans.text:
        #print(True)
        return pronunciation_spans.find_all('span', class_='Answer_Red')[-1].text
    else:
        #print(False)
        #print("Pronunciation not found")
        return None

def is_valid_result(result):
    if result is None:
        return False  # or however you want to handle a None result
    if re.search(r'^[a-zA-Z\-]+$', result):
        return True
    return False

def get_laymans(word):

    webscraped = get_laymans_webscrape(word)
    
    if is_valid_result(webscraped):
        print(f"webscraped: {webscraped}")
        webscraped_list = webscraped.split('-') 
        return webscraped_list
    
    else:
        for i in range(5):
            gpt4 = get_laymans_gpt4(word).strip()
            print(f"gpt4: {gpt4}")
            if is_valid_result(gpt4):
                gpt_list = gpt4.split('-')
                return gpt_list
            print(f"gpt4 failed, trying again... {i+1} Result: {gpt4}")
        return "null"
    
def create_word(word, laymans):

    #print("create_word reached", word, laymans)

    word = Word(word=word, laymans=laymans)
    word.save()

