from sklearn.cluster import KMeans
import matplotlib.cm as cm
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from mpl_toolkits.mplot3d import Axes3D
from sklearn import preprocessing
from sklearn.cluster import KMeans
from sklearn.decomposition import PCA
from sklearn.metrics import silhouette_samples, silhouette_score

features = pd.read_csv("mixed_segment_features.csv")
# features = pd.read_csv('features.csv')

selected_ftrs = features[
    [
        "std_acc",
        "prom_abs_jerk",
        "std_jerk",
        "std_pot",
        "prom_abs_pot",
        "prom_abs_current",
        "std_current",
        "std_current_std_jerk",
        "slope",
        "max_current",
        "max_jerk",
        "max_acc",
        "max_pot",
        "max_speed",
        "mean_speed",
        "std_speed",
    ]
]
"""
selected_ftrs = features[['prom_abs_current', 'prom_abs_pot',
                          'max_current', 'max_pot', 'prom_sobrepaso_jerk_acc']]
"""
x = selected_ftrs.values  # returns a numpy array

scaler = preprocessing.StandardScaler()
x_scaled = scaler.fit_transform(x)
# features_norm = pd.DataFrame(x_scaled, columns=selected_ftrs.columns)

pca = PCA(n_components=3)
pca.fit(x_scaled)
X_transformed = pca.transform(x_scaled)

""" 0.518 3 clusters
X_transformed = features[['max_current', 'max_power', 'std_potencia','std_jerk',
                          'prom_abs_current', 'std_current']].values
"""

""" 0.548 3 clusters
X_transformed = features[['max_current', 'max_power', 'std_potencia','std_jerk',
                          'prom_abs_current']].values
"""
""" 0.559 3 clusters
X_transformed = features[['max_current', 'max_power','std_jerk',
                          'prom_abs_current']].values
"""
X_transformed = features[["consumption_per_km", "max_pot", "slope"]].values

range_n_clusters = [2, 3, 4]

for n_clusters in range_n_clusters:
    # Create a subplot with 1 row and 2 columns
    fig, (ax1) = plt.subplots(1, 1)
    fig.set_size_inches(18, 7)

    # The 1st subplot is the silhouette plot
    # The silhouette coefficient can range from -1, 1 but in this example all
    # lie within [-0.1, 1]
    ax1.set_xlim([-0.1, 1])
    # The (n_clusters+1)*10 is for inserting blank space between silhouette
    # plots of individual clusters, to demarcate them clearly.
    ax1.set_ylim([0, len(X_transformed) + (n_clusters + 1) * 10])

    # Initialize the clusterer with n_clusters value and a random generator
    # seed of 10 for reproducibility.
    clusterer = KMeans(n_clusters=n_clusters, random_state=10)
    cluster_labels = clusterer.fit_predict(X_transformed)

    # The silhouette_score gives the average value for all the samples.
    # This gives a perspective into the density and separation of the formed
    # clusters
    silhouette_avg = silhouette_score(X_transformed, cluster_labels)
    print(
        "For n_clusters =",
        n_clusters,
        "The average silhouette_score is :",
        silhouette_avg,
    )

    # Compute the silhouette scores for each sample
    sample_silhouette_values = silhouette_samples(X_transformed, cluster_labels)

    y_lower = 10
    for i in range(n_clusters):
        # Aggregate the silhouette scores for samples belonging to
        # cluster i, and sort them
        ith_cluster_silhouette_values = sample_silhouette_values[cluster_labels == i]

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
            alpha=0.8,
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

    # 3d
    fig = plt.figure(figsize=[10, 10])
    ax = Axes3D(fig)
    ax.scatter(
        X_transformed[:, 0], X_transformed[:, 1], X_transformed[:, 2], c=colors, s=10
    )

    # ax2.scatter(X_transformed[:, 0], X_transformed[:, 1], marker='.', s=30, lw=0, alpha=0.7,
    #             c=colors, edgecolor='k')

    # Labeling the clusters
    centers = clusterer.cluster_centers_
    # Draw white circles at cluster centers
    # ax2.scatter(centers[:, 0], centers[:, 1], marker='o',
    #             c="white", alpha=1, s=200, edgecolor='k')

    ax.scatter(
        centers[:, 0],
        centers[:, 1],
        centers[:, 2],
        marker="o",
        c="white",
        alpha=1,
        s=200,
        edgecolor="k",
    )

    for i, c in enumerate(centers):
        ax.scatter(c[0], c[1], c[2], marker="$%d$" % i, alpha=1, s=50, edgecolor="k")

    ax.set_title("The visualization of the clustered osm_data.")
    ax.set_xlabel("Feature space for the 1st feature")
    ax.set_ylabel("Feature space for the 2nd feature")
    ax.set_ylabel("Feature space for the 3rd feature")

    plt.suptitle(
        (
            "Silhouette analysis for KMeans clustering on driving osm_data "
            "with n_clusters = %d" % n_clusters
        ),
        fontsize=14,
        fontweight="bold",
    )

plt.show()
