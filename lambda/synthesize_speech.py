import logging
import boto3
import json
import os

def synthesize_speech(event, context):
    # Extract bucket and english text from the event payload
    bucket = event['bucket']
    english_text = event['synth_file']

    # Create an Amazon polly client
    polly = boto3.client('polly')

    # Set the voice to a 60-year old man
    voiceId = 'Mathew'

    logging.info(f"received {english_text} for synthesis")

    try:
        response = polly.synthesize_speech(
            Text=english_text,
            OutputFormat='mp3',
            VoiceId=voiceId
        )

        # Get the audio stream from the response
        audio_stream = response['AudioStream'].read()
        # Save the audio stream to a file with the same name as input-text
        # but with .mp3 extension
        output_filename = os.path.splitext(input_text)[0] + '.mp3'
        with open(output_filename, 'wb') as file:
            file.write(audio_stream)

        logging.info(f"Audio stream saved as '{output_filename}'")

        # Return the name of the audio stream
        return output_filename, None

    except Exception as e:
        error = f"Error occurred during speech synthesis: {str(e)}"
        logging.info(error)
        return None, error



def synthesize_speech(event, context):
    # Extract the input text from the event payload
    input_text = event['input_text']

    # Create an Amazon Polly client
    polly_client = boto3.client('polly')

    # Set the voice ID and output format
    voice_id = 'Matthew'
    output_format = 'mp3'

    try:
        # Synthesize speech
        response = polly_client.synthesize_speech(
            Text=input_text,
            VoiceId=voice_id,
            OutputFormat=output_format
        )

        # Get the output URI of the synthesized audio
        output_uri = response['AudioStream'].name

        # Publish a message to an SNS topic with the output URI
        sns_client = boto3.client('sns')
        topic_arn = 'your-sns-topic-arn'
        message = json.dumps({'output_uri': output_uri})
        sns_client.publish(TopicArn=topic_arn, Message=message)

        return None

    except Exception as e:
        error_message = f"Error occurred during speech synthesis: {str(e)}"
        return error_message
