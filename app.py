#!/usr/bin/env python3.11

import os
from aws_cdk import (
    aws_s3 as s3,
    aws_lambda as _lambda,
    aws_s3_notifications as s3_notif,
    aws_iam as iam,
)
import aws_cdk as cdk
from constructs import Construct
import boto3


class TeluguToEnglishTranscriptionStack(cdk.Stack):
    def __init__(self, scope: Construct, id: str, **kwargs) -> None:
        super().__init__(scope, id, **kwargs)

        # S1. Create an S3 bucket to store the audio file
        audio_bucket = s3.Bucket(self, "transcribeBucket")

        transcribe_role = iam.Role(
            self,
            "TranscribeAccessRole",
            assumed_by=iam.ServicePrincipal("transcribe.amazonaws.com"),
        )

        transcribe_role.add_managed_policy(
            iam.ManagedPolicy.from_aws_managed_policy_name('AmazonTranscribeFullAccess')
        )

        # S2. Create a Lambda function to trigger the transcription process
        """
         a. Make sure there is a directory called 'lambda'
         b. With 'lambda' directory create a file called 'transcribe_audio.py'
         c. In 'transcription_lambda.py' use boto3 to AWS transcribe
        """
        transcription_lambda = _lambda.Function(
            self,
            "TranscriptionLambda",
            runtime=_lambda.Runtime.PYTHON_3_8,
            handler="transcribe_audio.handler",
            code=_lambda.Code.from_asset("lambda"),
            environment={
                "AUDIO_BUCKET_NAME": audio_bucket.bucket_name,
                "LANGUAGE_CODE": "te-IN",  # Telugu language code
                "TARGET_LANGUAGE_CODE": "en-US",  # English language code
                "TRANSCRIBE_ROLE_ARN": transcribe_role.role_arn
            }
        )
        function_id = "TranscriptionLambda"
        self.create_parameter("myapplication", function_id, transcription_lambda.function_name)

        audio_bucket.grant_read(transcribe_role)
        audio_bucket.grant_read_write(transcription_lambda.role)
        
        transcribe_role.add_to_policy(
            iam.PolicyStatement(
                actions=["s3:GetObject", "s3:PutObject"],
                resources=[f"arn:aws:s3:::{audio_bucket.bucket_name}/*"]
            )
        )

        transcribe_policy = iam.PolicyStatement(
            actions=["transcribe:StartTranscriptionJob",
                     "transcribe:GetTranscriptionJob"],
            resources=["*"])

        transcription_lambda.add_to_role_policy(transcribe_policy)


        # Grant the Lambda function permission to access the S3 bucket
        audio_bucket.grant_read(transcription_lambda)

        translate_lambda = _lambda.Function(
            self,
            "TranslateLambda",
            runtime=_lambda.Runtime.PYTHON_3_8,
            handler="translate_text.handler",
            code=_lambda.Code.from_asset("lambda"),
            environment={
                "AUDIO_BUCKET_NAME": audio_bucket.bucket_name,
                "LANGUAGE_CODE": "te-IN",  # Telugu language code
                "TARGET_LANGUAGE_CODE": "en-US"  # English language code
            }
        )
        function_id = "TranslateLambda"
        self.create_parameter("myapplication", function_id, translate_lambda.function_name)

        # Set up an S3 event trigger for the Lambda function
        audio_bucket.add_event_notification(
            s3.EventType.OBJECT_CREATED,
            s3_notif.LambdaDestination(transcription_lambda),
            s3.NotificationKeyFilter(prefix="translated/")
        )

        # S3. Create a Lambda function to trigger the synthesis process
        """
         a. Make sure there is a directory called 'lambda'
         b. With 'lambda' directory create a file called 'synthesize_speech.py'
         c. In 'synthesize_speech.py' use boto3 to AWS polly
        """
        SynthesizeLambda = _lambda.Function(
            self,
            "SynthesizeLambda",
            runtime=_lambda.Runtime.PYTHON_3_8,
            handler="synthesize_speech.synthesize_speech",
            code=_lambda.Code.from_asset("lambda"),
            environment={
                "AUDIO_BUCKET_NAME": audio_bucket.bucket_name,
                "LANGUAGE_CODE": "te-IN",  # Telugu language code
                "TARGET_LANGUAGE_CODE": "en-US"  # English language code
            }
        )
        function_id = "SynthesizeLambda"
        self.create_parameter("myapplication", function_id, SynthesizeLambda.function_name)


        # Grant the Lambda function permission to access the S3 bucket
        audio_bucket.grant_read(SynthesizeLambda)

        # Set up an S3 event trigger for the Lambda function
        audio_bucket.add_event_notification(
            s3.EventType.OBJECT_CREATED,
            s3_notif.LambdaDestination(SynthesizeLambda),
            s3.NotificationKeyFilter(prefix="audio/")
        )

    def create_parameter(self, app_name, function_id, function_name):
        from aws_cdk import aws_ssm as ssm
    
        param_name = f"/{app_name}/{function_id}FunctionName"
    
        ssm.StringParameter(
            self,
            f"{function_id}FunctionNameParam",
            parameter_name=param_name,
            string_value=function_name
        )
    
        return param_name



app = cdk.App()
TeluguToEnglishTranscriptionStack(app, "TeluguToEnglishTranscription")
app.synth()

