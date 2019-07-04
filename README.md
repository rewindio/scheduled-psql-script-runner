# scheduled-psql-script-runner
AWS Lambda function which runs postgres scripts against RDS on one of 3 predefined schedules (daily,weekly,monthly)

# Setup
The solution is packaged in a cloudformation template which creates the Lambda, an S3 bucket and the scheduled events.  The function can be deployed by using the helper script `package-and-deploy.sh` .  It takes the following positional arguments:

1. S3 bucket to upload the Lambda function code to
2. Bucket which will be created to hold the SQL queries and results
3. Database endpoint (available from the RDS console)
4. Database name
5. Database user
6. Name of an AWS Parameter store SecureString parameter that contains the database password
7. ID of the VPC to create the Lambda function in
8. ID of a subnet in the VPC to run the Lambda function in
9. Security group to associate with the Lambda function.  It must be allowed to access the database

Before running the package script you *MUST* download the Lambda-specfic version of the Python psycopg2 module from here and put into the `src` folder:  https://github.com/jkehler/awslambda-psycopg2


# Usage

Within the S3 bucket created by the cloudformation stack, create the following tree:

scripts
    |
    |--daily
    |--hourly
    |--weekly

Place any scripts you wish to have executed on the desired frequency into the respective folder.  Scripts should be named with a `.sql` extension and should *NOT* contain a trailing `;` as a query terminator

Results will be placed into a `results` folder in the same bucket, broken out by frequency and script name
