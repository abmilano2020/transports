import requests
import zipfile
import pandas as pd
import io
from flask import Flask, request, render_template_string
from datetime import datetime, timedelta

app = Flask(__name__)

# Load GTFS
url = "https://dati.toscana.it/dataset/8bb8f8fe-fe7d-41d0-90dc-49f2456180d1/resource/1f62d551-65f4-49f8-9a99-e19b02077be3/download/gest.gtfs"
response = requests.get(url)

with zipfile.ZipFile(io.BytesIO(response.content)) as z:
    stops_df = pd.read_csv(z.open('stops.txt'))
    stop_times_df = pd.read_csv(z.open('stop_times.txt'))
    trips_df = pd.read_csv(z.open('trips.txt'))
    routes_df = pd.read_csv(z.open('routes.txt'))

stop_names = sorted(stops_df['stop_name'].unique())

@app.route('/')
def index():
    return render_template_string("""
    <h1>Choose a Stop</h1>
    <form action="/choose" method="post">
        <select name="stop_name" required>
            {% for stop in stops %}
                <option value="{{ stop }}">{{ stop }}</option>
            {% endfor %}
        </select>
        <input type="submit" value="Choose">
    </form>
    """, stops=stop_names)

@app.route('/choose', methods=['POST'])
def choose():
    stop_name = request.form.get('stop_name', '')
    matched_stops = stops_df[stops_df['stop_name'].str.lower() == stop_name.lower()]
    if matched_stops.empty:
        return f"Stop not found: {stop_name}"

    stop_id = matched_stops.iloc[0]['stop_id']

    now = datetime.now()
    now_time = now.time()
    #TBD: let user choose delta minutes
    time_limit = (now + timedelta(minutes=5)).time()

    # Filter departures from this stop
    #Use .copy() when slicing a df and modifying it later.
    #it avoids warnings and ensures you're working on a clean, separate object.
    df = stop_times_df[stop_times_df['stop_id'] == stop_id].copy()
    df['departure_time'] = pd.to_datetime(df['departure_time'], format='%H:%M:%S', errors='coerce').dt.time
    df = df[df['departure_time'].between(now_time, time_limit)]

    if df.empty:
        return f"No upcoming departures from {stop_name} in the next 5 minutes."

    # Join with trips and routes to get headsign and line info
    df = df.merge(trips_df, on='trip_id', how='left')
    df = df.merge(routes_df, on='route_id', how='left')

    df = df.drop_duplicates(subset=['departure_time', 'route_short_name', 'trip_headsign'])
    df['route_short_name'] = df['route_short_name'].replace({'T1.3': 'T1'})

    # Create HTML output
    output = f"<h2>Upcoming departures from:<br>📍<strong>{stop_name}</strong><br>⌛in the next 5 minutes</h2><ul>"
    for row in df.sort_values(by='departure_time').itertuples(index=False):
        time_str = row.departure_time.strftime('%H:%M')
        emoji = '🟢' if row.route_short_name == 'T1' else '🔵' if row.route_short_name == 'T2' else '🚋'
        output += f"🕓 {time_str} {emoji} {row.route_short_name}➡️{row.trip_headsign}<br>"

    return output

if __name__ == "__main__":
    app.run(debug=True)