import pandas as pd
from pathlib import Path
from catboost import CatBoostRegressor

BASE_DIR = Path(__file__).resolve().parent
MODEL_PATH = BASE_DIR / "models" / "valve_model.cbm"

FEATURE_ORDER = [
    "Service_Fluid",
    "Valve_Type",
    "Body_Material_Grade",
    "Actuator_Type",
    "End_Connection",
    "Seat_Type",
    "Pressure_Class_ASME",
    "NPS_inch",
    "Operating_Pressure_bar",
    "Operating_Temperature_C",
    "DeltaP_bar",
    "Cv"
]

CAT_COLS = [
    "Service_Fluid",
    "Valve_Type",
    "Body_Material_Grade",
    "Actuator_Type",
    "End_Connection",
    "Seat_Type"
]

NUM_COLS = [
    "Pressure_Class_ASME",
    "NPS_inch",
    "Operating_Pressure_bar",
    "Operating_Temperature_C",
    "DeltaP_bar",
    "Cv"
]

model = CatBoostRegressor()
model.load_model(str(MODEL_PATH))

def predict_price(input_data):
    row = {}

    for col in FEATURE_ORDER:
        if col not in input_data:
            raise ValueError(f"Missing required field: {col}")
        row[col] = input_data[col]

    df = pd.DataFrame([row])

    for col in CAT_COLS:
        df[col] = df[col].astype(str)

    for col in NUM_COLS:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    price = model.predict(df)[0]
    return float(price)