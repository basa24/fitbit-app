#The application to run

import datetime
import pandas as pd
from sqlalchemy import create_engine, MetaData, Table, Column, Integer, Float, Date, Time, exc, text
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.exc import SQLAlchemyError
from taipy.gui import Gui, notify
from sqlalchemy import update

class DatabaseManager:
    def __init__(self, db_url="postgresql://postgres:Sarigama1@localhost:5432/postgres"):
        self.engine = create_engine(db_url)
        self.metadata = MetaData()  
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

#GoalsManager


class GoalsManager:
    def __init__(self, db_url="postgresql://postgres:Sarigama1@localhost:5432/postgres"):
        self.engine = create_engine(db_url)
        self.metadata = MetaData()  
        self.metadata.bind = self.engine
        self.health_goals=Table(
            'health_goals', self.metadata,
            Column('id', Integer, primary_key=True, autoincrement=True),  
            Column('start_time', Time),  
            Column('end_time', Time),   
            Column('fasting_hours', Integer),  
            Column('sleep_hours', Float(precision=2)),  
            Column('calorie_deficit', Integer)       
        )
    
    def create_table(self):
        try:
            self.metadata.create_all(self.engine)
            print("Table created successfully using SQLAlchemy")
        except Exception as e:
            print(f"An error occurred: {e}")
            


    def update_health_goals(self, df):
        row = df.iloc[0]
        with self.engine.connect() as connection:
            stmt = (
                update(self.health_metrics)
                .values(
                    start_time=row['start_time'],
                    end_time=row['end_time'],
                    fasting_hours=row['fasting_hours'],
                    sleep_hours=row['sleep_hours'],
                    calorie_deficit=row['calorie_deficit']
                )
                .where(self.health_metrics.c.id == 1)  
            )   
            connection.execute(stmt)
            connection.commit()
            
            
    def calculate_fasting_score(self, hours_fasted, fasting_goal):
        if fasting_goal == 0:
            return None  
        else:
            score = hours_fasted / fasting_goal
            return min(score, 1)  # Cap the score at 1 (or 100%)
    
    def calculate_calorie_deficit_score(self, actual_deficit, deficit_goal):
        if deficit_goal == 0:
            return None 
        elif actual_deficit <= 0:
            return 0  # Score is 0 if there's a calorie surplus or no deficit
        else:
            score = actual_deficit / deficit_goal
            return min(score, 1)  # Cap the score at 1 (or 100%)

    def calculate_sleep_score(self, actual_sleep, sleep_goal):
        if sleep_goal == 0:
            return None  
        else:
            score = actual_sleep / sleep_goal
            return min(score, 1)  # Cap the score at 1 (or 100%)

    def harmonic_mean_of_ratios(self, r1, r2, r3):
        ratios = [r for r in [r1, r2, r3] if r is not None and r > 0]
        if not ratios:
            return None  # Return None if there are no valid ratios
        harmonic_mean = len(ratios) / sum(1 / r for r in ratios)
        return harmonic_mean  

    def calculate_lifescore(self, hours_fasted, calorie_deficit, hours_slept, fasting_goal, deficit_goal, sleep_goal):
        fasting_score = self.calculate_fasting_score(hours_fasted, fasting_goal)
        sleep_score = self.calculate_sleep_score(hours_slept, sleep_goal)
        deficit_score = self.calculate_calorie_deficit_score(calorie_deficit, deficit_goal)
        life_score = self.harmonic_mean_of_ratios(fasting_score, sleep_score, deficit_score)
        return life_score

             
db_manager = DatabaseManager()
db_manager.create_table()
goal_manager = GoalsManager()
goal_manager.create_table()

def submit_data(state):
    try:
        with db_manager.engine.connect() as connection:
            entry_date_str = state.entry_date.strftime("%Y-%m-%d")
            query = text("SELECT calorie_expenditure, sleep_hours FROM health_metrics WHERE date = :date_param")
            result = connection.execute(query, {"date_param": entry_date_str}).fetchone()

            # Extracting the result if it exists and handling cases if one of them is None

            calorie_expenditure, sleep_hours = (result if result else (None, None))

            # Create a new row and overwrite the DataFrame
            new_entry = pd.DataFrame([{
                'date': state.entry_date,
                'calorie_expenditure': calorie_expenditure,
                'sleep_hours': sleep_hours,
                'weight': state.weight,
                'calorie_intake': state.calorie_intake,
                'fasting_hours': state.fasting_hours,
                'daily_lifescore': None
            }])

            # Print updated DataFrame for verification
            print(new_entry)
            db_manager.upsert_health_metrics(new_entry, True)

    except Exception as e:
        print(f"An error occurred: {e}")
        
def refresh_graphs(state):
    # Assume db_manager.fetch_data() fetches the updated dataset
    state.df_fetcheddata = db_manager.fetch_data()
    notify(state, "df_fetcheddata")  # Notify Taipy to update the UI components that use df_fetcheddata
df_fetcheddata = db_manager.fetch_data()

def submit_goals(state):
    if state.fasting_start_time is None or state.fasting_end_time is None:
        fasting_duration = 0  # Set fasting hours to 0 if either time is None
        start_time = None
        end_time = None
    else:
        try:
            start_time = datetime.strptime(state.fasting_start_time, "%H:%M").time()
            end_time = datetime.strptime(state.fasting_end_time, "%H:%M").time()
            start_dt = datetime.combine(datetime.today(), start_time)
            end_dt = datetime.combine(datetime.today(), end_time)
            fasting_duration = (end_dt - start_dt).total_seconds() / 3600
            if fasting_duration < 0:
                fasting_duration += 24
        except ValueError:
            print("Invalid time format. Please enter time as HH:MM.")
            return None 
    goals_data = {
        'start_time': [start_time],
        'end_time': [end_time],
        'fasting_hours': [fasting_duration],
        'sleep_hours': [state.sleep_goal],
        'calorie_deficit': [state.calorie_deficit_goal]
    }
    df = pd.DataFrame(goals_data)
    print(df)  
    goal_manager.update_health_goals(df)
    
page = """
<center><h1 style="color:#ADD8E6;">Health Tracking Dashboard</h1></center>
<|layout|columns=2|gap=20px|>
<|
<h3>Enter Entry Date</h3>
<|{entry_date}|date|label=Select a Date|>

<h3>Enter Weight (kg)</h3>
<|{weight}|input|type=number|label=Enter Weight (kg)|>

<h3>Enter Calorie Intake</h3>
<|{calorie_intake}|input|type=number|label=Enter Calorie Intake (kcal)|>

<h3>Enter Fasting Hours</h3>
<|{fasting_hours}|input|type=number|label=Enter Fasting Hours|>

<|Submit|button|on_action=submit_data|class_name=button|>
<|Refresh|button|on_action=refresh_graphs|class_name=button|>
|>

<|layout|columns=2|gap=20px|>
<|
<center><h2 style="color:#87CEEB;">Goals Manager</h2></center>

<h3>Fasting Start Time</h3>
<|{fasting_start_time}|input|type=text|placeholder="HH:MM"|label="Fasting Start Time (24-hour)"|>

<h3>Fasting End Time</h3>
<|{fasting_end_time}|input|type=text|placeholder="HH:MM"|label="Fasting End Time (24-hour)"|>

<h3>Sleep Hours Goal</h3>
<|{sleep_goal}|slider|min=6|max=16|step=1|value=8|label="Sleep Hours Goal"|>

<h3>Calorie Deficit Goal</h3>
<|{calorie_deficit_goal}|slider|min=0|max=2000|step=50|value=500|label="Calorie Deficit Goal"|>

<|Save Goals|button|on_action=submit_goals|class_name=button|>
|>
<|layout|columns=1|gap=10px|>
<|>
<center><h2 style="color:#87CEEB;">Weight Over Time</h2></center>
<|{df_fetcheddata}|chart|type=line|x=date|y=weight|color=#4682B4|title="Weight Tracking"|>
|>

<|>
<center><h2 style="color:#87CEEB;">Calorie Intake vs. Expenditure</h2></center>
<|{df_fetcheddata}|chart|type=bar|x=date|y[1]=calorie_intake|y[2]=calorie_expenditure|color[1]=#6495ED|color[2]=#4169E1|title="Calorie Metrics"|>
|>

<|>
<center><h2 style="color:#87CEEB;">Calorie Deficit Over Time</h2></center>
<|{df_fetcheddata}|chart|type=line|x=date|y=calorie_deficit|color=#1E90FF|title="Calorie Deficit Tracking"|>
|>

<|>
<center><h2 style="color:#87CEEB;">Sleep Hours Over Time</h2></center>
<|{df_fetcheddata}|chart|type=line|x=date|y=sleep_hours|color=#00BFFF|title="Sleep Hours"|>
|>
"""

weight = 50.0
calorie_intake = 2000
fasting_hours = 16
entry_date = datetime.date.today()
df_entry = pd.DataFrame(columns=["date", "calorie_expenditure", "sleep_hours", "weight", "calorie_intake", "fasting_hours", "daily_lifescore"])
gui = Gui(page=page)

if __name__ == "__main__":
    gui.run(
        title="Health Tracking Input Example",
        dark_mode=True,
        port=5001,
        state={
            "weight": weight,
            "entry_date": entry_date,
            "calorie_intake": calorie_intake,
            "fasting_hours": fasting_hours,
            "df_entry": df_entry
        }
    )