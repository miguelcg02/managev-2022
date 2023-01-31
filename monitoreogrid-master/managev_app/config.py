import os

from dotenv import load_dotenv
from flask import session

basedir = os.path.abspath(os.path.dirname(__file__))
load_dotenv(os.path.join(basedir, ".env"))


class SessionConfig:
    def __init__(self, now):
        self.sess = {
            "form_d1": now.strftime("%d/%m/%Y"),
            "form_h1": "0:01 AM",
            "form_h2": now.strftime("%I:%M %p"),
            "d1": now.strftime("%Y-%m-%d"),
            "h1": "00:00:00",
            "h2": now.strftime("%H:%M:%S"),
            "graph_var_x": "timestamp",
            "graph_var_y": "speed",
            "calendar_var": "drivetime",
            "map_var": "elevation",
            "time_interval": "2 d",
            "est_time": 0,
            "est_cons": 0,
            "lights": 0,
            "var1": "odometer",
            "var2": "speed",
            "var3": "mean_acc",
            "var4": "power_kw",
            "var5": "slope",
            "records": 200,
            "form_d2": now.strftime("%d/%m/%Y"),
            "form_h3": "0:01 AM",
            "form_h4": now.strftime("%I:%M %p"),
            "d2": now.strftime("%Y-%m-%d"),
            "h3": "00:00:00",
            "h4": now.strftime("%H:%M:%S"),
            "graph_var_x2": "timestamp",
            "graph_var_y2": "capacity",
        }

    def assign_missing_variables(self):
        """
        Mutates flask session to add key, value pairs from self.sess
        Returns:
            object:
        """
        for key in self.sess.keys():
            if key not in session.keys():
                session[key] = self.sess.get(key)


class OperationQuery:
    def __init__(self, vehicle):
        self.query_1 = (
            "SELECT "
            + session["graph_var_x"]
            + " ,"
            + session["graph_var_y"]
            + ' from operation WHERE vehicle_id = "'
            + str(vehicle.placa)
            + '" AND '
            + session["graph_var_y"]
            + ' IS NOT NULL AND timestamp BETWEEN "'
            + session["d1"]
            + " "
            + str(session["h1"])[:8]
            + '" and "'
            + str(session["d1"])
            + " "
            + str(session["h2"])[:8]
            + '"'
        )

        self.query_2 = (
            "SELECT "
            + session["graph_var_x2"]
            + " ,"
            + session["graph_var_y2"]
            + ' from operation WHERE vehicle_id = "'
            + str(vehicle.placa)
            + '" AND '
            + session["graph_var_y2"]
            + ' IS NOT NULL AND timestamp BETWEEN "'
            + session["d2"]
            + " "
            + str(session["h3"])[:8]
            + '" and "'
            + str(session["d2"])
            + " "
            + str(session["h4"])[:8]
            + '"'
        )


class CalendarQuery:
    def __init__(self, vehicle):
        self.query = (
            "SELECT date(timestamp), MAX("
            + session["calendar_var"]
            + ") as 'max_value' FROM operation WHERE vehicle_id = '"
            + str(vehicle.placa)
            + "' GROUP BY date(timestamp)"
        )


class DevConfig:
    SECRET_KEY = (
        os.environ.get("SECRET_KEY") or "adljsakldjk72s4e21cjn!Ew@fhfghfghggg4565t@dsa"
    )
    # La clave puede venir como configuración idealmente
    SQLALCHEMY_DATABASE_URI = (
        # os.environ.get("DATABASE_URL") or
        "mysql+pymysql://admin:5Actu_adores.@localhost/monitoreodb"
    )

    SQLALCHEMY_TRACK_MODIFICATIONS = True
    TESTING = False


class Config:
    SECRET_KEY = (
        os.environ.get("SECRET_KEY") or "adljsakldjk72s4e21cjn!Ew@fhfghfghggg4565t@dsa"
    )
    SQLALCHEMY_DATABASE_URI = (
        os.environ.get("DATABASE_URL")
        or "mysql+pymysql://admin:5Actu_adores.@localhost:3306/monitoreodb"
        # "mysql+pymysql://admin:actuadores@104.236.94.94:3306/monitoreodb"
    )

    SQLALCHEMY_TRACK_MODIFICATIONS = False
    TESTING = False
