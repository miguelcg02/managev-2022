import os

import numpy as np
import pandas as pd


class ConsumptionModelLookup:
    def __init__(
        self, road_segments, build_lookups: bool = False, save_lookups: bool = False
    ):
        self.road_segments = road_segments
        current_path = os.path.dirname(__file__)
        os.chdir(os.path.dirname(current_path))  # move one level up

        self.data_path = os.path.join(os.getcwd(), "UserDrivingData")

        # Would be nice to get these from a sql table if exists
        if build_lookups:
            self.user_slope_lookup = None
            self.slope_power_lookup = None

            self.create_slope_lookup_table(save_lookups=save_lookups)
            self.create_user_slope_to_power_lookup_table(save_lookups=save_lookups)

        else:
            self.user_slope_lookup = pd.read_csv(
                f"{self.data_path}/mean_features_by_user_and_slope.csv"
            )
            self.slope_power_lookup = pd.read_csv(
                f"{self.data_path}/mean_features_by_slope.csv"
            )

    def create_slope_lookup_table(self, save_lookups=False):
        """
        # Lookup tables for getting all users average power according to slope
        Args:
            road_segments:

        Returns: lookup table, road_segments with the new slope-based power column

        """
        slope_groups = self.road_segments.groupby(by=["slope_cat"])

        slope_power_lookup = slope_groups[["mean_power"]].mean().reset_index()
        slope_power_lookup.rename(
            columns={"mean_power": "mean_power_by_slope", "slope": "slope_cat"},
            inplace=True,
        )

        slope_power_lookup["slope_cat"] = slope_power_lookup["slope_cat"].astype(
            "string"
        )

        self.slope_power_lookup = slope_power_lookup.sort_values(by=["slope_cat"])
        if save_lookups:
            self.slope_power_lookup.to_csv(
                f"{self.data_path}/mean_features_by_slope.csv"
            )

    def create_user_slope_to_power_lookup_table(self, save_lookups=False):
        """
        Lookup tables for getting all user specific average power according to slope
        Args:
            self.road_segments: segments to build lookups from
            save_lookups: save to csv

        Returns: lookup_table, road_segments with the new slope-based power column

        """
        user_slope_lookup = self.road_segments.groupby(by=["slope_cat", "user_name"])
        user_slope_lookup = user_slope_lookup[["mean_power"]].mean().reset_index()
        user_slope_lookup.rename(
            columns={
                "mean_power": "mean_power_usr",
            },
            inplace=True,
        )

        user_slope_lookup["slope_cat"] = user_slope_lookup["slope_cat"].astype("string")

        self.user_slope_lookup = user_slope_lookup.sort_values(
            by=["user_name", "slope_cat"]
        )
        if save_lookups:
            self.user_slope_lookup.to_csv(
                f"{self.data_path}/mean_features_by_user_and_slope.csv"
            )

    def fill_with_lookups(self, road_segments):
        concat = road_segments
        if self.slope_power_lookup is not None and self.user_slope_lookup is not None:
            concat = pd.merge(
                left=concat,
                right=self.user_slope_lookup,
                left_on=["user_name", "slope_cat"],
                right_on=["user_name", "slope_cat"],
            )
            concat = pd.merge(
                left=concat,
                right=self.slope_power_lookup,
                left_on="slope_cat",
                right_on="slope_cat",
            )
            concat["mean_power_usr"] = concat.apply(
                lambda row: row["mean_power_by_slope"]
                if np.isnan(row["mean_power_usr"])
                else row["mean_power_usr"],
                axis=1,
            )
            # Only used to fill
            concat.drop(columns=["mean_power_by_slope"], inplace=True)
        return concat
