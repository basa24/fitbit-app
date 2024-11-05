import datetime
import logging
import pandas as pd
import requests
from sqlalchemy import create_engine, MetaData, Table, Column, Integer, Float, Date, exc, text
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.exc import SQLAlchemyError


class FitBitAPIClient:
    def __init__(self, access_token='eyJhbGciOiJIUzI1NiJ9.eyJhdWQiOiIyM1BRREgiLCJzdWIiOiI1RlIzSjUiLCJpc3MiOiJGaXRiaXQiLCJ0eXAiOiJhY2Nlc3NfdG9rZW4iLCJzY29wZXMiOiJyc29jIHJzZXQgcm94eSBybnV0IHJwcm8gcnNsZSByYWN0IHJsb2MgcnJlcyByd2VpIHJociBydGVtIiwiZXhwIjoxNzU1NTQ4MjMzLCJpYXQiOjE3MjQwMTIyMzN9.uH7tJ-m78eftEz0nMJBsCqKc7IVQMhk2GFSX5wgQQhk'  # Replace with your actual access token
, user_id='5FR3J5'):
        self.base_url = 'https://api.fitbit.com'
        self.user_id = user_id
        self.access_token = access_token
        self.headers = {"Authorization": f"Bearer {self.access_token}"}

    # Method for fetching sleep data from api
    def fetch_sleep_data(self, start_date, end_date):
        url = f"{self.base_url}/1.2/user/{self.user_id}/sleep/date/{start_date}/{end_date}.json"
        response = requests.get(url, headers=self.headers)
        if response.status_code == 200:
            return response.json()
        else:
            logging.error(f"Failed to fetch sleep data: {response.text}")
            return None

    # Method for fetching calorie expenditure data from api
    def fetch_calorie_expenditure_data(self, start_date, end_date):
        url = f"{self.base_url}/1.2/user/{self.user_id}/activities/calories/date/{start_date}/{end_date}.json"
        response = requests.get(url, headers=self.headers)
        if response.status_code == 200:
            return response.json()
        else:
            logging.error(f"Failed to fetch calorie data: {response.text}")
            return None
        
    def get_fitbit_df(self, start_date, end_date):
        sleep_data = self.fetch_sleep_data(start_date, end_date)
        calorie_data = self.fetch_calorie_expenditure_data(start_date, end_date)

        # Processing calorie data
        calorie_expenditure_list = []
        calorie_dates = []
        if calorie_data and 'activities-calories' in calorie_data:
            calorie_dict = {entry['dateTime']: int(entry['value']) for entry in calorie_data['activities-calories']}
            calorie_dates = list(calorie_dict.keys())
            calorie_expenditure_list = list(calorie_dict.values())

        df_calories = pd.DataFrame({
            'date': calorie_dates,
            'calorie_expenditure': calorie_expenditure_list
        })
        df_calories['date'] = pd.to_datetime(df_calories['date'])

        # Processing sleep data
        sleep_records = []
        if sleep_data and 'sleep' in sleep_data:
            for record in sleep_data['sleep']:
                date = record['dateOfSleep']
                sleep_minutes = record['minutesAsleep']
                sleep_records.append({'date': date, 'sleep_minutes': sleep_minutes})

        df_sleep = pd.DataFrame(sleep_records)
        if not df_sleep.empty:
            df_sleep['date'] = pd.to_datetime(df_sleep['date'])
            df_sleep = df_sleep.groupby('date', as_index=False).sum()
            df_sleep['sleep_hours'] = round(df_sleep['sleep_minutes'] / 60, 2)
            df_sleep = df_sleep[['date', 'sleep_hours']]

        # Merging calorie and sleep data
        df_merged = pd.merge(df_calories, df_sleep, on='date', how='left')
        df_merged = df_merged.sort_values(by='date').reset_index(drop=True)

        return df_merged
        
    
    
class DatabaseManager:
    def __init__(self, db_url="postgresql://postgres:Sarigama1@localhost:5432/postgres"):
        self.engine = create_engine(db_url)
        self.metadata = MetaData()  # Initialize without the bind argument
        self.metadata.bind = self.engine  # Bind the engine here
        
        self.health_metrics = Table(
            'health_metrics', self.metadata,
            Column('date', Date, primary_key=True),
            Column('sleep_hours', Float),
            Column('calorie_expenditure', Integer),
            Column('weight', Integer),
            Column('calorie_intake', Integer),
            Column('fasting_hours', Integer),
            Column('daily_lifescore', Float),
        )
        
    def create_table(self):
        try:
            self.metadata.create_all(self.engine)
            print("Table created successfully using SQLAlchemy")
        except Exception as e:
            print(f"An error occurred: {e}")
            
            
    def fetch_data(self):
        try:
            # Load the data from the 'health_metrics' table into a DataFrame, sorted by 'date' column
            health_data = pd.read_sql('SELECT * FROM health_metrics ORDER BY date ASC', con=self.engine)
            print("Data fetched successfully from the 'health_metrics' table.")
        except Exception as e:
            print(f"An error occurred while fetching data: {e}")    
        if 'date' in health_data.columns:
            health_data['date'] = health_data['date'].apply(lambda x: x.strftime('%Y-%m-%d')) 
            health_data["calorie_deficit"] = health_data["calorie_expenditure"] - health_data["calorie_intake"]
        return health_data
    
    def upsert_health_metrics(self, df, is_manualentry):
     
        health_metrics = Table('health_metrics', self.metadata, autoload_with=self.engine)
        record = df.to_dict(orient='records')[0]
        with self.engine.connect() as conn:
            stmt = insert(health_metrics).values(record)

            if is_manualentry:
                # Only update these fields if is_manualentry is True
                upsert_fields = {
                    'weight': stmt.excluded.weight,
                    'calorie_intake': stmt.excluded.calorie_intake,
                    'fasting_hours': stmt.excluded.fasting_hours,
                    'daily_lifescore': stmt.excluded.daily_lifescore
                }
            else:
                # Only update these fields if is_manualentry is False
                upsert_fields = {
                    'calorie_expenditure': stmt.excluded.calorie_expenditure,
                    'sleep_hours': stmt.excluded.sleep_hours
                }

            upsert_stmt = stmt.on_conflict_do_update(
                index_elements=['date'],  # Assuming 'date' is a unique or primary key
                set_=upsert_fields
            )
            try:
                conn.execute(upsert_stmt)
                conn.commit()
            except SQLAlchemyError as e:
                print(f"An error occurred: {e}")
                conn.rollback()

        print("Data upserted successfully into 'health_metrics'.")     
        
client = FitBitAPIClient()

today_date = datetime.datetime.now().strftime("%Y-%m-%d")

sleep_data = client.fetch_sleep_data(today_date, today_date)

calorie_data = client.fetch_calorie_expenditure_data(today_date, today_date)

df = client.get_fitbit_df(today_date, today_date)

db = DatabaseManager()
db.create_table()

db.upsert_health_metrics(df, False)





