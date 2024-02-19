from rest_framework.response import Response
from rest_framework.decorators import api_view
import re
import json
import requests
import time
import hashlib

from rest_framework import status
from engine.utility import make_openAI_request
from .serializers import WordSerializer
from .models import Word

import requests
import json
import stripe
from pels.env import config



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
    try:
        prompt = f"Convert {phonetic} from {word} to simple American layman's pronunciation. Give me the array ONLY, seperate each syllable."
        model = 'gpt-4-1106-preview'
        response = make_openAI_request(prompt,model,0)

        answer = response["choices"][0]["message"]["content"]
        print(answer)
        pattern = r"[\"'](.*?)[\"']"
        laymans = re.findall(pattern, answer)
        return laymans
    
    except Exception as e:
        print(f"Error occured on: {e}")
        return []


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

    print(request.data)

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

        response_laymans.append({"phrase": laymans.laymans[i], "score": x.get('overall')})

        if x.get('overall') <= 70:
            try:
                #print(x.get('overall'), laymans.laymans[i])
                prompt = f"For '{laymans.laymans[i]}' in '{word}', give a concise articulation tip. One sentence only."
                model = 'gpt-4-1106-preview'
                temperature = 1

                response = make_openAI_request(prompt,model,temperature)

                answer = response.json()["choices"][0]["message"]["content"]
                response_feedbacks.append({"phrase": laymans.laymans[i], "suggestion": answer})
               
            except Exception as e:
                print(f"Error occured on: {e}")
                return []
            
    return Response(data={"laymans": response_laymans, "feedbacks": response_feedbacks}, status=status.HTTP_200_OK)



@api_view(['POST'])
def create_payment_intent(request):
    try:
        stripe.api_key = config("STRIPE_SECRET_KEY",default='none')
        payment_intent = stripe.PaymentIntent.create(
            amount=1999,
            currency='eur',
            automatic_payment_methods={'enabled': True},
        )

        return Response(data={'clientSecret': payment_intent.client_secret}, status=status.HTTP_200_OK)
    except stripe.error.StripeError as e:
        return Response(data={'error': {'message': str(e)}}, status=status.HTTP_400_BAD_REQUEST)