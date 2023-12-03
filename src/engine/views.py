from rest_framework.response import Response
from rest_framework.decorators import api_view
import re
import json
import requests
import time
import hashlib
import os
import ast
from .serializers import WordSerializer
from .models import Word

import requests
import json

from pels.env import config


from rest_framework import status

def get_phonetic(word):

    baseURL = config("SPEECHSUPER_URL",default='none')
    appKey = config("SPEECH_SUPER_APP_KEY",default='none')
    secretKey = config("SPEECH_SUPER_SECRET_KEY",default='none')
    timestamp = str(int(time.time()))
    coreType = "word.eval"         # Change the coreType according to your needs.
    refText = f"{word}"        # Change the reference text according to your needs.
    audioType = "wav"              # Change the audio type corresponding to the audio file.
    audioSampleRate = 16000
    userId = "guest"
    url =  baseURL + coreType
    connectStr = (appKey + timestamp + secretKey).encode("utf-8")
    connectSig = hashlib.sha1(connectStr).hexdigest()
    startStr = (appKey + timestamp + userId + secretKey).encode("utf-8")
    startSig = hashlib.sha1(startStr).hexdigest()
    params={
        "connect":{
            "cmd":"connect",
            "param":{
                "sdk":{
                    "version":16777472,
                    "source":9,
                    "protocol":2
                },
                "app":{
                    "applicationId":appKey,
                    "sig":connectSig,
                    "timestamp":timestamp
                }
            }
        },
        "start":{
            "cmd":"start",
            "param":{
                "app":{
                    "userId":userId,
                    "applicationId":appKey,
                    "timestamp":timestamp,
                    "sig":startSig
                },
                "audio":{
                    "audioType":audioType,
                    "channel":1,
                    "sampleBytes":2,
                    "sampleRate":audioSampleRate
                },
                "request":{
                    "coreType":coreType,
                    "refText":refText,
                    "tokenId":"tokenId"
                }
            }
        }
    }
    datas=json.dumps(params)
    data={'text':datas}
    headers={"Request-Index":"0"}
    res=requests.post(url, data=data, headers=headers).text.encode('utf-8', 'ignore').decode('utf-8')
    data = json.loads(res)
    phonetics = [stress_entry['phonetic'] for stress_entry in data['result']['words'][0]['scores']['stress']]
    print(res)
    return phonetics

def phonetic_to_laymans(phonetic, word):

    OPENAI_SECRET_KEY = config("OPENAI_SECRET_KEY",default='none')
    OPENAI_ENDPOINT = config("OPENAI_ENDPOINT",default='none')
    prompt = f"Convert {phonetic} from {word} to simple American layman's pronunciation. Give me the array ONLY, seperate each syllable."
    message =[{"role": "user", "content" : prompt}]
    model = 'gpt-4-1106-preview'

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {OPENAI_SECRET_KEY}",
    }

    data = {
        "model": model,
        "messages": message,
        "temperature": 0,
    }

    response = requests.post(OPENAI_ENDPOINT, headers=headers, data=json.dumps(data))

    if response.status_code == 200:      
        #print(response.json())
        answer = response.json()["choices"][0]["message"]["content"]
        print(answer)
        pattern = r"[\"'](.*?)[\"']"
        laymans = re.findall(pattern, answer)
        return laymans
    else:
        raise Exception(f"Error {response.status_code}: {response.text}")

def search_word(word):

    if not word or not isinstance(word, str):

        return Response({'error': 'Invalid data'}, status=status.HTTP_400_BAD_REQUEST)

    # Check if the word exists
    if Word.objects.filter(word=word).exists():

        serializer = WordSerializer(Word.objects.get(word=word))

        return Response({'info': "word was found in database, created new word",
                         **serializer.data})
    
    else:
        
        return Response({'error': "word was not found in database"})

def get_laymans(word):

    phonetic = get_phonetic(word)
    laymans = phonetic_to_laymans(phonetic, word)
    return phonetic, laymans
    
def create_word(word, phonetic, laymans):

    word = Word(word=word, phonetic=phonetic, laymans=laymans)
    word.save()

def get_laymans_from_database(word):
    
        if not word or not isinstance(word, str):
    
            return None
    
        # Check if the word exists
        if Word.objects.filter(word=word).exists():

            print("word found in database")
    
            return Word.objects.get(word=word)
        
        else:
            
            return None

@api_view(['POST'])
def search(request):

    word = request.data.get('search')
    
    if not word or not isinstance(word, str):
        return Response({'error': 'Invalid data'}, status=status.HTTP_400_BAD_REQUEST)

    # Check if the word exists
    if Word.objects.filter(word=word).exists():

        serializer = WordSerializer(Word.objects.get(word=word))

        return Response({'info': "word was found in database",
                         **serializer.data})
    
    else:
        
        print("word not found in database")
        phonetic, laymans = get_laymans(word)
        create_word(word, phonetic, laymans)
        return search_word(word)

@api_view(['POST'])
def feedback(request):
    
    scores = request.data.get('response')
    word = request.data.get('word')
    laymans = get_laymans_from_database(word)
    #print(laymans.laymans)

    response_feedbacks = []
    response_laymans = []

    for i, x in enumerate(scores):

        if x.get('overall') <= 70:
            #print(x.get('overall'), laymans.laymans[i])
            response_laymans.append({"phrase": laymans.laymans[i], "score": x.get('overall')})
            OPENAI_SECRET_KEY = config("OPENAI_SECRET_KEY",default='none')
            OPENAI_ENDPOINT = config("OPENAI_ENDPOINT",default='none')
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {OPENAI_SECRET_KEY}",
            }

            prompt = f"For '{laymans.laymans[i]}' in '{word}', give a concise articulation tip. One sentence only."
            message = [{"role": "user", "content": prompt}]
            model = 'gpt-4-1106-preview'
            data = {
                "model": model,
                "messages": message,
                "temperature": 1,
            }

            response = requests.post(OPENAI_ENDPOINT, headers=headers, data=json.dumps(data))

            if response.status_code == 200:
                answer = response.json()["choices"][0]["message"]["content"]
                response_feedbacks.append({"phrase": laymans.laymans[i], "suggestion": answer})
            else:
                raise Exception(f"Error {response.status_code}: {response.text}")
            
    return Response(data={"laymans": response_laymans, "feedbacks": response_feedbacks}, status=status.HTTP_200_OK)
    