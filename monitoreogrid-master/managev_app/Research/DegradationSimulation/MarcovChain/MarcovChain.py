from collections import defaultdict
from dataclasses import dataclass
from typing import List
from statistics import mean

import numpy as np
from numpy.random import default_rng
from scipy import stats
import matplotlib.pyplot as plt

from managev_app.Research.DegradationSimulation.Charging.PiecewiseTimeSlots import (
    Piecewise,
)
from managev_app.Research.DegradationSimulation.Degradation.degradation_models import (
    XuDegradationModel,
)

rng = default_rng()


@dataclass
class VehicleSimulator:
    min_charge_level_interval: List[int] = None
    max_charge_level_interval: List[int] = None
    idle_time_interval: List[int] = None
    charge_simulator: Piecewise = None
    mean_voltage: float = 365.88
    mean_batt_temp: float = 26.0423
    capacity_kWh: float = 40
    capacity_AH: float = 100
    initial_Wh_capacity: int = 40000

    # These variables are used to compute averages within a cycle
    cycle_soc = []
    cycle_c_rates = []
    cycle_temperatures = []
    cycle_times = []

    model = XuDegradationModel

    def set_charge_levels(self, segments):
        initial_charges = segments["ini_cap"][segments["vehicle_state"] == "charging"]
        self.min_charge_level_interval = np.percentile(initial_charges, [10, 35])

        final_charges = segments["fin_cap"][segments["vehicle_state"] == "charging"]
        self.max_charge_level_interval = np.percentile(final_charges, [50, 100])

        idle_times = segments["time"][segments["vehicle_state"] == "idle"]
        self.idle_time_interval = np.percentile(idle_times, [70, 90])

    def reset_degradation_helpers(self):
        self.cycle_soc = []
        self.cycle_c_rates = []
        self.cycle_temperatures = []
        self.cycle_times = []

    def compute_degradation(self, soc, dod, c_rates, temp, cycles, durations):
        model = self.model(
            soc=soc,
            dod=dod,
            c_rates=c_rates,
            temp=temp,
            n=cycles,
            seconds=int(sum(durations)),
        )
        return model.compute_degradation()


class MarcovChain:
    def __init__(
        self,
        segments,
        vehicle: VehicleSimulator,
        scaler=None,
        x_scaler=None,
        model=None,
    ):
        self.segments = segments
        self.scaler = scaler
        self.vehicle = vehicle
        self.vehicle.set_charge_levels(segments)
        self.x_scaler = x_scaler
        self.model = model
        self.counters = defaultdict(int)
        self.attr_names = [
            "max_power",
            "min_acc",
            "mean_speed",
            "slope",
            "kms",
            "batt_temp",
        ]
        road_cluster_labels = segments.road_clusters
        prev = road_cluster_labels.iloc[0]
        for x in road_cluster_labels.iloc[1:]:
            self.counters[f"{prev}_{x}"] += 1
            prev = x

        self.transition_probs = {}
        self.road_attr = {}
        self.generators = {}
        for road_type in road_cluster_labels.unique():
            # if its a driving state
            if road_type.isdigit():
                variable_data = {}
                generators_dict = {}
                for attr in self.attr_names:
                    data = segments[attr][segments.road_clusters == road_type]
                    variable_data[attr] = data
                    if attr in ["mean_speed", "batt_temp"]:
                        shape, floc, scale = stats.lognorm.fit(data)
                        generators_dict[attr] = {
                            "method": stats.lognorm,
                            "shape": shape,
                            "floc": floc,
                            "scale": scale,
                        }
                    elif attr == "kms":
                        shape, floc, scale = stats.pareto.fit(data)
                        generators_dict[attr] = {
                            "method": stats.pareto,
                            "shape": shape,
                            "floc": floc,
                            "scale": scale,
                        }
                    elif attr == "slope":
                        mu, sigma = stats.norm.fit(data)
                        generators_dict[attr] = {
                            "method": stats.norm,
                            "mu": mu,
                            "sigma": sigma,
                        }
                    # max_power and min_acc
                    else:
                        generators_dict[attr] = data.mean()
                self.road_attr[road_type] = variable_data
                self.generators[road_type] = generators_dict

            n = road_cluster_labels[road_cluster_labels == road_type].count()
            state_prob = {
                key: val / n
                for key, val in self.counters.items()
                if key.startswith(str(road_type))
            }
            self.transition_probs[road_type] = state_prob

    def plot_road_cluster_attributes(self, road_cluster):
        for attr in self.attr_names:
            plt.figure()
            data = self.road_attr.get(road_cluster, {}).get(attr)
            plt.title(f"fitted dist for {attr}")
            if attr == "slope":
                mu, sigma = stats.norm.fit(data)
                _, bins, _ = plt.hist(data, 20, density=1, alpha=0.5)
                best_fit_line = stats.norm.pdf(bins, mu, sigma)
            elif attr == "kms":
                shape, floc, scale = stats.pareto.fit(data)
                _, bins, _ = plt.hist(data, 20, density=1, alpha=0.5)
                best_fit_line = stats.pareto.pdf(bins, shape, floc, scale)
            else:
                shape, floc, scale = stats.lognorm.fit(data)
                _, bins, _ = plt.hist(data, 20, density=1, alpha=0.5)
                best_fit_line = stats.lognorm.pdf(bins, shape, floc, scale)

            plt.plot(bins, best_fit_line)
            plt.show()

    def generate_values(self, road_type):
        values = {}
        for attr, generator in self.generators.get(road_type).items():
            if attr in {"min_acc", "max_power"}:
                # This just gets the mean for that road type
                values[attr] = generator
                continue

            # We create a copy since we are popping the method
            gen_copy = generator.copy()
            method = gen_copy.pop("method")
            value = method.rvs(*tuple(gen_copy.values()))
            if attr == "mean_speed":
                value = abs(value)

            historic = self.road_attr[road_type].get(attr)
            if value > historic.max():
                value = historic.max()
            elif value < historic.min():
                value = historic.min()
            values[attr] = value
        return values

    def compute_consumption(self, road_type):
        values = self.generate_values(road_type).copy()
        seconds = values.get("kms") / abs(values.get("mean_speed")) * 3600
        kms = values.pop("kms")
        batt_temp = values.pop("batt_temp")
        scaled_values = self.x_scaler.transform([list(values.values())])
        consumption = self.model.predict(scaled_values)
        kWh_per_km = self.scaler.data_min_[4] + (
            consumption / self.scaler.scale_[4]
        )
        kWh = kWh_per_km * kms
        return kWh[0], seconds, batt_temp

    def decide_transition(self, current_state):
        transition_states = [
            transition.split("_")[1]
            for transition in self.transition_probs.get(current_state).keys()
        ]

        transition_probabilities = list(
            self.transition_probs.get(current_state).values()
        )
        # normalize
        transition_probabilities /= sum(transition_probabilities)

        next_state = rng.choice(a=transition_states, p=transition_probabilities)
        return next_state

    def random_walk(self, state="idle", energy=40, days=10, plot_charges=False):
        """
        Random walk simulation to predict battery degradation

        :param state: initial chain state 0,1,2,3,4 (driving states) or idle or charging
        :param energy: initial battery kwh
        :param days:
        :return: graphs of driving cycles and degradation
        """
        energy_history = [energy]
        states = [state]
        degradation_history = [0]
        times = [0]
        end_time = days * 3600 * 24
        max_idle_hours = 24
        max_driving_hours = 3
        idle_time = 0

        # Degradation vector params
        cycles = []
        soc = []
        dod = []
        temp = []
        c_rates = []
        durations = []
        degradation = 0

        while times[-1] < end_time:
            if state.isdigit():
                consumption_kwh, seconds, batt_temp = self.compute_consumption(state)
                watts = consumption_kwh * 1000 / (seconds / 3600)
                amperes = watts / self.vehicle.mean_voltage

                # if its time to charge
                if (
                    self.vehicle.min_charge_level_interval[0]
                    < energy - consumption_kwh
                    < self.vehicle.min_charge_level_interval[1]
                ):
                    energy -= consumption_kwh
                    state = "charging"

                # dont take deeper than allowed consumptions into account
                elif (
                    energy - consumption_kwh < self.vehicle.min_charge_level_interval[0]
                ):
                    continue
                # If taking too long on a single state
                elif seconds / 3600 > max_driving_hours:
                    continue
                else:
                    final_energy = energy - consumption_kwh
                    # if regeneration happens at top level charge
                    # dont allow more than max capacity
                    if final_energy <= self.vehicle.capacity_kWh:
                        energy = final_energy
                    state = self.decide_transition(state)

                # for each battery half cycle we use this vectors to compute means
                # those means are used to compute degradation on the cycle
                self.vehicle.cycle_temperatures.append(batt_temp + 273.15)
                self.vehicle.cycle_soc.append(energy / self.vehicle.capacity_kWh)
                self.vehicle.cycle_c_rates.append(amperes / self.vehicle.capacity_AH)
                self.vehicle.cycle_times.append(seconds)

            elif state == "charging":
                max_level = rng.integers(*self.vehicle.max_charge_level_interval)
                if energy < max_level:
                    if len(self.vehicle.cycle_soc) >= 2:
                        # add a half life cycle
                        cycles.append(0.5)
                        soc.append(mean(self.vehicle.cycle_soc))
                        dod.append(
                            abs(self.vehicle.cycle_soc[0] - self.vehicle.cycle_soc[-1])
                        )
                        temp.append(mean(self.vehicle.cycle_temperatures))
                        c_rates.append(mean(self.vehicle.cycle_c_rates))
                        durations.append(sum(self.vehicle.cycle_times))

                        degradation = self.vehicle.compute_degradation(
                            soc, dod, c_rates, temp, cycles, durations
                        )

                        # Vectors for graphs
                        times.append(times[-1])
                        states.append(state)
                        degradation_history.append(degradation * 100)
                        energy_history.append(energy)
                        self.vehicle.reset_degradation_helpers()

                    # charge
                    initial_soc = energy / self.vehicle.capacity_kWh
                    final_soc = max_level / self.vehicle.capacity_kWh
                    charge_kw = 22
                    charge_dict = self.vehicle.charge_simulator.chargingTimeFunction(
                        initial_soc,
                        final_soc,
                        inputPower=charge_kw,
                        batterySize=self.vehicle.initial_Wh_capacity,
                    )
                    if plot_charges:
                        plt.figure()
                        plt.plot(
                            [c / 60 for c in charge_dict["times"]],
                            [c / 10e5 for c in charge_dict["eLevels"]],
                        )
                        plt.ylabel("kWh")
                        plt.xlabel("Minutes")
                        plt.show()
                    seconds = charge_dict.get("serviceTime")
                    energy = max_level

                    cycles.append(0.5)
                    soc.append(mean([initial_soc, final_soc]))
                    dod.append(final_soc - initial_soc)
                    # todo: fix this
                    temp.append(30 + 273)
                    c_rates.append(
                        charge_kw
                        * 1000
                        / (self.vehicle.mean_voltage * self.vehicle.capacity_AH)
                    )
                    durations.append(seconds)
                    degradation = self.vehicle.compute_degradation(
                        soc, dod, c_rates, temp, cycles, durations
                    )

                    self.vehicle.reset_degradation_helpers()

                state = self.decide_transition(state)
            elif state == "idle":
                seconds = rng.integers(*self.vehicle.idle_time_interval)
                idle_time += seconds
                state = self.decide_transition(state)
                if idle_time / 3600 > max_idle_hours:
                    # Ensure to pass to a driving state
                    while not state.isdigit():
                        state = self.decide_transition(state)
                    idle_time = 0

            times.append(times[-1] + seconds)
            states.append(state)
            degradation_history.append(degradation * 100)
            energy_history.append(energy)

        hours = [t / 3600 for t in times]
        plot_dict = {
            "Capacity (kWh)": energy_history,
            "states": states,
            "Capacity loss(%)": degradation_history,
        }

        for label, data in plot_dict.items():
            plt.figure()
            plt.plot(hours, data)
            plt.xlabel("Hours")
            plt.ylabel(label)
            plt.show()

        return plot_dict, hours
