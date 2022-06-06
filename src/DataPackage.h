#ifndef DATAPACKAGE_H
#define DATAPACKAGE_H

#include <stdint.h>
#include <string.h>
#include <stdio.h>

struct DataPackage {
    double latitude = 0;      // degrees
    double longitude = 0;   // degrees
    double altitude = 0;              // feet
    double speed = 0;                 // miles per hour
    double course = 0;                // degrees
    uint8_t year = 0;                 // Year (2000+)
    uint8_t month = 0;                // (1-12)
    uint8_t day = 0;                  // (1-31)
    uint8_t hour = 0;                 // (0-23)
    uint8_t minute = 0;               // (0-59)
    uint8_t second = 0;               // (0-59)
    uint8_t centisecond = 0;          // (0-99)
    float xAccel = 0;                 // g (earth gravity)
    float yAccel = 0;                 // g (earth gravity)
    float zAccel = 0;                 // g (earth gravity)
    float xGyro = 0;                  // degrees/seconds
    float yGyro = 0;                  // degrees/seconds
    float zGyro = 0;                  // degrees/seconds
    float temperatureC = 0;           // Celcius
    float temperatureF = 0;           // Fahrenheit
};

#endif