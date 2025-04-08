import json
import boto3
import pandas as pd
from io import StringIO
from sqlalchemy import create_engine

# AWS Region and Resource Names
REGION_NAME = "us-east-1"
SECRET_NAME = "prod/rds/salesdb_prod"
TOPIC_NAME = "dehtopic_load_local_data_to_RDS"
BUCKET_NAME = "dehlive-sales-{account_id}-{region}-raw"
CSV_KEY = "sales_rds_exercise_full.csv"  # Path in S3 bucket


def get_account_id():
    """
    Retrieves the AWS Account ID using STS.
    
    Returns:
        str: AWS Account ID
    """
    sts_client = boto3.client("sts")
    try:
        identity = sts_client.get_caller_identity()
        return identity["Account"]
    except Exception as error:
        error_msg = f"Failed to retrieve AWS Account ID: {error}"
        print(error_msg)
        raise


def get_secret():
    """
    Fetches the database credentials from AWS Secrets Manager.
    
    Returns:
        dict: A dictionary containing database credentials.
    
    Raises:
        ValueError: If the secret cannot be retrieved.
    """
    session = boto3.session.Session()
    client = session.client(service_name="secretsmanager", region_name=REGION_NAME)

    try:
        response = client.get_secret_value(SecretId=SECRET_NAME)
        secret_data = json.loads(response["SecretString"])
        return secret_data
    except Exception as error:
        error_msg = f"Error retrieving secret: {error}"
        print(error_msg)
        send_sns_notification("Database Secret Retrieval Failed", error_msg, status="FAILURE")
        raise ValueError(error_msg) from error


def send_sns_notification(subject, message, status="SUCCESS"):
    """
    Sends an email notification using AWS SNS.
    
    Args:
        subject (str): Subject of the notification.
        message (str): Message body of the notification.
        status (str): "SUCCESS" or "FAILURE" for categorization.
    """
    account_id = get_account_id()
    topic_arn = f"arn:aws:sns:{REGION_NAME}:{account_id}:{TOPIC_NAME}"
    sns_client = boto3.client("sns", region_name=REGION_NAME)

    try:
        response = sns_client.publish(
            TopicArn=topic_arn,
            Subject=f"[{status}] {subject}",
            Message=message
        )
        print(f"SNS Notification Sent: {response['MessageId']}")
    except Exception as error:
        print(f"Failed to send SNS notification: {error}")


def read_csv_from_s3():
    """
    Reads a CSV file from an S3 bucket into a Pandas DataFrame.
    
    Returns:
        pd.DataFrame: A Pandas DataFrame containing the CSV data.
    """
    account_id = get_account_id()
    bucket_name = BUCKET_NAME.format(account_id=account_id, region=REGION_NAME)
    s3_uri = f"s3://{bucket_name}/{CSV_KEY}"
    print(f"Reading CSV from {s3_uri}")

    try:
        s3_client = boto3.client("s3")
        response = s3_client.get_object(Bucket=bucket_name, Key=CSV_KEY)
        csv_data = response["Body"].read().decode("utf-8")

        df = pd.read_csv(StringIO(csv_data))
        print("CSV file successfully read from S3.")
        return df
    except Exception as error:
        error_msg = f"Failed to read CSV from S3: {error}"
        print(error_msg)
        send_sns_notification("S3 CSV Read Failed", error_msg, status="FAILURE")
        raise ValueError(error_msg) from error


def lambda_handler(event=None, context=None):
    """
    Main Lambda handler to load data from S3 into RDS MySQL.
    """
    try:
        secret = get_secret()
        db_user = secret["username"]
        db_password = secret["password"]
        db_host = secret["host"]
        db_name = secret["dbname"]
        table_name = secret["table_name"]

        engine = create_engine(f"mysql+mysqlconnector://{db_user}:{db_password}@{db_host}/{db_name}")

        df = read_csv_from_s3()
        df.to_sql(table_name, con=engine, if_exists="append", index=False)

        success_msg = f"Data successfully loaded into MySQL table: {table_name}."
        print(success_msg)
        send_sns_notification("Data Load Successful", success_msg, status="SUCCESS")

    except Exception as error:
        error_msg = f"Data load failed: {error}"
        print(error_msg)
        send_sns_notification("Data Load Failed", error_msg, status="FAILURE")
        raise
