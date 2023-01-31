import seaborn as sns
import pandas as pd
from sklearn import metrics
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler


class RoadClassifier:
    def __init__(self, raw_segments=None, n_clusters=5, n_components=2, **kwargs):
        segments = raw_segments[raw_segments.vehicle_state == "driving"]

        road_attributes = segments[
            [
                "slope",
                "mean_speed",
            ]
        ].fillna(0)

        X = road_attributes.values

        X = StandardScaler().fit_transform(X)

        for n_clusters in [n_clusters]:  # [2, 3, 4, 5]  # 5 has better coefficient
            kmeans = KMeans(n_clusters=n_clusters, random_state=0).fit(X)
            labels = kmeans.labels_

            # Number of clusters in labels, ignoring noise if present.
            n_clusters_ = len(set(labels)) - (1 if -1 in labels else 0)
            n_noise_ = list(labels).count(-1)

            print("Estimated number of clusters: %d" % n_clusters_)
            print("Estimated number of noise points: %d" % n_noise_)
            print("Silhouette Coefficient: %0.3f" % metrics.silhouette_score(X, labels))

            segments["road_clusters"] = labels
            if kwargs.get("swap_colors"):
                segments.road_clusters.replace(
                    {2: 0, 0: 2, 1: 4, 4: 3, 3: 1}, inplace=True
                )
            segments.rename(
                columns={"mean_speed": "mean_speed (km/h)", "slope": "slope (°)"},
                inplace=True,
            )
            fig = sns.pairplot(
                segments.sort_values(["mean_speed (km/h)"]),
                hue="road_clusters",
                palette="Paired",
                vars=["mean_speed (km/h)", "slope (°)"],
                kind="scatter",
            )

        raw_segments["road_clusters"] = segments["road_clusters"].astype(str)
        raw_segments["road_clusters"].fillna(
            raw_segments["vehicle_state"], inplace=True
        )
        self.road_clusters = raw_segments["road_clusters"]
        self.road_segments = raw_segments
