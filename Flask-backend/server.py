# import main Flask class and request object
from flask import Flask, request, jsonify, render_template, send_file
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.backends.backend_agg import FigureCanvasAgg as FigureCanvas
from matplotlib.figure import Figure
from datetime import datetime, timedelta
import math
from timeit import default_timer as timer
import pytz

# create the Flask app
app = Flask(__name__)

date_format='%m/%d/%Y %H:%M:%S %Z'
# "latitude" : "33.645993", "longitude" : "-117.842768",
# "latitude" : "33.644632", "longitude" : "-117.842432",
# "latitude" : "33.642444", "longitude" : "-117.841904",

#Global variables to be updated by JSON posts.
gps_locations = []
altitude = 0.0
speeds = [0]
course = 0
start_time = "-"
time_elapsed = 0
start = timer()
accel = [0]
gyro = []
temperature = 0.0

send_state = 0
esp32_state = 0

#Boundaries of UCI campus map for GPS plot
min_lat = 33.6499
max_lat = 33.6414
min_long = -117.8493
max_long = -117.8359

BBox = [min_long, max_long, max_lat, min_lat]

#Calculates the distance between two lat/lon coordinates.
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

#Compiles distances between coordinates given the global list storing the coordinates.
def calculate_distance():
    distance_traveled = 0.0
    for item in range(len(gps_locations)-1):
        distance_traveled += haversine(gps_locations[item], gps_locations[item+1])
    return distance_traveled *0.000621371192 #to get miles

#Turn seconds into hours, minutes, seconds.
def convert(seconds):
    min, sec = divmod(seconds, 60)
    hour, min = divmod(min, 60)
    return "%d:%02d:%02d" % (hour, min, sec)

#Plot the current speed over time.
@app.route('/print-plot')
def plot_png():
    # plt.rcParams["figure.figsize"] = [7.0, 3.0]
    # plt.rcParams["figure.autolayout"] = True
    fig = Figure()

    axis = fig.add_subplot(1, 1, 1)
    xs = list(range(0, len(speeds)))
    axis.set_xlabel("Time Elapsed")
    axis.set_ylabel("Speed")
    axis.set_title("Speed Over Time")

    axis.scatter(xs, speeds)

    fig.savefig('temp_speedplot.png', transparent=True)

    return send_file("temp_speedplot.png", mimetype='image/png')

@app.route('/print-acc')
def plot_acc():

    fig = Figure()

    axis = fig.add_subplot(1, 1, 1)
    xs = list(range(0, len(accel)))
    axis.set_xlabel("Time Elapsed")
    axis.set_ylabel("Max Acceleration")
    axis.set_title("Max Acceleration Over Time")

    axis.scatter(xs, accel)

    fig.savefig('temp_accplot.png', transparent=True)

    return send_file("temp_accplot.png", mimetype='image/png')

#Plot GPS points on map of UCI campus.
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

    if len(gps_locations) <= 1:
        lat = [item[0] for item in gps_locations]
        long = [item[1] for item in gps_locations]
        axis.scatter(long, lat, zorder=1, c='r', s=10)
    else:
        lat = [item[0] for item in gps_locations[:-1]]
        long = [item[1] for item in gps_locations[:-1]]
        axis.scatter(long, lat, zorder=1, c='r', s=10)
        # print(gps_locations[-1])
        lat = [gps_locations[-1][0]]
        long = [gps_locations[-1][1]]
        axis.scatter(long, lat, zorder=1, c='purple', s=10)

    axis.set_xticklabels(x_ticks)
    axis.set_yticklabels(y_ticks)

    axis.set_xlabel('Longitude')
    axis.set_ylabel('Latitude')

    axis.imshow(uci_map, zorder=0, extent = BBox, aspect= 'equal')

    fig.savefig('temp_gps.png', transparent=True)

    return send_file("temp_gps.png", mimetype='image/png')

#Retrieve data from ESP32 and its sensors and fill global variables.
@app.route('/json-post', methods=['POST'])
def json_example():
    request_data = request.get_json(force=True)
    print(request_data)
    #print(request_data)

    global gps_locations, altitude, speeds, course, start_time, start, time_elapsed, accel, gyro, temperature, esp32_state

    #If we're currently on standby, and esp32 starts running, reset saved values
    if (esp32_state == 0 and request_data["state"] == "1"): 
        # start_time = request_data["month"] + "/" + request_data["day"] + "/" + request_data["year"] + " " + request_data["hour"] + ":" + request_data["minute"] + ":" + request_data["second"]
        pst = pytz.timezone('America/Los_Angeles')

        start_time = datetime.now(pst)
        # print("start time looks like {start_time}")
        start = timer()
        speeds = [0]
        gps_locations = []
        accel = [0]
        
        esp32_state = 1
        # print("esp32 state should now be 1")

        gps_locations.append((float(request_data["latitude"]), float(request_data["longitude"])))
        altitude = request_data["altitude"]
        speeds.append(float(request_data["speed"]))
        course = request_data["course"]
        accel.append(max([request_data["xAccel"], request_data["yAccel"], request_data["zAccel"]]))
        gyro.append((request_data["xGyro"], request_data["yGyro"], request_data["zGyro"]))
        temperature = request_data["temperatureF"]

    #If esp32 goes to standby, go to standby
    elif request_data["state"] == 0:
        esp32_state = 0

    #if esp32 goes to sleep, we go to sleep
    elif request_data["state"] == 2:
        esp32_state = 2
        end = timer()
        time_elapsed = end - start

    else:
        gps_locations.append((float(request_data["latitude"]), float(request_data["longitude"])))
        altitude = request_data["altitude"]
        speeds.append(float(request_data["speed"]))
        course = request_data["course"]
        # accel.append(max([request_data["xAccel"], request_data["yAccel"], request_data["zAccel"]]))
        accel.append(max([request_data["xAccel"], request_data["yAccel"]]))

        gyro.append((request_data["xGyro"], request_data["yGyro"], request_data["zGyro"]))
        temperature = request_data["temperatureF"]
        
        end = timer()
        time_elapsed = end - start

    return '''
        The json looks like {}
        '''.format(request_data)

@app.route('/json-get', methods=['GET'])
def json_return():
    data = {
        "click" : send_state
    }
    return jsonify(data)

@app.route('/', methods=['GET', 'POST'])
def home_page():
    global send_state, start_time, esp32_state

    if "start" in request.form:
        #if starting from standby, then we need to keep esp32_state at 0
        if esp32_state == 0: 
            send_state = 1
        
        #if currently sleeping, then we need to let esp32 know to wake up, but keep previous data
        elif esp32_state == 2:
            send_state = 1
            esp32_state = 1

    elif "pause" in request.form:
        esp32_state = 2 
        send_state = 2

    elif "end" in request.form:
        esp32_state = 0
        send_state = 0

    # if state == "stopped":
    #     return render_template('finished_event.html', st = state, distance = calculate_distance(), alt = int(altitude), avg = sum(speeds)/len(speeds), max = max(speeds), date = start_time, current_time = convert(time_elapsed), temp = "{:.2f}".format(float(temperature)))
    # else:
    if (esp32_state == 0):
        display_state = "on standby"
    
    elif (esp32_state == 1):
        display_state = "running"
    
    elif esp32_state == 2:
        display_state = "sleeping"

    return render_template('home_page.html', st = display_state, distance = calculate_distance(), alt = altitude, avg = sum(speeds)/len(speeds), max = max(speeds), date = start_time, current_time = convert(time_elapsed), temp = "{:.2f}".format(float(temperature)))

if __name__ == '__main__':
    # run app in debug mode on port 5000
    app.run(debug=True, port=5000)


#TODO

#if ended, then display total time, ending stats, etc.

#start stop sleep. reset after stop

#standby - 0 - default, waiting for new trip
#running - 1 - running
#sleep - 2 - paused