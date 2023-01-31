from sklearn.neighbors import KDTree

from managev_app import open_dataframes


class Trees:
    stations = open_dataframes.get_stations()
    station_tree = KDTree(stations[["latitude", "longitude"]].values, leaf_size=2)

    zones = open_dataframes.get_zones()
    zones_tree = KDTree(zones[["latitude", "longitude"]].values, leaf_size=2)
