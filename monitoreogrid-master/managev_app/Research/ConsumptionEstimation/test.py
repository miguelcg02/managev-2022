import os
import time
from pickle import load

import numpy as np
import pandas as pd
import plotly
import plotly.graph_objects as go
import statsmodels.api as sm

from managev_app import app
from managev_app.Research.Route_segmentation.segmentation import (
    feature_extraction,
    generate_features_df,
)

path = os.path.join(app.root_path)

# Data cleaning
op = pd.read_csv(path + "/DataBackup/updated_old_vehicle_operation.csv")
op = op.dropna(subset=["power_kw", "odometer"])
op = op[(op["odometer"] > 1)]
op.drop(columns=["placa"], inplace=True)


def gen_test_traces(df):
    try:
        df.drop(columns="Unnamed: 0", inplace=True)
        df.drop(columns="id", inplace=True)
    except KeyError:
        pass
    trace_id = 1
    aux_trace_id = -1

    consolidar_id = 1
    testear_id = -1
    test_array = np.array([])

    trace_array = np.array([])
    suma = 0
    suma_testing = 0
    old_name = ""
    old_date = df["timestamp2"].iloc[0]

    for index, row in df.iterrows():
        suma = suma + row["run"]
        suma_testing = suma_testing + row["run"]
        trace_array = np.append(trace_array, aux_trace_id)

        nan = row["name"] != row["name"]

        # 2 horas sin transmitir
        if row["timestamp2"] - old_date > 3600:
            suma = 0
            trace_id += 1
            aux_trace_id -= 1
            consolidar_id += 1
            testear_id -= 1
            suma_testing = 0

        old_date = row["timestamp2"]

        # Si lleva más de 20km en ruta
        if suma_testing >= 25000 and row["operative_state"] < 3:
            test_array = np.append(test_array, testear_id)
            if suma_testing >= 50000:
                consolidar_id += 1
                testear_id -= 1
                suma_testing = 0
        elif (suma_testing < 25000) and row["operative_state"] < 3:
            test_array = np.append(test_array, consolidar_id)
        else:
            test_array = np.append(test_array, 0)

        # feature traces of more than 100m
        if suma > 1200:
            trace_array = np.where(trace_array == aux_trace_id, trace_id, trace_array)

        # Si cambia de vía - empiece un nuevo tramo se escoge 1000 para ver cambios en consumo
        if (
            suma >= 1200
            or row["operative_state"] >= 3
            or (old_name != row["name"] and not nan)
        ):  # pendiente
            suma = 0
            trace_id += 1
            aux_trace_id -= 1

        old_name = row["name"]

    print(trace_array)
    try:
        df.drop(["trace_id"], axis=1, inplace=True)
    except KeyError:
        pass
    df.insert(2, "trace_id", trace_array, True)

    try:
        df.drop(["test_id"], axis=1, inplace=True)
    except KeyError:
        pass
    df.insert(3, "test_id", test_array, True)
    return df


op_trace_test_index = gen_test_traces(op)

classifier_df = op_trace_test_index[op_trace_test_index["trace_id"] > 0]
segments = classifier_df.groupby(["trace_id"])

df_to_consolidate = op_trace_test_index[op_trace_test_index["test_id"] > 0]
df_to_test = op_trace_test_index[op_trace_test_index["test_id"] < 0]


def map_plot(df_to_m, df_to_t, i):
    fig = go.Figure(
        go.Scattermapbox(
            mode="markers+lines",
            lon=df_to_m["longitude"],
            lat=df_to_m["latitude"],
            marker={"size": 10},
        )
    )

    fig.add_trace(
        go.Scattermapbox(
            mode="markers+lines",
            lon=df_to_t["longitude"],
            lat=df_to_t["latitude"],
            marker={"size": 10},
        )
    )

    fig.update_layout(
        margin={"l": 0, "t": 0, "b": 0, "r": 0},
        mapbox={
            "center": {"lon": -75.58, "lat": 6.151},
            "style": "stamen-terrain",
            "zoom": 10,
        },
        title="test " + str(i),
    )

    plotly.offline.plot(fig)
    time.sleep(2)


# ------------------------- Measuring and testing groups generation ---------------------------------------#
lst_measure = []
lst_test = []

for index, segment in segments:
    if len(segment) > 1 and index > 0:
        if abs(segment["test_id"].iloc[0]) > 3:
            if segment["test_id"].iloc[0] > 0:
                lst_measure.append(feature_extraction(segment))

            if segment["test_id"].iloc[0] < 0:
                lst_test.append(feature_extraction(segment))

        elif abs(segment["test_id"].iloc[0]) > 15:
            break


measure_segments = generate_features_df(lst_measure)
test_segments = generate_features_df(lst_test)

# Assign the slope categorical variable
measure_segments["slope_cat"] = pd.cut(
    measure_segments["slope"], np.arange(-8.5, 8.6, 3.4)
).astype("string")
test_segments["slope_cat"] = pd.cut(
    test_segments["slope"], np.arange(-8.5, 8.6, 3.4)
).astype("string")

# Load the mean power feature for all users
mean_max_pot_by_slope = pd.read_csv(
    path + "/Develops/ConsumptionEstimation/mean_max_features_by_slope.csv",
    index_col=0,
)
mean_max_pot_by_slope["slope_cat"] = mean_max_pot_by_slope["slope_cat"].astype("string")


def test(i):

    # First group of measurement segments
    m = measure_segments[measure_segments["test_id"] == i]
    m = pd.merge(
        left=m, right=mean_max_pot_by_slope, left_on="slope_cat", right_on="slope_cat"
    )

    # Generate user attribute from measured segments
    slope_user_groups = m.groupby(by=["slope_cat", "user_id"])
    mean_max_p_per_user_and_slope = (
        slope_user_groups[["max_power"]].mean().reset_index()
    )
    mean_max_p_per_user_and_slope.rename(
        columns={"max_power": "mean_max_power_usr", "slope": "slope_cat"}, inplace=True
    )

    # -------------------------- Add atributes to prediction dataset--------------------------------------------
    p = test_segments[test_segments["test_id"] == -i]
    p = pd.merge(
        left=p,
        right=mean_max_pot_by_slope,
        left_on=["slope_cat"],
        right_on=["slope_cat"],
    )

    aux_p = pd.merge(
        left=p,
        right=mean_max_p_per_user_and_slope,
        left_on=["slope_cat", "user_id"],
        right_on=["slope_cat", "user_id"],
    )

    if len(aux_p) > 0:
        p = aux_p
    else:
        p["mean_max_power_usr"] = np.nan

    # p['mean_max_power_usr'] = np.nan
    p["mean_max_power_usr"] = p.apply(
        lambda row: row["mean_max_power"]
        if np.isnan(row["mean_max_power_usr"])
        else row["mean_max_power_usr"],
        axis=1,
    )

    # Apply scaling
    scaler = load(open(path + "/Develops/ConsumptionEstimation/scaler_lm.pkl", "rb"))
    columns = ["mean_max_power_usr", "mean_soc", "nominal_speed", "slope"]
    p_scaled = pd.DataFrame(scaler.transform(p[columns]), columns=columns)

    # Load linear model
    lm_cons = sm.load(path + "/Develops/ConsumptionEstimation/lm_consumo.pickle")

    # load randon forest regressor
    r_forest_reg = load(
        open(path + "/Develops/ConsumptionEstimation/randForest_model.pkl", "rb")
    )

    # load ANN regressor
    ann_reg = load(open(path + "/Develops/ConsumptionEstimation/ann_regr.pkl", "rb"))

    # Apply linear model
    # p_scaled['consumption_per_km'] = lm_cons.predict(p_scaled)
    # p_scaled['consumption_per_km'] = 0.873 * p_scaled['slope'] + 0.1295 * p_scaled['mean_max_power_usr'] - 0.0721 * \
    #                                  p_scaled['mean_speed']

    p_scaled["consumption_per_km"] = ann_reg.predict(
        p_scaled[["mean_max_power_usr", "mean_soc", "nominal_speed", "slope"]].values
    )

    # Load inverse scaler
    scaler_inv = load(open(path + "/Develops/ConsumptionEstimation/scaler.pkl", "rb"))

    # Apply inverse scaling
    p_pred = pd.DataFrame(
        scaler_inv.inverse_transform(p_scaled), columns=p_scaled.columns
    )

    # Multiply by segment length
    p["consumption_pred"] = p_pred["consumption_per_km"] * p["kms"]

    # plot
    p["end_time"] = pd.to_datetime(p.end_time)
    p = p.sort_values(by=["end_time"])

    # Plots of estimated segment - by - segment (not accumulating)
    fig = go.Figure(
        [go.Scatter(x=p["end_time"], y=p["consumption_pred"], name="Predicted")]
    )
    fig.add_trace(go.Scatter(x=p["end_time"], y=p["consumption"], name="Measured"))
    fig.update_layout(
        title="Model evaluation for route " + str(i),
        xaxis_title="Time",
        yaxis_title="kWh/km",
    )
    plotly.offline.plot(fig)

    time.sleep(2)

    fig2 = go.Figure(
        [
            go.Scatter(
                x=p["end_time"], y=p["consumption_pred"].cumsum(), name="Predicted"
            )
        ]
    )
    fig2.add_trace(
        go.Scatter(x=p["end_time"], y=p["consumption"].cumsum(), name="Measured")
    )
    fig2.update_layout(
        title="Model evaluation for route " + str(i),
        xaxis_title="Time",
        yaxis_title="kWh/km",
    )
    plotly.offline.plot(fig2)

    time.sleep(2)
    error = (
        100
        * (p["consumption"].cumsum().iloc[-1] - p["consumption_pred"].cumsum().iloc[-1])
        / p["consumption"].cumsum().iloc[-1]
    )

    print("error =", abs(error), "%")

    return abs(error)


# Test for each test_case
l = []
for t in range(5, 14):  # [5, 7, 10, 13, 15]:

    plot_consolidate = df_to_consolidate[df_to_consolidate["test_id"] == t].reset_index(
        drop=True
    )
    plot_test = df_to_test[df_to_test["test_id"] == -t].reset_index(drop=True)
    if (len(plot_consolidate) > 1) and (len(plot_test) > 1):
        print(
            "measure group",
            t,
            "length=",
            plot_consolidate["odometer"].iloc[-1]
            - plot_consolidate["odometer"].iloc[0],
        )
        print(
            "test group no:",
            t,
            "lenght=",
            plot_test["odometer"].iloc[-1] - plot_test["odometer"].iloc[0],
        )
        e = test(t)
        l.append(e)

print("mean_error =", np.mean(l))
print("min_error =", np.min(l))
print("max_error =", np.max(l))
