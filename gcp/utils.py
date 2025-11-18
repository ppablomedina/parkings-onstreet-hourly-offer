from gcp.paths import *
import pandas as pd


def get_historical_places_offered():
    df = pd.read_excel(historical_places_offered_path)
    return df

def get_historical_seconds_offered():
    df = pd.read_excel(historical_seconds_offered_path)
    return df

def upload_seconds(merged_df):
    merged_df.to_excel(f"merged_df_FINAL.xlsx", index=False)