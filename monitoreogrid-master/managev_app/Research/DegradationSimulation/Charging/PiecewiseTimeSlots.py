from dataclasses import dataclass
from typing import List

""" Código inicialmente escrito por Isabel Cardenas para su maestría """


@dataclass
class PiecewiseLinear:
    _breakPoints: List[list] = None
    _timePoints: List[list] = None
    _power: List = None

    @property
    def breakpoints(self):
        return self._breakPoints

    @property
    def time_points(self):
        return self._timePoints

    @property
    def power(self):
        return self._power


class Piecewise:
    def __init__(self, charging_powers: list = None, n_breakpoints: int = 4, E=None):
        """

        :param charging_powers: allowed charging powers in kW
        :param n_breakpoints: number of breakpoints
        :param E: Watts?? has to do something with energy?
        :time_points: tiempo de carga asociado a cada breakpoint
        :breakpoints: nivel de la bateria asociado a cada breakpoint

        """
        if charging_powers is None:
            charging_powers = [3, 11, 22, 44]
        self.charging_powers = charging_powers

        self.n_breakpoints = list(range(n_breakpoints))

        if E is None:
            E = [16000, 24000, 30000, 40000]
        self.E = [e * 1000 for e in E]

        self.breakPoints = [0, 0.85, 0.95, 1]
        self.timePoints = [0, 0.61, 0.76, 1]

        # miu(ghl) g in G, h in B, l in E

        breakpoints = {
            (power, e): [self.breakPoints[i] * e for i in self.n_breakpoints]
            for power in self.charging_powers
            for e in self.E
        }

        # psi(ghl) g in G, h in B, l in E

        self.powerStation = []
        time_points = {}
        power_to_coefficient_map = {
            3: 32.48,
            11: 16.04,
            22: 8.01,
            44: 4.01,
        }
        for power in self.charging_powers:
            self.powerStation.append(power)
            for e in self.E:
                time_points.update(
                    {
                        (power, e): [
                            self.timePoints[i]
                            * e
                            * power_to_coefficient_map.get(power, 1)
                            / 16000
                            for i in self.n_breakpoints
                        ]
                    }
                )

        self.piecewise_linear = PiecewiseLinear(
            breakpoints, time_points, self.powerStation
        )

    def chargingTimeFunction(self, startLevel, exitLevel, inputPower, batterySize):
        """
        Funcion para calcular la duracion de la carga

        # Parametros de entrada: estado de carga inicial, estado de carga final, potencia de carga, capacidad de la bateria
        # Para un vehiculo esto seria o,o+q,y,delta
        # startLevel y exitLevel [0,1], inputPower y batterySize en kW

        :param startLevel: initial SoC
        :param exitLevel: final SoC
        :param inputPower: kW
        :param batterySize: Watts*h?
        :return:
        """
        batterySize *= 1000
        outputTime = 0
        charge_config = (inputPower, batterySize)

        startLevel *= batterySize
        exitLevel *= batterySize

        times = []  # Inicio, Fin y BkPoints de tiempo de los tramos usados la PW
        eLevels = []  # Inicio, Fin y BkPoints de batLevel de los tramos usados la PW

        for i in range(1, len(self.piecewise_linear.breakpoints[charge_config])):
            # lowerBound y upperBound son los valores de los breakpoints
            # de bateria para el tramo correspondiente donde inicia la carga
            lowerBound = self.piecewise_linear.breakpoints[charge_config][i - 1]
            upperBound = self.piecewise_linear.breakpoints[charge_config][i]

            # identifica en que tramo de la función inicia el vehiculo la carga
            if lowerBound <= startLevel <= upperBound:
                # alpha es el porcentaje que falta para finalizar el tramo
                alpha = (startLevel - upperBound) / (lowerBound - upperBound)
                lowerTime = self.piecewise_linear.time_points[charge_config][
                    i - 1
                ]  # breakpoint del tiempo en que inicia el tramo
                UpperTime = self.piecewise_linear.time_points[charge_config][
                    i
                ]  # breakpoint del tiempo en que termina el tramo
                inputTime = lowerTime * alpha + UpperTime * (
                    1 - alpha
                )  # valor del tiempo en la piecewise en el que inicia el vehiculo la carga

                times.append(inputTime)
                eLevels.append(startLevel)

                for n in range(
                    i, len(self.piecewise_linear.breakpoints[charge_config])
                ):
                    # Este ciclo lo recorre cada vez que se usa un tramo de la PW
                    # son los valores de los breakpoints de bateria para el tramo correspondiente
                    lowerBoundOutput = self.piecewise_linear.breakpoints[charge_config][
                        n - 1
                    ]
                    upperBoundOutput = self.piecewise_linear.breakpoints[charge_config][
                        n
                    ]

                    if lowerBoundOutput <= exitLevel <= upperBoundOutput:
                        # Beta es el porcentaje que falta para finalizar el tramo
                        beta = (exitLevel - upperBoundOutput) / (
                            lowerBoundOutput - upperBoundOutput
                        )
                        lowerTimeOutput = self.piecewise_linear.time_points[
                            charge_config
                        ][
                            n - 1
                        ]  # breakpoint del tiempo en que inicia el tramo
                        upperTimeOutput = self.piecewise_linear.time_points[
                            charge_config
                        ][
                            n
                        ]  # breakpoint del tiempo en que termina el tramo
                        outputTime = lowerTimeOutput * beta + upperTimeOutput * (
                            1 - beta
                        )  # valor del tiempo en la piecewise en el que termina el vehiculo la carga

                        times.append(outputTime)
                        eLevels.append(exitLevel)
                        break

                    else:
                        times.append(
                            self.piecewise_linear.time_points[charge_config][n]
                        )
                        eLevels.append(upperBoundOutput)

                break

        # Energia cargada en cada tramo de la PW (de los tramos usados)
        eCharged = [(eLevels[i + 1] - eLevels[i]) for i in range(len(eLevels) - 1)]

        serviceTime = outputTime - inputTime

        return dict(
            serviceTime=serviceTime,
            times=times,
            eLevels=eLevels,
            eCharged=eCharged,
        )
