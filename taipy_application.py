from taipy.gui import Gui
import pandas as pd

# Dummy data for illustration purposes
health_data = {
    "date": pd.date_range(start="2024-09-01", periods=30, freq="D"),
    "weight": [70 + i * 0.1 for i in range(30)],
    "calorie_intake": [2000 + (i % 5) * 50 for i in range(30)],
    "calorie_expenditure": [1800 + (i % 4) * 70 for i in range(30)],
    "sleep_hours": [7 + (i % 3) * 0.5 for i in range(30)],
    "sleep_quality": [(i % 3) * 10 + 70 for i in range(30)]  # Simulated sleep quality metric
}

# Calculate Calorie Deficit
health_data["calorie_deficit"] = [
    health_data["calorie_expenditure"][i] - health_data["calorie_intake"][i] for i in range(30)
]

df = pd.DataFrame(health_data)

# Layout of the Dashboard in Dark Mode with a blueish color theme
page = """
<center><h1 style="color:#ADD8E6;">Health Tracking Dashboard</h1></center>

<|layout|columns=1|gap=10px|
<|
<|card|
<center><h2 style="color:#87CEEB;">Enter Your Health Data</h2></center>
<|layout|columns=2|gap=5px|
<|input|type=date|bind=entry_date|label=Date:|>
<|input|type=number|bind=weight|label=Weight (kg):|step=0.1|>
<|input|type=number|bind=calorie_intake|label=Calorie Intake (kcal):|>
<|input|type=number|bind=fasting_hours|label=Fasting Hours:|>
<|button|label=Submit Data|on_action=submit_health_data|>
|>
|>



#GRAPHS
<|layout|columns=1|gap=10px|
<|
<center><h2 style="color:#87CEEB;">Weight Over Time</h2></center>
<|{df}|chart|type=line|x=date|y=weight|color=#4682B4|title="Weight Tracking"|>
|>

<|
<center><h2 style="color:#87CEEB;">Calorie Intake vs. Expenditure</h2></center>
<|{df}|chart|type=bar|x=date|y[1]=calorie_intake|y[2]=calorie_expenditure|color[1]=#6495ED|color[2]=#4169E1|title="Calorie Metrics"|>
|>

<|
<center><h2 style="color:#87CEEB;">Calorie Deficit Over Time</h2></center>
<|{df}|chart|type=line|x=date|y=calorie_deficit|color=#1E90FF|title="Calorie Deficit Tracking"|>
|>

<|
<center><h2 style="color:#87CEEB;">Sleep Hours Over Time</h2></center>
<|{df}|chart|type=line|x=date|y=sleep_hours|color=#00BFFF|title="Sleep Hours"|>
|>

<|
<center><h2 style="color:#87CEEB;">Sleep Quality Over Time</h2></center>
<|{df}|chart|type=line|x=date|y=sleep_quality|color=#87CEFA|title="Sleep Quality"|>
|>

<|
<center><h2 style="color:#87CEEB;">Set Health Goals</h2></center>
<|Goal for Calorie Intake|number|value=2200|min=1000|max=4000|step=50|style="background-color:#f0f0f0; color:black;"|>
<|Goal for Sleep Hours|slider|min=6|max=9|value=8|style="background-color:#f0f0f0; color:black;"|>
|>
|>
"""

# Create GUI using Taipy
gui = Gui(page=page)

# Run the GUI in dark mode
gui.run(dark_mode=True, port=5000)
