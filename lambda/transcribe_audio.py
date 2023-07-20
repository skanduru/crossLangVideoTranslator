import os
import time
import sys
import json
import boto3
import logging
import botocore

# Configure logging settings
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def start_transcription_job(bucket, job_name, job_uri, language, service_role_arn):
    transcribe = boto3.client('transcribe')

    try:
        response = transcribe.start_transcription_job(
            TranscriptionJobName=job_name,
            Media={'MediaFileUri': job_uri},
            MediaFormat='mp3',
            LanguageCode=language,
            OutputBucketName=bucket,
            Settings={
                "ShowSpeakerLabels": True,
                "MaxSpeakerLabels": 2
            },
            ServiceRoleArn=service_role_arn,
        )
        return response['TranscriptionJob']['TranscriptionJobName']
    except botocore.exceptions.BotoCoreError as error:
        print(f"Error starting transcription job: {error}")
        return None


def handler(event, context):
    # Extract bucket and video key from the event payload
    bucket = event['bucket']
    media = event['media']

    region_name = 'us-west-1'
    logging.info(f"L: Received {media} for transcription")

    # Use Amazon Transcribe to transcribe the audio
    language_code = os.environ["LANGUAGE_CODE"]  # Source lang code
    target_language_code = os.environ["TARGET_LANGUAGE_CODE"]  # Dst lang code

    job_name = "tel2engTranscription".format(int(time.time()))
    job_uri  = f"s3://{bucket}/{media}"
    # Transcribe the audio from Telugu to English
    service_role_arn = os.environ.get('TRANSCRIBE_ROLE_ARN')
    jobName = start_transcription_job(bucket, job_name, job_uri, language_code, service_role_arn)
    logging.info(f"L: Transcription started: {jobName}")
    return  jobName
