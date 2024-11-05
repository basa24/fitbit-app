import datetime
import logging
import pandas as pd
import requests
import psycopg2
from sqlalchemy import create_engine, MetaData, Table, Column, Integer, Float, Date, exc, text
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.exc import SQLAlchemyError
from taipy.gui import Gui, notify

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
        
db_manager = DatabaseManager()
db_manager.create_table()

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