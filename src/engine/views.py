from rest_framework.response import Response
from rest_framework.decorators import api_view
from django.shortcuts import render

from .serializers import WordSerializer
from .models import Word

import requests
import json

from pels.env import config

from rest_framework.decorators import api_view, authentication_classes, permission_classes
from rest_framework.authentication import SessionAuthentication, TokenAuthentication
from rest_framework.permissions import IsAuthenticated
from rest_framework import status

from django.shortcuts import get_object_or_404

import re

# Create your views here.

@api_view(['POST'])
def search(request):
    word_data = request.data.get('search')

    print(word_data)
    
    # Validate that word_data exists and is a string (this is a simple validation example)
    if not word_data or not isinstance(word_data, str):
        return Response({'error': 'Invalid data'}, status=status.HTTP_400_BAD_REQUEST)

    # Check if the word exists
    if Word.objects.filter(word=word_data).exists():

        return Response({'info': "word was found in database",
                         'word': word_data,
                         'laymans': Word.objects.get(word=word_data).laymans})
    
    else:
        
        laymans = get_laymans(word_data)
        create_word(word_data, laymans)
        return search_word(word_data)

def search_word(word):

    if not word or not isinstance(word, str):
        return Response({'error': 'Invalid data'}, status=status.HTTP_400_BAD_REQUEST)

    # Check if the word exists
    if Word.objects.filter(word=word).exists():

        laymans = Word.objects.get(word=word).laymans

        return Response({'info': "word was not found in database, created new word",
                         'word': word,
                         'laymans': laymans})
    
    else:
        
        return Response({'error': "error"})

    
def get_laymans(word):

    print("laymans reached", word)

    message =[{"role": "user", "content" : f"generate english layman pronunciation of {word}"}]

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
        laymans_list = re.split('-', laymans)
        print(laymans_list)
        return laymans_list
        
    else:
        return Exception(f"Error {response.status_code}: {response.text}")
    
def create_word(word, laymans):

    print("create_word reached", word, laymans)

    word = Word(word=word, laymans=laymans)
    word.save()
    


