import os
import time
import sys
import json
import boto3
import logging

# Configure logging settings
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


def handler(event, context):
    # Extract bucket and video key from the event payload
    bucket = event['bucket']
    src_text = event['src_text']
    dst_text = event['dst_text']

    region_name = 'us-west-1'
    logging.info(f"L: Received {media} for transcription")

    # Use Amazon Transcribe to transcribe the audio
    language_code = os.environ["LANGUAGE_CODE"]  # Source lang code
    target_language_code = os.environ["TARGET_LANGUAGE_CODE"]  # Dst lang code

    s3 = boto3.client('s3')
    translate = boto3.client("translate", region_name = "us-west-1")

    # Get Telugu text from the file in S3
    response = s3.get_object(Bucket=bucket, Key=src_text)
    src_content = response["Body"].read().decode('utf-8')

    # Translate the text from src to dst lang
    response = translate.translate_text(
        Text = src_content,
        SourceLanguageCode=language_code,
        TargetLanguageCode=target_language_code
    )
    dst_content = result.get('TranslatedText')

    # Save the English text to a new file in S3
    s3.put_object(Bucket=bucket, Key=dst_text, Body=dst_content.encode('utf-8'))

    logging.info(f"L: Translation done: {dst_text}")

    # Return the name of the English text file
    return dst_text
