import json
import os
import re
import secrets
import time
import subprocess
from openai import OpenAI
from typing_extensions import override
from openai import AssistantEventHandler

from dotenv import load_dotenv
import requests
from bs4 import BeautifulSoup as bs
import azure.cognitiveservices.speech as speechsdk
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response
from django.core.files.storage import default_storage
from django.conf import settings
from django.core.exceptions import MultipleObjectsReturned


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
        if scores[i].get('score') <= 90:
            prompt = f"For '{x}' in '{word}', give a concise articulation tip. One sentence only."
            message = [{"role": "user", "content": prompt}]
            data = {
                "model": 'gpt-4-0125-preview',
                "messages": message,
                "temperature": 1,
            }
            response = requests.post(OPENAI_ENDPOINT, headers=headers, data=json.dumps(data))
            if response.status_code == 200:
                suggestion = response.json()["choices"][0]["message"]["content"]
                feedbacks.append({"phrase": x, "suggestion": suggestion})
                # score_and_laymans_joined[i]["articulation_tip"] = articulation_tip
            else:
                raise Exception(f"Error {response.status_code}: {response.text}")
            
    print(score_and_laymans_joined, feedbacks)
    return_data = {
        "laymans": score_and_laymans_joined,
        "feedbacks": feedbacks
    }
    
    return return_data

def process_audio_files(request):
    
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

    return path_converted_wav

def create_configuration(request, path_converted_wav, process_type):

    if (process_type == 'word'):
        granularity = speechsdk.PronunciationAssessmentGranularity.Phoneme
    else:
        granularity = speechsdk.PronunciationAssessmentGranularity.Word

    # if (process_type == 'chatbot'):
    #     speech_config = speechsdk.SpeechConfig(subscription=os.getenv('SPEECH_KEY'), region=os.getenv('SPEECH_REGION'))
    #     speech_config.speech_recognition_language="en-US"
    #     return speechsdk.SpeechRecognizer(speech_config=speech_config)

    speech_config = speechsdk.SpeechConfig(subscription=os.getenv('SPEECH_KEY'), region=os.getenv('SPEECH_REGION'))
    speech_config.speech_recognition_language="en-US"

    full_path = os.path.join(path_converted_wav)

    # audio config
    audio_config = speechsdk.audio.AudioConfig(filename = full_path)

    # Pronunciation config
    pronunciation_config = speechsdk.PronunciationAssessmentConfig( 
        reference_text=f"{request.data.get('word')}",
        grading_system=speechsdk.PronunciationAssessmentGradingSystem.HundredMark,
        granularity=granularity,
        enable_miscue=False)
    
    return_config = speechsdk.SpeechRecognizer(speech_config=speech_config, audio_config=audio_config)
    pronunciation_config.apply_to(return_config)
    return return_config

def process_sentence(request):
    path_converted_wav = process_audio_files(request)
    speech_recognizer = create_configuration(request, path_converted_wav, 'sentence')
    speech_recognition_result = speech_recognizer.recognize_once_async().get()
    pronunciation_assessment_result_json = speech_recognition_result.properties.get(speechsdk.PropertyId.SpeechServiceResponse_JsonResult)
    result_json = json.loads(pronunciation_assessment_result_json)
    print(result_json)
    return Response(data=result_json, status=status.HTTP_200_OK)

def process_word(request):
    path_converted_wav = process_audio_files(request)
    speech_recognizer = create_configuration(request, path_converted_wav, 'word')
    speech_recognition_result = speech_recognizer.recognize_once_async().get()
    pronunciation_assessment_result_json = speech_recognition_result.properties.get(speechsdk.PropertyId.SpeechServiceResponse_JsonResult)
    result_json = json.loads(pronunciation_assessment_result_json)
    scores = []
    for x in result_json.get("NBest", [])[0].get("Words", [])[0].get("Syllables", []):
        syllable = x.get("Syllable")
        score = x.get("PronunciationAssessment", {}).get("AccuracyScore")
        syllable = syllable.replace("x", "")
        #return_json[syllable] = score
        scores.append({"phrase": syllable, "score": score})
    try:
        word = Word.objects.get(word=request.data.get('word'))
    except MultipleObjectsReturned:
        words = Word.objects.filter(word=request.data.get('word'))
        word = words.first()
        words.exclude(pk=word.pk).delete()
    laymans = word.laymans
    request = {
        "scores": scores,
        "laymans": laymans,
        "word": word
    }
    feedback = generate_feedback(request)
    return Response(data=feedback, status=status.HTTP_200_OK)

def process_assessment(request):
    print(request.data)
    return Response(data={"message": "not implemented yet lel"}, status=status.HTTP_200_OK)

def init_chatbot(client: OpenAI, session):
    # Create a new assistant and thread as before
    chatbot = client.beta.assistants.create(
        name="pronunciation_assistant_roleplay",
        instructions="You are a chatbot that is roleplaying as an interviewer. You are interviewing a candidate for a job. The candidate is a non-native English speaker. You are to ask the candidate questions and provide feedback on their pronunciation.",
        model="gpt-4-turbo-preview",
    )
    thread = client.beta.threads.create()

    thread_id = thread.id
    chatbot_id = chatbot.id

    session['thread_id'] = thread_id
    session['chatbot_id'] = chatbot_id
    
    # Automatically generate the first chatbot message
    initial_message = "Hello! I'm your interviewer today. Let's start with a simple question: Could you tell me a little about yourself?"
    # Create the message in the thread with the specified role
    client.beta.threads.messages.create(
            thread_id=thread_id,
            role="assistant",  # This now depends on the sender_role argument
            content=initial_message
        )
    
    print(thread_id, chatbot_id, "initialized")

def add_message(message_content, sender_role, client: OpenAI, session):

    thread_id = session.get('thread_id')
    chatbot_id = session.get('chatbot_id')
    
    if not thread_id or not chatbot_id:
        # Handle uninitialized chat session
        return "Session expired or not initialized."

    try:
        # Create the message in the thread with the specified role
        message = client.beta.threads.messages.create(
            thread_id=thread_id,
            role=sender_role,  # This now depends on the sender_role argument
            content=message_content
        )

        # Add chatbot message and wait for the response
        run = client.beta.threads.runs.create_and_poll(
            thread_id=thread_id,
            assistant_id=chatbot_id,
            instructions="You are a chatbot that is roleplaying as an interviewer. You are interviewing a candidate for a job. The candidate is a non-native English speaker. You are to ask the candidate questions and provide feedback on their pronunciation."
        )

        #wait like 5 seconds
        time.sleep(5)
        
        # Assuming we get the chatbot response immediately
        chatbot_response = run.messages[-1]
        print(chatbot_response)
        return chatbot_response
        
    except Exception as e:
        # Handle errors (e.g., API failure, network issues)
        print(f"An error occurred: {str(e)}")
        return "An error occurred while adding the message."

def process_chatbot(request):
    try:
        session = request.session

        path_converted_wav = process_audio_files(request)
        speech_recognizer = create_configuration(request, path_converted_wav, 'chatbot')
        speech_recognition_result = speech_recognizer.recognize_once_async().get()
        pronunciation_assessment_result_json = speech_recognition_result.properties.get(speechsdk.PropertyId.SpeechServiceResponse_JsonResult)
        result_json = json.loads(pronunciation_assessment_result_json)

        user_message = result_json.get("DisplayText")
        fluency_score = result_json.get("NBest", [])[0].get("PronunciationAssessment", {}).get("FluencyScore")

        print(user_message, fluency_score)

        client = OpenAI()

        if not session.get('thread_id'):
            init_chatbot(client, session)

        chatbot_reponse = add_message(user_message, "user", client, session)

        JsonResponse = {
            "user_message": user_message,
            "fluency_score": fluency_score,
            "chatbot_response": chatbot_reponse
        }

        return Response(data=JsonResponse, status=status.HTTP_200_OK)
    except Exception as e:
        print(f"An error occurred: {str(e)}")
        return Response(data="An error occurred while processing chatbot", status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['POST'])
def process(request):

    process_type = request.data.get('type')
    print(process_type)
    if (process_type == 'word'):
        print("processing word")
        return process_word(request)
    elif (process_type == 'sentence'):
        print("processing sentence")
        return process_sentence(request)
    elif (process_type == 'assessment'):
        print("processing assessment")
        return process_assessment(request)
    elif (process_type == 'chatbot'):
        print("processing chatbot")
        return process_chatbot(request)
    else:
        return Response(data="Invalid process type", status=status.HTTP_400_BAD_REQUEST)
