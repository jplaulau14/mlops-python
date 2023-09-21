import requests
import logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

def lambda_handler(event, context):
    logger.info("Starting API request...")
    response = requests.get('http://ec2-34-220-99-125.us-west-2.compute.amazonaws.com:5000/evaluate_quality')
    logger.info(f"API responded with: {response.status_code}")
    return {
        'statusCode': 200,
        'body': response.text
    }