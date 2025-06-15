import json
import boto3
from typing import Dict


def get_aws_secrets(secret_name: str) -> Dict[str, str]:
    """
    Retrieve secrets from AWS Secrets Manager
    """
    session = boto3.session.Session()
    client = session.client(service_name="secretsmanager", region_name="us-east-1")

    try:
        get_secret_value_response = client.get_secret_value(SecretId=secret_name)
    except Exception as e:
        raise e
    else:
        if "SecretString" in get_secret_value_response:
            return json.loads(get_secret_value_response["SecretString"])
        raise ValueError("Secret value is not a string")
