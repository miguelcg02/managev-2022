import os

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import plotly.express as px
import scipy
import scipy.cluster.hierarchy as sch
import seaborn as sns
from sklearn.cluster import AgglomerativeClustering
from sklearn.decomposition import PCA
from sklearn.preprocessing import StandardScaler

from managev_app import app
from managev_app.Research.DataInteractor.data_fetcher import DataFetcher


class DrivingClassifier:
    def __init__(self, segments=None, n_clusters=2, n_components=2):
        self.segments = segments
        self.n_clusters = n_clusters
        x_scaled = self.prepare_data()
        self.x_transformed = self.make_pca(x_scaled, n_components)
        self.generate_label(n_clusters)
        self.cluster_labels = self.segments.cluster

    def prepare_data(self):

        # se eliminan las variables que no son interesantes para el problema de cluster,
        # ya que no hacen parte de los atributos de conducción

        X = self.segments.drop(
            columns=[
                "test_id",
                "user_name",
                "vehicle_id",
                "end_time",
                "road_name",
                "time",
                "mean_soc",
                "nominal_speed",
                "kms",
                "end_odometer",
                "traffic_factor",
                "vehicle_state",
                "mass",
                "highway",
                "end_odometer",
                "consumption",
                "kms",
            ]
        ).values

        # Escalamos antes de aplicar PCA
        scaler = StandardScaler()
        return scaler.fit_transform(X)

    def make_pca(self, x_scaled, n_components=2):
        """Hacemos PCA para poder visualizar en 2d o 3d"""
        pca = PCA()
        np.nan_to_num(x_scaled, copy=False)
        pca.fit(x_scaled)
        print(
            f"The explained variances with {n_components} components is:",
            pca.explained_variance_ratio_[0 : n_components - 1].sum(),
        )

        pca = PCA(n_components=n_components)
        pca.fit(x_scaled)
        x_transformed = pca.transform(x_scaled)
        return x_transformed

    def plot_clusters(self):
        plt.figure(figsize=[10, 5])
        sch.dendrogram(sch.linkage(self.x_transformed, method="ward"))
        plt.title("Dendrogram")
        plt.xlabel("Segments")
        plt.ylabel("Euclidean distances")
        plt.show()

        plt.figure(figsize=[9, 9])
        colors = ["red", "blue", "green", "cyan"]
        for i in range(self.n_clusters):
            len(colors)
            plt.scatter(
                self.x_transformed[self.y_hc == i, 0],
                self.x_transformed[self.y_hc == i, 1],
                s=20,
                c=colors[i % len(colors)],
                label=f"Cluster {i}",
            )

        plt.title("Driving Clusters")
        plt.xlabel("First Principal Component")
        plt.ylabel("Second Principal Component")
        plt.legend()
        plt.show()

        plot_segments = self.segments.copy()
        plot_segments.rename(
            columns={"mean_speed": "mean_speed (km/h)", "max_power": "max_power (kW)"},
            inplace=True,
        )
        sns.pairplot(
            plot_segments.sort_values(["slope"]),
            hue="cluster",
            palette="Paired",
            vars=[
                "max_power",
                "mean_speed",
            ],
            kind="scatter",
        )

    def generate_label(self, n_clusters):
        hc = AgglomerativeClustering(
            n_clusters=n_clusters, affinity="euclidean", linkage="ward"
        )

        self.y_hc = hc.fit_predict(self.x_transformed)
        self.segments["cluster"] = self.y_hc + 1

    def plot_metrics(self):
        t, p = scipy.stats.ttest_ind(
            self.segments["consumption_per_km"][(self.segments["cluster"] == 1)],
            self.segments["consumption_per_km"][self.segments["cluster"] == 2],
        )

        print("Consumption difference between clusters")
        print("t = " + str(t))
        print("p-value = " + str(p), "\n")

        # Observamos que las medias son significativamente diferentes

        # plt.figure(figsize=[9,9])
        # fig = plt.figure(figsize=[10, 10])
        # ax = Axes3D(fig)
        # fig = px.scatter_3d(self.segments['mean_speed'][y_hc == 0], self.segments['max_current'][y_hc == 0], self.segments['traffic_factor'][y_hc == 0]) #, color = 'red')  #, label = 'Cluster 1')
        fig = px.scatter_3d(
            self.segments,
            x="mean_speed",
            y="max_current",
            z="traffic_factor",
            color="cluster",
            width=800,
            height=800,
        )
        # px.scatter_3d(self.segments['mean_speed'][y_hc == 2], self.segments['max_current'][y_hc == 2], self.segments['traffic_factor'][y_hc == 2]) #, c = 'green', label = 'Cluster 3')
        # px.scatter_3d(self.segments['mean_speed'][y_hc == 3], self.segments['max_current'][y_hc == 3], self.segments['traffic_factor'][y_hc == 3]) #, c = 'cyan', label = 'Cluster 4')
        # plt.title('Clusters of drivers')
        # plt.xlabel('mean_speed kmh')
        # plt.ylabel('max_current A')
        # plt.legend()
        fig.show()

        # fig = px.scatter_3d(x=X_transformed[:, 0], y=X_transformed[:, 1], z=X_transformed[:, 2], log_x=False, size=np.repeat([4], len(X)))
        #     fig.show()

        # Evaluamos el performance del modelo mediante el coeficiente de silueta

        from sklearn.metrics import silhouette_samples, silhouette_score
        import matplotlib.cm as cm

        range_n_clusters = [2]

        for n_clusters in range_n_clusters:
            # Create a subplot with 1 row and 2 columns
            fig, (ax1, ax2) = plt.subplots(1, 2)
            fig.set_size_inches(18, 7)

            # The 1st subplot is the silhouette plot
            # The silhouette coefficient can range from -1, 1 but in this example all
            # lie within [-0.1, 1]
            ax1.set_xlim([-0.1, 1])
            # The (n_clusters+1)*10 is for inserting blank space between silhouette
            # plots of individual clusters, to demarcate them clearly.
            ax1.set_ylim([0, len(self.x_transformed) + (n_clusters + 1) * 10])

            # Initialize the clusterer with n_clusters value and a random generator
            # seed of 10 for reproducibility.
            clusterer = AgglomerativeClustering(
                n_clusters=n_clusters, affinity="euclidean", linkage="ward"
            )
            cluster_labels = clusterer.fit_predict(self.x_transformed)

            # The silhouette_score gives the average value for all the samples.
            # This gives a perspective into the density and separation of the formed
            # clusters
            silhouette_avg = silhouette_score(self.x_transformed, cluster_labels)
            print(
                "For n_clusters =",
                n_clusters,
                "The average silhouette_score is :",
                silhouette_avg,
            )

            # Compute the silhouette scores for each sample
            sample_silhouette_values = silhouette_samples(
                self.x_transformed, cluster_labels
            )

            y_lower = 10
            for i in range(n_clusters):
                # Aggregate the silhouette scores for samples belonging to
                # cluster i, and sort them
                ith_cluster_silhouette_values = sample_silhouette_values[
                    cluster_labels == i
                ]

                ith_cluster_silhouette_values.sort()

                size_cluster_i = ith_cluster_silhouette_values.shape[0]
                y_upper = y_lower + size_cluster_i

                color = cm.nipy_spectral(float(i) / n_clusters)
                ax1.fill_betweenx(
                    np.arange(y_lower, y_upper),
                    0,
                    ith_cluster_silhouette_values,
                    facecolor=color,
                    edgecolor=color,
                    alpha=0.7,
                )

                # Label the silhouette plots with their cluster numbers at the middle
                ax1.text(-0.05, y_lower + 0.5 * size_cluster_i, str(i))

                # Compute the new y_lower for next plot
                y_lower = y_upper + 10  # 10 for the 0 samples

            ax1.set_title("The silhouette plot for the various clusters.")
            ax1.set_xlabel("The silhouette coefficient values")
            ax1.set_ylabel("Cluster label")

            # The vertical line for average silhouette score of all the values
            ax1.axvline(x=silhouette_avg, color="red", linestyle="--")

            ax1.set_yticks([])  # Clear the yaxis labels / ticks
            ax1.set_xticks([-0.1, 0, 0.2, 0.4, 0.6, 0.8, 1])

            # 2nd Plot showing the actual clusters formed
            colors = cm.nipy_spectral(cluster_labels.astype(float) / n_clusters)
            ax2.scatter(
                self.x_transformed[:, 0],
                self.x_transformed[:, 1],
                marker=".",
                s=30,
                lw=0,
                alpha=0.7,
                c=colors,
                edgecolor="k",
            )

            ax2.set_title("The visualization of the clustered data.")
            ax2.set_xlabel("Feature space for the 1st feature")
            ax2.set_ylabel("Feature space for the 2nd feature")

            plt.suptitle(
                (
                    "Silhouette analysis for KMeans clustering on sample data "
                    "with n_clusters = %d" % n_clusters
                ),
                fontsize=14,
                fontweight="bold",
            )

        plt.show()


if __name__ == "__main__":
    # print("Enter file prefix")
    # name = input()
    name = "renault"
    data_path = os.path.join(app.root_path) + "/DataBackup/" + name

    data_fetcher = DataFetcher(name=name)
    segments = data_fetcher.get_segments()

    segments["energy_rec"].fillna(0, inplace=True)
    classifier = DrivingClassifier(
        segments.drop(columns=["road_clusters"]), n_clusters=2, n_components=2
    )
