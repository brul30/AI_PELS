from django.shortcuts import render
from rest_framework.decorators import api_view
from rest_framework.response import Response
import hashlib
import time
import requests
import json
from pels.env import config
import os

@api_view(['POST'])
def send_audio_to_speechsuper(request):
    print("new request just sent")
    audio_file = request.FILES.get('audioFile')
    if not audio_file:
        print("no audio")


    refText = request.data['refText']
    print(refText)
    appKey = config("SPEECH_SUPER_APP_KEY", default='none')
    secretKey = config("SPEECH_SUPER_SECRET_KEY", default='none')
    baseURL = "https://api.speechsuper.com/"


    # if audio_file:
    #         save_directory = 'recordings' 
    #         if not os.path.exists(save_directory):
    #             os.makedirs(save_directory) 

    #         file_path = os.path.join(save_directory, 'audio.wav')
    #         with open(file_path, 'wb') as file:
    #             for chunk in audio_file.chunks():
    #                 file.write(chunk)

    #         print(f'Audio file saved at: {file_path}')


    timestamp = str(int(time.time()))

    coreType = "word.eval" # Change the coreType according to your needs.
    #refText = "carpet" # Change the audio path corresponding to the reference text.
    audioType = "wav" # Change the audio type corresponding to the audio file.
    audioSampleRate = 16000
    userId = "guest"

    url =  baseURL + coreType
    connectStr = (appKey + timestamp + secretKey).encode("utf-8")
    connectSig = hashlib.sha1(connectStr).hexdigest()
    startStr = (appKey + timestamp + userId + secretKey).encode("utf-8")
    startSig = hashlib.sha1(startStr).hexdigest()

    # Prepare the data to send to SpeechSuper
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

    #print("params",params)

    # Send the data to the SpeechSuper API
    datas = json.dumps(params)
    data = {'text': datas}
    headers = {"Request-Index": "0"}
    files = {"audio": audio_file}
    
    #print("datas", datas)
    res = requests.post(url, data=data, headers=headers, files=files)
    #print({'response': res.text.encode('utf-8', 'ignore').decode('utf-8')})
    #return Response({'response': res.text.encode('utf-8', 'ignore').decode('utf-8')})


    response_data = json.loads(res.text)

    # Extract the "phonics" information
    phonics = response_data.get('result', {}).get('words', [])[0].get('phonics', [])

    # Prepare the response with only the "phonics" information
    response_phonics = [
        {
            "spell": item.get("spell"),
            "phoneme": item.get("phoneme"),
            "overall": item.get("overall"),
        }
        for item in phonics
    ]

    return Response({"phonics": response_phonics})