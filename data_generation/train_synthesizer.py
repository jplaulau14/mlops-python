import pandas as pd
from sdv.metadata import SingleTableMetadata
from sdv.single_table import CTGANSynthesizer
import boto3
import os
from datetime import datetime

s3 = boto3.client('s3')

metadata = SingleTableMetadata()

def train_synthesizer():
    # Load data from S3
    obj = s3.get_object(Bucket='mlops-python', Key='raw_data/telco_customer_churn_preprocessed.csv')
    data = pd.read_csv(obj['Body'])
    metadata.detect_from_dataframe(data=data)

    synthesizer = CTGANSynthesizer(
        metadata,
        enforce_rounding=False,
        epochs=100,
        verbose=True
    )

    synthesizer.fit(data)

    # Save synthesizer to S3
    synthesizer.save('tmp/telco_customer_churn_synthesizer.pkl')
    s3.put_object(
        Bucket='mlops-python',
        Key=f'models/ctgan/{datetime.now().strftime("%Y-%m-%d-%H-%M-%S")}.pkl',
        Body=open('tmp/telco_customer_churn_synthesizer.pkl', 'rb')
    )
    # Delete synthesizer from local storage
    os.remove('tmp/telco_customer_churn_synthesizer.pkl')
