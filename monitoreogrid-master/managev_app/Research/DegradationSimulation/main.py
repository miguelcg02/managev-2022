import os

import pandas as pd
import numpy as np
from pickle import load
import matplotlib.pyplot as plt
from scipy.stats import stats

from managev_app import app
from managev_app.Research.DataInteractor.data_fetcher import DataFetcher
from managev_app.Research.DegradationSimulation.Charging.PiecewiseTimeSlots import (
    Piecewise,
)
from managev_app.Research.DrivingClassification.cluster import DrivingClassifier
from managev_app.Research.DrivingClassification.road_clustering import RoadClassifier
from managev_app.Research.Route_segmentation.segmentation import SegmentTypes
from managev_app.Research.DegradationSimulation.MarcovChain.MarcovChain import (
    MarcovChain,
    VehicleSimulator,
)


def common_states(segments_df):
    """
    This function aims to create a dataframe of common
    states between the 2 clusters (aggressive vs non aggressive).

    common states are idle, charging, and driving out out those states
    """
    result = []
    indexes = []
    common = ["idle", "charging"]
    first = True
    for index, row in segments_df.iterrows():
        if first:
            first = False
            prev_row = row
            continue
        prev_state = prev_row["vehicle_state"]
        state = row["vehicle_state"]
        if state in common or (state == "driving" and prev_state in common):
            result.append(row)
            indexes.append(index)

        prev_row = row
    return pd.DataFrame(result, index=indexes)


def compute_matrix(chain):
    positions = list(sorted(chain.transition_probs.keys()))
    pos = {p: str(i) for i, p in enumerate(positions)}
    mat = np.zeros([len(positions), len(positions)])
    for state in sorted(chain.transition_probs.keys()):
        for s in sorted(chain.transition_probs.get(state).keys()):
            row, _, col = s.partition("_")
            mat[int(pos[col]), int(pos[row])] = chain.transition_probs.get(state).get(s)
    return mat


name = "renault"

models_path = os.path.join(
    os.path.dirname(__file__),
    "../ConsumptionEstimation",
    "MachineLearningModels",
)


query = (
    "select * from operation o where vehicle_id in"
    " ('GHW284', 'GVQ446', 'EGZ112', 'EPQ666', 'GVQ514')"
    " and o.operative_state > 0"
    " and elevation is not null ORDER BY vehicle_id desc, o.timestamp asc ;"
)

fetcher = DataFetcher(
    name=name, query=query, segment_type=SegmentTypes.degradation
)
segments = fetcher.get_segments()

# Remove outliers
# 2.5 standard deviations away a given observation is from the mean
for col in ["kms", "min_acc", "consumption"]:
    segments = segments[(np.abs(stats.zscore(segments[col])) < 2.5)]


# common states are idle and charging
common_states = common_states(segments)
driving_segments = segments.loc[segments.index.difference(common_states.index)]
driving_classifier = DrivingClassifier(segments=driving_segments)
driving_segments["driving_cluster"] = driving_classifier.cluster_labels

x_scaler = load(open(os.path.join(models_path, "x_scaler.pkl"), "rb"))
scaler = load(open(os.path.join(models_path, "scaler.pkl"), "rb"))
consumption_model = load(
    open(os.path.join(models_path, "linear_regr_sklearn.pkl"), "rb")
)

chains = {}
results = []
for driving_style in driving_classifier.cluster_labels.unique():
    drivers = driving_segments[driving_segments["driving_cluster"] == driving_style]
    drivers = drivers.append(common_states)
    kwargs = {}
    if driving_style == 1:
        kwargs["swap_colors"] = True
    road_classifier = RoadClassifier(drivers, **kwargs)
    charge_simulator = Piecewise()
    vehicle = VehicleSimulator(charge_simulator=charge_simulator)
    vehicle.set_charge_levels(road_classifier.road_segments)
    chain = MarcovChain(
        vehicle=vehicle,
        segments=road_classifier.road_segments,
        scaler=scaler,
        x_scaler=x_scaler,
        model=consumption_model,
    )
    chains[driving_style] = chain
    mat = compute_matrix(chain)

    results.append(chain.random_walk(days=365))

nissan_benchmark = {
    "hours": [
        0,
        730,
        1460,
        2190,
        2920,
        3650,
        4380,
        5110,
        5840,
        6570,
        7300,
        8030,
        8760,
        9490,
        10220,
        10950,
        11680,
        12410,
        13140,
        13870,
        14600,
        15330,
        16060,
        16790,
        17520,
        18250,
        18980,
        19710,
    ],
    "Capacity loss(%)": [
        0,
        0,
        0,
        0.141495187,
        0.495134185,
        0.848773184,
        1.202412183,
        1.556051181,
        1.90969018,
        2.263329179,
        2.616968178,
        2.970607176,
        3.324246175,
        3.677885174,
        4.031524172,
        4.385163171,
        4.73880217,
        5.092441168,
        5.446080167,
        5.799719166,
        6.153358165,
        6.506997163,
        6.860636162,
        7.214275161,
        7.567914159,
        7.921553158,
        8.275192157,
        8.628831156,
    ],
}

fig = plt.figure()
ax1 = fig.add_subplot(111)
colors = ["b", "r"]
labels = ["Non-aggressive", "Aggressive"]
for i, result in enumerate(results):
    ax1.scatter(
        result[1],  # Times
        result[0].get("Capacity loss(%)"),
        s=5,
        c=colors[i],
        marker="s",
        label=labels[i],
    )

# ax1.scatter(
#     nissan_benchmark.get("hours"),
#     nissan_benchmark.get("Capacity loss(%)"),
#     s=5,
#     c="grey",
#     marker="s",
#     label="Nissan Leaf",
# )

plt.legend(loc="upper left")
plt.show()

# SoH
fig = plt.figure()
ax1 = fig.add_subplot(111)
for i, result in enumerate(results):
    ax1.scatter(
        np.array(result[1]) / 24,  # Times
        100 - np.array(result[0].get("Capacity loss(%)")),
        s=3,
        c=colors[i],
        marker="s",
        label=labels[i],
    )

plt.xlabel("days")
plt.ylabel("SoH")
plt.legend(loc="upper left")
plt.show()

## Compare with real driving
a = pd.DataFrame({"time": results[0][1], "cap": results[0][0]["Capacity (kWh)"]})
a.to_csv("simulated_cycles.csv")
mat = compute_matrix(chain)

# Perform a simulation for one year
results.append(chain.random_walk(days=973))

nissan_benchmark = {
    "hours": [0, 730, 1460, 2190, 2920, 3650, 4380, 5110, 5840, 6570, 7300, 8030, 8760, 9490, 10220, 10950, 11680, 12410, 13140, 13870, 14600, 15330, 16060, 16790, 17520, 18250, 18980, 19710],
    "Capacity loss(%)": [0, 0, 0, 0.141495187, 0.495134185, 0.848773184, 1.202412183, 1.556051181, 1.90969018, 2.263329179, 2.616968178, 2.970607176, 3.324246175, 3.677885174, 4.031524172, 4.385163171, 4.73880217, 5.092441168, 5.446080167, 5.799719166, 6.153358165, 6.506997163, 6.860636162, 7.214275161, 7.567914159, 7.921553158, 8.275192157, 8.628831156]
}

fig = plt.figure()
ax1 = fig.add_subplot(111)
colors = ["b", "r"]
labels = ["Non-aggressive", "Aggressive"]
for i, result in enumerate(results):
    ax1.scatter(
        result[1],
        result[0].get("Capacity loss(%)"),
        s=5,
        c=colors[i],
        marker="s",
        label=labels[i],
    )

ax1.scatter(
        nissan_benchmark.get("hours"),
        nissan_benchmark.get("Capacity loss(%)"),
        s=5,
        c="grey",
        marker="s",
        label="Nissan Leaf",
    )

plt.legend(loc="upper left")
plt.show()
end = True
