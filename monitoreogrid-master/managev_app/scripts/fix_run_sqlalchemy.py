import math

import geopy.distance
from managev_app import db
from managev_app.models import Operation

for vehicle in ["EGZ112", "GVQ446", "GHW284"]:
    if vehicle == "EGZ112":
        items = (
            Operation.query.filter(
                Operation.vehicle_id == vehicle, Operation.id > 158278
            )
            .order_by(Operation.id.asc())
            .all()
        )
    else:
        items = (
            Operation.query.filter(Operation.vehicle_id == vehicle)
            .order_by(Operation.id.asc())
            .all()
        )
    prev = items[0]
    for index, item in enumerate(items):
        rise = item.elevation - prev.elevation
        run = geopy.distance.distance(
            (prev.latitude, prev.longitude), (item.latitude, item.longitude)
        ).m

        item.run = math.sqrt(run ** 2 + rise ** 2)

        slope = math.atan(rise / run) if run else 0  # radians
        item.slope = (slope * 180) / math.pi
        prev = item
        if index % 1000 == 0:
            db.session.commit()
            print("commited", index)
    print("finished vehicle", vehicle)
