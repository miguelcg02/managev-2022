from datetime import datetime

import pytz
from flask_login import UserMixin
from dictalchemy import DictableModel
from sqlalchemy.orm import backref
from werkzeug.security import generate_password_hash, check_password_hash

from managev_app import db, login


class User(UserMixin, db.Model, DictableModel):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), index=True, unique=True)
    email = db.Column(db.String(120), index=True, unique=True)
    password_hash = db.Column(db.String(128))
    genre = db.String(64)
    driven_kms = db.Column(db.Integer)
    co2_saved = db.Column(db.Integer)
    roi = db.Column(db.Integer)  # Return on investment
    age = db.Column(db.Integer)
    driving_cluster = db.Column(db.Integer)
    charging_cluster = db.Column(db.Integer)
    geo_cluster = db.Column(db.Integer)

    # For debuging purposes, we type the instance name and it prints self,username
    def __repr__(self):
        return "<User {}>".format(self.username)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    # tasks = db.relationship("Task", backref="user", lazy="dynamic")


# Crear un metodo para serializar
# insert into vehicle(placa, marca, modelo, year, weight, cd, frontal_area, odometer) values('GHW284', 'RENAULT', 'ZOE', 2020, 1528, 0.31, 2.43, 0);
# insert into vehicle(placa, marca, modelo, year, weight, cd, frontal_area, odometer) values('FRV020', 'NISSAN', 'LEAF', 2018, 1584, 0.29, 2.28, 730);
# insert into vehicle(placa, marca, modelo, year, weight, odometer) values('BOTE02', 'ENERGETICA', 'ERICK', 2021, 9, 0);


class Vehicle(db.Model, DictableModel):
    id = db.Column(db.Integer, primary_key=True)
    placa = db.Column(db.String(64), index=True)
    marca = db.Column(db.String(64))
    modelo = db.Column(db.String(64))
    year = db.Column(db.Integer)
    weight = db.Column(db.Float)
    # https://en.wikipedia.org/wiki/Automobile_drag_coefficient
    cd = db.Column(db.Float)  # 0.29 car 1.8 motorcycle # Drag coefficient
    frontal_area = db.Column(
        db.Float
    )  # 0.303  # 0.79 car 0.303 motorcycle # Frontal area m2
    capacity_nominal = db.Column(db.Float)
    odometer = db.Column(db.Integer)  # db.ForeignKey('operation.odometer')) ?
    soh = db.Column(db.Float)
    rul = db.Column(db.Integer)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"))

    user = db.relationship(
        "User", backref=backref("vehicles", cascade="all, delete-orphan")
    )

    activo = db.Column(db.Boolean)

    # For debuging purposes, we type the instance name and it prints self,username
    def __repr__(self):
        return "<Placa {}>".format(self.placa)


class Station(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64), index=True, unique=True)
    latitude = db.Column(db.Float)
    longitude = db.Column(db.Float)
    elevation = db.Column(db.Float)
    charger_types = db.Column(db.String(64))
    number_of_chargers = db.Column(db.Integer)

    # For debuging purposes, we type the instance name and it prints self,username
    def __repr__(self):
        return "<Name {}>".format(self.name)


@login.user_loader
def load_user(id):
    return User.query.get(int(id))


class Operation(db.Model, DictableModel):

    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(
        db.DateTime,
        index=True,
        default=datetime.strptime(
            (
                datetime.now(pytz.timezone("America/Bogota")).strftime(
                    "%Y-%m-%d %H:%M:%S"
                )
            ),
            "%Y-%m-%d %H:%M:%S",
        ),
    )
    operative_state = db.Column(db.Integer)
    latitude = db.Column(db.Float)
    longitude = db.Column(db.Float)
    elevation = db.Column(db.Float)
    elevation2 = db.Column(db.Float)
    slope = db.Column(db.Float)
    run = db.Column(db.Float)
    net_force = db.Column(db.Float)
    friction_force = db.Column(db.Float)
    speed = db.Column(db.Float)
    mean_speed = db.Column(db.Float)
    odometer = db.Column(db.Float)
    acceleration = db.Column(db.Float)
    user_name = db.Column(db.String(64))
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"))
    batt_temp = db.Column(db.Float)
    ext_temp = db.Column(db.Float)
    power_kw = db.Column(db.Float)
    mec_power = db.Column(db.Float)
    pressure = db.Column(db.Float)
    mean_acc = db.Column(db.Float)
    capacity = db.Column(db.Float)
    vehicle_id = db.Column(db.String(64))
    soc = db.Column(db.Float)
    soh = db.Column(db.Float)
    voltage = db.Column(db.Float)
    current = db.Column(db.Float)
    angle_x = db.Column(db.Float)
    angle_y = db.Column(db.Float)
    charge_current = db.Column(db.Float)
    kwh_km = db.Column(db.Float)
    throttle = db.Column(db.Integer)
    regen_brake = db.Column(db.Float)
    mass = db.Column(db.Integer)
    consumption = db.Column(db.Float)
    range_est = db.Column(db.Integer)
    range_ideal = db.Column(db.Float)
    range_full = db.Column(db.Float)
    drivetime = db.Column(db.Float)
    drivemode = db.Column(db.String(64))
    charge_time = db.Column(db.Integer)
    charger_type = db.Column(db.String(64))
    footbrake = db.Column(db.Integer)
    engine_temp = db.Column(db.Float)
    is_charging = db.Column(db.Integer)
    tpms = db.Column(db.Float)
    coulomb = db.Column(db.Float)
    energy = db.Column(db.Float)
    coulomb_rec = db.Column(db.Float)
    energy_rec = db.Column(db.Float)
    freeram = db.Column(db.Integer)
    tasks = db.Column(db.Integer)
    net_signal = db.Column(db.Float)
    rpm = db.Column(db.Integer)
    AcX = db.Column(db.Float)
    AcY = db.Column(db.Float)
    AcZ = db.Column(db.Float)
    humidity = db.Column(db.Float)
    assist_level = db.Column(db.Integer)
