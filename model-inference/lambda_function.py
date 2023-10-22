import json
import boto3
import pandas as pd
from io import StringIO
from sklearn.preprocessing import StandardScaler
from sklearn.ensemble import GradientBoostingClassifier
import pickle
import logging

logger = logging.getLogger()
logger.setLevel(logging.INFO)

binary_columns = ["gender", "Partner", "Dependents", "PhoneService", "PaperlessBilling"]
multi_value_columns = ["MultipleLines", "InternetService", "OnlineSecurity", "OnlineBackup", "DeviceProtection", "TechSupport", "StreamingTV", "StreamingMovies"]
dummies_columns = ["Contract", "PaymentMethod"]
numeric_columns = ["tenure", "MonthlyCharges", "TotalCharges"]

def preprocess_binary_columns(df):
    df = df.copy()
    for col in binary_columns:
        df[col] = df[col].apply(lambda x: 1 if x == "Yes" else 0)
    return df

def preprocess_multi_value_columns(df):
    # One-hot encoding
    df = df.copy()
    for col in multi_value_columns:
        # If value is "Yes", then 1, else 0
        df[col] = df[col].apply(lambda x: 1 if x == "Yes" else 0)
    return df

def preprocess_dummies_columns(df):
    df = df.copy()
    df = pd.get_dummies(df, columns=dummies_columns)
    # Convert all columns to 1 and 0
    for col in df.columns:
        # if col starts with Contract or PaymentMethod
        if col.startswith("Contract") or col.startswith("PaymentMethod"):
            df[col] = df[col].apply(lambda x: 1 if x == 1 else 0)
    return df

def preprocess_numeric_columns(df):
    df = df.copy()
    for col in numeric_columns:
        df[col] = df[col].astype(float)
    # Scale numeric columns
    scaler = StandardScaler()
    df[numeric_columns] = scaler.fit_transform(df[numeric_columns])
    return df

def preprocess(data: pd.DataFrame) -> pd.DataFrame:
    """
    Preprocess data before prediction
    """
    df = data.copy()
    logger.info("Preprocessing data")
    logger.info("Preprocessing binary columns")
    df = preprocess_binary_columns(df)
    logger.info("Preprocessing multi-value columns")
    df = preprocess_multi_value_columns(df)
    logger.info("Preprocessing dummies columns")
    df = preprocess_dummies_columns(df)
    logger.info("Preprocessing numeric columns")
    df = preprocess_numeric_columns(df)
    logger.info("Data preprocessing completed")
    return df

def get_model():
    s3 = boto3.client('s3')
    bucket = s3.get_bucket('mlops-python')
    logger.info("Downloading model from S3")
    bucket.download_file("models/gradient_boosting/gb_model.pkl", "model/gb_model_s3.pkl")
    logger.info("Loading model")
    with open("model/gb_model_s3.pkl", "rb") as f:
        model = pickle.load(f)
    logger.info("Model loaded")
    return model

def index():
    return {'hello': 'world'}

def predict(event, context):
    data = event['Records'][0]['s3']

    bucket = data['bucket']['name']
    key = data['object']['key']

    s3 = boto3.client('s3')
    logger.info("Downloading data from S3")
    obj = s3.get_object(Bucket=bucket, Key=key)
    df = pd.read_csv(obj["Body"])
    logger.info("Data downloaded from S3")

    logger.info("Preprocessing data")
    df_preprocessed = preprocess(df)
    logger.info("Data preprocessing completed")

    logger.info("Loading model")
    model = get_model()
    logger.info("Model loaded")

    logger.info("Predicting")
    y_pred = model.predict(df_preprocessed)
    logger.info("Prediction completed")

    logger.info("Attaching prediction to non-preprocessed data")
    df["prediction"] = y_pred
    logger.info("Prediction attached")

    logger.info("Writing data to S3")
    csv_buffer = StringIO()
    s3.put_object(Bucket=bucket, Key="xgboost_predicted_data/" + key, Body=df.to_csv(csv_buffer))
    logger.info("Data written to S3")

    return {
        'statusCode': 200,
        'body': json.dumps('Data transformed and saved successfully!')
    }