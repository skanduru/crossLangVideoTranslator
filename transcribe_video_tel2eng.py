
import boto3
import time
import subprocess
import requests
import logging
import json
import os
import sys
import re
from botocore.exceptions import BotoCoreError, ClientError

####################################
# Configuration
####################################
MY_REGION = 'us-west-1'
STEP_SIZE = 6
CONFIDENCE = '0.0'  # valid words seen for confidence of 0.043
MAXLINE_LEN = 90

# Configure logging settings
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Specify the S3 bucket name
# bucket_name = 'transcribeBucket'

# Specify the local video file path
audiodir = "./audio/"
dir = "./mediadir/"
outputdir = "./output/"
# telugu_video = 'CongressAchievement.mp4'
telugu_video = '2_20.mp4'
input_video_path = dir + telugu_video
video_only = dir + "video_only.mp4"
base_audio_input = "telugu_audio.mp3"
audio_only = dir + base_audio_input
audio_file = 'english_audio.mp3'
audio_path = outputdir + audio_file
english_video = 'english_video.mp4'
output_video_path = outputdir + english_video
t_text = 'telugu_text.txt'
telugu_text = outputdir + t_text
e_trans = 'english_text.txt'
english_text = outputdir + e_trans
myapp = "myapplication"

####################################
# Utility functions
####################################


def retrieve_audio_bucket():
    bucket = None
    s3 = boto3.client('s3')

    # Get a list of all bucket names
    buckets = s3.list_buckets()
    bucket_names = [bucket['Name'] for bucket in buckets['Buckets']]

    # Define a regular expression pattern for your bucket name
    pattern = re.compile(r'^telugutoenglishtranscrip-transcribebucket')

    # For each bucket name, check if it matches the regular expression
    for bucket_name in bucket_names:
        if pattern.match(bucket_name):
            print(f'The bucket you are looking for is: {bucket_name}')
            break
    return bucket_name


def convert_time_to_hh_mm_ss(seconds):
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    seconds = seconds % 60

    return f'{hours:02d}:{minutes:02d}:{seconds:02d}'

def align_sentences(items, step_size):
    aligned_sentences = []
    current_sentence = []
    curline_len = 0
    current_time = 0.0
    start_time = 0.00
    for item in items:
        if 'start_time' in item:
            item_start_time = float(item['start_time'])
            # if start_time is None:
            #    start_time = item_start_time  # start time of the current_sentence
            if item_start_time - start_time > step_size or curline_len > MAXLINE_LEN:
                # aligned_sentences.append((start_time, " ".join(current_sentence)))
                aligned_sentences.append({"time": start_time, "line": " ".join(current_sentence)})
                current_sentence = []
                curline_len = 0
                start_time = item_start_time
            current_time = item_start_time
        if item['type'] == 'pronunciation':
            if 'alternatives' in item and item['alternatives'][0]['confidence'] > CONFIDENCE:
                current_sentence.append(item['alternatives'][0]['content'])
                curline_len += len(item['alternatives'][0]['content']) + 1
        elif item['type'] == 'punctuation':
            if current_sentence and item['alternatives'][0]['confidence'] > CONFIDENCE:  # check if current_sentence is not empty
                current_sentence[-1] += item['alternatives'][0]['content']
                curline_len += len(item['alternatives'][0]['content']) + 1
    if current_sentence:
        # aligned_sentences.append((start_time, " ".join(current_sentence)))
        aligned_sentences.append({"time": start_time, "line": " ".join(current_sentence)})
    return aligned_sentences


def get_transcription_job(job_name):
    # Create a transcribe client
    transcribe = boto3.client("transcribe")

    if job_name is None:
        print("No transcription job to get status for")
        return None, None

    try:
        response = transcribe.get_transcription_job(TranscriptionJobName=job_name)
        transcript_uri = response['TranscriptionJob']['Transcript']['TranscriptFileUri']
        return response['TranscriptionJob']['TranscriptionJobStatus'], transcript_uri
    except BotoCoreError as error:
        print(f"Error getting transcription job status: {error}")
        return None, None

def transcribe_job(job_name, src_text):
    # Wait for transcription to complete (Transcription already started by a lambda)
    while True:
        jobstatus, transcript_uri = get_transcription_job(job_name)
        if jobstatus in ['COMPLETED', 'FAILED']:
            break
        time.sleep(10)

    # 3b. Processing the transcription job result
    if jobstatus == 'COMPLETED':
        logging.info(f"Transcription completed, extracting {src_text}...")
        response = requests.get(transcript_uri)
        result = json.loads(response.text)
        items = result['results']['items']
        lines = align_sentences(items, STEP_SIZE)
        with open(src_text, 'w') as f:
            for item_line in lines:
                time_in_hh_mm_ss = convert_time_to_hh_mm_ss(int(item_line["time"]))
                f.write(f'{time_in_hh_mm_ss}: {item_line["line"]}\n')
        logging.info(f'Transcript has been saved to {src_text}')
    elif jobstatus == 'FAILED':
        logging.info("Transcription failed")
    else:
        logging.info("Transcription still in progress")

    return src_text


def remove_timecode(input_file):
    output_file = re.sub(r'\..*', '_no_tc.txt', input_file)
    with open(input_file, 'r') as file:
        lines = file.readlines()

    with open(output_file, 'w') as file:
        for line in lines:
            line = line.split(': ', 1)[-1]  # Remove the timecode at the beginning
            file.write(line)

    logging.info(f"Timecode removed. Result saved in '{output_file}'")
    return output_file

# ffmpeg -i telugu_video -c:v copy -map 0:v -c:a copy -map 0:a output_video.mp4 -c:a copy -map 0:a telugu_audio.mp3
# ffmpeg -i audio_video.mp4 -c:v copy -an video_only.mp4 -vn -c:a libmp3lame -q:a 2 audio_only.mp3
def split_video_audio(input_path, video_path, audio_path):
    # Run FFmpeg command to split video and audio
    # ffmpeg -i audio_video.mp4 -c:v copy -an video_only.mp4 -vn -c:a libmp3lame -q:a 2 audio_only.mp3
    ffmpeg_cmd = [
        'ffmpeg',
        '-i', input_path,
        '-c:v', 'copy',
        '-an', video_path,
        '-vn',
        '-c:a', 'libmp3lame',
        '-map', '0:a',
        '-q:a', "2",
        audio_path
    ]

    subprocess.run(ffmpeg_cmd, check=True)

# Combinee
def combine_video_audio(video_path, audio_path, output_path, offset = None):
    # Run FFmpeg command to combine video and audio
    ffmpeg_cmd = [
        'ffmpeg',
        '-i', video_path,
        '-i', audio_path,
        '-c:v', 'copy',
        '-c:a', 'aac',
        '-map', '0:v:0',
        '-map', '1:a:0',
        # '-itsoffset', offset,
        '-shortest',
        output_path
    ]

    subprocess.run(ffmpeg_cmd, check=True)

def get_lambda_function_name(app_name, function_id):
    ssm_client = boto3.client('ssm')
    
    param_name = f"/{app_name}/{function_id}FunctionName"
    
    try:
        response = ssm_client.get_parameter(
            Name=param_name,
            WithDecryption=True
        )
    except (BotoCoreError, ClientError) as error:
        print(error)
        raise error
    else:
        return response['Parameter']['Value']


####################################
# End of Utility functions
####################################

s3_client = boto3.client('s3')
lambda_client = boto3.client('lambda')


def process_audio_bucket(bucket_name):
    # Split multimedia into video and audio only
    split_video_audio(input_video_path, video_only, audio_only)

    # get the S3 bucket

    # Upload the video file to the S3 bucket
    s3_client.upload_file(audio_only, bucket_name, audio_only)

    logging.info(f"Audio upload of {input_video_path} completed.")

    event = {
        "bucket": bucket_name,
        "media": audio_only,
        "transcript_file": telugu_text,
        "dir": dir,
        "src_lang": "te-IN",
        "dst_lang": "en-US",
    }

    # Invoke the transcribe_audio Lambda function for telugu text availability
    function_name = get_lambda_function_name(myapp, "TranscriptionLambda")
    response = lambda_client.invoke(
        FunctionName=function_name,
        InvocationType='RequestResponse',
        Payload=json.dumps(event)
    )

    # Check if the response indicates completion
    payload = response['Payload'].read().decode('utf-8')
    resp = json.loads(payload)  # Convert the JSON string to a Python object
    if response['StatusCode'] == 200:

        # Get the transcript file for the target language
        job_name = resp
        transcript_file =  transcribe_job(job_name, telugu_text)
    else: 
        logging.error(f"Received error: {response['StatusCode']}: {resp}")
        sys.exit(1)

    # Next do the translation (telugu) to (english)
    telugu_file = transcript_file

    event = {
        "bucket": bucket_name,
        "src_text": telugu_text,
        "dst_text": english_text,
        "dir": dir,
        "src_lang": "te-IN",
        "dst_lang": "en-US",
    }

    # Invoke the translate_text Lambda function for telugu to English text
    function_name = get_lambda_function_name(myapp, "TranslateLambda")
    response = lambda_client.invoke(
        FunctionName=function_name,
        InvocationType='RequestResponse',
        Payload=json.dumps(event)
    )

    # Check if the response indicates completion
    payload = response['Payload'].read().decode('utf-8')
    resp = json.loads(payload)  # Convert the JSON string to a Python object
    pprint(response)
    if response['StatusCode'] != 200:
        logging.error(f"Received error: {response['StatusCode']}: {resp}")
        sys.exit(1)

    # Now trigger the synthesis
    synth_file = remove_timecode(english_text)
    event = {
        "bucket": bucket_name,
        "synth_file": synth_file,
    }

    # Upload file to be synthesized
    s3_client.upload_file(synth_file, bucket_name, os.basename(synth_file))

    # Poll the synthesize_video Lambda function for audio stream availability
    function_name = get_lambda_function_name(myapp, "SynthesizeLambda")
    response = lambda_client.invoke(
        FunctionName=function_name,
        InvocationType='RequestResponse',
        Payload=json.dumps(event)
    )

    # Check if the response indicates completion
    if response['StatusCode'] == 200:
        payload = response['Payload'].read().decode('utf-8')
        result = json.loads(payload)
        if result[0] is None:
            logging.error(f"Error occurred: {result[1]}")
            sys.exit(2)

    # jobId = response['SynthesisTask']['TaskId']
    outputUri = response['SynthesisTask']['OutputUri']
    # if 'status' in response_payload and response_payload['status'] == 'completed':
    # English text is available, download it
    s3_client.download_file(bucket_name, os.path.basename(outputUri), audio_path)
    logging.info("Audio synthesis completed.")


    combine_video_audio(video_only, audio_path, output_video_path, offset = english_text)

    logging.info("English video creation completed.")


bucket_name = retrieve_audio_bucket()
process_audio_bucket(bucket_name)

