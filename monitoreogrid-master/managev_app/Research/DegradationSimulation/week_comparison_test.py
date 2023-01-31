import mysql.connector
import pandas as pd
import matplotlib.pyplot as plt


cnx = mysql.connector.connect(
    user="admin",
    password="actuadores",
    host="104.236.94.94",
    database="monitoreodb",
)


query = (
    "select timestamp, capacity, soc from operation"
    " where vehicle_id='GVQ446' and date(timestamp) > '2021-06-09' "
    "and date(timestamp) < '2021-06-27' and soc > 10 and soc < 100"
)

data = pd.read_sql_query(query, cnx)


fig = plt.figure()
ax1 = fig.add_subplot(111)
colors = ["b", "r"]
labels = ["Simulated", "Real"]

sim = pd.read_csv("simulated_cycles.csv")
ax1.plot(
    sim.time,
    sim.cap,
    c=colors[0],
    label=labels[0],
)


date = data.timestamp.astype("int64") // 1e9
initial = date.iloc[0]
hours = (date - initial) / 3600

ax1.plot(
    hours,
    data.soc * 40 / 100,
    c=colors[1],
    label=labels[1],
)

plt.ylabel("Capacity (kW)")
plt.xlabel("Hours")
plt.legend(loc="upper left")
plt.show()
end = True
