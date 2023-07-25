# Welcome to Cross-Video Translation Project

This project translates videos from Telugu to English using Amazon Web Services (AWS). The project consists of five main steps, each of which leverages a different AWS service:

1. **upload_video**: This step uploads the input Telugu video file to an Amazon S3 bucket. S3 is a scalable object storage service that allows for easy retrieval of data. Make sure the video files are in the supported format and AWS has the necessary permissions to access and upload the file.

2. **transcribe_audio**: This step uses Amazon Transcribe, an automatic speech recognition (ASR) service, to transcribe the audio from the Telugu video. The transcription results are saved as a JSON file. Ensure that the audio quality is good and the speech is clear to improve the accuracy of the transcription.

3. **translate_text**: This step uses Amazon Translate, a neural machine translation service, to translate the Telugu transcript into English. Ensure that the input text (transcription from the previous step) is in a structured and clear format for best translation results.

4. **synthesize_speech**: This step uses Amazon Polly, a text-to-speech service, to synthesize English speech from the translated text and returns an audio stream. Pay attention to the selected voice and speech speed to ensure natural-sounding speech.

5. **create_english_video**: This final step combines the original Telugu video and the English audio using FFmpeg to create the final English video. Ensure that the audio and video are properly synchronized.

The project has been tested with Python 3.11 and AWS Cloud Development Kit (CDK) v2.

The `cdk.json` file tells the AWS CDK Toolkit how to execute your application. This file includes information about the necessary dependencies and environment settings, as well as the instructions for deployment.

## Prerequisites

Ensure that you have the following installed on your machine before you proceed:

- Python 3.11
- Node.js 10.3.0 or later
- AWS CDK v2

## Setting Up

1. Install the necessary Python packages:

    ```bash
    python3 -m venv .env
    source .env/bin/activate
    pip install -r requirements.txt
    ```

3. Bootstrap the project in the target environment:

    ```bash
    cdk bootstrap
    ```

4. Deploy the project:

    ```bash
    cdk deploy
    ```

Remember to replace any placeholders in the code with your specific AWS resource names and IAM roles.

## Testing

python3.11 transcribe_video_tel2eng.py

## Troubleshooting

If you face issues while executing the project, check the AWS CloudWatch Logs for error messages. Make sure the IAM roles and policies are correctly set to give AWS services the required permissions.

To check the lambda logs:

```bash
aws logs get-log-events --log-group-name "/aws/lambda/TranscriptionLambda --start '3h ago'" --log-stream-name "YourStreamName" --region us-west-1
```

to stream your logs directly to your console

```bash
aws logs tail /aws/lambda/YourFunctionName --follow --region us-west-1
```

```bash
awslogs get /aws/lambda/<MyLambdaFunction> --start='3h ago' --aws-region=us-west-1
```

