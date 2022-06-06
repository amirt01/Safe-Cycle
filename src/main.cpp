#include <SoftwareSerial.h>   // for the GPS
#include <TinyGPSPlus.h>      // for the GPS
#include <TFT_eSPI.h>         // for the screen
#include <SparkFunLSM6DSO.h>  // for the 6DoF Sensor
#include <Wire.h>             // for communicaiton
#include <SPI.h>              // for communicaiton
#include <HTTPClient.h>       // For HTTP requests
#include <WiFi.h>

#include "DataPackage.h"

// for controls
#define LEFT_BUTTON 0
#define RIGHT_BUTTON 35

// for GPS serial communication
#define RX_PIN 27
#define TX_PIN 26

// For Display
TFT_eSPI tft = TFT_eSPI(); 

// For GPS
int GPSBaud = 9600, SerialBaud = 9600;
TinyGPSPlus myGPS;
SoftwareSerial gpsSerial(RX_PIN, TX_PIN);

// For 6DoF Sensor
LSM6DSO myIMU;

// WiFi connection. Must get Httpclient.h and Wifi.h
char ssid[] = "UCInet Mobile Access";    // your network SSID (name) 
char pass[] = "";                       // your network password (use for WPA, or use as key for WEP)

const char* serverName = "54.67.110.37"; //need to update w/ every new AWS instance

// Data Management Vatriables
DataPackage data;
unsigned long serverSyncTime = 0;
unsigned long displayUpdateTime = 0;

// Status Varibales
enum Status { Standbye, Running, Sleep };
Status status, lastPrintedStatus;
bool call = false;  // flag variable to indicate if we are about to call

// Data Collection/Processing
void collectData();
bool checkForCollision();
void displayData();
void printData();
void sendData();
void recieveData();

/*  Interupts  */

// The right button will be responsible for starting/stoping a trip and also canceling
// an emergency call.
void RightButton() {
  switch (status) {
   case Running:
    if (call) {
      call = false;
    } else {
      status = Standbye;
    }
    break;
  
   case Standbye:
    status = Running;
    data = DataPackage();
    break;
  }
}

// The left button will be responsible for putting our device to sleep and waking it up again.
// This function will sleep our device if we are not currently on a trip.
void LeftButton() {
  if (status != Running) {
    Serial.println("Going to sleep");
    status = Sleep;
  }
}

void setup() {
  Serial.begin(SerialBaud);
  gpsSerial.begin(GPSBaud);
  delay(500);

  // LSM6DOS Setup
  Wire.begin();
  delay(10);
  if (myIMU.begin())
    Serial.println("Ready.");
  else
    Serial.println("Could not connect to LSM6DOS.");
  if (myIMU.initialize(BASIC_SETTINGS))
    Serial.println("Loaded Settings.");
  
  //WiFi Setup
  Serial.print("Connecting to ");
  Serial.println(ssid);
  WiFi.begin(ssid, pass);
  while (WiFi.status() != WL_CONNECTED) {
      delay(500);
      Serial.print(".");
  }

  // Pin Setup
  pinMode(LEFT_BUTTON, INPUT_PULLUP);
  pinMode(RIGHT_BUTTON, INPUT_PULLUP);
  
  attachInterrupt(digitalPinToInterrupt(RIGHT_BUTTON), RightButton, RISING);
  attachInterrupt(digitalPinToInterrupt(LEFT_BUTTON), LeftButton, RISING);

  esp_sleep_enable_ext0_wakeup(GPIO_NUM_0, LOW);

  delay(1000);  // wait for everything to be initialized

  // TTGO Display Setup
  tft.init();
  tft.setRotation(0);
  tft.setTextColor(TFT_WHITE,TFT_BLACK);
  tft.setTextSize(1);
  tft.fillScreen(TFT_LIGHTGREY);
  tft.setCursor(0, 0, 2);

  status = Standbye;  // start in standbye mode after wake
  lastPrintedStatus = status;
  Serial.println("Standbye");
  tft.println("Standbye");
}

void loop() {
  // Only print if the status changes
  if (status != lastPrintedStatus) {
    tft.fillScreen(TFT_LIGHTGREY);
    tft.setCursor(0, 0, 2);
    switch (status) {
    case Running: 
      Serial.println("Running");
      tft.println("Running");
      break;
    case Standbye:
      Serial.println("Standbye");
      tft.println("Standbye");
      break;
    case Sleep:
      Serial.println("Sleep");
      tft.println("Sleep");
      break;
    }
    lastPrintedStatus = status;
  }

  switch (status) {
  case Running:
    collectData();
    if (checkForCollision()) {
      for (int i = 10; i >= 0; i--) {  // wait 10 seconds before calling emergency servecies
        if (!call) break;
        tft.fillScreen(TFT_LIGHTGREY);
        tft.setCursor(0, 0, 2);
        tft.printf("Calling in %d\n", i);
        Serial.printf("Calling in %d\n", i);
        delay(1000);
      }
      if (call) {
        // TODO: Implement calling through phone App
        status = Standbye;
      }
    } else if (millis() > displayUpdateTime) {
      displayData();
      displayUpdateTime = millis() + 500;
    }
    break;

  case Standbye:
    break;

  case Sleep:
    sendData();
    delay(1000);
    esp_deep_sleep_start();
    break;
  }

  // Send the most recent data every 1 second
  if (millis() > serverSyncTime) {
    sendData();
    recieveData();
    serverSyncTime = millis() + 1000;
  }
}

// Display the most recent data to the TTGO Display
void displayData() {
  tft.fillScreen(TFT_LIGHTGREY);
  tft.setCursor(0, 0, 2);
  tft.print("Longitude: ");
  tft.println(data.longitude);
  tft.print("Latitude: ");
  tft.println(data.latitude);
  tft.print("Course: ");
  tft.println(data.course);
  tft.print("Speed: ");
  tft.println(data.speed);

  tft.print("Date: ");
  tft.print(data.month);
  tft.print("/");
  tft.print(data.day);
  tft.print("/");
  tft.println(data.year);

  tft.print("Time: ");
  if (data.hour < 10) tft.print(F("0"));
  tft.print(data.hour);
  tft.print(":");
  if (data.minute < 10) tft.print(F("0"));
  tft.print(data.minute);
  tft.print(":");
  if (data.second < 10) tft.print(F("0"));
  tft.print(data.second);
  tft.print(".");
  if (data.centisecond < 10) tft.print(F("0"));
  tft.println(data.centisecond);

  tft.println("Accelerometer: ");
  tft.print("(");
  tft.print(data.xAccel, 2);
  tft.print(", ");
  tft.print(data.yAccel, 2);
  tft.print(", ");
  tft.print(data.zAccel, 2);
  tft.println(")");

  tft.println("Gyroscope: ");
  tft.print("(");
  tft.print(data.xGyro, 2);
  tft.print(", ");
  tft.print(data.yGyro, 2);
  tft.print(", ");
  tft.print(data.zGyro, 2);
  tft.println(")");

  tft.print("Temperature: ");
  tft.print(data.temperatureF, 2);
  tft.println("F");
}

// If our user experiences an extreme acceleration, return true
bool checkForCollision() {
  if (data.xAccel > 3 || data.yAccel > 3 || data.zAccel > 3) {
    call = true;
    return true;
  } else {
    return false;
  }
}

// Update all the data from both sensors
void collectData() {
  // only update values if data is recieved from the GPS
  if (gpsSerial.available() && myGPS.encode(gpsSerial.read())) {
    // Location
    data.latitude = myGPS.location.lat();
    data.longitude = myGPS.location.lng();
    data.altitude = myGPS.altitude.meters();

    // Date
    data.year = myGPS.date.year();
    data.month = myGPS.date.month();
    data.day = myGPS.date.day();

    data.year = 22;
    data.month = 3;
    data.day = 6;

    // Time
    data.hour = myGPS.time.hour();
    data.minute = myGPS.time.minute();
    data.second = myGPS.time.second();
    data.centisecond = myGPS.time.centisecond();
  }

  // Accelerometer
  data.xAccel = myIMU.readFloatAccelX();
  data.yAccel = myIMU.readFloatAccelY();
  data.zAccel = myIMU.readFloatAccelZ();

  // Gyroscope
  data.xGyro = myIMU.readFloatGyroX();
  data.yGyro = myIMU.readFloatGyroY();
  data.zGyro = myIMU.readFloatGyroZ();

  // Temperature
  data.temperatureF = myIMU.readTempF();
  data.temperatureC = myIMU.readTempC();
}

// Print the most recent data to the Serial monitor
void printData() {
    Serial.print("Latitude: "); Serial.println(data.latitude, 6);
    Serial.print("Longitude: "); Serial.println(data.longitude, 6);
    Serial.print("Altitude: "); Serial.println(data.altitude);
    
    Serial.print("Date: ");
    Serial.print(data.month);
    Serial.print("/");
    Serial.print(data.day);
    Serial.print("/");
    Serial.println(data.year);

    Serial.print("Time: ");
    if (data.hour < 10) Serial.print(F("0"));
    Serial.print(data.hour);
    Serial.print(":");
    if (data.minute < 10) Serial.print(F("0"));
    Serial.print(data.minute);
    Serial.print(":");
    if (data.second < 10) Serial.print(F("0"));
    Serial.print(data.second);
    Serial.print(".");
    if (data.centisecond < 10) Serial.print(F("0"));
    Serial.println(data.centisecond);

    Serial.print("Accelerometer: ");
    Serial.print("(");
    Serial.print(data.xAccel, 3);
    Serial.print(", ");
    Serial.print(data.yAccel, 3);
    Serial.print(", ");
    Serial.print(data.zAccel, 3);
    Serial.println(")");

    Serial.print("Gyroscope: ");
    Serial.print("(");
    Serial.print(data.xGyro, 3);
    Serial.print(", ");
    Serial.print(data.yGyro, 3);
    Serial.print(", ");
    Serial.print(data.zGyro, 3);
    Serial.println(")");

    Serial.print("Temperature: ");
    Serial.print(data.temperatureF, 3);
    Serial.println("F");
}

// Send the most recent data to the server using HTTP
void sendData() {
  char dataJSON[512];
  snprintf(dataJSON, 512,
"{\"latitude\" : \"%f\",\
\"longitude\" : \"%f\",\
\"altitude\" : \"%f\",\
\"speed\" : \"%f\",\
\"course\" : \"%f\",\
\"year\" : \"%d\",\
\"month\" : \"%d\",\
\"day\" : \"%d\",\
\"hour\" : \"%d\",\
\"minute\" : \"%d\",\
\"second\" : \"%d\",\
\"centisecond\" : \"%d\",\
\"xAccel\" : \"%f\",\
\"yAccel\" : \"%f\",\
\"zAccel\" : \"%f\",\
\"xGyro\" : \"%f\",\
\"yGyro\" : \"%f\",\
\"zGyro\" : \"%f\",\
\"temperatureC\" : \"%f\",\
\"temperatureF\" : \"%f\",\
\"state\" : \"%d\"}",
  data.latitude, data.longitude, data.altitude, data.speed, data.course,
  data.year, data.month, data.day, data.hour, data.minute, data.second, data.centisecond,
  data.xAccel, data.yAccel, data.zAccel, data.xGyro, data.yGyro, data.zGyro,
  data.temperatureC, data.temperatureF, status);
  // Serial.println(dataJSON);
  // Serial.println();
  // Serial.println();

  if (WiFi.status()== WL_CONNECTED) {
      HTTPClient http;
    
      // Your Domain name with URL path or IP address with path
      http.begin("http://3.101.59.180:5000/json-post");  // TODO: make the url form variables
      http.addHeader("Content-Type", "application/json");
      // int httpResponseCode = http.POST("{\"api_key\":\"tPmAT5Ab3j7F9\",\"sensor\":\"BME280\",\"value1\":\"24.25\",\"value2\":\"49.54\",\"value3\":\"1005.14\"}");
      int httpResponseCode = http.POST(dataJSON);
      Serial.print("Got status code: ");
      Serial.println(httpResponseCode);

      http.end();
    }
}

//was using this as reference https://randomnerdtutorials.com/esp32-http-get-post-arduino/
// #include <Arduino_JSON.h>
//might need string library?
void recieveData() {
  // if(WiFi.status()== WL_CONNECTED) {
  //     HTTPClient http;
  //     http.begin("http://3.101.59.180:5000/json-get");

  //     int httpResponseCode = http.GET();

  //     String payload = "{}"; 

  // if (httpResponseCode>0) {
  //   Serial.print("HTTP Response code: ");
  //   Serial.println(httpResponseCode);
  //   String sensorReadings = http.getString();
  // }
  // else {
  //   Serial.print("Error code: ");
  //   Serial.println(httpResponseCode);
  // }
  
  // JSONVar myObject = JSON.parse(sensorReadings);

  // // JSON.typeof(jsonVar) can be used to get the type of the var
  // if (JSON.typeof(myObject) == "undefined") {
  //   Serial.println("Parsing input failed!");
  //   return;
  // }

  // Serial.print("JSON object = ");
  // Serial.println(myObject);

  // int status_reading;
  // //   // myObject.keys() can be used to get an array of all the keys in the object
  // JSONVar keys = myObject.keys();

  // JSONVar value = myObject[keys[0]];
  // Serial.print(keys[0]);
  // Serial.print(" = ");
  // Serial.println(value);
  // status_reading = int(value);
  
  // return status_reading;
  // }
}