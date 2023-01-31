import ast
from cgi import print_arguments
import json
import logging
import math
import os
import csv
from datetime import datetime, timedelta
import requests
import geopy.distance
import googlemaps
import numpy as np
import pandas as pd
import pytz
import osmnx as ox
import matplotlib.pyplot as plt
import cv2
from skimage.morphology import skeletonize
from skimage.util import invert

from flask import (
    request,
    session,
    redirect,
    Blueprint,
    url_for,
    Markup,
    render_template,
    flash,
    send_from_directory,
    Response,
    current_app,
)
from flask_login import current_user, login_user, logout_user, login_required
from werkzeug.urls import url_parse

from managev_app import open_dataframes, plot, db, consumption_models
from managev_app.Research.DegradationSimulation.Degradation import degradation_models
from managev_app.Research.Google import google_interactor
from managev_app.closest_points import Trees
from managev_app.config import SessionConfig, OperationQuery, CalendarQuery
from managev_app.forms import (
    LoginForm,
    RegistrationForm,
    VehicleRegistrationForm,
    read_form_dates,
    BoatRoutesCoords,
    Ruta2Puntos,
    DistanciaCoords,
)
from managev_app.models import User, Operation, Vehicle

dashboard = Blueprint("dashboard", __name__)

logger = logging.getLogger(__name__)
google_sdk_key = os.environ.get("GOOGLE_SDK_KEY")


users_list = ["esgomezo", "auribev1", "sechava4"]
elevation_endpoint = "https://elevation.racemap.com/api"


# ---------------------------------Vehicle routes ----------------------------------#
@dashboard.route("/my_vehicles/<username>")
@login_required
def my_vehicles(username):
    user = User.query.filter_by(username=username).first_or_404()

    query = 'SELECT * FROM vehicle where user_id = "' + str(user.id) + '"'

    df_vehicles = pd.read_sql_query(query, db.engine)
    print(df_vehicles.to_json(orient="records", indent=True))
    return render_template(
        "vehicle.html", user=user, vehicles=df_vehicles.to_json(orient="records")
    )


@dashboard.route("/update_vehicle/<placa>")
@login_required
def update_vehicle(placa):
    vehicles = Vehicle.query.filter_by(user_id=current_user.id)
    for vehicle in vehicles:
        if vehicle.placa == placa:
            vehicle.activo = True
            print("Activando vehiculo:", placa)
        else:
            vehicle.activo = False
    db.session.commit()
    return redirect(url_for("dashboard.show_entries"))


@dashboard.route("/register_vehicle", methods=["GET", "POST"])
@login_required
def register_vehicle():
    form = VehicleRegistrationForm()
    if form.validate_on_submit():
        existing_vehicles = (
            db.session.query(Vehicle).filter(Vehicle.user_id == current_user.id).all()
        )
        for existing in existing_vehicles:
            existing.activo = False
        properties = {}
        if form.marca.data == "RENAULT":
            properties.update(dict(cd=0.31, frontal_area=2.43, weight=1528))
        vehicle = Vehicle(
            placa=form.placa.data,
            marca=form.marca.data,
            year=int(form.year.data),
            user_id=current_user.id,
            cd=properties.get("cd"),
            frontal_area=properties.get("frontal_area"),
            weight=properties.get("weight"),
            odometer=0,
            activo=True,
        )
        db.session.add(vehicle)
        db.session.commit()
        flash("Has registrado un nuevo vehículo!")
        return redirect(
            url_for("dashboard.my_vehicles", username=current_user.username)
        )
    return render_template("register_vehicle.html", title="Register", form=form)


# ----------------------------------- Dashboards --------------------------------------------------#


@dashboard.route("/", methods=["GET", "POST"])
@login_required
def show_entries():
    """
    main page
    :return:
    """
    user_vehicles = [
        v.asdict() for v in Vehicle.query.filter(Vehicle.user == current_user).all()
    ]
    vehicle = Vehicle.query.filter_by(user=current_user, activo=True).first()
    now = datetime.now(pytz.timezone("America/Bogota")) + timedelta(hours=1)

    sess_conf = SessionConfig(now)
    sess_conf.assign_missing_variables()

    if request.method == "POST":
        for var in [
            "graph_var_y",
            "graph_var_y2",
            "graph_var_y2",
        ]:
            session[var] = request.form[var]

        for var in ["d1", "h1", "h2", "d2", "h3", "h4"]:
            session["form_" + var] = request.form[var]

        read_form_dates(session, day=1, hour=1)  # hours 1 and 2
        read_form_dates(session, day=2, hour=3)  # hours 3 and 4

    if vehicle:
        operation_query = OperationQuery(vehicle)
        calendar_query = CalendarQuery(vehicle)

        df_calendar = pd.read_sql_query(calendar_query.query, db.engine)
        df_calendar = df_calendar.dropna()
        if session.get("calendar_var") == "drivetime":
            df_calendar["max_value"] = df_calendar["max_value"] / 3600
        df_o = pd.read_sql_query(operation_query.query_1, db.engine)
        df_o2 = pd.read_sql_query(operation_query.query_2, db.engine)

        scatter = plot.create_plot(df_o, session["graph_var_x"], session["graph_var_y"])
        scatter2 = plot.create_plot(
            df_o2, session["graph_var_x2"], session["graph_var_y2"]
        )
        box = df_o[session["graph_var_y"]].tolist()
        box2 = df_o2[session["graph_var_y2"]].tolist()

        for var in [
            "graph_var_y",
            "graph_var_y2",
        ]:
            session[var + "_pretty"] = open_dataframes.pretty_var_name(session[var])

        # map graph
        lines_df = open_dataframes.get_lines(
            vehicle, session["d1"], session["h1"], session["h2"]
        )
        json_lines = Markup(lines_df.to_json(orient="records"))

        alturas_df = open_dataframes.get_heights(
            vehicle,
            session["graph_var_y2"],
            session["d1"],
            session["h1"],
            session["h2"],
        )

        session["map_var_pretty"] = open_dataframes.pretty_var_name(session["map_var"])
        json_operation = Markup(alturas_df.to_json(orient="records"))

    else:
        scatter = 0
        scatter2 = 0
        box = 0
        box2 = 0
        df_calendar = pd.DataFrame()
        json_lines = ({},)
        json_operation = ({},)

    return render_template(
        "show_entries.html",
        plot=scatter,
        box=box,
        plot2=scatter2,
        box2=box2,
        calendar=df_calendar.to_json(orient="records"),
        vehicles=json.dumps(user_vehicles),
        json_lines=json_lines,
        json_operation=json_operation,
        users_list=users_list,
    )


@dashboard.route("/updateplot")
def update_plot():
    """
    updates graphs of main page
    :return:
    """
    vehicle = Vehicle.query.filter_by(user_id=current_user.id, activo=True).first()
    if "calendar_var" not in session.keys():
        session["calendar_var"] = "drivetime"

    operation_query = OperationQuery(vehicle)
    df_o = pd.read_sql_query(operation_query.query_1, db.engine)
    scatter = plot.create_plot(df_o, session["graph_var_x"], session["graph_var_y"])

    return scatter


@dashboard.route("/energy", methods=["GET", "POST"])
@login_required
def energy_monitor():
    """
    page for energy related features such as consumption prediction and energy regeneration
    :return:
    """
    vehicle = Vehicle.query.filter_by(user_id=current_user.id, activo=True).first()
    now = datetime.now(pytz.timezone("America/Bogota"))
    sess_conf = SessionConfig(now)
    sess_conf.assign_missing_variables()
    coords = []
    # todo: this post can be in another api endpoint
    if request.method == "POST":
        session["time_interval"] = request.form["time_interval"]
        try:
            session["P_ini"] = ast.literal_eval(request.form["pos_o"])
            session["P_fin"] = ast.literal_eval(request.form["pos_d"])
            now = datetime.now()
            gmaps = googlemaps.Client(key=google_sdk_key)
            google_client = gmaps.directions(
                origin=session["P_ini"],
                destination=session["P_fin"],
                mode="driving",
                alternatives=False,
                departure_time=now,
                traffic_model="pessimistic",
            )

            segments = google_interactor.get_segments(google_client)
            coords = list(segments["location"])

            (
                model_to_consumption_map,
                session["est_time"],
            ) = google_interactor.calculate_segments_consumption(
                segments, user=current_user.username
            )
            session.update(model_to_consumption_map)

        except SyntaxError:
            session["est_cons"] = 0
            session["est_time"] = 0

    session["energy_t1"] = now

    number = int(session["time_interval"].split()[0])
    unit = session["time_interval"].split()[1]
    if "h" in unit:
        session["energy_t2"] = now - timedelta(hours=number)
    elif "d" in unit:
        session["energy_t2"] = now - timedelta(days=number)

    operation_query = (
        'SELECT timestamp, power_kw from operation WHERE speed > 0 AND timestamp BETWEEN "'
        + str(session["energy_t2"])
        + '" and "'
        + str(session["energy_t1"])
        + '" ORDER BY timestamp'
    )

    df_o = pd.read_sql_query(operation_query, db.engine)
    try:
        scatter_cons = plot.create_double_plot(df_o, "timestamp", "power_kw")
        donut = plot.create_kwh_donut(df_o, "timestamp", "power_kw", "cons", "regen")
    except TypeError:
        scatter_cons = 0
        donut = 0
    session["t_int_pretty"] = open_dataframes.pretty_var_name(session["time_interval"])

    if current_user.username in users_list:
        return render_template(
            "energy_monitor.html",
            plot=scatter_cons,
            donut=donut,
            vehicle=vehicle,
            google_sdk_key=google_sdk_key,
            coords=coords,
        )


@dashboard.route("/tables", methods=["GET", "POST"])
@login_required
def show_tables():
    """
    page for displaying osm_data in tabular form
    :return:
    """
    query = 'SELECT * FROM vehicle where user_id = "' + str(current_user.id) + '"'
    df_vehicles = pd.read_sql_query(query, db.engine)

    vehicle = Vehicle.query.filter_by(user_id=current_user.id, activo=True).first()
    now = datetime.now(pytz.timezone("America/Bogota"))
    sess_conf = SessionConfig(now)
    sess_conf.assign_missing_variables()

    if request.method == "POST":
        for i in range(1, 6):
            session["var%d" % i] = request.form["var%d" % i]

        session["records"] = request.form["records"]
        for var in ["d1", "h1", "h2"]:
            session["form_" + var] = request.form[var]

        if session["records"] is None:
            session["records"] = 20

        read_form_dates(session, day=1, hour=1)

    if vehicle:
        query = (
            "SELECT timestamp, "
            + session["var1"]
            + " ,"
            + session["var2"]
            + " ,"
            + session["var3"]
            + " ,"
            + session["var4"]
            + " ,"
            + session["var5"]
            + ' from operation WHERE vehicle_id = "'
            + str(vehicle.placa)
            + '" AND timestamp BETWEEN "'
            + session["d1"]
            + " "
            + str(session["h1"])[:8]
            + '" and "'
            + str(session["d1"])
            + " "
            + str(session["h2"])[:8]
            + '" limit '
            + str(session["records"])
        )

        session["query"] = query
        calendar_query = CalendarQuery(vehicle)
        df_calendar = pd.read_sql_query(calendar_query.query, db.engine)
        df_calendar = df_calendar.dropna()
        operation_df = pd.read_sql_query(query, db.engine)
        scatter = 0
        integral_jimenez = 0
        integral_power = 0
        integral_fiori = 0
        if (
            all(
                col in operation_df.columns
                for col in ["slope", "speed", "mean_acc", "power_kw"]
            )
            and len(operation_df.columns) == 6
            and len(operation_df) > 1
        ):

            try:
                consumption_models.add_consumption_cols(
                    operation_df,
                    float(vehicle.weight),
                    float(vehicle.frontal_area),
                    float(vehicle.cd),
                )

                scatter = plot.create_plot(
                    operation_df, "jimenez_estimation", "power_kw"
                )
                integral_jimenez = plot.create_plot(
                    operation_df, "timestamp", "jimenez_int"
                )
                integral_fiori = plot.create_plot(
                    operation_df, "timestamp", "fiori_int"
                )
                integral_power = plot.create_plot(
                    operation_df, "timestamp", "power_int"
                )
            except Exception as e:
                print(e)

        else:
            integral_jimenez = 0
            integral_fiori = 0
            integral_power = 0

        if all(col in operation_df.columns for col in ["current", "batt_temp"]):
            degradation_models.add_wang_column(operation_df)
    else:
        integral_jimenez = 0
        integral_fiori = 0
        integral_power = 0
        operation_df = pd.DataFrame([])
        session["query"] = None
        df_calendar = pd.DataFrame([])
        scatter = 0

    session["var1_pretty"] = open_dataframes.pretty_var_name(session["var1"])
    session["var2_pretty"] = open_dataframes.pretty_var_name(session["var2"])
    session["var3_pretty"] = open_dataframes.pretty_var_name(session["var3"])
    session["var4_pretty"] = open_dataframes.pretty_var_name(session["var4"])
    session["var5_pretty"] = open_dataframes.pretty_var_name(session["var5"])
    session["calendar_pretty"] = open_dataframes.pretty_var_name(
        session["calendar_var"]
    )

    return render_template(
        "tables.html",
        tables=[operation_df.to_html(classes="osm_data")],
        titles=operation_df.columns.values,
        plot=scatter,
        plotint1=integral_jimenez,
        plotint2=integral_power,
        plotint3=integral_fiori,
        calendar=df_calendar.to_json(orient="records"),
        vehicles=df_vehicles.to_json(orient="records"),
        users_list=users_list,
    )

@dashboard.route("/boat", methods=["GET", "POST"])
@login_required
def show_boat_routes():
    form = BoatRoutesCoords()

    if request.method == 'POST':
        # if form.validate_on_submit():
        if request.form.get('action1') == 'VALUE1':
            # Establecer coordenadas
            north = form.lonIni.data
            south = form.lonFin.data
            west = form.latIni.data
            east = form.latFin.data

            # Sacar tag y bbox de OX
            tags = {'natural':'water'}
            agua = ox.geometries_from_bbox(north,south,east,west,tags)
            # Plot Agua
            agua.plot(facecolor='blue')

            #Preprocesar imagen
            plt.xlim(west,east)
            plt.ylim(south,north)
            plt.axis('off')

            # Medidas norte sur
            coords_1 = (north,west)
            coords_2 = (south,west) 

            # Medidas oeste - este
            coords_3 = (north,west) 
            coords_4 = (north,east) 

            # Sacara las distancias norte sur y oeste este
            nor_sur = geopy.distance.geodesic(coords_1, coords_2).km
            oes_est = geopy.distance.geodesic(coords_3, coords_4).km

            # Guardar plot limpio
            plt.savefig('managev_app/static/intento.png', bbox_inches='tight',pad_inches = 0)

            print("Guardar plot limpio")

            #Abrir imagen con cv2
            img1 = cv2.imread('managev_app/static/intento.png')

            print("Abrir imagen con cv2")

            # Se instancian las variables para el nuevo alto y ancho al redimencionar
            # pixelAlto = (nor_sur/0.00854) #Se divide por la medida en kilometros que quiere que sean los nuevos pixeles, en este caso c/ pixel medirá 0.00854 km -> 8.54m
            # pixelAncho = (oes_est/0.00854)

            # # Se le saca el promedio para la proporcion de aumento del resize
            # proporcion = ((pixelAlto/len(img1))+(pixelAncho/len(img1[0])))/2 

            # #Redondear nueva cantidad de pixeles
            # nueAlt = round(proporcion*len(img1))
            # nueAnch= round(proporcion*len(img1[0]))

            # # Resize
            # imagenFinal = cv2.resize(img1, (nueAnch,nueAlt))

            # # Guardado de la imagen con cv2
            # cv2.imwrite('managev_app/static/intento.png',imagenFinal)
 
            # define a threshold, 128 is the middle of black and white in grey scale
            thresh = 128
        
            # assign blue channel to zeros
            img_binary = cv2.threshold(img1, thresh, 255, cv2.THRESH_BINARY)[1]

            # Invert the horse image
            image_invert = invert(img_binary)
            # perform skeletonization
            skeleton_img = skeletonize(image_invert)

            # display results
            rows = len(img1)
            colums = len(img1[0])

            posSke = []
            posVer = {}
            for i in range(rows):
                for j in range(colums):
                    if(skeleton_img[i][j][1] == 255):
                        img1[i][j] = [0, 255, 0]
                        posSke.append([i,j])
                        if i in posVer.keys():
                            posVer[i].append(j)
                        else:
                            posVer[i] = [j]

            tf = open("managev_app/static/coordsSke.json", "w")
            json.dump(posVer,tf)
            tf.close()

            with open('managev_app/static/coordsSke.csv', 'w') as file:
                writer = csv.writer(file)
                writer.writerow(posSke)

            cv2.imwrite('managev_app/static/intentoSke.png', img1) #Path where you want to save the skeletonize of the imaga

            imagen = '../../static/intento.png'
            coords =[north,south,west,east,rows,colums]

            return render_template("boat/boat_routes_seleccion.html",form=form,imagen=imagen,coords=coords)
    
    if request.method == 'GET':
        return render_template("boat/boat_routes.html",form=form)


@dashboard.route("/boat/ruta2puntos/<coords>", methods=["GET", "POST"])
@login_required
def ruta2puntos(coords):
    formRuta = Ruta2Puntos()
    imagen = '../../static/intentoSke.png'
    arr = coords[1:-1]
    arr = arr.split(", ")
    north = arr[0]
    south = arr[1]
    west = arr[2]
    east = arr[3]
    height = arr[4]
    width = arr[5]
    north = float(north)
    south = float(south)
    west = float(west)
    east = float(east)
    height = float(height)
    width = float(width)
    increment = (((north-south)/height)+(east-west)/width)/2

    if request.method == 'POST':
        coordX1 = formRuta.rutalatIni.data
        coordY1 = formRuta.rutalonIni.data
        coordX2 = formRuta.rutalatFin.data
        coordY2 = formRuta.rutalonFin.data

        posX1 = (coordX1-west)/increment
        posY1 = ((coordY1-north)/(-1*increment))

        posX2 = (coordX2-west)/increment
        posY2 = ((coordY2-north)/(-1*increment))

        posX1 = round(posX1)
        posY1 = round(posY1)
        posX2 = round(posX2)
        posY2 = round(posY2)

        pruebaX1 = posX1 # PruebaX es con el que se va a buscar la coord util en X
        pruebaY1 = posY1 # PruebaY es con el que se va a buscar la coord util en  Y
        pruebaX2 = posX2 # PruebaX es con el que se va a buscar la coord util en X
        pruebaY2 = posY2 # PruebaY es con el que se va a buscar la coord util en  Y
        encontrado = False
        resultadoX1 = 0 #resultadoX es la coord util encontrada en X 
        resultadoY1 = 0 #resultadoY es la coord util encontrada en Y
        resultadoX2 = 0 #resultadoX es la coord util encontrada en X 
        resultadoY2 = 0 #resultadoY es la coord util encontrada en Y

        tf = open("managev_app/static/coordsSke.json", "r")
        DicCoordsVerd = json.load(tf)

        if DicCoordsVerd:
            # Is not empty
            difActual = 100000000000
            while encontrado == False:
                if pruebaX1 > width:
                    pruebaX1 = list(DicCoordsVerd.keys())[-1]
                    print("Entro a pruebaX > width")
                    for posibleY1 in DicCoordsVerd[pruebaX1]:
                        if(abs(posibleY1-pruebaY1)<difActual):
                            difActual = abs(posibleY1-pruebaY1)
                            resultadoY1 = posibleY1
                    print("Salio de pruebaX > width")
                    break

                if str(pruebaX1) in DicCoordsVerd.keys():
                    print("Entro a pruebaX in DicCoordsVerd.keys():")
                    resultadoX1 = pruebaX1
                    if pruebaY1 in DicCoordsVerd[str(pruebaX1)]:
                        print("Entro a pruebaY in DicCoordsVerd[pruebaX]:")
                        resultadoY1 = pruebaY1
                        print("Salio de pruebaY in DicCoordsVerd[pruebaX]:")
                        break
                    else:
                        for posibleY1 in DicCoordsVerd[str(pruebaX1)]:
                            print("Entro a for posibleY in DicCoordsVerd[pruebaX]:")
                            if(abs(posibleY1-pruebaY1)<difActual):
                                difActual = abs(posibleY1-pruebaY1)
                                resultadoY1 = posibleY1
                        print("Salio del ultimo else y del for")
                        break
                else:
                    pruebaX1 = pruebaX1+1

        if DicCoordsVerd:
            # Is not empty
            difActual = 100000000000
            while encontrado == False:
                if pruebaX2 > width:
                    pruebaX2 = list(DicCoordsVerd.keys())[-1]
                    print("Entro a pruebaX > width")
                    for posibleY2 in DicCoordsVerd[pruebaX2]:
                        if(abs(posibleY2-pruebaY2)<difActual):
                            difActual = abs(posibleY2-pruebaY2)
                            resultadoY2 = posibleY2
                    print("Salio de pruebaX > width")
                    break

                if str(pruebaX2) in DicCoordsVerd.keys():
                    print("Entro a pruebaX in DicCoordsVerd.keys():")
                    resultadoX2 = pruebaX2
                    if pruebaY2 in DicCoordsVerd[str(pruebaX2)]:
                        print("Entro a pruebaY in DicCoordsVerd[pruebaX]:")
                        resultadoY2 = pruebaY2
                        print("Salio de pruebaY in DicCoordsVerd[pruebaX]:")
                        break
                    else:
                        for posibleY2 in DicCoordsVerd[str(pruebaX2)]:
                            print("Entro a for posibleY in DicCoordsVerd[pruebaX]:")
                            if(abs(posibleY2-pruebaY2)<difActual):
                                difActual = abs(posibleY2-pruebaY2)
                                resultadoY2 = posibleY2
                        print("Salio del ultimo else y del for")
                        break
                else:
                    pruebaX2 = pruebaX2+1
            
        return render_template("boat/boat_2puntos.html",imagen=imagen,formRuta=formRuta,coords=coords,north=north,south=south,west=west,east=east,height=height,width=width)

    return render_template("boat/boat_2puntos.html",imagen=imagen,formRuta=formRuta,coords=coords,north=north,south=south,west=west,east=east,height=height,width=width)

@dashboard.route("/boat/rutaDistancia/<coords>", methods=["GET", "POST"])
@login_required
def rutaDistancia(coords):
    formDis = DistanciaCoords()
    imagen = '../../static/intentoSke.png'
    arr = coords[1:-1]
    arr = arr.split(", ")
    north = arr[0]
    south = arr[1]
    west = arr[2]
    east = arr[3]
    height = arr[4]
    width = arr[5]
    north = float(north)
    south = float(south)
    west = float(west)
    east = float(east)
    height = float(height)
    width = float(width)
    increment = (((north-south)/height)+(east-west)/width)/2

    if request.method == 'POST':
        coordX = formDis.distlatIni.data
        coordY = formDis.distlonIni.data

        posX = (coordX-west)/increment
        posY = ((coordY-north)/(-1*increment))
        posX = round(posX) # Donde presiona el man en X
        posY = round(posY) # Donde presiona el man en Y

        pruebaX = posX # PruebaX es con el que se va a buscar la coord util en X
        pruebaY = posY # PruebaY es con el que se va a buscar la coord util en  Y
        encontrado = False
        resultadoX = 0 #resultadoX es la coord util encontrada en X 
        resultadoY = 0 #resultadoY es la coord util encontrada en Y

        tf = open("managev_app/static/coordsSke.json", "r")
        DicCoordsVerd = json.load(tf) 

        print(DicCoordsVerd)
        
        # Se va a buscar cual es la coordena util mas cerca al punto seleccionado
        if DicCoordsVerd:
            # Is not empty
            difActual = 100000000000
            while encontrado == False:
                print(pruebaX)
                print(width)
                print("---------")
                if pruebaX > width:
                    pruebaX = list(DicCoordsVerd.keys())[-1]
                    print("Entro a pruebaX > width")
                    for posibleY in DicCoordsVerd[pruebaX]:
                        if(abs(posibleY-pruebaY)<difActual):
                            difActual = abs(posibleY-pruebaY)
                            resultadoY = posibleY
                    print("Salio de pruebaX > width")
                    break

                if str(pruebaX) in DicCoordsVerd.keys():
                    print("Entro a pruebaX in DicCoordsVerd.keys():")
                    resultadoX = pruebaX
                    if pruebaY in DicCoordsVerd[str(pruebaX)]:
                        print("Entro a pruebaY in DicCoordsVerd[pruebaX]:")
                        resultadoY = pruebaY
                        print("Salio de pruebaY in DicCoordsVerd[pruebaX]:")
                        break
                    else:
                        for posibleY in DicCoordsVerd[str(pruebaX)]:
                            print("Entro a for posibleY in DicCoordsVerd[pruebaX]:")
                            if(abs(posibleY-pruebaY)<difActual):
                                difActual = abs(posibleY-pruebaY)
                                resultadoY = posibleY
                        print("Salio del ultimo else y del for")
                        break
                else:
                    pruebaX = pruebaX+1

        print(posX)
        print(posY)
        print("......")
        print(resultadoX)
        print(resultadoY)

        return render_template("boat/boat_distancia.html",imagen=imagen,formDis=formDis,coords=coords,north=north,south=south,west=west,east=east,height=height,width=width)

    return render_template("boat/boat_distancia.html",imagen=imagen,formDis=formDis,coords=coords,north=north,south=south,west=west,east=east,height=height,width=width)

@dashboard.route("/<username>/download-csv")
def download_csv(username):
    query = session["query"] or "select 1"
    operation = pd.read_sql_query(query, db.engine)
    return Response(
        operation.to_csv(sep=";"),
        mimetype="text/csv",
        headers={
            "Content-disposition": "attachment; filename=operation-{}.csv".format(
                username
            )
        },
    )


@dashboard.route("/vehicle_map", methods=["GET", "POST"])
@login_required
def show_vehicle_map():
    """
    page for showing all user vehicles in map
    :return:
    """
    stations_df = Trees.stations
    json_stations = Markup(stations_df.to_json(orient="records"))

    user_vehicles = Vehicle.query.filter(Vehicle.user == current_user).all()

    vehicle_list = []
    keys = ["latitude", "longitude", "elevation", "vehicle_id", "timestamp"]
    for vehicle in user_vehicles:
        last = (
            db.session.query(Operation)
            .filter(Operation.vehicle_id == vehicle.placa)
            .order_by(Operation.id.desc())
            .first()
        )

        if last:
            last = {k: v for k, v in last.asdict().items() if k in keys}
            last["name"] = last.get("vehicle_id")
            # Closest station
            _, st_id = Trees.station_tree.query(
                np.array([last["latitude"], last["longitude"]]).reshape(1, -1), k=1
            )
            last["closest_station"] = (
                stations_df["name"].reindex(index=st_id[0]).tolist()
            )
            vehicle_list.append(last)

    return render_template(
        "vehicle_map.html",
        json_stations=json_stations,
        json_operation=json.dumps(vehicle_list, default=str),
        vehicles=json.dumps([v.asdict() for v in user_vehicles]),
        users_list=users_list,
    )


# --------------------------------- IoT routes ---------------------------------------------------#


@dashboard.route("/addjson", methods=["POST", "GET"])
def add_entry():
    """
    communication route for handling incoming vehicle data
    """
    # If its coming in json format:
    if request.method == "POST":
        args = request.get_json()

    # If its coming by url
    else:
        args = request.args

    if not args:
        return "Null osm_data"
    else:
        
        operation = Operation(**args)
        operation.timestamp = datetime.strptime(
            (
                datetime.now(pytz.timezone("America/Bogota")).strftime(
                    "%Y-%m-%d %H:%M:%S"
                )
            ),
            "%Y-%m-%d %H:%M:%S",
        )

        last = (
            db.session.query(Operation)
            .filter(Operation.vehicle_id == args.get("vehicle_id"))
            .order_by(Operation.id.desc())
            .first()
        )

        coords_2 = (float(args.get("latitude")), float(args.get("longitude")))

        elevation_request = requests.get(
            url=elevation_endpoint
            + "/?lat="
            + args.get("latitude")
            + "&lng="
            + args.get("longitude")
        )
        if elevation_request.status_code == 200:
            operation.elevation = float(elevation_request.content.decode("utf-8"))
        else:
            operation.elevation = last.elevation

        if last:
            delta_t = (operation.timestamp - last.timestamp).total_seconds()
            coords_1 = (last.latitude, last.longitude)
            if not last.elevation or not operation.elevation:
                rise = 0
            else:
                rise = operation.elevation - last.elevation

        else:
            coords_1 = coords_2
            delta_t = 7
            rise = 0

        run = geopy.distance.distance(coords_1, coords_2).m  # meters
        operation.run = run
        print(operation.vehicle_id)
        vehicle = Vehicle.query.filter_by(placa=operation.vehicle_id).first()
        if not vehicle:
            return "Please create the vehicle first"
        try:
            vehicle.odometer = float(args.get("odometer", vehicle.odometer + run))
        except TypeError:
            vehicle.odometer = run

        vehicle.weight = float(args.get("mass"))
        if "bote" in operation.vehicle_id.lower():
            operation.mec_power, operation.net_force = consumption_models.zavitsky(
                (float(operation.mean_speed) / 3.6),
                float(operation.mean_acc),
                float(vehicle.weight),
            )

        slope = math.atan(rise / run) if run else 0
        degree = (slope * 180) / math.pi
        operation.slope = degree

        db.session.add(operation)
        db.session.commit()
        return "Data received"


@dashboard.route("/login", methods=["GET", "POST"]) 
def login():
    """
    login page
    :return:
    """
    if current_user.is_authenticated:
        session["graph_var_x"] = "timestamp"
        session["graph_var_y"] = "soc"
        return redirect(url_for("dashboard.show_vehicle_map"))
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user is None or not user.check_password(form.password.data):
            flash("Invalid username or password")
            return redirect(url_for("dashboard.login"))
        login_user(user, remember=form.remember_me.data)
        next_page = request.args.get("next")
        if not next_page or url_parse(next_page).netloc != "":
            next_page = url_for("dashboard.show_vehicle_map")
        session["graph_var_x"] = "timestamp"
        session["graph_var_y"] = "soc"
        return redirect(next_page)
    return render_template("login.html", title="Sign In", form=form)


@dashboard.route("/register", methods=["GET", "POST"])
def register():
    """
    register page
    :return:
    """
    if current_user.is_authenticated:
        return redirect(url_for("dashboard.show_vehicle_map"))
    form = RegistrationForm()
    if form.validate_on_submit():
        user = User(username=form.username.data, email=form.email.data)
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()
        flash("Congratulations, you are now a registered user!")
        return redirect(url_for("dashboard.login"))
    return render_template("register.html", title="Register", form=form)


@dashboard.route("/logout")
def logout():
    """
    logout page
    :return:
    """
    logout_user()
    return redirect(url_for("dashboard.show_entries"))


@dashboard.route("/map_var", methods=["POST"])
def map_var():
    """
    redirects when map form is submitted
    :return:
    """
    session["map_var"] = request.form["map_var"]
    for var in ["d1", "h1", "h2"]:
        session["form_" + var] = request.form[var]

    read_form_dates(session, day=1, hour=1)

    return redirect(url_for("dashboard.show_vehicle_map"))


@dashboard.route("/favicon.ico")
def favicon():
    """
    favicon
    """
    return send_from_directory(
        os.path.join(current_app.root_path, "static"), "monitor.ico"
    )
