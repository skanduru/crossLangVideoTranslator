
import os
import time
import sys
import json
import boto3
import logging

# Configure logging settings
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


def handler(event, context):
    logging.info(f"entering function translate_handler")

    # Check if necessary keys are present
    if not all(key in event for key in ('bucket', 'src_text', 'dst_text')):
        logging.error("Necessary keys not present in the event")
        return

    # Extract bucket and video key from the event payload
    bucket = event['bucket']
    src_text = event['src_text']
    dst_text = event['dst_text']

    # Check if source and destination texts are not same
    if src_text == dst_text:
        logging.error("Source and destination texts are same")
        return

    region_name = 'us-west-1'
    logging.info(f"L: Received {media} for transcription")

    # Use Amazon Transcribe to transcribe the audio
    language_code = os.environ["LANGUAGE_CODE"]  # Source lang code
    target_language_code = os.environ["TARGET_LANGUAGE_CODE"]  # Dst lang code

    s3 = boto3.client('s3', region_name = region_name)
    translate = boto3.client("translate", region_name = region_name)

    # Get source language text from the file in S3
    try:
        response = s3.get_object(Bucket=bucket, Key=src_text)
        src_content = response["Body"].read().decode('utf-8')
    except Exception as e:
        logging.error(f"Error while getting the object from S3: {e}")
        return

    # Translate the text from src to dst lang
    try:
        response = translate.translate_text(
            Text = src_content,
            SourceLanguageCode=language_code,
            TargetLanguageCode=target_language_code
        )
        dst_content = response.get('TranslatedText')
    except Exception as e:
        logging.error(f"Error while translating the text: {e}")
        return

    # Save the translated text to a new file in S3
    try:
        s3.put_object(Bucket=bucket, Key=dst_text, Body=dst_content.encode('utf-8'))
    except Exception as e:
        logging.error(f"Error while putting the object in S3: {e}")
        return

    logging.info(f"L: Translation done: {dst_text}")

    # Return the name of the English text file
    return dst_text

