from sqlalchemy import create_engine, MetaData, Table, Column, Integer, Float, Time, select, insert, update
from sqlalchemy.orm import sessionmaker
from datetime import datetime, timedelta
import pandas as pd


class GoalsManager:
    def __init__(self, db_url="postgresql://postgres:Sarigama1@localhost:5432/postgres"):
        self.engine = create_engine(db_url)
        self.metadata = MetaData()
        self.metadata.bind = self.engine
        self.Session = sessionmaker(bind=self.engine)  # Session factory

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
            if not time_str:  # Handles None and empty string
                return None
            return datetime.strptime(time_str, "%H:%M").time()

        def calculate_fasting_hours(start_time, end_time):
            if not start_time or not end_time:
                return None
            today = datetime.today()
            start_datetime = datetime.combine(today, start_time)
            end_datetime = datetime.combine(today, end_time)
            if end_datetime < start_datetime:  # Handle end_time on the next day
                end_datetime += timedelta(days=1)
            fasting_duration = (end_datetime - start_datetime).seconds / 3600  # Convert to hours
            return round(fasting_duration, 2)

        # Parse times in the DataFrame
        df['start_time'] = df['start_time'].apply(parse_time)
        df['end_time'] = df['end_time'].apply(parse_time)

        # Extract first row
        row = df.iloc[0]
        fasting_hours = calculate_fasting_hours(row['start_time'], row['end_time'])

        session = self.Session()  # Start a session
        try:
            select_stmt = select(self.health_goals).where(self.health_goals.c.id == 1)
            result = session.execute(select_stmt).fetchone()

            values = {
                'start_time': row['start_time'],
                'end_time': row['end_time'],
                'fasting_hours': fasting_hours,
                'sleep_hours': float(row['sleep_hours']) if row.get('sleep_hours') not in [None, ''] else 0.0,
                'calorie_deficit': int(row['calorie_deficit']) if row.get('calorie_deficit') not in [None, ''] else 0
            }

            if result:  # Row exists, perform update
                stmt = update(self.health_goals).values(**values).where(self.health_goals.c.id == 1)
                session.execute(stmt)
            else:  # Row does not exist, perform insert
                stmt = insert(self.health_goals).values(id=1, **values)  # Explicitly set id=1
                session.execute(stmt)

            session.commit()
            print("Goals updated successfully")
        except Exception as e:
            session.rollback()
            print(f"An error occurred during update: {e}")
        finally:
            session.close()

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

    def calculate_fasting_score(self, hours_fasted, fasting_goal):
        if fasting_goal == 0 or fasting_goal is None:
            return None
        return min(hours_fasted / fasting_goal, 1)

    def calculate_calorie_deficit_score(self, actual_deficit, deficit_goal):
        if deficit_goal == 0 or deficit_goal is None:
            return None
        if actual_deficit <= 0:
            return 0
        return min(actual_deficit / deficit_goal, 1)

    def calculate_sleep_score(self, actual_sleep, sleep_goal):
        if sleep_goal == 0 or sleep_goal is None:
            return None
        return min(actual_sleep / sleep_goal, 1)

    def arithmetic_mean_of_ratios(self, r1, r2, r3):
        ratios = [r for r in [r1, r2, r3] if r is not None]
        if not ratios:
            return None
        return sum(ratios) / len(ratios)

    def calculate_lifescore(self, hours_fasted, calorie_deficit, hours_slept, fasting_goal, deficit_goal, sleep_goal):
        fasting_score = self.calculate_fasting_score(hours_fasted, fasting_goal)
        sleep_score = self.calculate_sleep_score(hours_slept, sleep_goal)
        deficit_score = self.calculate_calorie_deficit_score(calorie_deficit, deficit_goal)
        return self.arithmetic_mean_of_ratios(fasting_score, sleep_score, deficit_score)


# Example Usage
gm = GoalsManager()
cg = 500  # Calorie deficit goal
sg = 8    # Sleep goal
fg = 16   # Fasting goal
goals_df = gm.fetch_goals()
# Calculate a life score
lifescore = gm.calculate_lifescore(
            8,
            500,
            6,
            goals_df.iloc[0]['fasting_hours'],
            goals_df.iloc[0]['calorie_deficit'],
            goals_df.iloc[0]['sleep_hours']
        )
# Fetch goals from the database
print(gm.fetch_goals())
print(lifescore)