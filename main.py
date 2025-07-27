import requests
import zipfile
import pandas as pd
import io
from flask import Flask, request, render_template_string, jsonify

app = Flask(__name__)

# Load GTFS
url = "https://dati.toscana.it/dataset/8bb8f8fe-fe7d-41d0-90dc-49f2456180d1/resource/1f62d551-65f4-49f8-9a99-e19b02077be3/download/gest.gtfs"
response = requests.get(url)

with zipfile.ZipFile(io.BytesIO(response.content)) as z:
    stops_df = pd.read_csv(z.open('stops.txt'))

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
    return f"You chose this stop: {stop_name}"

if __name__ == "__main__":
    app.run(debug=True)