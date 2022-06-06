# import main Flask class and request object
from flask import Flask, request, jsonify, render_template, send_file
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.backends.backend_agg import FigureCanvasAgg as FigureCanvas
from matplotlib.figure import Figure
from datetime import datetime, timedelta
import math
from timeit import default_timer as timer

# create the Flask app
app = Flask(__name__)

userID = None
id = None
title = None
body = None

date_format='%m/%d/%Y %H:%M:%S %Z'

#gps_locations = [(33.645993, -117.842768), (33.644632, -117.842432), (33.642444, -117.841904)]
gps_locations = []
altitude = 0.0
speeds = [0]
course = 0
start_time = "-"
time_elapsed = 0
start = timer()
accel = []
gyro = []
temperature = 0.0
state = "stopped"

#just uci campus
min_lat = 33.6499
max_lat = 33.6414
min_long = -117.8493
max_long = -117.8359

BBox = [min_long, max_long, max_lat, min_lat]

test_gps_points_long = [-117.842768, -117.842432, -117.841904]

test_gps_points_lat = [33.645993, 33.644632, 33.642444]


app = Flask(__name__)

def haversine(coord1, coord2):
    R = 6372800  # Earth radius in meters
    lat1, lon1 = coord1
    lat2, lon2 = coord2
    
    phi1, phi2 = math.radians(lat1), math.radians(lat2) 
    dphi       = math.radians(lat2 - lat1)
    dlambda    = math.radians(lon2 - lon1)
    
    a = math.sin(dphi/2)**2 + \
        math.cos(phi1)*math.cos(phi2)*math.sin(dlambda/2)**2
    
    return 2*R*math.atan2(math.sqrt(a), math.sqrt(1 - a))

def calculate_distance():
    distance_traveled = 0.0
    for item in range(len(gps_locations)-1):
        distance_traveled += haversine(gps_locations[item], gps_locations[item+1])
    return distance_traveled *0.000621371192 #to get miles

def convert(seconds):
    min, sec = divmod(seconds, 60)
    hour, min = divmod(min, 60)
    return "%d:%02d:%02d" % (hour, min, sec)

@app.route('/print-plot')
def plot_png():
    plt.rcParams["figure.figsize"] = [7.50, 3.50]
    plt.rcParams["figure.autolayout"] = True
    fig = Figure()

    axis = fig.add_subplot(1, 1, 1)
    xs = list(range(0, len(speeds)))
    axis.set_xlabel("Time Elapsed")
    axis.set_ylabel("Speed")
    axis.set_title("Speed Over Time")

    axis.scatter(xs, speeds)

    fig.savefig('temp_speedplot.png', transparent=True)

    return send_file("temp_speedplot.png", mimetype='image/png')

@app.route('/gps-plot')
def plot_gps():
    fig = Figure()
    axis = fig.add_subplot(1, 1, 1)

    axis.set_title("GPS Data on UCI Campus")

    uci_map = plt.imread('static/map.png')

    axis.set_xlim(BBox[0],BBox[1]) #minlong, maxlong
    axis.set_ylim(BBox[2],BBox[3]) #minlat, maxlat
    
    x_ticks = map(lambda x: round(x, 4), np.linspace(BBox[0],BBox[1], num=7))
    y_ticks = map(lambda x: round(x, 4), np.linspace(BBox[2],BBox[3], num=8))

    lat = [item[0] for item in gps_locations]
    long = [item[1] for item in gps_locations]

    axis.scatter(long, lat, zorder=1, c='r', s=10)
    #MAYBE GRAPH AS TUPLES

    axis.set_xticklabels(x_ticks)
    axis.set_yticklabels(y_ticks)

    axis.set_xlabel('Longitude')
    axis.set_ylabel('Latitude')

    axis.imshow(uci_map, zorder=0, extent = BBox, aspect= 'equal')

    fig.savefig('temp_gps.png', transparent=True)

    return send_file("temp_gps.png", mimetype='image/png')

@app.route('/json-post', methods=['POST'])
def json_example():
    request_data = request.get_json(force=True)

    print(request_data)

    global gps_locations, altitude, speeds, course, start_time, start, time_elapsed, accel, gyro, temperature, state

    if start_time == "-": # or if request_data["status"] == "restart"
        start_time = request_data["month"] + "/" + request_data["day"] + "/" + request_data["year"] + " " + request_data["hour"] + ":" + request_data["minute"] + ":" + request_data["second"]
        start = timer()
        speeds = []
        state = "running"
        gps_locations = []
    else:
        end = timer()
        time_elapsed = end - start
    
    gps_locations.append((float(request_data["latitude"]), float(request_data["longitude"])))
    altitude = request_data["altitude"]
    speeds.append(float(request_data["speed"]))
    course = request_data["course"]
    accel.append((request_data["xAccel"], request_data["yAccel"], request_data["zAccel"]))
    gyro.append((request_data["xGyro"], request_data["yGyro"], request_data["zGyro"]))
    temperature = request_data["temperatureF"]

    return '''
        The json looks like {}
        '''.format(request_data)

@app.route('/json-get', methods=['GET'])
def json_return():
    data = {
        "click" : state
    }
    return jsonify(data)

@app.route('/', methods=['GET', 'POST'])
def home_page():
    global state

    if "start" in request.form:
        state = "running"
    elif "pause" in request.form:
        state = "paused"
    elif "end" in request.form:
        state = "stopped"

    return render_template('home_page.html', st = state, distance = calculate_distance(), alt = int(altitude), avg = sum(speeds)/len(speeds), max = max(speeds), date = start_time, current_time = convert(time_elapsed), temp = "{:.2f}".format(float(temperature)))

if __name__ == '__main__':
    # run app in debug mode on port 5000
    app.run(debug=True, port=5000)


#TODO
#update running / paused/ stopped based on ESP32 POSTS?
    #maybe if there hasnt been anything added to speeds > 2 seconds, pause activity.

#if ended, then display total time, ending stats, etc.

#need restart sequence