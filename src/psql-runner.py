import os
import json
import tempfile
import datetime
import boto3
from boto3.s3.transfer import S3Transfer
from botocore.exceptions import ClientError
import psycopg2
import pprint

from db_util import make_conn, fetch_data, fetch_data_to_file

ssm_client = boto3.client('ssm')
s3_client  = boto3.client("s3")

def get_invoked_frequency(event):
    frequency = None
    
    if 'frequency' in event:
        frequency = event['frequency']
        
    return frequency
    
def get_db_password():
    db_password = None
    
    print("Obtaining the DB password from parameter store path {}".format(os.environ['DB_PASS_ARN']))
    
    try:
        response = ssm_client.get_parameter(
            Name=os.environ['DB_PASS_ARN'],
            WithDecryption=True
        )
        db_password = response['Parameter']['Value']
        print("Successfully obtained the DB password from parameter store")
    except ClientError as ex:
        print("Unable to obtain DB passsword: {}".format(ex.response['Error']['Code']))
        
    return db_password
    
def get_db_conn(db_password):
    conn = None
    db_host = None
    db_name = None
    db_user = None
    
    if 'DB_HOST' in os.environ:
        db_host = os.environ['DB_HOST']
        
    if 'DB_NAME' in os.environ:
        db_name = os.environ['DB_NAME']
        
    if 'DB_USER' in os.environ:
        db_user = os.environ['DB_USER']
        
    if db_host and db_name and db_user:
        print("Attempting to connect to DB [host={} name={} user={} pass=******]".format(db_host,db_name,db_user))
    
        conn = make_conn(os.environ['DB_HOST'],os.environ['DB_NAME'],os.environ['DB_USER'],db_password)
    else:
        print("Missing database config.  Ensure DB_HOST, DB_NAME and DB_USER are defined in the environment")
        
    return conn

def get_script_file_names(frequency):
    filenames = []
    
    script_prefix = 'scripts/' + frequency + '/'
        
    try:
        response = s3_client.list_objects(
            Bucket=os.environ['S3_BUCKET'],
            MaxKeys=1000,
            Prefix=script_prefix
        )
    except ClientError as ex:
        print("Unable to list scripts in S3: {}".format(ex.response['Error']['Code'])) 
        
    if 'Contents' in response:
        bucket_content = response['Contents']
        
        # There is always an item in the list for the "folder"
        if len(bucket_content) > 1:
            for item in bucket_content:
                if item['Key'] != script_prefix:
                    filenames.append(item['Key'])
            
        if 'DEBUG' in os.environ:
            pprint.pprint(filenames)
        
    return filenames
    
def read_file_from_s3(bucket, key):
    object_content = None
    
    print("Attempting to read {} from bucket {}".format(key, bucket))
    
    try:
        s3_response_object = s3_client.get_object(Bucket=bucket, Key=key)
        object_content = s3_response_object['Body'].read().decode('utf-8')
    except ClientError as ex:
        print("Unable to read file from S3: {}".format(ex.response['Error']['Code'])) 
        
    return object_content
    
def write_results_to_s3(bucket, frequency, dt_str, script, output_filename):
    script_name = script.rsplit('/',1)[1].split('.')[0]
    output_key = 'results/' + frequency + '/' + script_name + '/' + script_name + '-results_' + dt_str + '.csv'
    
    print("Writing results to {} in S3 bucket {}".format(output_key, bucket))
    
    try:
        transfer = S3Transfer(s3_client)
        transfer.upload_file(output_filename, bucket, output_key, extra_args={'ServerSideEncryption': "AES256"})
    except ClientError as ex:
        print("Unable to write to S3: {}".format(ex.response['Error']['Code'])) 
    
def run_scripts(frequency):
    db_password = None
    ret_code = 0
    db_conn = None
    s3_bucket = os.environ['S3_BUCKET']
    
    print("Running all scripts scheduled for the {} time slot".format(frequency))
    script_file_names = get_script_file_names(frequency)
    
    if len(script_file_names) > 0:
        db_password = get_db_password()
    
        if db_password:
            db_conn = get_db_conn(db_password)
        
            if db_conn:
                print("Successfully obtained a database connection")
                
                # Get the current date-time for outputing the results
                now = datetime.datetime.now()
                dt_str = str(now.year) + now.strftime('%m') + now.strftime('%d') + '_' + now.strftime('%H') + now.strftime('%M')
    
                for script in script_file_names:
                    print("Running script: {}".format(script))
                    sql = read_file_from_s3(s3_bucket, script)
                    
                    # The DB query results are written to a file in CSV format
                    results_file = tempfile.NamedTemporaryFile(mode='w')
                    fetch_data_to_file(db_conn, sql, results_file.name)
                    
                    write_results_to_s3(s3_bucket, frequency, dt_str, script, results_file.name)
                    
                    results_file.close()
                
                db_conn.close()
            else:
                print("ERROR: Unable to connect to the database")
                ret_code = 1
        else:
            print("ERROR: No DB password, unable to continue")
            ret_code = 1
            
    return ret_code
        
def lambda_handler(event, context):
    ret_code = 0
    frequency = None
    
    if 'DEBUG' in os.environ:
        print("Received event: " + json.dumps(event, indent=2))
        
    if 'S3_BUCKET' in os.environ:
        frequency = get_invoked_frequency(event)
        
        if frequency == 'daily':
            ret_code = run_scripts('daily')
        elif frequency == 'weekly':
            ret_code = run_scripts('weekly')
        elif frequency == 'monthly':
            ret_code = run_scripts('monthly')
        else:
            print("Unhandled frequency [{}] found in event - no handlder".format(frequency))
            ret_code = 1
    else:
        print("No S3_BUCKET environment variable configured - unable to continue")
        ret_code = 1
    
    return ret_code