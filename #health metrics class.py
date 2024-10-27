#health metrics class

import requests
import json
import logging

class FitBitAPIClient:
    def __init__(self, access_token, user_id='5FR3J5'):
        self.base_url = 'https://api.fitbit.com'
        self.user_id = user_id
        self.access_token = access_token
        self.headers = {"Authorization": f"Bearer {self.access_token}"}

    def fetch_sleep_data(self, start_date, end_date):
        url = f"{self.base_url}/1.2/user/{self.user_id}/sleep/date/{start_date}/{end_date}.json"
        response = requests.get(url, headers=self.headers)
        if response.status_code == 200:
            return response.json()
        else:
            logging.error(f"Failed to fetch sleep data: {response.text}")
            return None

    def fetch_calorie_expenditure_data(self, start_date, end_date):
        url = f"{self.base_url}/1.2/user/{self.user_id}/activities/calories/date/{start_date}/{end_date}.json"
        response = requests.get(url, headers=self.headers)
        if response.status_code == 200:
            return response.json()
        else:
            logging.error(f"Failed to fetch calorie data: {response.text}")
            return None
        
        
class DataBaseManager:



class DataProcessor:

class Scheduler:

class ETLController:
    




class HealthMetrics:
    def __init__(self, date, calorie_intake, calorie_expenditure, weight, sleep, fasting_hours, calorie_goal, sleep_goal):
        self.date = date
        self.calorie_intake = calorie_intake
        self.calorie_expenditure = calorie_expenditure
        self.weight = weight
        self.sleep = sleep
        self.fasting_hours = fasting_hours
        self.calorie_goal = calorie_goal
        self.sleep_goal = sleep_goal

    
