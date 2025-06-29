import boto3
import json
import logging
from typing import Dict, Any
from botocore.exceptions import ClientError, NoCredentialsError

logger = logging.getLogger(__name__)


def get_aws_parameter_store_secrets(parameter_prefix: str = "/better-call-buffet") -> Dict[str, Any]:
    """
    Retrieve secrets from AWS Systems Manager Parameter Store.
    
    This replaces AWS Secrets Manager to use the free tier service.
    Parameter Store provides up to 10,000 free standard parameters.
    
    Args:
        parameter_prefix: The prefix for parameter names (e.g., "/better-call-buffet")
    
    Returns:
        Dictionary of parameter names (without prefix) and their values
        
    Educational Note:
        - Parameter Store is free for standard parameters (up to 4KB each)
        - Automatically encrypts SecureString parameters using AWS KMS
        - Integrates with IAM for fine-grained access control
        - Supports parameter hierarchies for organization
    """
    try:
        # Initialize SSM client (Systems Manager)
        ssm_client = boto3.client('ssm')
        
        # Get parameters by path (retrieves all parameters under the prefix)
        response = ssm_client.get_parameters_by_path(
            Path=parameter_prefix,
            Recursive=True,  # Get parameters in subdirectories too
            WithDecryption=True  # Decrypt SecureString parameters
        )
        
        # Convert to dictionary format
        secrets = {}
        for parameter in response['Parameters']:
            # Remove the prefix to get clean parameter names
            param_name = parameter['Name'].replace(f"{parameter_prefix}/", "")
            secrets[param_name] = parameter['Value']
            
        logger.info(f"✅ Successfully retrieved {len(secrets)} parameters from Parameter Store")
        return secrets
        
    except NoCredentialsError:
        logger.warning("⚠️ AWS credentials not found. Falling back to environment variables.")
        return {}
    except ClientError as e:
        error_code = e.response['Error']['Code']
        if error_code == 'ParameterNotFound':
            logger.warning(f"⚠️ No parameters found with prefix {parameter_prefix}")
        elif error_code == 'AccessDenied':
            logger.error(f"❌ Access denied to Parameter Store. Check IAM permissions.")
        else:
            logger.error(f"❌ AWS Parameter Store error: {e}")
        return {}
    except Exception as e:
        logger.error(f"❌ Unexpected error retrieving secrets: {e}")
        return {}
