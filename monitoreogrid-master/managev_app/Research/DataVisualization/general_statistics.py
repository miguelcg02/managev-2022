from datetime import datetime
from collections import defaultdict
from statistics import mean
import json
import matplotlib.pyplot as plt


from managev_app.Research.DataInteractor.data_fetcher import DataFetcher

fetcher = DataFetcher()

# Energy consumed per day per car
results = {}
users = ["sechava4", "usuarios_eafit_vehiculo_2"]
for user in users:
    cursor = fetcher.cnx.cursor()
    cursor.execute(
        f"select distinct(date(timestamp)) from operation where user_name = '{user}';"
    )
    dates = cursor.fetchall()
    dates_dict = {}
    for date in dates:
        date = datetime.strftime(date[0], "%Y-%m-%d")
        mycursor = fetcher.cnx.cursor()
        mycursor.execute(
            f"SELECT energy, energy_rec, drivetime "
            f"from operation where date(timestamp) = '{date}' and operation.user_name = '{user}';"
        )
        result = mycursor.fetchall()

        e_used = {}
        e_rec = {}
        drivetime = {}
        run_index = 0
        prev_energy_used = 0
        prev_energy_rec = 0
        prev_seconds = 0
        prev_prev_seconds = 0
        for index, row in enumerate(result):
            energy_used = row[0]
            energy_rec = row[1]
            seconds = row[2]
            e_used[run_index] = prev_energy_used
            e_rec[run_index] = prev_energy_rec
            drivetime[run_index] = prev_seconds

            # If a new route starts:
            if seconds == 0 and prev_seconds > 0 and prev_prev_seconds > 0:
                run_index += 1
            prev_energy_used = energy_used
            prev_energy_rec = energy_rec
            prev_prev_seconds = prev_seconds
            prev_seconds = seconds

        e_used.pop(run_index)
        e_rec.pop(run_index)
        drivetime.pop(run_index)
        e_used["total"] = sum(e_used.values())
        e_rec["total"] = sum(e_rec.values())
        drivetime["total"] = sum(drivetime.values()) / 60

        dates_dict[date] = {
            "energy_used": e_used,
            "energy_rec": e_rec,
            "drivetime": drivetime,
        }
    results[user] = dates_dict

with open("result.json", "w") as fp:
    json.dump(results, fp, indent=2)

totals = {}
for vehicle, dates in results.items():
    vehicle_data = defaultdict(list)
    for date, data in dates.items():
        metric_data = {}
        for metric_type, metric_data in data.items():
            vehicle_data[metric_type].append(metric_data["total"])
        vehicle_data["n_trips"].append(len(metric_data) - 1)
    totals[vehicle] = vehicle_data

for field in ["energy_used", "energy_rec", "drivetime", "n_trips"]:
    fig, ax = plt.subplots()
    ax.set_title(f"{field} diario por vehículo (kWh)")
    ax.boxplot(
        [
            totals[users[0]][field],
            totals[users[1]][field],
        ],
        showmeans=True,
    )
    plt.show()
    print(mean(totals[users[0]][field]))
    print(mean(totals[users[1]][field]))
