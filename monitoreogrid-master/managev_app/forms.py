from datetime import datetime

from flask import request
from flask_wtf import FlaskForm
from wtforms import (
    StringField,
    PasswordField,
    BooleanField,
    SubmitField,
    TextAreaField,
    IntegerField,
    FloatField,
)
from wtforms.validators import ValidationError, DataRequired, Email, EqualTo

from managev_app.models import User, Vehicle


def read_form_dates(session, day, hour):
    session["d%d" % day] = (
        datetime.strptime(request.form["d%d" % day], "%d/%m/%Y")
    ).strftime("%Y-%m-%d")
    session["h%d" % hour] = (
        datetime.strptime(request.form["h%d" % hour], "%I:%M %p")
    ).strftime("%H:%M:%S")
    session["h%d" % (hour + 1)] = (
        datetime.strptime(request.form["h%d" % (hour + 1)], "%I:%M %p")
    ).strftime("%H:%M:%S")
    if session["h%d" % (hour + 1)] < session["h%d" % hour]:
        session["h%d" % hour], session["h%d" % (hour + 1)] = (
            session["h%d" % (hour + 1)],
            session["h%d" % hour],
        )


class LoginForm(FlaskForm):
    username = TextAreaField("Usuario", validators=[DataRequired()])
    password = PasswordField("Contraseña", validators=[DataRequired()])
    remember_me = BooleanField("Recordar usuario")
    submit = SubmitField("Sign In")


class RegistrationForm(FlaskForm):
    username = StringField("Usuario", validators=[DataRequired()])
    email = StringField("Email", validators=[DataRequired(), Email()])
    password = PasswordField("Contraseña", validators=[DataRequired()])
    password2 = PasswordField(
        "Repetir Contraseña", validators=[DataRequired(), EqualTo("password")]
    )
    submit = SubmitField("Register")

    def validate_username(self, username):
        user = User.query.filter_by(username=username.data).first()
        if user is not None:
            raise ValidationError("Por favor ingrese un usuario diferente.")

    def validate_email(self, email):
        user = User.query.filter_by(email=email.data).first()
        if user is not None:
            raise ValidationError("Por favor ingrese un email diferente.")


class VehicleRegistrationForm(FlaskForm):
    placa = StringField("Placa", validators=[DataRequired()])
    marca = StringField("Marca", validators=[DataRequired()])
    year = IntegerField("Modelo", validators=[DataRequired()])
    submit = SubmitField("Register")

class BoatRoutesCoords(FlaskForm):
    lonIni = FloatField("Longitud Inicial", validators=[DataRequired()])
    latIni = FloatField("Latitud Inicial", validators=[DataRequired()])
    lonFin = FloatField("Longitud Final", validators=[DataRequired()])
    latFin = FloatField("Latitud Final", validators=[DataRequired()])
    submit = SubmitField("Submit data")

class Ruta2Puntos(FlaskForm):
    rutalonIni = FloatField("Longitud Inicial", validators=[DataRequired()])
    rutalatIni = FloatField("Latitud Inicial", validators=[DataRequired()])
    rutalonFin = FloatField("Longitud Final", validators=[DataRequired()])
    rutalatFin = FloatField("Latitud Final", validators=[DataRequired()])
    submit = SubmitField("Distancia")

class DistanciaCoords(FlaskForm):
    distlonIni = FloatField("Longitud Inicial", validators=[DataRequired()])
    distlatIni = FloatField("Latitud Inicial", validators=[DataRequired()])
    distancia = FloatField("Distancia", validators=[DataRequired()])
    submit = SubmitField("Ruta entre 2 puntos")
