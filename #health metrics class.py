#health metrics class
import requests
import json
// add documentation
class FitBitAPIClient:
    def __init__(self, base_url, user_id, access_token, headers):
        self.base_url = 'https://api.fitbit.com'
        self.user_id = '5FR3J5'
        self.access_token='eyJhbGciOiJIUzI1NiJ9.eyJhdWQiOiIyM1BRREgiLCJzdWIiOiI1RlIzSjUiLCJpc3MiOiJGaXRiaXQiLCJ0eXAiOiJhY2Nlc3NfdG9rZW4iLCJzY29wZXMiOiJyc29jIHJzZXQgcm94eSBybnV0IHJwcm8gcnNsZSByYWN0IHJsb2MgcnJlcyByd2VpIHJociBydGVtIiwiZXhwIjoxNzU1NTQ4MjMzLCJpYXQiOjE3MjQwMTIyMzN9.uH7tJ-m78eftEz0nMJBsCqKc7IVQMhk2GFSX5wgQQhk'
        self.headers =  {"Authorization": "Bearer {}".format(access_token)}


    def fetch_sleep_data(start_date, end_date):
        url = f"{self.base_url}/1.2/user/{self.user_id}/sleep/date/{start_date}/{end_date}.json"
        response = requests.get(url, headers=self.headers)
        if response.status_code == 200:
            return 
        else:
            return json.text()
        
    def fetch_calorie_expediture_data(start_date, end_date):
        url = f"{self.base_url}/1.2/user/{self.user_id}/sleep/date/{start_date}/{end_date}.json"
        response = requests.get(url=url, headers=headers)


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

    
