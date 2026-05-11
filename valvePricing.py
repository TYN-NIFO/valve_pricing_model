DB_CONFIG = {
    "host": "localhost",
    "port": 5432,
    "dbname": "valve_ml_db",
    "user": "postgres",
    "password": "264638"
}

import pandas as pd
import numpy as np
from catboost import CatBoostRegressor, Pool
from sklearn.model_selection import train_test_split

print("Loading dataset...")

# Load CSV from same folder
df = pd.read_csv("valve_pricing_dataset_2000.csv")

# Identify categorical columns
cat_cols = df.select_dtypes(include=["object"]).columns.tolist()

# Fill missing categorical values
for col in cat_cols:
    df[col] = df[col].fillna("Unknown")

# Fill missing numeric values
num_cols = df.select_dtypes(include=["int64","float64"]).columns.tolist()
for col in num_cols:
    df[col] = df[col].fillna(df[col].median())

TARGET = "Price_INR"

# Split features and target
X = df.drop(columns=[TARGET])
y = df[TARGET]

# Identify categorical columns
cat_cols = X.select_dtypes(include=["object"]).columns.tolist()

# Train test split
X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42
)

train_pool = Pool(X_train, y_train, cat_features=cat_cols)
test_pool = Pool(X_test, y_test, cat_features=cat_cols)

print("Training CatBoost Model...")

model = CatBoostRegressor(
    iterations=1500,
    learning_rate=0.05,
    depth=8,
    loss_function="RMSE",
    verbose=200
)

model.fit(train_pool, eval_set=test_pool)

print("\nModel Training Complete")

import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

# Predict on test data
y_pred = model.predict(X_test)

# Evaluation metrics
mae = mean_absolute_error(y_test, y_pred)
rmse = mean_squared_error(y_test, y_pred)**0.5
r2 = r2_score(y_test, y_pred)

print("\nMODEL PERFORMANCE")
print("---------------------")
print("MAE :", mae)
print("RMSE:", rmse)
print("R2 Score:", r2)

# =========================
# USER INPUT SECTION
# =========================

def ask_option(question, options):
    print("\n", question)
    for i, o in enumerate(options):
        print(f"{i+1}. {o}")
        
    choice = int(input("Select option: "))
    return options[choice-1]


print("\n\n====== VALVE PRICE PREDICTION ======")

service = ask_option(
    "Select Service Fluid",
    df["Service_Fluid"].unique()
)

valve_type = ask_option(
    "Select Valve Type",
    df["Valve_Type"].unique()
)

body_material = ask_option(
    "Select Body Material",
    df["Body_Material_Grade"].unique()
)

actuator = ask_option(
    "Select Actuator Type",
    df["Actuator_Type"].unique()
)

end_connection = ask_option(
    "Select End Connection",
    df["End_Connection"].unique()
)

seat = ask_option(
    "Select Seat Type",
    df["Seat_Type"].unique()
)

pressure_class = ask_option(
    "Select Pressure Class",
    df["Pressure_Class_ASME"].unique()
)

nps = float(input("\nEnter Valve Size (NPS inch): "))
pressure = float(input("Operating Pressure (bar): "))
temperature = float(input("Operating Temperature (C): "))
deltaP = float(input("Pressure Drop ΔP (bar): "))
cv = float(input("Flow coefficient Cv: "))

# Create input dataframe
user_data = pd.DataFrame({
    "Service_Fluid":[service],
    "Valve_Type":[valve_type],
    "Body_Material_Grade":[body_material],
    "Actuator_Type":[actuator],
    "End_Connection":[end_connection],
    "Seat_Type":[seat],
    "Pressure_Class_ASME":[pressure_class],
    "NPS_inch":[nps],
    "Operating_Pressure_bar":[pressure],
    "Operating_Temperature_C":[temperature],
    "DeltaP_bar":[deltaP],
    "Cv":[cv]
})

# Fill missing columns with median/mode
for col in X.columns:
    
    if col not in user_data.columns:
        
        if col in cat_cols:
            user_data[col] = df[col].mode()[0]
        else:
            user_data[col] = df[col].median()

# Arrange column order
user_data = user_data[X.columns]

# Predict price
pred_price = model.predict(user_data)[0]

# Confidence (simple approximation)
confidence = max(50, min(95, 100 - (np.std(y)/np.mean(y))*10))

print("\n===============================")
print(f"Estimated Valve Price : ₹{pred_price:,.0f}")
print(f"Confidence Score      : {confidence:.1f}%")
print("===============================")