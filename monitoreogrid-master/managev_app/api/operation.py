from flask import jsonify, request

from managev_app.api import bp
from managev_app.models import Operation


@bp.route("/returndata")
def returndata():
    placa = request.args.get("placa")
    num = int(request.args.get("num"))
    query = (
        Operation.query.filter(Operation.vehicle_id == placa)
        .order_by(Operation.id.desc())
        .limit(num)
        .all()
    )
    dicts = {}
    for i in range(0, num):
        dicts[i] = query[i].asdict()
    return jsonify(dicts)
