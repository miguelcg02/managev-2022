import datetime
import logging
import math
import os
from pickle import load

import geopy
import googlemaps
import networkx as nw
import numpy as np
import osmnx as ox 
import pandas as pd
import pytz
from flask import current_app

from managev_app.Research.ConsumptionEstimation.DataProcessing.lookup_tables import (
    ConsumptionModelLookup,
)
from managev_app.Research.ConsumptionEstimation.Models.consumption_models import (
    WangModel,
)

logger = logging.Logger(__name__)
google_sdk_key = os.environ.get("GOOGLE_SDK_KEY")

try:
    gmaps = googlemaps.Client(key=google_sdk_key)
except ValueError:
    logger.info("Google sdk key not set properly")


def get_segments(g_json):
    # The large segments taken from google
    steps = g_json[0]["legs"][0]["steps"]
    g_df = pd.DataFrame(steps)
    final_df = pd.DataFrame()
    for index, row in g_df.iterrows():
        m = row["distance"]["value"]
        t = row["duration"]["value"]

        speed_kmh = (m / t) * 3.6
        n_segments = int(math.sqrt(m))
        line_path = gmaps.elevation_along_path(row["polyline"]["points"], n_segments)
        line_df = pd.DataFrame(line_path)
        line_df["m"] = m
        line_df["mean_speed"] = speed_kmh

        final_df = final_df.append(line_df)

    final_df.reset_index(drop=True, inplace=True)

    aux_loc = final_df["location"][1:].reset_index(drop=True)
    # Repita valor en la última posición
    aux_loc._set_value(len(aux_loc), g_df.iloc[-1]["end_location"])
    final_df["end_location"] = aux_loc

    # para la altitud
    aux_ele = final_df["elevation"][1:].reset_index(drop=True)
    # Repita valor en la última posición
    aux_ele._set_value(len(aux_ele), final_df["elevation"].iloc[-1])
    final_df["end_elevation"] = aux_ele

    end_lat = []
    end_lng = []
    distances = []
    slopes = []
    travel_time = []
    # Para cada polilinea se calculan las distancias entre los 10 puntos
    for line_index, line_row in final_df.iterrows():

        end_lat.append(line_row["end_location"]["lat"])
        end_lng.append(line_row["end_location"]["lng"])

        coord1 = (line_row["location"]["lat"], line_row["location"]["lng"])
        coord2 = (line_row["end_location"]["lat"], line_row["end_location"]["lng"])
        run = geopy.distance.great_circle(coord1, coord2).km
        travel_time.append(3600 * run / line_row["mean_speed"])

        rise = line_row["end_elevation"] - line_row["elevation"]
        distance = math.sqrt((run * 1000) ** 2 + rise ** 2)  # m
        distances.append(distance / 1000)  # km

        try:
            slope = math.atan(rise / (run * 1000))  # radians
        except ZeroDivisionError:
            slope = 0
        degree = (slope * 180) / math.pi

        slopes.append(degree)

    final_df["slope"] = slopes
    final_df["kms"] = distances
    final_df["end_lat"] = end_lat
    final_df["end_lng"] = end_lng
    final_df["travel_time"] = travel_time
    final_df["slope_cat"] = pd.cut(final_df["slope"], np.arange(-10, 10.1, 5)).astype(
        "string"
    )
    final_df["slope_cat"] = final_df["slope_cat"].astype("string")

    final_df = final_df.reset_index(drop=True)
    return final_df


def calc_shortest_path(G, lat_o, lon_o, lat_d, lon_d):
    point_o = (lat_o, lon_o)
    point_d = (lat_d, lon_d)
    nearest_node_o = ox.distance.get_nearest_node(
        G, point_o, method="haversine", return_dist=True
    )
    nearest_node_d = ox.distance.get_nearest_node(
        G, point_d, method="haversine", return_dist=True
    )
    try:
        shortest_path = nw.algorithms.shortest_paths.weighted.dijkstra_path(
            G=G,
            source=nearest_node_o[0],
            target=nearest_node_d[0],
            weight="travel_time",
        )
        traffic_lights = 0
        for node in shortest_path:
            try:
                G.nodes[node]["highway"]
                traffic_lights += 1
            except Exception:
                pass

        return shortest_path, traffic_lights
    except Exception:
        return 0, 0


def calculate_segments_consumption(
    segments,
    base_path=os.path.join(current_app.root_path) + "/Research/ConsumptionEstimation",
    user="Santiago_Echavarria_01",
):
    segments["id"] = segments.index
    segments["mass"] = 1604
    segments["user_name"] = user

    app_lookups = ConsumptionModelLookup(segments)
    segments = app_lookups.fill_with_lookups(segments)

    segments = segments.sort_values(by=["id"])
    # Apply scaling
    scaler = load(open(base_path + "/MachineLearningModels/scaler.pkl", "rb"))
    x_scaler = load(open(base_path + "/MachineLearningModels/x_scaler.pkl", "rb"))

    columns = [
        "mean_power_usr",
        "mean_speed",
        "slope",
    ]
    segments_scaled = pd.DataFrame(x_scaler.transform(segments[columns]), columns=columns)

    # load random forest regresor
    r_forest_reg = load(
        open(
            base_path + "/MachineLearningModels/random_forest.pkl",
            "rb",
        )
    )

    # Load XGBoost model
    xgb_reg = load(
        open(base_path + "/MachineLearningModels/xg_reg_model.pickle.dat", "rb")
    )

    # Load linear model
    linear_regr_sklearn = load(
        open(base_path + "/MachineLearningModels/linear_regr_sklearn.pkl", "rb")
    )

    # load ANN regressor
    ann_reg = load(open(base_path + "/MachineLearningModels/ann_regr.pkl", "rb"))

    models = {
        "linear": linear_regr_sklearn,
        "RF": r_forest_reg,
        "XGB": xgb_reg,
        "ANN": ann_reg,
    }

    for mod in models:
        segments_scaled["consumption_per_km"] = models[mod].predict(
            segments_scaled[columns].values
        )

        # Apply inverse scaling
        p_pred = pd.DataFrame(
            scaler.inverse_transform(segments_scaled),
            columns=segments_scaled.columns,
        )
        segments["consumption_per_km_" + mod] = p_pred["consumption_per_km"] * 1000

        segments["consumptionWh_" + mod] = (
            segments["consumption_per_km_" + mod] * segments["kms"]
        )

    estimated_time = segments["travel_time"].sum() / 60
    wang_model = WangModel()
    wang_consumption_list = wang_model.compute_consumption(segments)
    wang_consumption = np.nansum(wang_consumption_list).round(3)

    model_to_consumption_map = {
        mod: (segments[f"consumptionWh_{mod}"].sum() / 1000).round(3)
        for mod in models.keys()
    }
    model_to_consumption_map["wang"] = wang_consumption
    return (
        model_to_consumption_map,
        estimated_time.round(3),
    )


if __name__ == "__main__":
    path = os.path.join(current_app.root_path) + "/Research/ConsumptionEstimation"
    now = datetime.datetime.now(pytz.timezone("America/Bogota"))
    test_date = datetime.datetime.strptime("2020-08-12 10:26:45", "%Y-%m-%d %H:%M:%S")
    a = gmaps.directions(
        origin=(6.201123674133, -75.5757960580202),
        destination=(6.1976485409797535, -75.55707688749959),
        mode="driving",
        alternatives=False,
        departure_time=now,
        traffic_model="optimistic",
    )

    df = get_segments(a)

    consumption, time, df = calculate_segments_consumption(
        segments=df, base_path=path, soc=100, user="Santiago_Echavarria_01"
    )

    print("Consumo estimado", consumption, "kWh")
