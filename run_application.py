"""INCLUDE GETTER METHODS FOR DB MANAG ER AND GOAL MANAGER: 
CALCULTAE DAILY LIFE SCORE IN SUBMIT METHOD AND ADD TO HEALTH_METRICS
WHEN APPLICTSION IS RUNNING; THE BACKRGOUDN API_TO_DB CANNOT XCECUTE:
AUTOMATICALLY QUIT APPLICATION
CLOSE CONN WHEN DONE
"""
# Third-party library imports
import pandas as pd
from sqlalchemy import (
    create_engine, MetaData, Table, Column, Integer, Float, Date, Time, text, select, update
)
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session
from taipy.gui import Gui, notify  # For Taipy GUI components

import datetime
from datetime import datetime, timedelta
import pandas as pd
from sqlalchemy import create_engine, MetaData, Table, Column, Integer, Float, Date, Time, exc, text
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.exc import SQLAlchemyError
from taipy.gui import Gui, notify
from sqlalchemy import update
from sqlalchemy import create_engine, select, MetaData, Table, Column, Integer, Float, Time
from sqlalchemy.orm import Session
from sqlalchemy import select, insert
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import SQLAlchemyError



class DatabaseManager:
    def __init__(self, db_url="postgresql://postgres:Sarigama1@localhost:5432/postgres"):
        self.engine = create_engine(db_url)
        self.metadata = MetaData()
        self.metadata.bind = self.engine
        self.Session = sessionmaker(bind=self.engine)  # Create a session factory
        
        # Define the health_metrics table
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
        # Use a session for executing queries
        session = self.Session()
        try:
            # Execute the SQL query to fetch data
            query = text('SELECT * FROM health_metrics ORDER BY date ASC')
            result = session.execute(query)
            # Convert the result into a DataFrame
            health_data = pd.DataFrame(result.fetchall(), columns=result.keys())
            
            print("Data fetched successfully from the 'health_metrics' table.")
            if not health_data.empty and 'date' in health_data.columns:
                health_data['date'] = health_data['date'].apply(lambda x: x.strftime('%Y-%m-%d'))
                health_data["calorie_deficit"] = (
                    health_data["calorie_expenditure"].fillna(0) - health_data["calorie_intake"].fillna(0)
                )
            return health_data
        except Exception as e:
            print(f"An error occurred while fetching data: {e}")
            return pd.DataFrame()  # Return an empty DataFrame on error
        finally:
            session.close()  # Always close the session
            
   
            
    def upsert_health_metrics(self, df, is_manualentry):
        session = self.Session()  # Open a session
        try:
            health_metrics = self.health_metrics
            record = df.to_dict(orient='records')[0]  # Convert the DataFrame to a dictionary (first row)
            
            stmt = insert(health_metrics).values(record)
            
            # Determine which fields to update
            if is_manualentry:
                upsert_fields = {
                    'weight': stmt.excluded.weight,
                    'calorie_intake': stmt.excluded.calorie_intake,
                    'fasting_hours': stmt.excluded.fasting_hours,
                    'daily_lifescore': stmt.excluded.daily_lifescore,
                }
            else:
                upsert_fields = {
                    'calorie_expenditure': stmt.excluded.calorie_expenditure,
                    'sleep_hours': stmt.excluded.sleep_hours,
                }
            
            upsert_stmt = stmt.on_conflict_do_update(
                index_elements=['date'],  # Conflict on 'date' column
                set_=upsert_fields
            )
            
            session.execute(upsert_stmt)
            session.commit()  # Commit the transaction
            print("Data upserted successfully into 'health_metrics'.")
        except SQLAlchemyError as e:
            session.rollback()  
            print(f"An error occurred during upsert: {e}")
        finally:
            session.close()   

#GoalsManager


class GoalsManager:
    def __init__(self, db_url="postgresql://postgres:Sarigama1@localhost:5432/postgres"):
        self.engine = create_engine(db_url)
        self.metadata = MetaData()
        self.metadata.bind = self.engine
        self.Session = sessionmaker(bind=self.engine) 

        self.health_goals = Table(
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
        def parse_time(time_str):
            # Parse time, return None if the input is None or an empty string
            if not time_str:  # Handles None and empty string
                return None
            return datetime.strptime(time_str, "%H:%M").time()
        
        def calculate_fasting_hours(start_time, end_time):
        
            if not start_time or not end_time:  # If either time is None
                return None

            # Combine times with today's date for calculation
            today = datetime.today()
            start_datetime = datetime.combine(today, start_time)
            end_datetime = datetime.combine(today, end_time)

            if end_datetime < start_datetime:  # Handle end_time on the next day
                end_datetime += timedelta(days=1)

            # Calculate the duration in hours
            fasting_duration = (end_datetime - start_datetime).seconds / 3600  # Convert seconds to hours
            return round(fasting_duration, 2)

        # Apply parsing to start_time and end_time columns
        df['start_time'] = df['start_time'].apply(parse_time)
        df['end_time'] = df['end_time'].apply(parse_time)

       
        row = df.iloc[0]

        # Calculate fasting hours dynamically
        fasting_hours = calculate_fasting_hours(row['start_time'], row['end_time'])

        session = self.Session()  # Start a session
        try:
            # Check if a row with id=1 exists
            select_stmt = select(self.health_goals).where(self.health_goals.c.id == 1)
            result = session.execute(select_stmt).fetchone()


            values = {
                'start_time': row['start_time'] if row['start_time'] not in [None, ''] else datetime.strptime("00:00", "%H:%M").time(),
                'end_time': row['end_time'] if row['end_time'] not in [None, ''] else datetime.strptime("00:00", "%H:%M").time(),
                'fasting_hours': fasting_hours, 
                'sleep_hours': float(row['sleep_hours']) if row.get('sleep_hours') not in [None, ''] else 0.0,
                'calorie_deficit': int(row['calorie_deficit']) if row.get('calorie_deficit') not in [None, ''] else 0
            }

            if result:  # Row exists, perform update
                stmt = update(self.health_goals).values(**values).where(self.health_goals.c.id == 1)
                session.execute(stmt)
            else:  # Row does not exist, perform insert
                stmt = insert(self.health_goals).values(id=1, **values)  
                session.execute(stmt)

            session.commit()  
            print("Goals updated successfully")
        except Exception as e:
            session.rollback() 
            print(f"An error occurred during update: {e}")
        finally:
            session.close()  # Always close the session
                
                
 

    def fetch_goals(self):
        session = self.Session()  # Start a session
        try:
            query = "SELECT start_time, end_time, fasting_hours, sleep_hours, calorie_deficit FROM health_goals"
            df = pd.read_sql_query(query, con=self.engine)

            if df.empty:
                print("No data found in the database.")
            return df
        except Exception as e:
            print(f"An error occurred while fetching goals: {e}")
            return pd.DataFrame()  # Return an empty DataFrame in case of an error
        finally:
            session.close()

    def fetch_fasting_window(self):
        fasting_window = [self.fetch_goals()['start_time'].iloc[0], self.fetch_goals()['end_time'].iloc[0]]
        fasting_start = fasting_window[0]
        fasting_end = fasting_window[1]
        if fasting_start is None or fasting_end is None:
            return None
        
        fasting_display = f"{fasting_start} to {fasting_end}"
        return fasting_display
        
      
    def calculate_fasting_score(self, hours_fasted, fasting_goal):
        if fasting_goal == 0 or fasting_goal is None:
            return None  
        else:
            score = hours_fasted / fasting_goal
            return min(score, 1)  # Cap the score at 1 (or 100%)
    
    def calculate_calorie_deficit_score(self, actual_deficit, deficit_goal):
        if deficit_goal == 0 or deficit_goal is None:
            return None 
        elif actual_deficit <= 0:
            return 0  # Score is 0 if there's a calorie surplus or no deficit
        else:
            score = actual_deficit / deficit_goal
            return min(score, 1)  # Cap the score at 1 (or 100%)

    def calculate_sleep_score(self, actual_sleep, sleep_goal):
        if sleep_goal == 0 or sleep_goal is None:
            return None  
        else:
            score = actual_sleep / sleep_goal
            return min(score, 1)  # Cap the score at 1 (or 100%)
        
    

    def arithmetic_mean_of_ratios(self, r1, r2, r3):
        ratios = [r for r in [r1, r2, r3] if r is not None]
    
        if not ratios:
            return None  # If all scores are None, return None
        
        # Calculate the arithmetic mean
        arithmetic_mean = sum(ratios) / len(ratios)
        return arithmetic_mean
    
#CHANGE THIS
    def calculate_lifescore(self, hours_fasted, calorie_deficit, hours_slept, fasting_goal, deficit_goal, sleep_goal):
        # Check for None in actual values
        if hours_fasted in (None, '') or calorie_deficit in (None, '') or hours_slept in (None, ''):
            print("One or more actual values are None. Returning None for life score.")
            return None

       
        # Calculate individual scores
        fasting_score = self.calculate_fasting_score(hours_fasted, fasting_goal)
        sleep_score = self.calculate_sleep_score(hours_slept, sleep_goal)
        deficit_score = self.calculate_calorie_deficit_score(calorie_deficit, deficit_goal)

        # Calculate the life score
        life_score = self.arithmetic_mean_of_ratios(fasting_score, sleep_score, deficit_score)*100

        return life_score

             
db_manager = DatabaseManager()
db_manager.create_table()
goal_manager = GoalsManager()
goal_manager.create_table()



def submit_data(state):
    goals_df = goal_manager.fetch_goals()
    if goals_df.empty:
        print("No goals found. Cannot calculate life score.")
        return

    try:
        # Fetch calorie expenditure and sleep hours
        entry_date_str = state.entry_date.strftime("%Y-%m-%d")
        query = text("SELECT calorie_expenditure, sleep_hours FROM health_metrics WHERE date = :date_param")
        session = db_manager.Session()  # Start a session
        result = session.execute(query, {"date_param": entry_date_str}).fetchone()

        
        calorie_expenditure, sleep_hours = result if result else (0, 0.0)
        if calorie_expenditure is None or state.calorie_intake is None:
            calorie_deficit = None
        else:
            calorie_deficit = int(calorie_expenditure) - int(state.calorie_intake)

        # Handle sleep_hours
        sleep_hours = float(sleep_hours) if sleep_hours is not None else None

        # Handle fasting_hours
        fasting_hours = float(state.fasting_hours) if state.fasting_hours is not None else None

       
        lifescore = goal_manager.calculate_lifescore(
            fasting_hours,
            calorie_deficit,
            sleep_hours,
            goals_df.iloc[0]['fasting_hours'],
            goals_df.iloc[0]['calorie_deficit'],
            goals_df.iloc[0]['sleep_hours']
        )

        # Create a new DataFrame for the new entry
        new_entry = pd.DataFrame([{
            'date': state.entry_date,
            'calorie_expenditure': calorie_expenditure,
            'sleep_hours': sleep_hours,
            'weight': state.weight,
            'calorie_intake': state.calorie_intake,
            'fasting_hours': state.fasting_hours,
            'daily_lifescore': lifescore
        }])

       
        print("New Entry DataFrame:")
        print(new_entry)
        state.df_entry = new_entry.drop(columns=['sleep_hours', 'calorie_expenditure', 'daily_lifescore'], errors='ignore').reset_index(drop=True)




        # Upsert the data
        db_manager.upsert_health_metrics(new_entry, is_manualentry=True)

        # Commit session
        session.commit()
        print("Data submitted successfully.")
        
    except Exception as e:
        # Rollback session on failure
        session.rollback()
        print(f"An error occurred: {e}")
    finally:
        # Ensure the session is closed
        session.close()

df_fetcheddata = db_manager.fetch_data()
fasting_display=goal_manager.fetch_fasting_window()


def refresh_graphs(state):
    state.df_fetcheddata = db_manager.fetch_data()
    state.fasting_display=goal_manager.fetch_fasting_window()
    
    

def save_goals(state):
    print("save_goals called")
    try:
        print("Start Time:", state.start_time)
        print("End Time:", state.end_time)
        print("Sleep Goal:", state.sleep_goal)
        print("Calorie Deficit Goal:", state.calorie_deficit_goal)

        # Using a safe conversion function for floats and ints that handles None values.
        def safe_float(value):
            try:
                return float(value)
            except (TypeError, ValueError):
                return None

        def safe_int(value):
            try:
                return int(value)
            except (TypeError, ValueError):
                return None
        
        
        def safe_string(value):
            try: 
                return str(value)
            except (TypeError, ValueError):
                return None

        goals_data = pd.DataFrame([{
            'start_time': safe_string(state.start_time),
            'end_time': safe_string(state.end_time),
            'fasting_hours': None,
            'sleep_hours': safe_float(state.sleep_goal),
            'calorie_deficit': safe_int(state.calorie_deficit_goal)
        }])
        print("DataFrame:\n", goals_data)
        

        goal_manager.update_health_goals(goals_data)
        state.goals_data = goals_data.drop(columns=['fasting_hours'], errors='ignore').reset_index(drop=True)


    except Exception as e:
        
        print(f"An error occurred: {e}")
      
#fetch the goals data for display and no need for the fetched data to display    
#fasting window here
page = """
<center><h1 style="color:#ADD8E6;">Health Tracking Dashboard</h1></center>
<|Fasting Window:|text|>
<|{fasting_display}|>

<|layout|rows=2|gap=0px|>
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

<|>
<center><h2 style="color:#87CEEB;">Entries</h2></center>
<|{df_entry}|table|class_name=table-style|placeholder="No entries available"|>
|>

<|layout|rows=2|gap=20px|>
<|
<center><h2 style="color:#87CEEB;">Goals Manager</h2></center>

<h3>Fasting Start Time</h3>
<|{start_time}|input|type=text|placeholder="HH:MM"|label=Enter start time (HH:MM)|>

<h3>Fasting End Time</h3>
<|{end_time}|input|type=text|placeholder="HH:MM"|label=Enter end time (HH:MM)|>

<h3>Sleep Goal</h3>
<|{sleep_goal}|input|type=number|label=Enter sleep goal (hours)|>

<h3>Calorie Deficit Goal</h3>
<|{calorie_deficit_goal}|input|type=number|label=Enter calorie deficit goal (kcal)|>

<|Save|button|on_action=save_goals|class_name=button|>
|>

<|>
<center><h2 style="color:#87CEEB;">New goals</h2></center>
<|{goals_data}|table|class_name=table-style|placeholder="No goals set"|>
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

<|>
<center><h2 style="color:#87CEEB;">Lifescore Over Time</h2></center>
<|{df_fetcheddata}|chart|type=line|x=date|y=daily_lifescore|color=#00BFFF|title="Lifescore"|>
|>
"""


weight = 50.0
calorie_intake = 2000
fasting_hours = 16
start_time = '18:00'
end_time = '8:00'
sleep_goal = 8
calorie_deficit_goal = 500
from datetime import date
entry_date = datetime.today().date()
df_entry = pd.DataFrame(columns=["date", "weight", "calorie_intake", "fasting_hours", "daily_lifescore"])
goals_data= pd.DataFrame(columns=["start_time", "end_time", "sleep_hours", "calorie_deficit"])
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
            "df_entry": df_entry,
            "start_time": start_time,
            "end_time":end_time,
            "sleep_goal":sleep_goal,
            "calorie_deficit_goal":calorie_deficit_goal,
            "goals_data": goals_data,
            "fasting_display": fasting_display
            
        }
    )