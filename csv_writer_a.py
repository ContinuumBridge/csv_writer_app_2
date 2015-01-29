#!/usr/bin/env python
# csv_writer_a.py
# Copyright (C) ContinuumBridge Limited, 2014 - All Rights Reserved
# Written by Peter Claydon
#
ModuleName = "csv_writer_2" 

import sys
import os.path
import time
import logging
from cbcommslib import CbApp
from cbconfig import *

FILENAME = CB_CONFIG_DIR + "csv_writer_2.csv"

config = {
    "temperature": "True",
    "temp_min_change": 0.2,
    "irtemperature": "True",
    "irtemp_min_change": 0.5,
    "humidity": "True",
    "humidity_min_change": 0.2,
    "buttons": "True",
    "accel": "False",
    "accel_min_change": 0.02,
    "accel_polling_interval": 3.0,
    "gyro": "False",
    "gyro_min_change": 0.5,
    "gyro_polling_interval": 3.0,
    "magnet": "True",
    "magnet_min_change": 1.5,
    "magnet_polling_interval": 3.0,
    "binary": "True",
    "luminance": "True",
    "luminance_min_change": 1.0,
    "slow_polling_interval": 300
}

class DataManager:
    """ Managers data storage for all sensors """
    def __init__(self, sendMessage):
        self.sendMessage = sendMessage
        self.now = self.niceTime(time.time())
        self.cvsList = []
        self.cvsLine = []
        self.index = []

    def niceTime(self, timeStamp):
        localtime = time.localtime(timeStamp)
        milliseconds = '%03d' % int((timeStamp - int(timeStamp)) * 1000)
        now = time.strftime('%Y:%m:%d,  %H:%M:%S:', localtime) + milliseconds
        return now

    def writeCVS(self, timeStamp):
        self.then = self.now
        self.now = self.niceTime(timeStamp)
        if self.now != self.then:
            self.f.write(self.then + ",")
            for i in range(len(self.cvsLine)):
                self.f.write(self.cvsLine[i] + ",")
                self.cvsLine[i] = ""
            self.f.write("\n")

    def initFile(self, idToName):
        self.idToName = idToName
        for i in self.idToName:
            self.index.append(self.idToName[i])
        services = ["temperature", 
                    "ir_temperature", 
                    "accel x", "accel y", "accel z",
                    "buttons l", "buttons r",
                    "rel humidily",
                    "gyro x", "gyro y", "gyro z"]
        self.numberServices = len(services)
        for i in self.idToName:
            for s in services:
                self.cvsList.append(s)
                self.cvsLine.append("")
        if os.path.isfile(FILENAME):
            self.f = open(FILENAME, "a+", 0)
        else:
            self.f = open(FILENAME, "a+", 0)
            for d in self.idToName:
                self.f.write(d + ", " + self.idToName[d] + "\n")
            self.f.write("date, time, ")
            for i in self.cvsList:
                self.f.write(i + ", ")
            self.f.write("\n")

    def storeAccel(self, deviceID, timeStamp, a):
        self.writeCVS(timeStamp)
        index = self.index.index(deviceID)
        for i in range(3):
            self.cvsLine[index*self.numberServices + 2 + i] = str("%2.3f" %a[i])

    def storeTemp(self, deviceID, timeStamp, temp):
        self.writeCVS(timeStamp)
        index = self.index.index(deviceID)
        self.cvsLine[index*self.numberServices + 0] = str("%2.1f" %temp)

    def storeIrTemp(self, deviceID, timeStamp, temp):
        self.writeCVS(timeStamp)
        index = self.index.index(deviceID)
        self.cvsLine[index*self.numberServices + 1] = str("%2.1f" %temp)

    def storeHumidity(self, deviceID, timeStamp, h):
        self.writeCVS(timeStamp)
        index = self.index.index(deviceID)
        self.cvsLine[index*self.numberServices + 7] = str("%2.1f" %h)

    def storeButtons(self, deviceID, timeStamp, buttons):
        self.writeCVS(timeStamp)
        index = self.index.index(deviceID)
        self.cvsLine[index*self.numberServices + 5] = str(buttons["leftButton"])
        self.cvsLine[index*self.numberServices + 6] = str(buttons["rightButton"])

    def storeGyro(self, deviceID, timeStamp, gyro):
        pass

    def storeMagnet(self, deviceID, timeStamp, magnet):
        self.writeCVS(timeStamp)
        index = self.index.index(deviceID)
        for i in range(3):
            self.cvsLine[index*self.numberServices + 8 + i] = str("%2.3f" %magnet[i])

    def storeBinary(self, deviceID, timeStamp, b):
        pass

    def storeLuminance(self, deviceID, timeStamp, v):
        pass

class Accelerometer:
    def __init__(self, id):
        self.previous = [0.0, 0.0, 0.0]
        self.id = id

    def processAccel(self, resp):
        accel = [resp["data"]["x"], resp["data"]["y"], resp["data"]["z"]]
        timeStamp = resp["timeStamp"]
        event = False
        for a in range(3):
            if abs(accel[a] - self.previous[a]) > config["accel_min_change"]:
                event = True
                break
        if event:
            self.dm.storeAccel(self.id, timeStamp, accel)
            self.previous = accel

class TemperatureMeasure():
    """ Either send temp every minute or when it changes. """
    def __init__(self, id):
        # self.mode is either regular or on_change
        self.mode = "on_change"
        self.minChange = 0.2
        self.id = id
        epochTime = time.time()
        self.prevEpochMin = int(epochTime - epochTime%60)
        self.currentTemp = 0.0

    def processTemp (self, resp):
        timeStamp = resp["timeStamp"] 
        temp = resp["data"]
        if self.mode == "regular":
            epochMin = int(timeStamp - timeStamp%60)
            if epochMin != self.prevEpochMin:
                temp = resp["data"]
                self.dm.storeTemp(self.id, self.prevEpochMin, temp) 
                self.prevEpochMin = epochMin
        else:
            if abs(temp-self.currentTemp) >= config["temp_min_change"]:
                self.dm.storeTemp(self.id, timeStamp, temp) 
                self.currentTemp = temp

class IrTemperatureMeasure():
    """ Either send temp every minute or when it changes. """
    def __init__(self, id):
        # self.mode is either regular or on_change
        self.mode = "on_change"
        self.minChange = 0.2
        self.id = id
        epochTime = time.time()
        self.prevEpochMin = int(epochTime - epochTime%60)
        self.currentTemp = 0.0

    def processIrTemp (self, resp):
        timeStamp = resp["timeStamp"] 
        temp = resp["data"]
        if self.mode == "regular":
            epochMin = int(timeStamp - timeStamp%60)
            if epochMin != self.prevEpochMin:
                temp = resp["data"]
                self.dm.storeTemp(self.id, self.prevEpochMin, temp) 
                self.prevEpochMin = epochMin
        else:
            if abs(temp-self.currentTemp) >= config["irtemp_min_change"]:
                self.dm.storeIrTemp(self.id, timeStamp, temp) 
                self.currentTemp = temp

class Buttons():
    def __init__(self, id):
        self.id = id

    def processButtons(self, resp):
        timeStamp = resp["timeStamp"] 
        buttons = resp["data"]
        self.dm.storeButtons(self.id, timeStamp, buttons)

class Gyro():
    def __init__(self, id):
        self.id = id
        self.previous = [0.0, 0.0, 0.0]

    def processGyro(self, resp):
        gyro = [resp["data"]["x"], resp["data"]["y"], resp["data"]["z"]]
        timeStamp = resp["timeStamp"] 
        event = False
        for a in range(3):
            if abs(gyro[a] - self.previous[a]) > config["gyro_min_change"]:
                event = True
                break
        if event:
            self.dm.storeGyro(self.id, timeStamp, gyro)
            self.previous = gyro

class Magnet():
    def __init__(self, id):
        self.id = id
        self.previous = [0.0, 0.0, 0.0]

    def processMagnet(self, resp):
        mag = [resp["data"]["x"], resp["data"]["y"], resp["data"]["z"]]
        timeStamp = resp["timeStamp"] 
        event = False
        for a in range(3):
            if abs(mag[a] - self.previous[a]) > config["magnet_min_change"]:
                event = True
                break
        if event:
            self.dm.storeMagnet(self.id, timeStamp, mag)
            self.previous = mag

class Humid():
    """ Either send temp every minute or when it changes. """
    def __init__(self, id):
        self.id = id
        self.previous = 0.0

    def processHumidity (self, resp):
        h = resp["data"]
        timeStamp = resp["timeStamp"] 
        if abs(h-self.previous) >= config["humidity_min_change"]:
            self.dm.storeHumidity(self.id, timeStamp, h) 
            self.previous = h

class Binary():
    def __init__(self, id):
        self.id = id
        self.previous = 0

    def processBinary(self, resp):
        timeStamp = resp["timeStamp"] 
        b = resp["data"]
        if b == "on":
            bi = 1
        else:
            bi = 0
        if bi != self.previous:
            self.dm.storeBinary(self.id, timeStamp-1.0, self.previous)
            self.dm.storeBinary(self.id, timeStamp, bi)
            self.previous = bi

class Luminance():
    def __init__(self, id):
        self.id = id
        self.previous = 0

    def processLuminance(self, resp):
        v = resp["data"]
        timeStamp = resp["timeStamp"] 
        if abs(v-self.previous) >= config["luminance_min_change"]:
            self.dm.storeLuminance(self.id, timeStamp, v) 
            self.previous = v

class App(CbApp):
    def __init__(self, argv):
        logging.basicConfig(filename=CB_LOGFILE,level=CB_LOGGING_LEVEL,format='%(asctime)s %(message)s')
        self.appClass = "monitor"
        self.state = "stopped"
        self.status = "ok"
        configFile = CB_CONFIG_DIR + "csv_writer.config"
        global config
        try:
            with open(configFile, 'r') as configFile:
                newConfig = json.load(configFile)
                logging.info('%s Read eew_app.config', ModuleName)
                config.update(newConfig)
        except:
            logging.warning('%s eew_app.config does not exist or file is corrupt', ModuleName)
        for c in config:
            if c.lower in ("true", "t", "1"):
                config[c] = True
            elif c.lower in ("false", "f", "0"):
                config[c] = False
        logging.debug('%s Config: %s', ModuleName, config)
        self.accel = []
        self.gyro = []
        self.magnet = []
        self.temp = []
        self.irTemp = []
        self.buttons = []
        self.humidity = []
        self.binary = []
        self.luminance = []
        self.power = []
        self.devices = []
        self.devServices = [] 
        self.idToName = {} 
        #CbApp.__init__ MUST be called
        CbApp.__init__(self, argv)

    def setState(self, action):
        if action == "clear_error":
            self.state = "running"
        else:
            self.state = action
        logging.debug("%s state: %s", ModuleName, self.state)
        msg = {"id": self.id,
               "status": "state",
               "state": self.state}
        self.sendManagerMessage(msg)

    def onConcMessage(self, resp):
        #logging.debug("%s resp from conc: %s", ModuleName, resp)
        if resp["resp"] == "config":
            msg = {
               "msg": "req",
               "verb": "post",
               "channel": int(self.id[3:]),
               "body": {
                        "msg": "services",
                        "appID": self.id,
                        "idToName": self.idToName,
                        "services": self.devServices
                       }
                  }
            self.sendMessage(msg, "conc")
        else:
            msg = {"appID": self.id,
                   "msg": "error",
                   "message": "unrecognised response from concentrator"}
            self.sendMessage(msg, "conc")

    def onAdaptorData(self, message):
        """
        This method is called in a thread by cbcommslib so it will not cause
        problems if it takes some time to complete (other than to itself).
        """
        #logging.debug("%s onadaptorData, message: %s", ModuleName, message)
        if message["characteristic"] == "acceleration":
            for a in self.accel:
                if a.id == self.idToName[message["id"]]: 
                    a.processAccel(message)
                    break
        elif message["characteristic"] == "temperature":
            for t in self.temp:
                if t.id == self.idToName[message["id"]]:
                    t.processTemp(message)
                    break
        elif message["characteristic"] == "ir_temperature":
            for t in self.irTemp:
                if t.id == self.idToName[message["id"]]:
                    t.processIrTemp(message)
                    break
        elif message["characteristic"] == "gyro":
            for g in self.gyro:
                if g.id == self.idToName[message["id"]]:
                    g.processGyro(message)
                    break
        elif message["characteristic"] == "magnetometer":
            for g in self.magnet:
                if g.id == self.idToName[message["id"]]:
                    g.processMagnet(message)
                    break
        elif message["characteristic"] == "buttons":
            for b in self.buttons:
                if b.id == self.idToName[message["id"]]:
                    b.processButtons(message)
                    break
        elif message["characteristic"] == "humidity":
            for b in self.humidity:
                if b.id == self.idToName[message["id"]]:
                    b.processHumidity(message)
                    break
        elif message["characteristic"] == "binary_sensor":
            for b in self.binary:
                if b.id == self.idToName[message["id"]]:
                    b.processBinary(message)
                    break
        elif message["characteristic"] == "power":
            for b in self.power:
                if b.id == self.idToName[message["id"]]:
                    b.processPower(message)
                    break
        elif message["characteristic"] == "luminance":
            for b in self.luminance:
                if b.id == self.idToName[message["id"]]:
                    b.processLuminance(message)
                    break

    def onAdaptorService(self, message):
        #logging.debug("%s onAdaptorService, message: %s", ModuleName, message)
        self.devServices.append(message)
        serviceReq = []
        for p in message["service"]:
            # Based on services offered & whether we want to enable them
            if p["characteristic"] == "temperature":
                if config["temperature"] == 'True':
                    self.temp.append(TemperatureMeasure((self.idToName[message["id"]])))
                    self.temp[-1].dm = self.dm
                    serviceReq.append({"characteristic": "temperature",
                                       "interval": config["slow_polling_interval"]})
            elif p["characteristic"] == "ir_temperature":
                if config["irtemperature"] == 'True':
                    self.irTemp.append(IrTemperatureMeasure(self.idToName[message["id"]]))
                    self.irTemp[-1].dm = self.dm
                    serviceReq.append({"characteristic": "ir_temperature",
                                       "interval": config["slow_polling_interval"]})
            elif p["characteristic"] == "acceleration":
                if config["accel"] == 'True':
                    self.accel.append(Accelerometer((self.idToName[message["id"]])))
                    serviceReq.append({"characteristic": "acceleration",
                                       "interval": config["accel_polling_interval"]})
                    self.accel[-1].dm = self.dm
            elif p["characteristic"] == "gyro":
                if config["gyro"] == 'True':
                    self.gyro.append(Gyro(self.idToName[message["id"]]))
                    self.gyro[-1].dm = self.dm
                    serviceReq.append({"characteristic": "gyro",
                                       "interval": config["gyro_polling_interval"]})
            elif p["characteristic"] == "magnetometer":
                if config["magnet"] == 'True': 
                    self.magnet.append(Magnet(self.idToName[message["id"]]))
                    self.magnet[-1].dm = self.dm
                    serviceReq.append({"characteristic": "magnetometer",
                                       "interval": config["magnet_polling_interval"]})
            elif p["characteristic"] == "buttons":
                if config["buttons"] == 'True':
                    self.buttons.append(Buttons(self.idToName[message["id"]]))
                    self.buttons[-1].dm = self.dm
                    serviceReq.append({"characteristic": "buttons",
                                       "interval": 0})
            elif p["characteristic"] == "humidity":
                if config["humidity"] == 'True':
                    self.humidity.append(Humid(self.idToName[message["id"]]))
                    self.humidity[-1].dm = self.dm
                    serviceReq.append({"characteristic": "humidity",
                                       "interval": config["slow_polling_interval"]})
            elif p["characteristic"] == "binary_sensor":
                if config["binary"] == 'True':
                    self.binary.append(Binary(self.idToName[message["id"]]))
                    self.binary[-1].dm = self.dm
                    serviceReq.append({"characteristic": "binary_sensor",
                                       "interval": 0})
            elif p["characteristic"] == "luminance":
                if config["luminance"] == 'True':
                    self.luminance.append(Luminance(self.idToName[message["id"]]))
                    self.luminance[-1].dm = self.dm
                    serviceReq.append({"characteristic": "luminance",
                                       "interval": 0})
        msg = {"id": self.id,
               "request": "service",
               "service": serviceReq}
        self.sendMessage(msg, message["id"])
        self.setState("running")

    def onConfigureMessage(self, config):
        """ Config is based on what sensors are available """
        for adaptor in config["adaptors"]:
            adtID = adaptor["id"]
            if adtID not in self.devices:
                # Because configure may be re-called if devices are added
                name = adaptor["name"]
                friendly_name = adaptor["friendly_name"]
                logging.debug("%s Configure app. Adaptor name: %s", ModuleName, name)
                self.idToName[adtID] = friendly_name.replace(" ", "_")
                self.devices.append(adtID)
        self.dm = DataManager(self.bridge_id)
        self.dm.initFile(self.idToName)
        self.setState("starting")

if __name__ == '__main__':
    App(sys.argv)
