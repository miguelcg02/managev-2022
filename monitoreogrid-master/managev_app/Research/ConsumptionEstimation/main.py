import numpy as np
import pandas as pd
from matplotlib import pyplot as plt
from scipy.stats import stats
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import r2_score, mean_squared_error
from sklearn.preprocessing import MinMaxScaler
from pickle import dump

import statsmodels.api as sm
from statsmodels.formula.api import ols

from sklearn.model_selection import train_test_split

from managev_app.Research.ConsumptionEstimation.DataProcessing.lookup_tables import (
    ConsumptionModelLookup,
)
from managev_app.Research.ConsumptionEstimation.ExploratoryAnalysis.exporatory_analysis import (
    plot_exploratory_analysis,
)
from managev_app.Research.DataInteractor.data_fetcher import DataFetcher
from managev_app.Research.Route_segmentation.segmentation import SegmentTypes

y_name = "consumption_per_km"

query = (
    "select * from operation o where vehicle_id in"
    " ('GHW284', 'GVQ446', 'EGZ112', 'EPQ666', 'GVQ514')"
    " and o.operative_state > 0"
    " and elevation is not null ORDER BY vehicle_id desc, o.timestamp asc ;"
)

fetcher = DataFetcher(
    name="defensa_renault", query=query, segment_type=SegmentTypes.consumption
)
segments = fetcher.get_segments()

# Remove outliers
# 2.5 standard deviations away a given observation is from the mean
for col in ["kms", "min_acc", y_name, "consumption"]:
    segments = segments[(np.abs(stats.zscore(segments[col])) < 2.5)]

# Exploratory analysis
# plot_exploratory_analysis(segments)

app_lookups = ConsumptionModelLookup(segments, build_lookups=True, save_lookups=True)


train, test = train_test_split(segments, test_size=0.2)


train, train_measure = train_test_split(train, test_size=0.3)
test, test_measure = train_test_split(test, test_size=0.4)

# Since power is not available on prediction, we need a lookup to get it
train_power_lookup = ConsumptionModelLookup(train_measure, build_lookups=True)
train = train_power_lookup.fill_with_lookups(train)


# ------------------- Model Training -------------------------------#
x_cols = ["mean_power_usr", "mean_speed", "slope"]
model_cols = ["mean_power_usr", "mean_speed", "slope", y_name]
selected_ft = train[model_cols]

print("\n", selected_ft.corr(), "\n")

scaler = MinMaxScaler()
scaler.fit(train[model_cols])
dump(scaler, open("MachineLearningModels/scaler.pkl", "wb"))

x_scaler = MinMaxScaler()
x_scaler.fit(train[x_cols])
dump(x_scaler, open('MachineLearningModels/x_scaler.pkl', 'wb'))

train_scaled = pd.DataFrame(scaler.transform(train[model_cols]), columns=model_cols)

# For linear regression
formula = "consumption_per_km ~ mean_power_usr + mean_speed + slope -1"

lm_consumo = ols(formula=formula, data=train_scaled).fit()
print("\n", lm_consumo.summary(), "\n")

plt.figure(figsize=[20, 20])
fig = sm.graphics.plot_partregress_grid(lm_consumo)
plt.show()


#  ------------------------ Test the models ----------------------------------- #
test_power_lookup = ConsumptionModelLookup(test_measure, build_lookups=True)
test = test_power_lookup.fill_with_lookups(test)

test_scaled = pd.DataFrame(scaler.transform(test[model_cols]), columns=model_cols)

y_test = test_scaled[y_name]

predictions = lm_consumo.predict(test_scaled)


def model_evaluation(y_test, predictions):
    rmse = np.sqrt(mean_squared_error(y_test, predictions))
    print("\n", "RMSE =", rmse)

    rmspe = (np.sqrt(np.mean(np.square((y_test - predictions) / y_test)))) * 100
    print("RMSPE =", rmspe)

    rme = np.mean(np.abs((y_test - predictions) / y_test)) * 100
    print("RME =", rme)

    print("R2 =", r2_score(y_test, predictions))
    print("max error=", max(abs(y_test - predictions)), "\n")
    plt.figure()
    plt.scatter(x=y_test, y=predictions)
    plt.title("title")
    plt.xlabel("Real")
    plt.ylabel("Predicted")
    plt.show()


model_evaluation(y_test, predictions)


#  ---------------- Random Forest -----------------------#
X = train_scaled[x_cols].values
y = train_scaled[y_name].values

random_forest_regresor = RandomForestRegressor(
    n_estimators=149,
    max_depth=5,
    random_state=0,
    max_features="auto",
    criterion="mse",
    max_samples=0.219,
)

random_forest_regresor.fit(X, y)
y_pred = random_forest_regresor.predict(test_scaled[x_cols].values)

model_evaluation(y_test, y_pred)
dump(random_forest_regresor, open("MachineLearningModels/random_forest.pkl", "wb"))
