import json
import os
import re
import secrets
import subprocess

from dotenv import load_dotenv
import requests
from bs4 import BeautifulSoup as bs
import azure.cognitiveservices.speech as speechsdk
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response
from django.core.files.storage import default_storage
from django.conf import settings

from .models import Word
from .serializers import WordSerializer
from pels.env import config

load_dotenv()

def webscrapeHowManySyllables(word) -> list[str] | None:
    
    response = requests.get(f'https://www.howmanysyllables.com/syllables/{word}')
    soup = bs(response.text, 'html.parser')
    if "How to pronounce" in soup.text:
        result = soup.find('p', id='SyllableContentContainer').findAll('span')[-1].text.split('-')
    else:
        result = None
    return result

def webscrapeYouGlish(word) -> list[str] | None:

    link = f"https://youglish.com/pronounce/{word}/english?"
    response = requests.get(link)
    soup = bs(response.content, "html.parser")
    try:
        text = soup.findAll('ul', {'class': 'transcript'})[0].findAll('li')[-1].text
        processed = re.findall(r'"(.*?)"', text)
        result = [match.lower() for match in processed]
    except IndexError:
        result = None
    return result

def openai_laymans(word) -> list[str] | None:

    headers = {
        "X-RapidAPI-Key": os.getenv('RAPIDAPI_KEY'),
        "X-RapidAPI-Host": "wordsapiv1.p.rapidapi.com"
    }

    url1 = f"https://wordsapiv1.p.rapidapi.com/words/{word}/syllables"
    syllables = requests.get(url1, headers=headers).json().get('syllables')
    list_syllables = syllables['list']

    print(list_syllables)

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {os.getenv('OPENAI_SECRET_KEY')}",
    }

    data = {
        "model": 'gpt-4-0125-preview',
        "messages": [{"role": "user", "content" : f"Convert {word} to simple American layman's pronunciation. Give me the array ONLY, in this regex: [^a-zA-Z,]+(,[^a-zA-Z,]+)* {list_syllables}."}],
        "temperature": 0,
    }

    response = requests.post(os.getenv('OPENAI_ENDPOINT'), headers=headers, data=json.dumps(data))

    if response.status_code == 200:      
        print(response.json())
        return response.json()["choices"][0]["message"]["content"]
    else:
        raise Exception(f"Error {response.status_code}: {response.text}")

@api_view(['POST'])
def search(request):

    # check if word is already in db
    existing = Word.objects.filter(word=request.data.get('search'))
    if existing:
        print("existing word found in db. returning...")
        serializer = WordSerializer(existing, many=True)
        return Response(data=serializer.data, status=status.HTTP_200_OK)
    
    print("word not found in db. scraping...")

    word = request.data.get('search')
    word = word.lower()

    print("web scraping howmanysyllables...")

    scrapedHowManySyllables = webscrapeHowManySyllables(word)
    
    if scrapedHowManySyllables:
        print("web scraped from howmanysyllables")
        new_word = Word(word=word, laymans=scrapedHowManySyllables)
        
    else:
        print("web scraping youglish...")
        scrapedYouGlish = webscrapeYouGlish(word)

        if scrapedYouGlish:
            print("web scraped from youglish")
            new_word = Word(word=word, laymans=scrapedYouGlish)

        else:
            print("openai_laymans")
            generated = openai_laymans(word)
            new_word = Word(word=word, laymans=generated)

    new_word.save()
    serializer = WordSerializer(new_word)

    return Response(data=[serializer.data], status=status.HTTP_200_OK)

def generate_feedback(request):

    scores = request.get('scores')
    laymans = request.get('laymans')
    word = request.get('word')

    #print(scores, laymans, word)
    
    OPENAI_SECRET_KEY = os.getenv('OPENAI_SECRET_KEY')
    OPENAI_ENDPOINT = os.getenv('OPENAI_ENDPOINT')
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {OPENAI_SECRET_KEY}",
    }

    print('generate_feedback')
    score_and_laymans_joined = []
    feedbacks = []
    #print(scores, laymans, word)
    for i, x in enumerate(laymans):
        score_and_laymans_joined.append({"phrase": x, "score": scores[i].get('score')})
        if scores[i].get('score') <= 80:
            prompt = f"For '{x}' in '{word}', give a concise articulation tip. One sentence only."
            message = [{"role": "user", "content": prompt}]
            data = {
                "model": 'gpt-4-0125-preview',
                "messages": message,
                "temperature": 1,
            }
            response = requests.post(OPENAI_ENDPOINT, headers=headers, data=json.dumps(data))
            if response.status_code == 200:
                articulation_tip = response.json()["choices"][0]["message"]["content"]
                feedbacks.append({"phrase": x, "articulation_tip": articulation_tip})
                # score_and_laymans_joined[i]["articulation_tip"] = articulation_tip
            else:
                raise Exception(f"Error {response.status_code}: {response.text}")
            
    print(score_and_laymans_joined, feedbacks)
    return_data = {
        "laymans": score_and_laymans_joined,
        "feedbacks": feedbacks
    }
    
    return return_data

@api_view(['POST'])
def test_feedback(request):

    scores = request.data.get('scores')
    laymans = request.data.get('laymans')
    word = request.data.get('word')

    #print(scores, laymans, word)
    
    OPENAI_SECRET_KEY = os.getenv('OPENAI_SECRET_KEY')
    OPENAI_ENDPOINT = os.getenv('OPENAI_ENDPOINT')
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {OPENAI_SECRET_KEY}",
    }

    print('generate_feedback')
    score_and_laymans_joined = []
    feedbacks = []
    #print(scores, laymans, word)
    for i, x in enumerate(laymans):
        score_and_laymans_joined.append({"phrase": x, "score": scores[i].get('score')})
        if scores[i].get('score') <= 80:
            prompt = f"For '{x}' in '{word}', give a concise articulation tip. One sentence only."
            message = [{"role": "user", "content": prompt}]
            data = {
                "model": 'gpt-4-0125-preview',
                "messages": message,
                "temperature": 1,
            }
            response = requests.post(OPENAI_ENDPOINT, headers=headers, data=json.dumps(data))
            if response.status_code == 200:
                articulation_tip = response.json()["choices"][0]["message"]["content"]
                feedbacks.append({"phrase": x, "articulation_tip": articulation_tip})
                # score_and_laymans_joined[i]["articulation_tip"] = articulation_tip
            else:
                raise Exception(f"Error {response.status_code}: {response.text}")
            
    print(score_and_laymans_joined, feedbacks)
    return_data = {
        "scores": score_and_laymans_joined,
        "feedbacks": feedbacks
    }
    
    return Response(data=return_data, status=status.HTTP_200_OK)
           
@api_view(['POST'])
def process_audio(request):

    # print(request.data)

    isSingleWord = request.data.get('isSingleWord')

    mp3_dir = os.path.join('media', 'mp3')
    wav_dir = os.path.join('media', 'wav')
    os.makedirs(mp3_dir, exist_ok=True)
    os.makedirs(wav_dir, exist_ok=True)

    audio_blob = request.FILES['audio']

    # Generate a 5 character random token
    token = secrets.token_hex(3)  # Generates a 6 character long token, as each byte is 2 characters

    # Derive original and new filenames without extension
    base_filename = os.path.splitext(audio_blob.name)[0] + '_' + token

    # Append the token and file extensions to filenames
    original_mp3_name = f'{base_filename}.mp3'
    converted_wav_name = f'{base_filename}.wav'

    # Define paths
    path_original_mp3 = os.path.join(mp3_dir, original_mp3_name)
    path_converted_wav = os.path.join(wav_dir, converted_wav_name)

    # Save the original audio blob in MP3 format
    with default_storage.open(path_original_mp3, 'wb+') as destination:
        destination.write(audio_blob.read())

    print(f'Original MP3 file saved at {path_original_mp3}')
    print(f'Converted WAV file saved at {path_converted_wav}')

    # Convert the audio to WAV format using FFmpeg
    command = [
        'ffmpeg',
        '-i', default_storage.path(path_original_mp3),
        '-acodec', 'pcm_s16le',  # Convert to WAV format
        '-ac', '1',  # Mono channel
        '-ar', '16000',  # 16 kHz sample rate
        default_storage.path(path_converted_wav)
    ]
    subprocess.run(command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    # print('Audio converted to WAV format')

    # speech config
    speech_config = speechsdk.SpeechConfig(subscription=os.getenv('SPEECH_KEY'), region=os.getenv('SPEECH_REGION'))
    speech_config.speech_recognition_language="en-US"

    full_path = os.path.join(path_converted_wav)

    # audio config
    audio_config = speechsdk.audio.AudioConfig(filename = full_path)

    # speech recognizer
    speech_recognizer = speechsdk.SpeechRecognizer(speech_config=speech_config, audio_config=audio_config)

    # Pronunciation config
    pronunciation_config = speechsdk.PronunciationAssessmentConfig( 
        reference_text=f"{request.data.get('word')}",
        grading_system=speechsdk.PronunciationAssessmentGradingSystem.HundredMark,
        granularity=speechsdk.PronunciationAssessmentGranularity.Phoneme,
        enable_miscue=False)

    # add pronunciation assessment to speech recognizer
    pronunciation_config.apply_to(speech_recognizer)

    speech_recognition_result = speech_recognizer.recognize_once_async().get()
    pronunciation_assessment_result_json = speech_recognition_result.properties.get(speechsdk.PropertyId.SpeechServiceResponse_JsonResult)

    result_json = json.loads(pronunciation_assessment_result_json)

    if isSingleWord.lower() == 'false':
        # send word laymans, score, and feedback
        print('isSingleWord is false')
        #sentence_result = result_json.get("NBest", [])[0]
        return Response(data=result_json, status=status.HTTP_200_OK)
    
    else:
        # send only word laymans and score
        scores = []
        print('isSingleWord is true')
        for x in result_json.get("NBest", [])[0].get("Words", [])[0].get("Syllables", []):
            syllable = x.get("Syllable")
            score = x.get("PronunciationAssessment", {}).get("AccuracyScore")
            syllable = syllable.replace("x", "")
            #return_json[syllable] = score
            scores.append({"phrase": syllable, "score": score})
        #print(scores)
        word = Word.objects.get(word=request.data.get('word'))
        laymans = word.laymans
        request = {
            "scores": scores,
            "laymans": laymans,
            "word": word
        }
        feedback = generate_feedback(request)

    try:
        os.remove(path_original_mp3)
        print(f'Deleted MP3 file: {path_original_mp3}')
    except Exception as e:
        print(f'Error deleting MP3 file: {e}')
    
    try:
        os.remove(path_converted_wav)
        print(f'Deleted WAV file: {path_converted_wav}')
    except Exception as e:
        print(f'Error deleting WAV file: {e}')

    return Response(data=feedback, status=status.HTTP_200_OK)