import math
import statistics as stats
import time
from typing import List

import numpy as np
import pandas as pd


def wang(current, delta_t, batt_temp):
    """

    :param current: mean amperes during delta t seconds
    :param delta_t: seconds
    :param batt_temp: celcius degrees
    :return: capacity loss in %
    """
    ah = current * delta_t / 3600
    c_rate = current / 100  # 100 = Amperios hora totales bateria
    if c_rate > 0:
        b = 448.96 * c_rate ** 2 - 6301.1 * c_rate + 33840
        try:
            q_loss = (
                b
                * math.exp((-31700 + (c_rate * 370.3)) / (8.314472 * (batt_temp)))
                * ah ** 0.552
            )
        except OverflowError:
            q_loss = 0
    else:
        q_loss = 0

    return q_loss


def add_wang_column(df):
    dates = pd.to_datetime(df["timestamp"], format="%Y-%m-%d %H:%M:%S.%f")
    x = np.array(
        [time.mktime(t.timetuple()) for t in dates]
    )  # total seconds since epoch
    df["x1"] = x
    dates2 = df["x1"].iloc[1:]
    dates2 = dates2.append(pd.Series(df["x1"].iloc[-1]), ignore_index=True)
    df["x2"] = dates2

    df["delta_t"] = df["x2"] - df["x1"]
    df["wang_degradation"] = df.apply(
        lambda row: wang(row["current"], row["delta_t"], row["batt_temp"]), axis=1
    )
    df["cumulative_degradation"] = df["wang_degradation"].cumsum()
    del df["x2"], df["x1"]


class XuDegradationModel:
    # TODO: add helper method to append a row
    def __init__(
        self, soc: List, dod: List, c_rates: List, temp: List, n: List, seconds: int
    ):
        """
        n:  (n1, n2, . . . , nn) where ni = 1 if full cycle or 0.5 if half cycle
        Half-cycle means one single charge or discharge event

        soc: (SoC1, SoC2, . . . , SoCn) float numbers ranging from 0 to 1
        dod: (DoD1, DoD2, . . . , DoDn) float numbers ranging from 0 to 1
        c_rates:  (C1, C2, . . . , Cn)
        temp:  (T1, T2, . . . , Tn) in kelvin degrees

        Ci = DoDi· 2n · (3600s) / tend − tstart where time are in the unit of second
        Ti = average in Kelvin

        """

        self.soc = soc
        self.dod = dod
        self.c_rates = c_rates
        self.temp = temp
        self.n = n
        self.length: int = len(soc)

        self.soc_avg = stats.mean(self.soc)
        self.t_avg = stats.mean(self.temp)

        self.seconds = seconds

    def compute_degradation(self) -> float:
        """
        The capacity degradation model begins with the nonlinear degradation function,
        which models SEI formation process and the effect of lithium loss on
        degradation, shown as:
        L = 1 − (pSEI · e**−rSEI·fd + (1 − pSEI) · e**−fd )

        SoH = 1 − L

        :rtype: loss: % of capacity loss
        """
        self.validate()
        fd = self.f_cycle() + self.f_calendar()
        r_sei = 121
        p_sei = 5.75e-2
        loss = 1 - (p_sei * math.exp(-r_sei * fd) + (1 - p_sei) * math.exp(-fd))
        return loss

    def f_cycle(self):
        """
        Calculates degradation due to cycle ageing
        = (fDoD(DoD) · fC(C) + ft(t/N)) · fSoC(SoC) · fT (T) · N
        :return: fd non-dimensional parameter
        """
        return sum(
            self._f_dod(self.dod[i])
            * self._f_soc(self.soc[i])
            * self._f_c_rate(self.c_rates[i])
            * self._f_temp(self.temp[i])
            * self.n[i]
            for i in range(self.length)
        )

    def f_calendar(self):
        """
        Calculates degradation due to calendar ageing
        :return: fc non-dimensional parameter
        """
        kt = 4.14e-10  # 4.14E-10/s
        return kt * self.seconds * self._f_soc(self.soc_avg) * self._f_temp(self.t_avg)

    @staticmethod
    def _f_soc(soc):
        """
        kSoC is the SoC stress coefficient and SoCref is the reference SoC
        level
        :param soc: 0 to 1
        :return: f_soc non-dimensional parameter
        """
        k_soc = 1.04
        soc_ref = 0.5
        return math.exp(k_soc * (soc - soc_ref))

    @staticmethod
    def _f_dod(dod):
        """
        independent from time
        fDoD(DoD) = (kDoD1DoDkDoD2 + kDoD3)**−1
        where kDoD1, kDoD3, and kDoD3 are DoD stress model coefficients
        fitted according to 20% capacity loss

        :param dod:
        :return: f_dod non-dimensional parameter
        """
        k_dod_1 = 8.95e4
        k_dod_2 = -4.86e-1
        k_dod_3 = -7.28e4
        return (k_dod_1 * (dod ** k_dod_2) + k_dod_3) ** -1

    @staticmethod
    def _f_c_rate(c_rate):
        """
        Thus C-rate capacity
        fading tests must be carefully designed to avoid the influence from temperature
        C = |I| · (1h) / Qr

        Qr is the remaining or total charge capacity of the battery at current
        status
        :param c_rate:
        :return: f_c_rate non-dimensional parameter
        """
        try:
            c_ref = 1
            k_c = 2.63e-1
            return math.exp(k_c * (c_rate - c_ref))

        except OverflowError:
            print("c-rate too large")
            return 1

    @staticmethod
    def _f_temp(t) -> float:
        """
        where kT is the temperature stress coefficient,
        Tref is the reference temperature, in Kelvin.
        Here the reference temperature is set to 293K or 25◦C,
        in which most of the calendar ageing experiments are performed
        :rtype: f_temp non-dimensional parameter
        """
        k_t = 6.93e-2
        t_ref = 293  # or 25 celsius
        return math.exp(k_t * (t - t_ref) * (t_ref / t))

    def validate(self):
        if any(
            len(i) != len(self.soc)
            for i in [self.soc, self.dod, self.c_rates, self.temp, self.n]
        ):
            raise ValueError("Input vector lengths not equal")
