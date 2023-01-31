import numpy as np
from abc import ABC, abstractmethod


class BaseModel(ABC):
    @abstractmethod
    def compute_consumption(self):
        pass


class MachineLearningConsumptionModel(BaseModel):
    def __init__(self, mean_power_usr):
        pass

    def compute_consumption(self):
        pass


class WangModel(BaseModel):
    def __init__(
        self, v_i=10, acc=1.5, acc_fr=-2, frontal_area=2.43, cd=0.31, mass=1622
    ):
        """

        :param v_i: Velocidad inicial kmh
        :param acc: limite máximo de aceleración m/s**2
        :param acc_fr: limite máximo de desaceleración m/s**2
        :param frontal_area: m**2
        :param cd: ?
        :param mass: kg
        """
        self.v_i = v_i
        self.acc = acc  # 5.1 zoe
        self.acc_fr = acc_fr
        self.frontal_area = frontal_area
        self.cd = cd
        self.mass = mass  # con Santiago manejando en leaf

    def compute_consumption(self, df):
        consumption = []
        df["m"] = df["kms"] * 10 ** 3
        vars = df[["slope", "travel_time", "mean_speed", "m"]]

        for index, row in vars.iterrows():
            # m/s
            nominal_speed = row["mean_speed"] / 3.6
            if self.v_i < nominal_speed:
                a = self.acc
                v_f = np.sqrt(self.v_i ** 2 + 2 * a * row["m"])
                v_f = min([v_f, nominal_speed])

            elif self.v_i == nominal_speed:
                v_f = nominal_speed
                a = 0

            else:
                a = self.acc_fr
                v_f = np.sqrt(self.v_i ** 2 + 2 * a * row["m"])
                v_f = v_f if v_f == v_f else nominal_speed  # si es nan
                v_f = max([v_f, nominal_speed])

            mean_speed = np.mean([self.v_i, v_f])

            # seconds
            t = row["m"] / mean_speed
            dv = v_f - self.v_i

            # Force calculation
            p = 1.2  # Air density kg/m3
            cr = 0.01 * (1 + mean_speed / (100))  # Rolling coefficient 1
            bar = 30 / 14.504
            cr2 = 0.005 + (1 / bar) * (
                0.01 + 0.0095 * (mean_speed / 100) ** 2
            )  # Rolling coefficient 2
            n_drive = 0.98  # transmission efficiency
            n_motor = 0.97  # Motor efficiency
            n_batt = 0.98  # Battery efficiency
            k = 0  # speed factor
            p_aux = 1.5  # kW aux components

            rad = row["slope"] * np.pi / 180

            friction_force = (cr2 * self.mass * 9.81 * np.cos(rad)) + (
                0.5 * p * self.frontal_area * self.cd * (mean_speed) ** 2
            )

            Fw = self.mass * 9.81 * np.sin(rad)
            net_force = self.mass * (dv / t) + Fw + friction_force

            if mean_speed < 5:
                k = mean_speed * 0.89
            else:
                k = 0.89 + 0.015 * (mean_speed - 5)

            # Adaptando eficiencias de Jimenez
            # si está consumiendo
            if any([a == self.acc, a == 0]):
                net_force = net_force / (n_drive * n_batt * n_motor)
            # regenerando
            else:
                net_force = k * net_force * n_drive * n_motor * n_batt

            consumption.append(net_force * row["m"] * 0.00000028 + p_aux * t / 3600)

            self.v_i = v_f

        return np.array(consumption)
