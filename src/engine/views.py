from rest_framework.response import Response
from rest_framework.decorators import api_view

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
   
def get_laymans(word):

    #print("laymans reached", word)

    message =[{"role": "user", "content" : f"generate english layman pronunciation of {word} in the format: abc-def-ghi. no extra symbols"}]

    key = config("OPENAI_SECRET_KEY", default='none')
    endpoint = config("OPENAI_ENDPOINT", default='none')

    headers = {

        "Content-Type": "application/json",
        "Authorization": f"Bearer {key}",
    }

    data = {

        "model": "gpt-4-0613",
        "messages": message,
        "temperature": 0,
    }

    response = requests.post(endpoint, headers=headers, data=json.dumps(data))

    if response.status_code == 200:

        laymans = response.json()['choices'][0]['message']['content']
        #laymans_list = re.split('-', laymans)
        laymans_list = laymans.split('-')
        #print(laymans_list)
        return laymans_list
        
    else:
        return Exception(f"Error {response.status_code}: {response.text}")
    
def create_word(word, laymans):

    #print("create_word reached", word, laymans)

    word = Word(word=word, laymans=laymans)
    word.save()
    return  status.HTTP_200_OK



@api_view(['POST'])
def feedback(request):
    mispronounced_phoneme=request.data.get('mispronounciation')
    word = request.data.get('word')
    laymans = request.data.get('laymans')
    message =[{"role": "user", "content" : f"In one sentece Generate advice for correcting mispronunciation of '{mispronounced_phoneme}' from the word {word} with laysmans {laymans}. Use the following as reference, for the laymans of in-tuh-lek-choo-uhl, the user misspronounced the choo and the feedback is as follow: Try to say choo instead of shoo How to improve Try to block the air with your tongue then relax it slightly to let air out for a 'sh' sound."}]


    key = "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"
    endpoint = "https://api.openai.com/v1/chat/completions"

    headers = {

        "Content-Type": "application/json",
        "Authorization": f"Bearer {key}",
    }

    data = {

        "model": "gpt-4-0613",
        "messages": message,
        "temperature": 0,
    }

    response = requests.post(endpoint, headers=headers, data=json.dumps(data))

    if response.status_code == 200:

        output = response.json()['choices'][0]['message']['content']
        #laymans_list = re.split('-', laymans)
        #laymans_list = laymans.split('-')
        #print(laymans_list)
        return Response({"feedback":output})
    else:
        return Exception(f"Error {response.status_code}: {response.text}")
