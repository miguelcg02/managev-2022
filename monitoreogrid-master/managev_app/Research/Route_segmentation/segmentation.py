from enum import Enum

import numpy as np
import pandas as pd
from scipy import integrate
from scipy.stats import skew

# estados de consumo y regeneración
vehicle_states = {1: "driving", 2: "driving", 3: "charging", 4: "idle"}


class SegmentTypes(Enum):
    consumption = "consumption"
    degradation = "degradation"


def consumption_traces(df, length):
    """
    Consolidates puntual measurements into segments:
    This type of segment takes into consideration length and road type change
    to define a segment change

    df comes chronologically ordered
    """
    trace_id = 1
    trace_array = np.array([])
    suma = 0
    old_name = ""

    for _, row in df.iterrows():
        suma = suma + row["run"]
        trace_array = np.append(trace_array, -trace_id)
        nan = row["name"] != row["name"]

        # Si recorre mas de length metros
        # cambie el id del segmento actual de aux a definitivo(+) para que se tenga en cuenta
        if suma >= length:
            trace_array = np.where(trace_array == -trace_id, trace_id, trace_array)

        if (
            suma >= length
            or (old_name != row["name"] and not nan)
            or row["operative_state"] == 3
        ):
            suma = 0
            trace_id += 1

        old_name = row["name"]

    try:
        df.drop(["trace_id"], axis=1, inplace=True)
    except KeyError:
        pass

    df.insert(2, "trace_id", trace_array, True)
    return df


def degradation_traces(df):
    """
    Consolidates puntual measurements into segments:
    This type of segment don't take into consideration length, just road type change to define
    a new segment start
    """
    trace_id = 1
    trace_array = np.array([])
    old_name = ""
    old_state = "idle"

    for _, row in df.iterrows():
        trace_array = np.append(trace_array, trace_id)
        state = vehicle_states.get(row["operative_state"])

        # Si cambia de vía o empieza a cargar
        # empiece un nuevo tramo
        if (old_name != row["name"]) or state != old_state:
            trace_id += 1

        old_name = row["name"]
        old_state = state
    try:
        df.drop(["trace_id"], axis=1, inplace=True)
    except KeyError:
        pass

    df.insert(2, "trace_id", trace_array, True)
    return df


def gen_traces(raw_df, length=1000, segment_type=SegmentTypes.degradation):
    """"generate traces id according to either consumption needs or Markov degradation model"""
    if segment_type == SegmentTypes.consumption:
        df = consumption_traces(raw_df, length)
    elif segment_type == SegmentTypes.degradation:
        df = degradation_traces(raw_df)
    positive_traces = df[df["trace_id"] > 0]
    traces = positive_traces.groupby(["trace_id"])
    lst = []
    for index, trace in traces:
        if index > 0 and len(trace) > 2:
            lst.append(feature_extraction(trace))

    features = generate_features_df(lst)
    features["slope_cat"] = pd.cut(features["slope"], np.arange(-10, 10.1, 5)).astype(
        "string"
    )
    return features


def peak_features(var):
    mean_val = np.mean(var)
    prom_abs = np.mean(np.absolute(var))
    std = np.std(var)
    max_val = np.max(var)
    min_val = np.min(var)
    return mean_val, prom_abs, std, max_val, min_val, skew(var)


def feature_extraction(trace):
    """
    :param trace: slice of operation_df for an specific trace number
    :return: list of attributes for that trace
    """
    trace["cumulative_distance"] = trace["run"].cumsum()

    # Picos aceleraciones y frenadas
    acc = trace["mean_acc"].to_numpy()
    mean_acc, prom_abs_acc, std_acc, max_acc, min_acc, skew_acc = peak_features(acc)

    # Picos corriente
    current = trace["current"].to_numpy()
    (
        mean_current,
        prom_abs_current,
        std_current,
        max_current,
        min_current,
        skew_current,
    ) = peak_features(current)
    slope = np.mean(trace["slope"])

    # Medidas de potencia específica
    power = trace["power_kw"].to_numpy()
    (
        mean_power,
        prom_abs_power,
        std_power,
        max_power,
        min_power,
        skew_power,
    ) = peak_features(power)

    energy_rec = trace["energy_rec"].iloc[-1] - trace["energy_rec"].iloc[0]
    energy = trace["energy"].iloc[0] - trace["energy"].iloc[-2]

    # With battery capacity
    consumption2 = trace["capacity"].iloc[0] - trace["capacity"].iloc[-2]

    # With power integration
    consumption3 = integrate.cumtrapz(trace["power_kw"], trace["timestamp2"])
    consumption3 = (consumption3[-2] - consumption3[0]) / 3600

    consumption = (consumption2 + consumption3) / 2
    kms = trace["cumulative_distance"].iloc[-2] / 1000
    consumption_per_km = consumption / kms

    speed = trace["speed"].to_numpy()
    (
        mean_speed,
        prom_abs_speed,
        std_speed,
        max_speed,
        min_speed,
        skew_speed,
    ) = peak_features(speed)

    time = trace["timestamp2"].iloc[-2] - trace["timestamp2"].iloc[0]

    traffic_factor = mean_speed / std_speed if std_speed != 0 else 0
    batt_temp = trace["batt_temp"].mean()
    nominal_speed = trace["speed_kph"].iloc[0]
    speed_ind = (
        nominal_speed / np.max(trace["speed"]) if np.max(trace["speed"]) > 0 else 1
    )

    try:
        test_id = trace["test_id"].iloc[0]
    except KeyError:
        test_id = 0

    return [
        mean_acc,
        prom_abs_acc,
        std_acc,
        max_acc,
        min_acc,
        skew_acc,
        mean_current,
        prom_abs_current,
        std_current,
        max_current,
        min_current,
        skew_current,
        mean_power,
        prom_abs_power,
        std_power,
        max_power,
        min_power,
        skew_power,
        mean_speed,
        prom_abs_speed,
        std_speed,
        max_speed,
        min_speed,
        skew_speed,
        kms,
        consumption_per_km,
        consumption,
        energy,
        energy_rec,
        trace["highway"].iloc[0],
        trace["name"].iloc[0],
        vehicle_states.get(trace["operative_state"].iloc[-2]),
        trace["capacity"].iloc[0],
        trace["capacity"].iloc[-2],
        slope,
        nominal_speed,
        trace["soc"].mean(),
        batt_temp,
        time,
        traffic_factor,
        trace["user_name"].iloc[0],
        trace["vehicle_id"].iloc[0],
        speed_ind,
        test_id,
        trace["timestamp"].iloc[-2],
        trace["mass"].iloc[-2],
        trace["odometer"].iloc[-2],
    ]


def generate_features_df(lst):
    cols = [
        "mean_acc",
        "prom_abs_acc",
        "std_acc",
        "max_acc",
        "min_acc",
        "skew_acc",
        "mean_current",
        "prom_abs_current",
        "std_current",
        "max_current",
        "min_current",
        "skew_current",
        "mean_power",
        "prom_abs_power",
        "std_power",
        "max_power",
        "min_power",
        "skew_power",
        "mean_speed",
        "prom_abs_speed",
        "std_speed",
        "max_speed",
        "min_speed",
        "skew_speed",
        "kms",
        "consumption_per_km",
        "consumption",
        "energy",
        "energy_rec",
        "highway",
        "road_name",
        "vehicle_state",
        "ini_cap",
        "fin_cap",
        "slope",
        "nominal_speed",
        "mean_soc",
        "batt_temp",
        "time",
        "traffic_factor",
        "user_name",
        "vehicle_id",
        "speed_ind",
        "test_id",
        "end_time",
        "mass",
        "end_odometer",
    ]

    return pd.DataFrame(lst, columns=cols)
