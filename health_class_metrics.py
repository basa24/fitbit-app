#health metrics class

import requests
import pandas as pd
import logging
from sqlalchemy import create_engine
import psycopg2
from apscheduler.schedulers.background import BackgroundScheduler
import datetime
import time

class FitBitAPIClient:
    def __init__(self, access_token, user_id='5FR3J5'):
        self.base_url = 'https://api.fitbit.com'
        self.user_id = user_id
        self.access_token = 'eyJhbGciOiJIUzI1NiJ9.eyJhdWQiOiIyM1BRREgiLCJzdWIiOiI1RlIzSjUiLCJpc3MiOiJGaXRiaXQiLCJ0eXAiOiJhY2Nlc3NfdG9rZW4iLCJzY29wZXMiOiJyc29jIHJzZXQgcm94eSBybnV0IHJwcm8gcnNsZSByYWN0IHJsb2MgcnJlcyByd2VpIHJociBydGVtIiwiZXhwIjoxNzU1NTQ4MjMzLCJpYXQiOjE3MjQwMTIyMzN9.uH7tJ-m78eftEz0nMJBsCqKc7IVQMhk2GFSX5wgQQhk'
        self.headers = {"Authorization": f"Bearer {self.access_token}"}

    #method for fetching sleep data from watch
    def fetch_sleep_data(self, start_date, end_date):
        url = f"{self.base_url}/1.2/user/{self.user_id}/sleep/date/{start_date}/{end_date}.json"
        response = requests.get(url, headers=self.headers)
        if response.status_code == 200:
            return response.json()
        else:
            logging.error(f"Failed to fetch sleep data: {response.text}")
            return None
        
    #method for fetching calorie expenditure data from watch
    def fetch_calorie_expenditure_data(self, start_date, end_date):
        url = f"{self.base_url}/1.2/user/{self.user_id}/activities/calories/date/{start_date}/{end_date}.json"
        response = requests.get(url, headers=self.headers)
        if response.status_code == 200:
            return response.json()
        else:
            logging.error(f"Failed to fetch calorie data: {response.text}")
            return None
        
        

class HealthMetrics:
    def __init__(self, fitbit_api_client, db_connection_string):
        self.fitbit_api_client = fitbit_api_client
        self.db_connection_string = db_connection_string
        self.db_manager = DatabaseManager(db_connection_string) 
        self.df = pd.DataFrame(columns=['date', 'weight', 'calorie_intake', 'fasting_hours', 'calorie_expenditure', 'sleep_hours'])

    def update_daily_metrics(self, date, weight=None, calorie_intake=None, fasting_hours=None, calorie_expenditure=None, sleep_hours=None):
        new_data = {
            "date": date,
            "weight": weight,
            "calorie_intake": calorie_intake,
            "fasting_hours": fasting_hours,
            "calorie_expenditure": calorie_expenditure,
            "sleep_hours": sleep_hours
        }

        
        self.df = self.df.append(new_data, ignore_index=True)

        
        self.df.drop_duplicates(subset=['date'], keep='last', inplace=True)

    def fetch_and_update_metrics(self, date):
        
        sleep_data = self.fitbit_api_client.fetch_sleep_data(date, date)
        calorie_data = self.fitbit_api_client.fetch_calorie_expenditure_data(date, date)

       
        sleep_hours = sleep_data.get('summary', {}).get('totalMinutesAsleep', 0) / 60 if sleep_data else None
        calories_burned = calorie_data.get('activities-calories', [{}])[0].get('value', None) if calorie_data else None

    
        self.update_daily_metrics(date=date, calorie_expenditure=calories_burned, sleep_hours=sleep_hours)

    def save_to_postgres(self):
        try:
            engine = create_engine(self.db_connection_string)
            self.df.to_sql('health_metrics', engine, if_exists='append', index=False)
            logging.info("Data successfully saved to PostgreSQL.")
        except Exception as e:
            logging.error(f"An error occurred while saving to PostgreSQL: {e}")

    def reset_daily_dataframe(self):
        self.df = pd.DataFrame(columns=['date', 'weight', 'calorie_intake', 'fasting_hours', 'calorie_expenditure', 'sleep_hours'])

    def fetch_and_modify_data_for_date(self, date):
       
        data = self.db_manager.fetch_data_by_date(date)
        if data:
           
            print(f"Data for {date}: {data}")
            
           
            weight = float(input(f"Enter new weight for {date} (current: {data['weight']}): ") or data['weight'])
            calorie_intake = float(input(f"Enter new calorie intake for {date} (current: {data['calorie_intake']}): ") or data['calorie_intake'])
            fasting_hours = float(input(f"Enter new fasting hours for {date} (current: {data['fasting_hours']}): ") or data['fasting_hours'])
            calorie_expenditure = float(input(f"Enter new calorie expenditure for {date} (current: {data['calorie_expenditure']}): ") or data['calorie_expenditure'])
            sleep_hours = float(input(f"Enter new sleep hours for {date} (current: {data['sleep_hours']}): ") or data['sleep_hours'])
            
           
            self.db_manager.update_data_by_date(date, weight, calorie_intake, fasting_hours, calorie_expenditure, sleep_hours)


    
         
class Scheduler:
    def __init__(self, health_metrics):
        self.health_metrics = health_metrics
        self.scheduler = BackgroundScheduler()

    def start(self):
        
        self.scheduler.add_job(self.fetch_and_store_fitbit_data, 'cron', hour=0)  
        self.scheduler.add_job(self.save_daily_data, 'cron', hour=23, minute=59)  # 
        self.scheduler.start()

    def fetch_and_store_fitbit_data(self):
        """
        Fetch data from Fitbit and update health metrics for today.
        """
        today = datetime.datetime.now().date().isoformat()

       
        self.health_metrics.fetch_and_update_metrics(date=today)

    def save_daily_data(self):
      
        self.health_metrics.save_to_postgres()

        self.health_metrics.reset_daily_dataframe()

    def shutdown(self):
       
        self.scheduler.shutdown()
       
               
class DatabaseManager:
    def __init__(self, db_connection_string):
        self.conn = psycopg2.connect(db_connection_string)
        self.cursor = self.conn.cursor()
        self.create_tables()

    def create_tables(self):
        # Create health metrics table if it doesn't exist
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS health_metrics (
                date DATE PRIMARY KEY,
                weight REAL,
                calorie_intake REAL,
                fasting_hours REAL,
                calorie_expenditure REAL,
                sleep_hours REAL
            )
        """)
        self.conn.commit()

    def fetch_data_by_date(self, date):
        """
        Fetch data for a specific date.
        """
        self.cursor.execute("""
            SELECT * FROM health_metrics WHERE date = %s
        """, (date,))
        result = self.cursor.fetchone()
        if result:
            columns = ['date', 'weight', 'calorie_intake', 'fasting_hours', 'calorie_expenditure', 'sleep_hours']
            return dict(zip(columns, result))
        else:
            logging.info(f"No data found for date: {date}")
            return None

    def update_data_by_date(self, date, weight=None, calorie_intake=None, fasting_hours=None, calorie_expenditure=None, sleep_hours=None):
        """
        Update the health metrics for a specific date.
        """
        try:
            self.cursor.execute("""
                UPDATE health_metrics
                SET weight = %s, calorie_intake = %s, fasting_hours = %s, calorie_expenditure = %s, sleep_hours = %s
                WHERE date = %s
            """, (weight, calorie_intake, fasting_hours, calorie_expenditure, sleep_hours, date))
            self.conn.commit()
            logging.info(f"Data for date {date} successfully updated.")
        except Exception as e:
            logging.error(f"An error occurred while updating the data for date {date}: {e}")

    def close(self):
        self.conn.close()


class DataProcessor:
    pass

         
class ETLController:
    pass
