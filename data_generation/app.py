from sdv.evaluation.single_table import evaluate_quality
from sdv.single_table import CTGANSynthesizer
from sdv.metadata import SingleTableMetadata
from flask import Flask, jsonify
from train_synthesizer import train_synthesizer
import pandas as pd
import random
import boto3
from datetime import datetime
import great_expectations as ge
from great_expectations.exceptions import GreatExpectationsError
from great_expectations.core.batch import RuntimeBatchRequest
import logging
import warnings
warnings.filterwarnings("ignore")

logging.basicConfig(level=logging.INFO)
s3 = boto3.client('s3')

app = Flask(__name__)
# Load latest model from S3
objects = s3.list_objects_v2(Bucket='mlops-python', Prefix='models/ctgan/')

try:
    latest_model = objects['Contents'][-1]['Key']
    # If KeyErrors are raised, it means there are no models in the S3 bucket
except KeyError:
    logging.info("No models found in S3. Training a new synthesizer...")
    train_synthesizer()
    latest_model = objects['Contents'][-1]['Key']
    logging.info("Synthesizer trained successfully.")

try:
    s3.download_file('mlops-python', latest_model, 'tmp/telco_customer_churn_synthesizer.pkl')
    logging.info(f"Model {latest_model} downloaded successfully from S3.")
except Exception as e:
    logging.error(f"Error downloading model from S3: {str(e)}")
    exit(1)

ctgan = CTGANSynthesizer.load('tmp/telco_customer_churn_synthesizer.pkl')
obj = s3.get_object(Bucket='mlops-python', Key='raw_data/telco_customer_churn_preprocessed.csv')
real_data = pd.read_csv(obj['Body'])
metadata = SingleTableMetadata()
metadata.detect_from_dataframe(data=real_data)
logging.info("Metadata detected from real data.")

# Store the most recently generated synthetic data
latest_synthetic_data = None

def send_metric_to_cloudwatch(metric_name, metric_value):
    """
    Send a metric to CloudWatch
    """
    cloudwatch = boto3.client('cloudwatch', region_name='us-west-2')
    cloudwatch.put_metric_data(
        Namespace='MLOps/QualityMetrics',
        MetricData=[
            {
                'MetricName': 'QualityScore',
                'Dimensions': [
                    {
                        'Name': 'ModelName',
                        'Value': 'CTGANSynthesizer'
                    },
                ],
                'Value': metric_value,
                'Unit': 'None'
            },
        ]
    )

def generate_synthetic_data():
    global latest_synthetic_data
    samples = random.randint(100, 1000)
    latest_synthetic_data = ctgan.sample(samples)
    logging.info(f"Generated {samples} synthetic data samples.")

def validate_synthetic_data(data):
    """
    Validate the synthetic data using Great Expectations.
    """

    expected_categorical_values = {
        'gender': ['Male', 'Female'],
        'Partner': ['Yes', 'No'],
        'Dependents': ['Yes', 'No'],
        'PhoneService': ['Yes', 'No'],
        'MultipleLines': ['Yes', 'No', 'No phone service'],
        'InternetService': ['DSL', 'Fiber optic', 'No'],
        'OnlineSecurity': ['Yes', 'No', 'No internet service'],
        'OnlineBackup': ['Yes', 'No', 'No internet service'],
        'DeviceProtection': ['Yes', 'No', 'No internet service'],
        'TechSupport': ['Yes', 'No', 'No internet service'],
        'StreamingTV': ['Yes', 'No', 'No internet service'],
        'StreamingMovies': ['Yes', 'No', 'No internet service'],
        'Contract': ['Month-to-month', 'One year', 'Two year'],
        'PaperlessBilling': ['Yes', 'No'],
        'PaymentMethod': ['Electronic check', 'Mailed check', 'Bank transfer (automatic)', 'Credit card (automatic)'],
        'Churn': ['Yes', 'No']
    }

    # Create a GE dataframe from the synthetic data
    context = ge.get_context()
    context.add_or_update_expectation_suite("my_expectation_suite")

    # Get the validator using the batch request
    name = "synthetic_data"
    datasource = context.sources.add_or_update_pandas(name="pandas_datasource")
    data_asset = datasource.add_dataframe_asset(name=name)
    batch_request = data_asset.build_batch_request(dataframe=data)
    validator = context.get_validator(
        batch_request=batch_request,
        expectation_suite_name="my_expectation_suite",
    )

    # Check for null values
    for column in data.columns:
        logging.info(f"Checking for null values in column {column}")
        validator.expect_column_values_to_not_be_null(column)

    # Check data types
    for column, dtype in data.dtypes.items():
        logging.info(f"Checking data type for column {column}")
        if dtype == "object":
            validator.expect_column_values_to_be_of_type(column, "object")
        elif dtype == "float64":
            validator.expect_column_values_to_be_of_type(column, "float")
        elif dtype == "int64":
            validator.expect_column_values_to_be_of_type(column, "int")

    # Check for outliers (negative values for specific columns)
    for column in ["tenure", "MonthlyCharges", "TotalCharges"]:
        logging.info(f"Checking for negative values in column {column}")
        validator.expect_column_values_to_be_between(column, min_value=0)

    # Check expected categorical values
    for column, values in expected_categorical_values.items():
        logging.info(f"Checking expected categorical values for column {column}")
        validator.expect_column_distinct_values_to_be_in_set(column, values)

    # Validate the expectations
    results = validator.validate()
    if not results["success"]:
        # Show validation results in the logs
        logging.error(f"Validation failed: {results}")
        raise GreatExpectationsError("Data validation failed!")

    return True

@app.route('/generate_data', methods=['GET'])
def generate_data_endpoint():
    """
    Generate synthetic data using CTGAN and return a response.
    """
    generate_synthetic_data()  # Call the function to generate data
    
    if latest_synthetic_data is not None:
        logging.info("Synthetic data generation was successful.")        
        return jsonify({"message": "Synthetic data generated successfully."}), 200
    else:
        logging.error("Error generating synthetic data.")
        return jsonify({"error": "Error generating synthetic data."}), 400

    
@app.route('/evaluate_quality', methods=['GET'])
def evaluate_quality_endpoint():
    global latest_synthetic_data
    # Generate data using the generate_data_endpoint
    generate_data_endpoint()
    # log type of latest_synthetic_data
    logging.info(f"latest_synthetic_data type: {type(latest_synthetic_data)}")
    # Ensure synthetic data has been generated before trying to evaluate its quality
    if latest_synthetic_data is None:
        logging.warning("Synthetic data has not been generated yet.")
        return jsonify({"error": "Please generate synthetic data first using /generate_data endpoint."}), 400

    # Validate the synthetic data using the function
    try:
        validate_synthetic_data(latest_synthetic_data)
        logging.info("Synthetic data validation passed.")
    except GreatExpectationsError as e:
        logging.error(f"Synthetic data validation failed: {str(e)}")
        return jsonify({"error": "Synthetic data validation failed!"}), 400

    quality_report = evaluate_quality(real_data, latest_synthetic_data, metadata)
    quality_score = quality_report.get_score()
    send_metric_to_cloudwatch('SyntheticDataQualityScore', quality_score)
    if quality_score < 0.8:
        logging.warning("Synthetic data quality is below threshold. Retraining synthesizer...")
        train_synthesizer()
        return jsonify({"error": "Synthetic data quality is too low. Retraining synthesizer..."}), 400
    else:
        try:
            s3_key = f'synthetic_data/{datetime.now().strftime("%Y-%m-%d-%H-%M-%S")}.csv'
            s3.put_object(
                Bucket='mlops-python',
                Key=s3_key,
                Body=latest_synthetic_data.to_csv(index=False)
            )
            logging.info(f"Synthetic data uploaded to S3 at {s3_key}.")
            return jsonify({"message": f"The synthetic data quality score is {quality_score}."}), 200
        except Exception as e:
            logging.error(f"Error uploading synthetic data to S3: {str(e)}")
            return jsonify({"error": str(e)}), 400

# if __name__ == '__main__':
#     app.run(host='0.0.0.0', port=5000, debug=True)