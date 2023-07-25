#!/usr/bin/env python3.11

import os
from aws_cdk import (
    aws_s3 as s3,
    aws_lambda as _lambda,
    aws_iam as iam,
    aws_logs as aws_logs,
    aws_ssm as ssm,
    aws_sns as sns,
    aws_sns_subscriptions as sns_subs
)
import aws_cdk as cdk
from constructs import Construct
import boto3


class TeluguToEnglishTranscriptionStack(cdk.Stack):
    def __init__(self, scope: Construct, id: str, **kwargs) -> None:
        super().__init__(scope, id, **kwargs)

        # Bucket creation
        audio_bucket = s3.Bucket(self, "TranscribeBucket", bucket_name="transcription-bucket")

        # Save the bucket_name in ssm to be retrieved in the runscript.
        ssm.StringParameter(
            self,
            "BucketNameParameter",
            parameter_name="BucketName",
            string_value=audio_bucket.bucket_name
        )

        # Creating single role for all Lambda functions
        lambda_role = iam.Role(
            self,
            "LambdaRole",
            assumed_by=iam.ServicePrincipal("lambda.amazonaws.com"),
        )

        # Add policies to the role
        lambda_role.add_managed_policy(iam.ManagedPolicy.from_aws_managed_policy_name('AmazonTranscribeFullAccess'))
        lambda_role.add_managed_policy(iam.ManagedPolicy.from_aws_managed_policy_name('service-role/AWSLambdaBasicExecutionRole'))
        lambda_role.add_managed_policy(iam.ManagedPolicy.from_aws_managed_policy_name('TranslateReadOnly'))

        # Custom PolicyStatement for S3 and Polly
        lambda_role.add_to_policy(
            iam.PolicyStatement(
                actions=["s3:GetObject", "s3:PutObject", "s3:ListBucket", "polly:SynthesizeSpeech"],
                resources=[f"{audio_bucket.bucket_arn}/*", f"arn:aws:polly:us-west-1:{cdk.Aws.ACCOUNT_ID}:lexicon/*"]
            )
        )

        # Transcription Lambda
        transcription_lambda = self.create_lambda_function(audio_bucket, "TranscriptionLambda", "transcribe_audio.handler")

        # Translate Lambda
        translate_lambda = self.create_lambda_function(audio_bucket, "TranslateLambda", "translate_text.handler")

        # Synthesize Lambda
        synthesize_lambda = self.create_lambda_function(audio_bucket, "SynthesizeLambda", "synthesize_speech.synthesize_speech")

    def create_lambda_function(self, audio_bucket, function_id, handler):

        lambda_role = iam.Role(
            self,
            f"{function_id}LambdaRole",
            assumed_by=iam.ServicePrincipal("lambda.amazonaws.com"),
        )

        lambda_func = _lambda.Function(
            self,
            function_id,
            runtime=_lambda.Runtime.PYTHON_3_8,
            handler=handler,
            code=_lambda.Code.from_asset("lambda"),
            role=lambda_role,  # Use common role
            environment={
                "AUDIO_BUCKET_NAME": audio_bucket.bucket_name,
                "LANGUAGE_CODE": "te-IN",
                "TARGET_LANGUAGE_CODE": "en-US"
            }
        )

        self.create_parameter("myapplication", function_id, lambda_func)

        return lambda_func

    def create_parameter(self, app_name, function_id, lambda_func):

        param_name = f"/{app_name}/{function_id}FunctionName"

        ssm_parameter = ssm.StringParameter(
            self,
            f"{function_id}FunctionNameParam",
            parameter_name=param_name,
            string_value=lambda_func.function_name
        )

        # Assume that lambda_function is an instance of lambda_.Function
        ssm_parameter.grant_read(lambda_func.role)

        return param_name


app = cdk.App()
TeluguToEnglishTranscriptionStack(
   app,
   "TeluguToEnglishTranscription",
   env=cdk.Environment(region='us-west-1')
)
app.synth()
