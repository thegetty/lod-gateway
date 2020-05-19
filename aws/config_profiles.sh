#!/bin/bash

aws configure set aws_access_key_id $ECR_ACCESS_KEY_ID --profile getty
aws configure set aws_secret_access_key $ECR_SECRET_ACCESS_KEY --profile getty
aws configure set region $ECR_REGION --profile getty

aws configure list --profile getty