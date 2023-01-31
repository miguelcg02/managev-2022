import os

import mysql.connector
import pandas as pd
import numpy as np

from managev_app import app
from managev_app.Research.OpenStreetMaps.associate_edges_to_operation import (
    OsmDataAdapter,
)
from managev_app.Research.Route_segmentation.segmentation import (
    gen_traces,
    SegmentTypes,
)


class DataFetcher:
    def __init__(
        self,
        name: str = None,
        query: str = "SELECT * from operation",
        segment_length=1000,
        segment_type=SegmentTypes.degradation,
    ):
        try:
            self.cnx = mysql.connector.connect(
                user="admin",
                password="actuadores",
                host="104.236.94.94",
                database="monitoreodb",
            )
        except mysql.connector.errors.DatabaseError:
            self.cnx = None

        self.name = name
        self.data_path = os.path.join(app.root_path) + "/DataBackup/" + name

        self.query = query
        self.segment_length = segment_length
        self.segment_type = segment_type

    def get_operation_with_osm_data(self):
        try:
            loaded_data = pd.read_hdf(
                self.data_path + "_data.h5", key=f"{self.name}_updated_df_operation"
            )
        except FileNotFoundError:
            all_data_with_osm = self.update_operation_with_osm_data(self.query)
            all_data_with_osm.name.fillna("undefined", inplace=True)
            all_data_with_osm.to_hdf(
                self.data_path + "_data.h5",
                key=f"{self.name}_updated_df_operation",
                mode="w",
            )
            loaded_data = pd.read_hdf(
                self.data_path + "_data.h5", key=f"{self.name}_updated_df_operation"
            )
        return loaded_data

    def update_operation_with_osm_data(self, query):
        all_data = pd.read_sql_query(query, self.cnx, index_col="id")
        all_data.dropna(axis=1, how="all", inplace=True)

        osm_adapter = OsmDataAdapter()
        all_data_with_osm = osm_adapter.add_osmn_attributes(all_data)

        convert_dict = {
            "vehicle_id": str,
            "charger_type": str,
            "drivemode": str,
            "user_name": str,
            "osmid": str,
            "lanes": str,
            "name": str,
            "highway": str,
            "geometry": str,
            "maxspeed": str,
            "bridge": str,
            "junction": str,
            "ref": str,
            "width": str,
            "tunnel": str,
            "access": str,
        }
        try:
            all_data_with_osm = all_data_with_osm.astype(convert_dict)
            return all_data_with_osm
        except KeyError:
            return all_data_with_osm

    def update_data_on_h5(
        self,
    ):

        operation_with_osm_data = self.get_operation_with_osm_data()

        segments = gen_traces(
            operation_with_osm_data,
            length=self.segment_length,
            segment_type=self.segment_type,
        )

        # Cleaning segments
        segments.replace([np.inf, -np.inf], np.nan, inplace=True)
        for col in ["batt_temp", "speed_ind"]:
            segments[col].fillna(value=np.mean(segments[col]), inplace=True)
        segments.end_odometer.ffill(inplace=True)
        segments.dropna(inplace=True)
        segments = segments[segments["kms"] < 20]
        segments = segments[segments["consumption"] < 40]

        segments.to_hdf(self.data_path + "_data.h5", key=self.name + "_segments")
        return segments

    def get_segments(self):
        try:
            segments = pd.read_hdf(
                self.data_path + "_data.h5", key=f"{self.name}_segments"
            )

        except FileNotFoundError:
            segments = self.update_data_on_h5()
        return segments
