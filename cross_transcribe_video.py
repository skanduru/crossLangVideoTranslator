import json
import logging
import os
import re
import subprocess
import time
from pathlib import Path

import boto3
import requests
from botocore.exceptions import BotoCoreError, ClientError

# Configure logging settings
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

####################################
# Configuration
####################################
MY_REGION = 'us-west-1'
STEP_SIZE = 6
CONFIDENCE = '0.0'
MAXLINE_LEN = 90
MY_BUCKET_PATTERN = re.compile(r'^telugutoenglishtranscrip-transcribebucket')
MYAPP = "myapplication"

# Define Paths
BASE_DIR = Path(__file__).parent.absolute()
AUDIO_DIR = BASE_DIR / "audio"
MEDIA_DIR = BASE_DIR / "mediadir"
OUTPUT_DIR = BASE_DIR / "output"
TELUGU_VIDEO = MEDIA_DIR / '2_20.mp4'
VIDEO_ONLY = MEDIA_DIR / "video_only.mp4"
BASE_AUDIO_INPUT = "telugu_audio.mp3"
AUDIO_ONLY = MEDIA_DIR / BASE_AUDIO_INPUT
AUDIO_FILE = 'english_audio.mp3'
AUDIO_PATH = OUTPUT_DIR / AUDIO_FILE
ENGLISH_VIDEO = 'english_video.mp4'
OUTPUT_VIDEO_PATH = OUTPUT_DIR / ENGLISH_VIDEO
T_TEXT = 'telugu_text.txt'
TELUGU_TEXT = OUTPUT_DIR / T_TEXT
E_TRANS = 'english_text.txt'
ENGLISH_TEXT = OUTPUT_DIR / E_TRANS

# All the clients needed
ssm_client = boto3.client('ssm', region_name=MY_REGION)
s3_client = boto3.client('s3', region_name=MY_REGION)
lambda_client = boto3.client('lambda', region_name=MY_REGION)

# Further utility functions...

def split_video_audio(video_path, video_output, audio_output):
    subprocess.run(['ffmpeg', '-i', video_path, '-vcodec', 'copy', '-an', video_output])
    subprocess.run(['ffmpeg', '-i', video_path, '-acodec', 'pcm_s16le', '-ar', '16000', '-ac', '1', audio_output])

def remove_timecode(file_path):
    temp_file_path = file_path.with_stem(file_path.stem + "_temp")
    with file_path.open() as file, temp_file_path.open("w") as temp_file:
        for line in file:
            temp_file.write(re.sub(r'\s*-\s*\[\d+:\d+:\d+]\s*', ' ', line))
    file_path.unlink()  # Remove the original file
    temp_file_path.rename(file_path)  # Rename the temp file as the original file
    return file_path

def get_lambda_function_name(app, function):
    return app + "-" + function

def transcribe_job(job_name, output_file):
    time.sleep(5)
    while True:
        status = s3_client.head_object(Bucket=bucket_name, Key=job_name)
        if status['ResponseMetadata']['HTTPStatusCode'] == 200:
            s3_client.download_file(bucket_name, job_name, output_file)
            break
        time.sleep(5)

def combine_video_audio(video_input, audio_input, output_file):
    subprocess.run(['ffmpeg', '-i', video_input, '-i', audio_input, '-c:v', 'copy', '-c:a', 'aac', output_file])

def retrieve_bucket_name():
    response = ssm_client.get_parameter(Name='/myapp/s3bucket')
    bucket_name = response['Parameter']['Value']
    return bucket_name

def create_event(bucket_name, text_path, dir_path):
    return {
        "bucket": bucket_name,
        "media": str(AUDIO_ONLY),
        "transcript_file": text_path,
        "dir": dir_path,
        "src_lang": "te-IN",
        "dst_lang": "en-US",
    }

def invoke_lambda(lambda_id, event, output_path, transcribe=True):
    function_name = get_lambda_function_name(MYAPP, lambda_id)
    response = lambda_client.invoke(
        FunctionName=function_name,
        InvocationType='RequestResponse',
        Payload=json.dumps(event)
    )

    if response['StatusCode'] == 200:
        payload = response['Payload'].read().decode('utf-8')
        resp = json.loads(payload)
        if transcribe:
            job_name = resp
            transcribe_job(job_name, output_path)
    else:
        logging.error(f"Received error: {response['StatusCode']}: {resp}")
        sys.exit(1)

def process_audio_bucket(bucket_name):
    # Split multimedia into video and audio only
    split_video_audio(str(TELUGU_VIDEO), str(VIDEO_ONLY), str(AUDIO_ONLY))

    # Upload the video file to the S3 bucket
    s3_client.upload_file(str(AUDIO_ONLY), bucket_name, str(AUDIO_ONLY))
    logging.info(f"Audio upload of {TELUGU_VIDEO} completed.")

    event = create_event(bucket_name, str(TELUGU_TEXT), str(MEDIA_DIR))

    # Invoke the transcribe_audio Lambda function for Telugu text availability
    invoke_lambda("TranscriptionLambda", event, str(TELUGU_TEXT))

    # Invoke the translate_text Lambda function for Telugu to English text
    invoke_lambda("TranslateLambda", event, str(ENGLISH_TEXT))

    # Now trigger the synthesis
    synth_file = remove_timecode(ENGLISH_TEXT)

    event = {
        "bucket": bucket_name,
        "synth_file": str(synth_file),
    }

    # Upload file to be synthesized
    s3_client.upload_file(str(synth_file), bucket_name, os.path.basename(synth_file))

    # Poll the synthesize_video Lambda function for audio stream availability
    invoke_lambda("SynthesizeLambda", event, None, False)

    combine_video_audio(str(VIDEO_ONLY), str(AUDIO_PATH), str(OUTPUT_VIDEO_PATH))

    logging.info("English video creation completed.")

bucket_name = retrieve_bucket_name()
process_audio_bucket(bucket_name)
