import pandas as pd
from catboost import CatBoostRegressor
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_absolute_error, r2_score

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

TARGET = "Price_INR"

print("Loading dataset...")
df = pd.read_csv("valve_pricing_dataset_2000.csv")

# Keep only the fields your API/UI will send
df = df[FEATURE_ORDER + [TARGET]].copy()

# Fill missing values
cat_cols = [
    "Service_Fluid",
    "Valve_Type",
    "Body_Material_Grade",
    "Actuator_Type",
    "End_Connection",
    "Seat_Type"
]

num_cols = [
    "Pressure_Class_ASME",
    "NPS_inch",
    "Operating_Pressure_bar",
    "Operating_Temperature_C",
    "DeltaP_bar",
    "Cv"
]

for col in cat_cols:
    df[col] = df[col].fillna("Unknown").astype(str)

for col in num_cols:
    df[col] = pd.to_numeric(df[col], errors="coerce")
    df[col] = df[col].fillna(df[col].median())

X = df[FEATURE_ORDER]
y = df[TARGET]

X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42
)

print("Training CatBoost model...")

model = CatBoostRegressor(
    iterations=1500,
    depth=8,
    learning_rate=0.05,
    loss_function="RMSE",
    verbose=200
)

model.fit(
    X_train,
    y_train,
    cat_features=cat_cols,
    eval_set=(X_test, y_test)
)

y_pred = model.predict(X_test)

print("\nModel performance")
print("MAE:", mean_absolute_error(y_test, y_pred))
print("R2 :", r2_score(y_test, y_pred))

# Save new model
model.save_model("models/valve_model.cbm")

print("\nNew model saved to models/valve_model.cbm")
print("Feature count:", len(FEATURE_ORDER))
print("Feature order:", FEATURE_ORDER)
print("Categorical features:", cat_cols)