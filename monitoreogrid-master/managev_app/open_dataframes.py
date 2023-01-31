import os

import numpy as np
import pandas as pd

from flask import current_app
from scipy.stats import stats

from managev_app import db
from managev_app.models import Operation

min_col_size = 0
max_col_size = 150


def get_stations():
    file = os.path.join(current_app.root_path, "stations.json")
    df = pd.read_json(file)
    df.columns = ["name", "latitude", "longitude", "charger_types"]
    return df


def get_zones():
    file = os.path.join(current_app.root_path, "zones.csv")
    zones = pd.read_csv(file)
    zones = zones[["name", "longitude", "latitude"]]
    return zones


def concat(df1, df2):
    result = pd.concat([df1, df2], axis=1, join="inner")
    return result


def filter_by_column_value(df, colname, value):
    s = df[df[colname] == value]
    return s


def pretty_var_name(var_name):
    doc_var = os.path.join(current_app.root_path, "variables.csv")
    variables = pd.read_csv(doc_var, index_col="id")
    return variables.var_pretty[variables["var"] == var_name].values[0]


def form_var(titles):
    doc_var = os.path.join(current_app.root_path, "variables.csv")
    variables = pd.read_csv(doc_var, index_col="id")
    groups_list = []
    for i in range(len(variables)):
        if variables["var"][i] in titles:
            if variables["var"][i] in ["longitude", "latitude"]:
                continue
            groups_list.insert(i, [(variables["var"][i]), (variables["var_pretty"][i])])
    return groups_list


def get_lines(vehicle, d1, h1, h2):
    query = (
        "SELECT latitude, longitude from operation WHERE "
        ' latitude != 0 AND longitude != 0 AND vehicle_id = "'
        + str(vehicle.placa)
        + '" AND timestamp BETWEEN "'
        + str(d1)
        + " "
        + str(h1)[:8]
        + '" and "'
        + str(d1)
        + " "
        + str(h2)[:8]
        + '"'
    )

    df = pd.read_sql_query(query, db.engine)
    lat2 = df["latitude"].iloc[1:]
    if len(lat2) == 0:
        return df
    else:
        aux1 = lat2.append(pd.Series(df["latitude"].iloc[-1]), ignore_index=True)
        df["latitude2"] = aux1

        lon2 = df["longitude"].iloc[1:]
        aux2 = lon2.append(pd.Series(df["longitude"].iloc[-1]), ignore_index=True)
        df["longitude2"] = aux2
        df = df.drop(df.tail(1).index)
        df = df.drop(df.head(1).index)
        return df


def get_heights(vehicle, var, d1, h1, h2):

    query = (
        "SELECT timestamp, "
        + var
        + ', latitude, longitude from operation WHERE latitude != 0 AND longitude != 0 AND vehicle_id = "'
        + str(vehicle.placa)
        + '" AND timestamp BETWEEN "'
        + str(d1)
        + " "
        + str(h1)[:8]
        + '" and "'
        + str(d1)
        + " "
        + str(h2)[:8]
        + '"'
    )

    df = pd.read_sql_query(query, db.engine)
    if var not in df.columns:
        var = "elevation"

    if all(
        elem in df.columns for elem in ["latitude", "longitude", "timestamp", var]
    ) and len(df[var]):
        df = df[["latitude", "longitude", "timestamp", var]]
        df["name"] = df[var]
        # Remove outliers
        if not df.isnull().values.any():
            df = df[(np.abs(stats.zscore(df[var])) < 3)]
        # Reemplaza por la 0 pero antes por backfill and fulfill (revisar). Se hace cuando hay algún null antes de remover outliers
        else:
            df.fillna(method="ffill", inplace=True)
            df.fillna(method="bfill", inplace=True)
            df.fillna(0, inplace=True)

        x_max = df[var].max()
        x_min = df[var].min()
        # Formula taken from
        # https://www.atoti.io/articles/when-to-perform-a-feature-scaling/

        visualization_scaler = lambda x: ((x - x_min) * (max_col_size)) / (
            x_max - x_min
        )
        df["var"] = df[var].map(visualization_scaler)
        df = df[["latitude", "longitude", "name", "var", "timestamp"]]
    return df


if __name__ == "__main__":
    a = get_heights("elevation")
    titles = Operation.__dict__
    print(titles)
    b = form_var(titles)
