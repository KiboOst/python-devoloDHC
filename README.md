<img align="right" src="/readmeAssets/devoloAPI.jpg" width="150">

# python-devoloDHC

## python API for Devolo Home Control

This python API allows you to control your Devolo Home Control devices.
The following devices are currently supported:

- Devolo Smart Metering Plug (get/set)
- Devolo Wall Switch / Devolo Key Fob (get/set)
- Devolo Siren (get/set)
- Devolo Room Thermostat / Radiator Thermostat(valve) (get/set)
- Devolo Flood Sensor (get)
- Devolo Humidity Sensor (get)
- Devolo Motion Sensor (get)
- Devolo Door/Window Contact (get)
- http devices (get/set)<br /><br /> 
- Scenes (get/set)
- Groups (get/set)
- Timers (get/set)
- Rules (get/set)
- Messages (get/set)<br /><br /> 
- Qubino "Flush Shutter" ZMNHCD1 (get/set)
- Qubino "Flush 1D Relay" ZMNHND1 (get/set)
- Qubino "Flush 2 Relay" ZMNHBD1 (get/set one or both contacts)
- Qubino "Flush Dimmer" ZMNHDD1 (get/set/dim)<br /><br /> 
- Busch-Jaeger Duro 2000 - ZME_05461 (get/set) 

Changing settings will appear in Devolo web interface / Apps daily diary with your account as usual.

Feel free to submit an issue or pull request to add more.

Need a php version of this API ? [php-devoloDHC](https://github.com/KiboOst/php-devoloDHC)

*This isn't an official API | USE AT YOUR OWN RISK!<br />
Anyway this API use exact same commands as your Devolo Home Control, which is based on ProSyst mBS SDK. When you ask bad stuff to the central, this one doesn't burn but just answer this isn't possible or allowed.<br />
This API is reverse-engineered, provided for research and development for interoperability.*

[Requirements](#requirements)<br />
[How-to](#how-to)<br />
[Connection](#connection)<br />
[Reading datas](#reading-operations)<br />
[Changing datas](#changing-operations)<br />
[Consumption](#consumption)<br />
[Unsupported device](#unsupported-device)<br />
[Version history](#version-history)<br />

<img align="right" src="/readmeAssets/requirements.png" width="48">

## Requirements
- Python 2.7.11+ / Python 3+
- The API require internet access (it will authenticate against Devolo servers).

[&#8657;](#python-devolodhc)
<img align="right" src="/readmeAssets/howto.png" width="48">

## How-to
- Download module/pyDHC.py.
- If you can, allow write permission for the API folder. It will support keeping DHC user session between consecutive executions of your script (also lot faster).
- load pyDHC module.
- Start it with your Devolo username/password.

#### Connection

```python
import sys
sys.path.append(r'C:\path\to\api')
from pyDHC import pyDHC

DHC = pyDHC('login', 'password')
if DHC.error: print DHC.error
```

If you have several Central Units, or keep the demo central on your *mydevolo* page, you can choose which to connect to:

```python
#(login | password | which central, default 0)
DHC = pyDHC('login', 'password', 1)
if DHC.error: print DHC.error
```

Let the fun begin:

```python
#for better looking print, we will use pprint:
import pprint
pp = pprint.PrettyPrinter(indent=4)

#get some infos on your Devolo Home Control box:
infos = DHC.getInfos()
pp.pprint(infos)
```
[&#8657;](python-devolodhc)
<img align="right" src="/readmeAssets/read.png" width="48">

#### READING OPERATIONS<br />
*Change devices names by yours!*

```python
#get all devices in a zone:
zone = DHC.getDevicesByZone('living room')
pp.pprint(zone)

#get rule or timer state:
state = DHC.isRuleActive("MyRule")
pp.pprint(state)
state = DHC.isTimerActive("MyTimer")
pp.pprint(state)

#Check if a device is on (0=off, 1=on)
state = DHC.isDeviceOn("My Wall Plug")
pp.pprint(state)

#Check for devices with 2 relays (eg. Qubino Flush 2 Relay ZMNHBD1) is on (0=off, 1=on)
#contact 1
state = DHC.isDeviceOn("myRelay", 1)
pp.pprint(state['result'])
#contact 2
state = DHC.isDeviceOn("myRelay", 2)
pp.pprint(state['result'])
#all contacts
state = DHC.isDeviceOn("myRelay", all)
pp.pprint(state['result'])

#check a device battery level:
batteryLevel = DHC.getDeviceBattery('My Motion Sensor')
pp.pprint(batteryLevel)

#get all batteries level under 20% (ommit argument to have all batteries levels):
BatLevels = DHC.getAllBatteries(20)
pp.pprint(BatLevels)

#get daily diary, last number of events:
diary = DHC.getDailyDiary(10)
pp.pprint(diary)

#get daily device stat:
#0:today, 1:yesterday, 2:day before yesterday
stats = DHC.getDailyStat('My MotionSensor', 0)
pp.pprint(stats)

#get weather report:
weather = DHC.getWeather()
pp.pprint(weather)

#Get one device states (all sensors):
states = DHC.getDeviceStates('My Motion Sensor')
pp.pprint(states)

#Get one sensor data for any device, like light from a Motion Sensor or energy from a Wall Plug:
data = DHC.getDeviceData('My Motion Sensor', 'light')
pp.pprint(data['result']['value'])
data = DHC.getDeviceData('Radiator', 'temperature')
pp.pprint(data['result']['value'])

#You can first ask without data, it will return all available sensors datas for this device:
data = DHC.getDeviceData('My Wall Plug')
pp.pprint(data)

#get url from http device:
url = DHC.getDeviceURL('myhttp device')

#get message data:
url = DHC.getMessageData('MyAlert')
```

[&#8657;](#python-devolodhc)
<img align="right" src="/readmeAssets/set.png" width="48">

#### CHANGING OPERATIONS<br />
*Change devices names by yours!*

```python
#TURN DEVICE ON(1) or OFF(0):
#supported: all on/off devices and http devices
dev = DHC.turnDeviceOnOff("My Room wallPlug", 1)
pp.pprint(dev)

#For devices with 2 relays as Qubino Flush 2 Relay ZMNHBD1 (device name, state, contact):
#contact 1 on
DHC.turnDeviceOnOff("myRelay", 1, 1)
#contact 2 on
DHC.turnDeviceOnOff("myRelay", 1, 2)
#all contacts on
DHC.turnDeviceOnOff("myRelay", 1, "All")

#TURN GROUP ON(1) or OFF(0):
DHC.turnGroupOnOff("My Plugs Group", 1)

#RUN HTTP DEVICE:
DHC.turnDeviceOnOff("My http device", 1) #0 won't do anything of course.

#START SCENE:
DHC.startScene("We go out")

#SEND MESSAGE:
DHC.sendMessage("Alert")

#CHANGE THERMOSTAT/VALVE VALUE:
targetValue = DHC.setDeviceValue('My radiator', 21)
DHC.setDeviceValue('my thermostat', 19)
#press thermostat button:
DHC.pressDeviceKey('my thermostat', 1)

#TURN SIREN ON: (last number is the indice of the tone in the interface list. For example, 1 is alarm and won't stop! 0 will!)
DHC.setDeviceValue('My Devolo Siren', 5)

#SET SHUTTER OPENING:
DHC.setDeviceValue('qubShutter', 50)

#SET DIMMER VALUE:
DHC.setDeviceValue('qubDimmer', 50)

#PRESS REMOTE SWITCH KEY OR KEY FOB KEY:
DHC.pressDeviceKey('MySwitch', 3)

#TURN RULE ACTIVE (1 or 0)
DHC.turnRuleOnOff('MyRule', 1)

#TURN TIMER ACTIVE (1 or 0)
DHC.turnTimerOnOff('MyTimer', 1)

#TURN OFF DAILY DIARY REPORT (true/false):
DHC.setDeviceDiary('movekitchen', false)
```

[&#8657;](#python-devolodhc)
<img align="right" src="/readmeAssets/consumption.png" width="48">

#### Consumption

Some people would like to have more than 3days consumption log for devices like Wall Plugs.
Here are two functions to log consumptions, and read them between two dates of choice. So you can make a cron task to call this function everyday, it will log the yesterday total consumption of each Wall Plugs:

```python
DHC.logConsumption('log.json')
```
If you don't provide a file path, or it can't write to, the api will return an error, but also provide the result (so you can write your own custom functions).<br />
Then, to read the log and know consumption for a month, or along summer/winter etc:

```python
stats = DHC.getLogConsumption('log.json', '01.03.2017', '31.03.2017')
pp.pprint(stats)
```
Of course, it needs a valid previously saved log file by the api. You can provide no dates (full log), or only one (set first as null if needed). Just respect day.month.year (php 'd.m.Y').

[&#8657;](#php-devolodhc)
#### Unsupported device

If you have unsupported device, you can call special function with this device and post the return in a new issue.

[Request for unsupported device](../../issues/)

```python
help = DHC.debugDevice('MyStrangeDevice')
pp.pprint(help)
```
[&#8657;](#python-devolodhc)
<img align="right" src="/readmeAssets/changes.png" width="48">

## Version history

#### v 1.3 (2017-10-19)
- Now support Python3! Same module will check your Python version and work on both 2.7/3!

#### v 1.0 (2017-09-24)
- New: getNumStats() report number of devices, rules, timers, scenes, groups, zones, messages
- Enhanced: Qubino Flush 2 Relay ZMNHBD1 support<br />
DHC.turnDeviceOnOff('my2relay', 1, 'All') //support 1, 2, 'All' for Q1, Q2, both<br />
DHC.isDeviceOn('my2relay', 1) //support 1, 2, 'All' for Q1, Q2, both

#### v 0.9 (2017-06-12)
- First public version

[&#8657;](#python-devolodhc)
<img align="right" src="/readmeAssets/mit.png" width="48">

## License

The MIT License (MIT)

Copyright (c) 2017 KiboOst

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
