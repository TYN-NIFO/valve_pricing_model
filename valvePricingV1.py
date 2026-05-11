import pandas as pd
import numpy as np
import psycopg2
import matplotlib.pyplot as plt
import seaborn as sns
import uuid

from catboost import CatBoostRegressor
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

# ===============================
# DATABASE CONNECTION
# ===============================

DB_CONFIG = {
    "host": "localhost",
    "port": 5432,
    "dbname": "valve_ml_db",
    "user": "postgres",
    "password": "264638"
}

def save_to_db(data):

    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cur = conn.cursor()

        # SQL QUERY
        query = """
        INSERT INTO valve_price_predictions(
            valve_id,
            service_fluid,
            valve_type,
            body_material_grade,
            actuator_type,
            end_connection,
            seat_type,
            pressure_class_asme,
            nps_inch,
            operating_pressure_bar,
            operating_temperature_c,
            deltap_bar,
            cv,
            predicted_price_inr,
            confidence_score,
            lower_price_range,
            upper_price_range,
            model_name
        )
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
        """

        cur.execute(query, data)

        conn.commit()
        cur.close()
        conn.close()

        print("Prediction saved to PostgreSQL")

    except Exception as e:
        print("Database Error:", e)

# ===============================
# LOAD DATASET
# ===============================

print("Loading Dataset...")

df = pd.read_csv("valve_pricing_dataset_2000.csv")

# Replace missing categorical values
cat_cols = df.select_dtypes(include=["object"]).columns

for col in cat_cols:
    df[col] = df[col].fillna("Unknown")

# Replace missing numeric values
num_cols = df.select_dtypes(include=["float64","int64"]).columns

for col in num_cols:
    df[col] = df[col].fillna(df[col].median())

TARGET = "Price_INR"

X = df.drop(columns=[TARGET])
y = df[TARGET]

cat_cols = X.select_dtypes(include=["object"]).columns.tolist()

# ===============================
# TRAIN TEST SPLIT
# ===============================

X_train, X_test, y_train, y_test = train_test_split(
    X,y,test_size=0.2,random_state=42
)

print("Training CatBoost Model...")

model = CatBoostRegressor(
    iterations=1500,
    depth=8,
    learning_rate=0.05,
    loss_function="RMSE",
    verbose=200
)

model.fit(X_train,y_train,cat_features=cat_cols)

# ===============================
# MODEL EVALUATION
# ===============================

y_pred = model.predict(X_test)

mae = mean_absolute_error(y_test,y_pred)
rmse = np.sqrt(mean_squared_error(y_test,y_pred))
r2 = r2_score(y_test,y_pred)

print("\nMODEL PERFORMANCE")
print("-----------------")
print("MAE:",mae)
print("RMSE:",rmse)
print("R2:",r2)

# ===============================
# VISUALIZATION
# ===============================

plt.figure(figsize=(6,6))
plt.scatter(y_test,y_pred,alpha=0.6)

plt.xlabel("Actual Price")
plt.ylabel("Predicted Price")

plt.title("Actual vs Predicted Valve Price")

plt.plot(
    [y_test.min(),y_test.max()],
    [y_test.min(),y_test.max()],
    color="red"
)

plt.show()

# Error Distribution

residuals = y_test - y_pred

plt.figure(figsize=(7,5))

sns.histplot(residuals,bins=30,kde=True)

plt.title("Prediction Error Distribution")

plt.show()

# Feature Importance

importance = model.get_feature_importance()

fi = pd.DataFrame({
    "feature":X.columns,
    "importance":importance
}).sort_values(by="importance",ascending=False)

plt.figure(figsize=(10,6))

sns.barplot(
    data=fi.head(10),
    x="importance",
    y="feature"
)

plt.title("Top Features Affecting Valve Price")

plt.show()

# ===============================
# USER INTERACTION
# ===============================

def ask_option(question,options):

    print("\n",question)

    for i,o in enumerate(options):
        print(i+1,o)

    choice = int(input("Choose option:"))

    return options[choice-1]

print("\n=========== VALVE PRICE PREDICTOR ===========")

service = ask_option(
    "Select Service Fluid",
    df["Service_Fluid"].unique()
)

valve_type = ask_option(
    "Select Valve Type",
    df["Valve_Type"].unique()
)

material = ask_option(
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

nps = float(input("Enter Valve Size (NPS inch):"))

pressure = float(input("Operating Pressure (bar):"))

temperature = float(input("Operating Temperature (C):"))

deltaP = float(input("Pressure Drop ΔP:"))

cv = float(input("Flow coefficient Cv:"))

# ===============================
# CREATE INPUT DATAFRAME
# ===============================

user_input = pd.DataFrame({

"Service_Fluid":[service],
"Valve_Type":[valve_type],
"Body_Material_Grade":[material],
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

# Fill missing columns

for col in X.columns:

    if col not in user_input.columns:

        if col in cat_cols:
            user_input[col] = df[col].mode()[0]
        else:
            user_input[col] = df[col].median()

user_input = user_input[X.columns]

# ===============================
# PREDICT PRICE
# ===============================

pred_price = model.predict(user_input)[0]

# Confidence estimation

confidence = max(
    50,
    min(95,100 - (np.std(y)/np.mean(y))*10)
)

print("\n============================")
print("Estimated Valve Price: ₹{:,.0f}".format(pred_price))
print("Confidence Score:",confidence,"%")
print("============================")

# ===============================
# SAVE TO DATABASE
# ===============================

valve_id = str(uuid.uuid4())

data = (
valve_id,
str(service),
str(valve_type),
str(material),
str(actuator),
str(end_connection),
str(seat),
int(pressure_class),
float(nps),
float(pressure),
float(temperature),
float(deltaP),
float(cv),
float(pred_price),
float(confidence),
float(pred_price * 0.9),
float(pred_price * 1.1),
"CatBoost_V1"
)

save_to_db(data)