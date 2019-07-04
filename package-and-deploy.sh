#!/bin/bash

LAMBDA_S3_BUCKET=$1
SQL_BUCKET=$2
DB_HOST=$3
DB_NAME=$4
DB_USER=$5
DB_PASS_NAME=$6
VPC=$7
SUBNET=$8
SG=$9

echo "Installing Python dependencies"
echo "Make sure you have downloaded https://github.com/jkehler/awslambda-psycopg2 into the src folder"

if [ ! -d "src/psycopg2" ]; then
    echo "ERROR! Please install psycopg2"
    exit 1
fi

echo "Packaging Lambda function for deploy"

aws cloudformation package \
    --template-file ./template.yml \
    --s3-bucket ${LAMBDA_S3_BUCKET} \
    --output-template-file packaged-template.yml

STATUS=$?

if [ "${STATUS}" -eq 0 ]; then
    echo "Deploying Lambda function to AWS"

    aws cloudformation deploy \
        --template-file ./packaged-template.yml \
        --capabilities CAPABILITY_IAM \
        --parameter-overrides \
            S3BucketName=${SQL_BUCKET} \
            DBHost=${DB_HOST} \
            DBName=${DB_NAME} \
            DBUser=${DB_USER} \
            DBPassSSMName=${DB_PASS_NAME} \
            VPCId=${VPC} \
            VPCSubnet=${SUBNET} \
            SecurityGroup=${SG} \
        --stack-name psql-script-runner-${DB_NAME}
else
    echo "Package step failed - not deploying function"
fi

