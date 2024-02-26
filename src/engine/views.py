from rest_framework.response import Response
from rest_framework.decorators import api_view
from hyphen import Hyphenator, dictools
import nltk
from nltk.corpus import cmudict
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


def get_syllabus(word):

    # Check if the dictionary is available, if not, download it
    if not dictools.is_installed('en_US'):
        dictools.install('en_US')

    hyphenator = Hyphenator('en_US')

    #word = "install"
    syllables = hyphenator.syllables(word)
    if syllables:
        hyphenated_word = '-'.join(syllables)
    else:
        hyphenated_word = word  # fallback in case the word can't be hyphenated
    
    return hyphenated_word
    print(f"Hyphenated word: {hyphenated_word}")

def get_cmu_fomat(word):
        nltk.download('cmudict')
        pronouncing_dict = cmudict.dict()
        """
        Get the IPA representation of a word using CMU Pronouncing Dictionary.
        """
        word = word.lower()
        if word in pronouncing_dict:
            return pronouncing_dict[word][0]
        else:
            return None



def get_cmu(word):
# Download the CMU Pronouncing Dictionary if not already downloaded
    #word = "controversial"
    ipa = get_ipa(word)
    if ipa:
        print(f"IPA representation of '{word}': {' '.join(ipa)}")
    else:
        print(f"No IPA representation found for '{word}'")    


def phonetic_to_laymans(cmu_pronounciation, word,syllabus):
    try:
        prompt = f"Convert {word} using {cmu_pronounciation} to simple American layman's pronunciation. Give me the array ONLY, seperate each syllable {syllabus}."
        model = 'gpt-4-1106-preview'
        response = make_openAI_request(prompt,model,0)

        answer = response["choices"][0]["message"]["content"]
        print(answer)
        pattern = r"[\"'](.*?)[\"']"
        laymans = re.findall(pattern, answer)
        print(laymans)
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
    syllabus = get_syllabus(word)
    cmu_pronounciation = get_cmu(word)
    laymans = phonetic_to_laymans(cmu_pronounciation, word,syllabus)
#    return phonetic, laymans
    return cmu_pronounciation, laymans
   
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