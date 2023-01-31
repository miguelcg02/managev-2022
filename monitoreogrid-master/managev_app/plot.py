import json
import time

import numpy as np
import pandas as pd
import plotly
import plotly.graph_objs as go


def create_double_plot(data_frame, x_name, y_name):
    x = data_frame[x_name]
    y = data_frame[y_name].to_numpy()
    y1 = np.where(y >= 0, y, 0)
    y2 = np.where(y <= 0, y, 0)

    fig = go.Figure(
        go.Scatter(
            x=x,
            y=y1,
            mode="lines",
            name="Consumption",
            fill="tozeroy",
            fillcolor="blue",
        )
    )
    fig.add_trace(
        go.Scatter(
            x=x,
            y=y2,
            mode="lines",
            name="Regeneration",
            fill="tozeroy",
            fillcolor="orange",
        )
    )

    scatter_json = json.dumps(fig, cls=plotly.utils.PlotlyJSONEncoder)
    return scatter_json


def create_plot(data_frame, x, y):
    data_scatter = [go.Scatter(x=data_frame[x], y=data_frame[y])]
    scatter_json = json.dumps(data_scatter, cls=plotly.utils.PlotlyJSONEncoder)
    return scatter_json


def create_kwh_donut(df, x_name, y_name, out1_name, out2_name):
    dates = pd.to_datetime(df["timestamp"], format="%Y-%m-%d %H:%M:%S.%f")
    x = np.array(
        [time.mktime(t.timetuple()) for t in dates]
    )  # total seconds since epoch

    y = df[y_name].to_numpy()
    y1 = np.where(y >= 0, y, 0)
    y2 = np.where(y <= 0, y, 0)
    # x = df[x_name].to_numpy()
    labels = [out1_name, out2_name]

    try:
        values = [
            np.around((np.trapz(y1, x) / 3600), 3),
            abs(np.around((np.trapz(y2, x) / 3600), 3)),
        ]  # j to kwh
    except IndexError:
        values = [0.000001, 0.000001]
    print(["Integrals = ", values])
    data_donut = [go.Pie(labels=labels, values=values, hole=0.3)]
    pie_json = json.dumps(data_donut, cls=plotly.utils.PlotlyJSONEncoder)
    return pie_json
