#!/usr/bin/python
# -*- coding: utf-8 -*-

import sys
import os

import urllib2
import urllib
from cookielib import CookieJar, LWPCookieJar

import json
from collections import OrderedDict
import base64

import datetime
from time import gmtime, strftime

"""
All functions return an array containing 'result', and 'error' if there is a problem.
So we can always check for error, then parse the result:
	state = DHC.isDeviceOn('MyPlug')
	if 'error' in state:
		print state['error']
	else:
		print "Device state:", state['result']
"""
class pyDHC():
	#user functions======================================================
	def getInfos(self): #@return['result'] array infos from this api, Devolo user, and Devolo central
		if self._userInfos == None:
			#get uuid:
			if self._uuid == None:
				jsonString = '{"jsonrpc":"2.0", "method":"FIM/getFunctionalItemUIDs","params":["(objectClass=com.devolo.fi.page.Dashboard)"]}'
				answer = self.sendCommand(jsonString)
				try:
					uuid = answer['result'][0]
					self._uuid = uuid.split('devolo.Dashboard.')[1]
				except:
					return {'error':{'message':"can't find uuid!"}}

			#get user infos:
			jsonString = '{"jsonrpc":"2.0", "method":"FIM/getFunctionalItems","params":[["devolo.UserPrefs.'+self._uuid+'"],0]}'
			answer = self.sendCommand(jsonString)
			self._userInfos = answer['result']['items'][0]['properties']

		if self._centralInfos == None:
			#get portal manager token:
			jsonString = '{"jsonrpc":"2.0", "method":"FIM/getFunctionalItemUIDs","params":["(objectClass=com.devolo.fi.gw.PortalManager)"]}'
			answer = self.sendCommand(jsonString)
			try:
				var = answer['result'][0]
				self._token = var.replace('devolo.mprm.gw.PortalManager.', '')
			except:
				return {'error':'Could not find info token.'}

			#get central infos:
			jsonString = '{"jsonrpc":"2.0", "method":"FIM/getFunctionalItems","params":[["devolo.mprm.gw.PortalManager.'+self._token+'"],0]}'
			answer = self.sendCommand(jsonString)
			try:
				self._centralInfos = answer['result']['items'][0]['properties']
				self._gateway = self._centralInfos['gateway']
			except:
				self._centralInfos = None
				self._gateway = None

		infos = {
				'python API version': self._version,
				'user': self._userInfos,
				'central': self._centralInfos
		}

		return {'result': infos}
	#
	def getNumStats(self): #@return['result'] array containing number of devices, rules, etc...
		if len(self._AllRules) == 0: self.getRules()
		if len(self._AllTimers) == 0: self.getTimers()
		if len(self._AllScenes) == 0: self.getScenes()
		if len(self._AllMessages) == 0: self.getMessages()

		report = {
					'Devices'   : len(self._AllDevices),
					'Rules'     : len(self._AllRules),
					'Timers'    : len(self._AllTimers),
					'Scenes'    : len(self._AllScenes),
					'Groups'    : len(self._AllGroups),
					'Messages'  : len(self._AllMessages),
					'Zones'     : len(self._AllZones)
					}
		return {'result': report}
	#


	#______________________IS:
	def isRuleActive(self, rule): #@rule name | @return['result'] string active/inactive
		if type(rule) == str:
			rule = self.getRuleByName(rule)
			if 'error' in rule: return rule

		answer = self.fetchItems([rule['element']])
		if 'error' in answer: return {'result': None, 'error':answer['error']['message']}
		state = answer['result']['items'][0]['properties']['enabled']
		state = 'active' if state == 1 else 'inactive'
		return {'result': state}
	#
	def isTimerActive(self, timer): #@timer name | @return['result'] string active/inactive
		if type(timer) == str:
			timer = self.getTimerByName(timer)
			if 'error' in timer: return timer

		return self.isRuleActive(timer)
	#
	def isDeviceOn(self, device, switch=None): #@device name | @return['result'] string on/off
		if type(device) == str:
			device = self.getDeviceByName(device)
			if 'error' in device: return device

		if 'sensors' in device: sensors = device['sensors']
		else: return {'result':None, 'error' : 'No sensor found in this device'}

		for sensor in sensors:
			sensorType = self.getSensorType(sensor)
			if sensorType in self._SensorsOnOff:
				#check qubino 2 relay:
				if switch != None:
					thisSwitch = sensor[-2:]
					#several switches detected?
					if thisSwitch != '#1' and thisSwitch != '#2': return {'result': None, 'error':'This switch does not seem to have several contacts'}
					#get the other switch:
					if thisSwitch == '#1': otherSensor = sensor.replace('#1', '#2')
					if thisSwitch == '#2': otherSensor = sensor.replace('#2', '#1')
					#so, which switch(es) to fetch:
					if switch == 'All':
						toFetch = [sensor, otherSensor]
						answer = self.fetchItems(toFetch)
						if 'error' in answer: return {'result': None, 'error':answer['error']['message']}
						state1 = answer['result']['items'][0]['properties']['state']
						state2 = answer['result']['items'][1]['properties']['state']
						isOn1 = 'on' if state1 > 0 else 'off'
						isOn2 = 'on' if state2 > 0 else 'off'
						return {'result':[isOn1, isOn2]}
					if (switch == 1 and thisSwitch == '#1') or (switch == 2 and thisSwitch == '#2'):
						toFetch = [sensor]
					else:
						toFetch = [otherSensor]

					answer = self.fetchItems(toFetch)
					if 'error' in answer: return {'result': None, 'error':answer['error']['message']}
					try:
						state = answer['result']['items'][0]['properties']['state']
						isOn = 'on' if state > 0 else 'off'
						return {'result':isOn}
					except:
						pass
				else: #single sensor request
					answer = self.fetchItems([sensor])
					if 'error' in answer: return {'result': None, 'error':answer['error']['message']}
					try:
						state = answer['result']['items'][0]['properties']['state']
						isOn = 'on' if state > 0 else 'off'
						return {'result':isOn}
					except:
						pass
		return {'result':None, 'error':'No supported sensor for this device'}
	#

	#______________________GET:
	def getDeviceStates(self, device, DebugReport=None): #@return['result'] array of sensor type and state
		if type(device) == str:
			device = self.getDeviceByName(device)
			if 'error' in device: return device

		if 'sensors' in device: sensors = device['sensors']
		else: return {'result':None, 'error' : 'No sensor found in this device'}

		#fetch sensors:
		states = []
		for sensor in sensors:
			sensorType = self.getSensorType(sensor)
			param = self.getValuesByType(sensorType)
			if param!=None:
				answer = self.fetchItems([sensor])
				if 'error' in answer: return {'result':None, 'error':answer['error']['message']}
				if DebugReport: print answer
				jsonSensor = {'sensorType': sensorType}
				for key in param:
					value = answer['result']['items'][0]['properties'][key]
					if key == 'sensorType' and value == 'unknown': continue
					value = self.formatStates(sensorType, key, value)
					jsonSensor[key] = value
				states.append(jsonSensor)
			elif not sensorType in self._SensorsNoValues: #Unknown, unsupported sensor!
				answer = self.fetchItems([sensor])
				print "DEBUG - UNKNOWN PARAM - Please help and report this message on https://github.com/KiboOst/pyDHC or email it to "+base64.b64decode('a2lib29zdEBmcmVlLmZy')
				print answer

		return {'result':states}
	#
	def getDeviceData(self, device, askData=None): #@device name | @return['result'] sensor data. If not asked data, @return['available'] all available sensors/data array
		if type(device) == str:
			device = self.getDeviceByName(device)
			if 'error' in device: return device

		datas = self.getDeviceStates(device)
		availableDatas = []
		for item in datas['result']:
			availableDatas.append(item['sensorType'])
			if 'switchType' in item:
				availableDatas.append(item['switchType'])
				if item['switchType'] == askData: return {'result':item}

			if item['sensorType'] == askData: return {'result':item}

		error = {
				'result': None,
				'error': 'Unfound data for this Device',
				'available': availableDatas
				}
		return error
	#
	def getDevicesByZone(self, zoneName): #@zone name | @return['result'] array of devices
		for zone in self._AllZones:
			if zone['name'] == zoneName:
				devicesUIDS = zone['deviceUIDs']
				jsonArray = []
				for device in self._AllDevices:
					if device['uid'] in devicesUIDS:
						jsonArray.append(device)
				return {'result': jsonArray}
		return {'result': None, 'error': 'Unfound '+zoneName}
	#
	def getDeviceURL(self, device): #@device name | @return['result'] string
		if type(device) == str:
			device = self.getDeviceByName(device)
			if 'error' in device: return device

		uid = device['uid']
		if not 'hdm:DevoloHttp:virtual' in uid: return {'result': None, 'error': 'This is not an http virtual device'}

		hdm = uid.replace('hdm:DevoloHttp:virtual', 'hs.hdm:DevoloHttp:virtual')
		answer = self.fetchItems([hdm])
		if 'error' in answer: return {'result':None, 'error':answer['error']['message']}
		url = answer['result']['items'][0]['properties']['httpSettings']['request']
		return {'result': url}
	#
	def getDeviceBattery(self, device): #@device name | @return['result'] string
		if type(device) == str:
			device = self.getDeviceByName(device)
			if 'error' in device: return device

		batLevel = device['batteryLevel']
		if batLevel == 'None' or batLevel == -1: batLevel = 'No battery'
		return {'result': batLevel}
	#
	def getAllBatteries(self, lowLevel=100, filter=1): #@return['result'] array of device name / battery level under lowLevel. filter other than 1 return even no battery devices.
		jsonDatas = []
		for device in self._AllDevices:
			deviceName = device['name']
			deviceBat = device['batteryLevel']
			if deviceBat == -1 or deviceBat == 'None':
				if filter == 1: continue

			datas = {'name': deviceName, 'battery_percent': deviceBat}
			if deviceBat <= lowLevel:
				jsonDatas.append(datas)

		return {'result': jsonDatas}
	#
	def getDailyDiary(self, numEvents=20): #@number of events to return | @return['result'] array of daily events
		if not type(numEvents) == int: return {'error': 'Provide numeric argument as number of events to report'}
		if numEvents < 0: return {'error': 'Dude, what should I report as negative number of events ? Are you in the future ?'}

		jsonString = '{"jsonrpc":"2.0", "method":"FIM/invokeOperation","params":["devolo.DeviceEvents","retrieveDailyData",[0,0,'+str(numEvents)+']]}';
		answer = self.sendCommand(jsonString)
		if 'error' in answer: return {'result':None, 'error':answer['error']['message']}

		jsonDatas = []
		numEvents = len(answer['result']) #may have less than requested
		for event in reversed(answer['result']):
			deviceName = event['deviceName']
			deviceZone = event['deviceZone']
			author = event['author']
			timeOfDay = event['timeOfDay']
			timeOfDay = strftime('%H:%M:%S', gmtime(float(timeOfDay)))

			datas ={
					'deviceName': deviceName,
					'deviceZone': deviceZone,
					'author': author,
					'timeOfDay': timeOfDay
					}
			jsonDatas.append(datas)
		return {'result': jsonDatas}
	#
	def getDailyStat(self, device, dayBefore=0): #@device name, @day before 0 1 or 2 | @return['result'] array
		if type(device) == str:
			device = self.getDeviceByName(device)
			if 'error' in device: return device

		if type(dayBefore)!=int: return {'error': 'Second argument should be 0 1 or 2 for today, yesterday, day before yesterday'}

		operation = "retrieveDailyStatistics"
		statSensor = device['statUID']
		if statSensor == 'None': return {'result': None, 'error': "No statistic for such device"}

		answer = self.invokeOperation(statSensor, operation, str(dayBefore))
		if 'error' in answer: return {'result':None, 'error':answer['error']['message']}

		jsonDatas = []
		for item in answer['result']:
			sensor = item['widgetElementUID']
			values = item['value']
			if 'timeOfDay' in item:
				timesOfDay = item['timeOfDay']

			if device['model'] in 'Door/Window:Sensor':
				if sensor in 'BinarySensor:hdm': sensor = 'opened'
				if sensor in '#MultilevelSensor(1)': sensor = 'temperature'
				if sensor in '#MultilevelSensor(3)': sensor = 'light'
			if device['model'] in 'Motion:Sensor':
				if sensor in 'BinarySensor:hdm': sensor = 'alarm'
				if sensor in '#MultilevelSensor(1)': sensor = 'temperature'
				if sensor in '#MultilevelSensor(3)': sensor = 'light'
			if device['model'] in 'Wall:Plug:Switch:and:Meter':
				if sensor in 'Meter:hdm': sensor = 'consumption'

			sensorData = {'sensor': sensor}
			countValues = len(values)
			for i in xrange(countValues):
				timeOfDay = strftime('%H:%M:%S', gmtime(float(timesOfDay[i])))
				sensorData[timeOfDay] = values[i]

			jsonDatas.append(sensorData)

		return {'result': jsonDatas}
	#
	def getWeather(self): #@return['result'] array of weather data for next three days
		jsonString = '{"jsonrpc":"2.0","method":"FIM/getFunctionalItems","params":[["devolo.WeatherWidget"],0]}'
		answer = self.sendCommand(jsonString)
		if 'error' in answer: return {'result':None, 'error':answer['error']['message']}

		data = answer['result']['items'][0]['properties']
		self._Weather = {}
		self._Weather['currentTemp'] = data['currentTemp']

		del(data['forecastData'][0]['weatherCode'])
		del(data['forecastData'][1]['weatherCode'])
		del(data['forecastData'][2]['weatherCode'])

		self._Weather['Today'] = data['forecastData'][0]
		self._Weather['Tomorrow'] = data['forecastData'][1]
		self._Weather['DayAfterT'] = data['forecastData'][2]

		value = data['lastUpdateTimestamp']
		self._Weather['lastUpdate'] = self.formatStates('LastActivity', 'lastActivityTime', value)

		return {'result': self._Weather}
	#
	def getMessageData(self, msg): #@message name | @return['result'] array of message data
		if type(msg) == str:
			msg = self.getMessageByName(msg)
			if 'error' in msg: return msg

		answer = self.fetchItems([msg['element']])
		if 'error' in answer: return {'result':None, 'error':answer['error']['message']}

		return {'result': answer['result']['items'][0]['properties']['msgData']}
	#

	#______________________CONSUMPTION:
	def logConsumption(self, filePath='/'): #@log file path | always @return['result'] array of yesterday total consumptions, @return['error'] if can't write file
		dir = os.path.dirname(__file__)
		filePath = os.path.join(dir, filePath)
		if os.path.isfile(filePath):
			jsonDatas = open(filePath, "r").read()
			prevDatas = json.loads(jsonDatas, object_pairs_hook=OrderedDict)
			prevDatas = OrderedDict(reversed(list(prevDatas.items())))
		else:
			prevDatas = {}

		#get yesterday sums for each device:
		yesterday = datetime.date.today() - datetime.timedelta(1)
		yesterday = yesterday.strftime('%d.%m.%Y')
		datasArray = {}
		datasArray[yesterday] = {}

		for device in self._AllDevices:
			if device['model'] in self._MeteringDevices:
				name = device['name']
				datas = self.getDailyStat(device, 1)
				datas = datas['result'][0]
				total = 0
				for date, value in datas.items():
					if date == 'sensor': continue
					total += float(value)
				total = str(total/1000)+'kWh'
				datasArray[yesterday][name] = total

		#add yesterday sums to previously loaded datas:
		prevDatas[yesterday] = datasArray[yesterday]

		#set recent up:
		prevDatas = OrderedDict(reversed(list(prevDatas.items())))

		#write it to file:
		try:
			with open(filePath, 'w') as f:
				f.write(json.dumps(prevDatas, indent=4, sort_keys=False, encoding="utf-8"))
			return {'result':datasArray}
		except:
			return {'result':datasArray, 'error': 'Unable to write file!'}
	#
	def getLogConsumption(self, filePath='/', dateStart=None, dateEnd=None): #@log file path | @return['result'] array, @return['error'] if can't read file
		dir = os.path.dirname(__file__)
		filePath = os.path.join(dir, filePath)
		if os.path.isfile(filePath):
			jsonDatas = open(filePath, "r").read()
			prevDatas = json.loads(jsonDatas, object_pairs_hook=OrderedDict)

			keys = list(prevDatas.keys())
			logDateStart = keys[-1]
			logDateEnd = keys[0]

			if dateStart==None: dateStart = logDateStart
			if dateEnd==None: dateEnd = logDateEnd
			dateStart = datetime.datetime.strptime(dateStart, '%d.%m.%Y')
			dateEnd = datetime.datetime.strptime(dateEnd, '%d.%m.%Y')

			sumArray = {}
			for i in xrange(len(prevDatas)):
				thisDate = keys[i]
				data = prevDatas[thisDate]
				thisDate = datetime.datetime.strptime(thisDate, '%d.%m.%Y')
				if dateStart<=thisDate<=dateEnd:
					for name, value in data.items():
						if not name in sumArray: sumArray[name] = 0.0
						sumArray[name] += float(value[:-3])

			for name, value in sumArray.items():
				sumArray[name] = str(round(value,2))+'kWh'

			return {'result':sumArray}
		else:
			return {'result': None, 'error':'Unable to open file'}
	#

	#______________________SET:
	def startScene(self, scene): #@scene name | @return['result'] central answer, @return['error'] if any
		if type(scene) == str:
			scene = self.getSceneByName(scene)
			if 'error' in scene: return scene

		element = scene['element']
		answer = self.invokeOperation(element, "start")
		if 'error' in answer: return {'result': None, 'error':answer['error']['message']}
		result = True if answer['result']==None else False
		return {'result':result}
	#
	def turnRuleOnOff(self, rule, state=0): #@rule name | @return['result'] central answer, @return['error'] if any
		if type(rule) == str:
			rule = self.getRuleByName(rule)
			if 'error' in rule: return rule

		value = 'false' if state == 0 else 'true'
		jsonString = '{"jsonrpc":"2.0","method":"FIM/setProperty","params":["'+rule['element']+'","enabled",'+value+']}'
		answer = self.sendCommand(jsonString)
		if 'error' in answer: return {'result': None, 'error':answer['error']['message']}
		return {'result':answer}
	#
	def turnTimerOnOff(self, timer, state=0): #@timer name | @return['result'] central answer, @return['error'] if any
		if type(timer) == str:
			timer = self.getTimerByName(timer)
			if 'error' in timer: return timer

		value = 'false' if state == 0 else 'true'
		jsonString = '{"jsonrpc":"2.0","method":"FIM/setProperty","params":["'+timer['element']+'","enabled",'+value+']}'
		answer = self.sendCommand(jsonString)
		if 'error' in answer: return {'result': None, 'error':answer['error']['message']}
		return {'result':answer}
	#
	def turnDeviceOnOff(self, device, state, switch=None): #@device name | @return['result'] central answer, @return['error'] if any
		if type(device) == str:
			device = self.getDeviceByName(device)
			if 'error' in device: return device

		if 'sensors' in device: sensors = device['sensors']
		else: return {'result':None, 'error' : 'No sensor found in this device'}

		if state < 0: state = 0
		for sensor in sensors:
			sensorType = self.getSensorType(sensor)
			if sensorType in self._SensorsOnOff:
				operation = 'turnOff' if state == 0 else 'turnOn'

				#check qubino 2 relay:
				if switch != None:
					thisSwitch = sensor[-2:]
					#several switches detected?
					if thisSwitch != '#1' and thisSwitch != '#2': return {'result': None, 'error':'This switch does not seem to have several contacts'}
					#get the other switch:
					if thisSwitch == '#1': otherSensor = sensor.replace('#1', '#2')
					if thisSwitch == '#2': otherSensor = sensor.replace('#2', '#1')
					#so, which switch(es) to activate:
					if switch == 'All':
						answer = self.invokeOperation(sensor, operation)
						if 'error' in answer: return {'result': None, 'error':answer['error']['message']}
						answer = self.invokeOperation(otherSensor, operation)
						if 'error' in answer: return {'result': None, 'error':answer['error']['message']}
						return {'result':True}
					if (switch == 1 and thisSwitch == '#1') or (switch == 2 and thisSwitch == '#2'):
						answer = self.invokeOperation(sensor, operation)
						if 'error' in answer: return {'result': None, 'error':answer['error']['message']}
						return {'result':True}
				else: #single sensor request
					answer = self.invokeOperation(sensor, operation)
					if 'error' in answer: return {'result': None, 'error':answer['error']['message']}
					else: return {'result':True}

			if sensorType in self._SensorsSend:
				operation = 'send'
				answer = self.invokeOperation(sensor, operation)
				if 'error' in answer: return {'result': None, 'error':answer['error']['message']}
				else: return {'result':True}

		return {'result':None, 'error':'No supported sensor for this device'}
	#
	def turnGroupOnOff(self, group, state=0): #@group name | @return['result'] central answer, @return['error'] if any
		if type(group) == str:
			group = self.getGroupByName(group)
			if 'error' in group: return group

		sensor = 'devolo.BinarySwitch:'+group['id']
		if state < 0: state = 0
		operation = 'turnOff' if state == 0 else 'turnOn'
		answer = self.invokeOperation(sensor, operation)
		if 'error' in answer: return {'result': None, 'error':answer['error']['message']}
		else: return {'result':True}
	#
	def setDeviceValue(self, device, value): #@device name, @value | @return['result'] central answer, @return['error'] if any
		if type(device) == str:
			device = self.getDeviceByName(device)
			if 'error' in device: return device

		if 'sensors' in device: sensors = device['sensors']
		else: return {'result':None, 'error' : 'No sensor found in this device'}

		for sensor in sensors:
			sensorType = self.getSensorType(sensor)
			if sensorType in self._SensorsSendValue:
				operation = 'sendValue'
				answer = self.invokeOperation(sensor, operation, str(value))
				if 'error' in answer: return {'result': None, 'error':answer['error']['message']}
				else: return {'result':True}
	#
	def pressDeviceKey(self, device, key=None): #@device name, @key number | @return['result'] central answer, @return['error'] if any
		if key == None: return {'result': None, 'error': 'No defined key to press'}
		if key > 4: return {'result': None, 'error': 'You really have Wall Switch with more than 4 buttons ? Let me know!'}

		if type(device) == str:
			device = self.getDeviceByName(device)
			if 'error' in device: return device

		if 'sensors' in device: sensors = device['sensors']
		else: return {'result':None, 'error' : 'No sensor found in this device'}

		for sensor in sensors:
			sensorType = self.getSensorType(sensor)
			if sensorType in self._SensorsPressKey:
				operation = 'pressKey'
				answer = self.invokeOperation(sensor, operation, str(key))
				if 'error' in answer: return {'result': None, 'error':answer['error']['message']}
				else: return {'result':True}

		return {'result': None, 'error': 'No supported sensor for this device'}
	#
	def sendMessage(self, msg): #@message name | @return['result'] central answer, @return['error'] if any
		if type(msg) == str:
			msg = self.getMessageByName(msg)
			if 'error' in msg: return msg

		element = msg['element']
		answer = self.invokeOperation(element, "send")
		if 'error' in answer: return {'result': None, 'error':answer['error']['message']}
		result = True if answer['result']==None else False
		return {'result':result}
	#
	def setDeviceDiary(self, device, state=True): #@device name, @state true/false | @return['result'] central answer, @return['error'] if any
		if type(device) == str:
			device = self.getDeviceByName(device)
			if 'error' in device: return device

		deviceName = device['name']
		deviceIcon = device['icon']
		zoneID = device['zoneId']
		deviceSetting = 'gds.'+device['uid']
		state = str(state)

		jsonString = '{"jsonrpc":"2.0","method":"FIM/invokeOperation","params":["'+deviceSetting+'","save",[{"name":"'+deviceName+'","icon":"'+deviceIcon+'","zoneID":"'+zoneID+'","eventsEnabled":'+state+'}]]}'
		answer = self.sendCommand(jsonString)
		if 'error' in answer: return {'result':None, 'error':answer['error']['message']}
		return {'result': True}
	#


	#INTERNAL FUNCTIONS==================================================
	#______________________GET shorcuts:
	def getDeviceByName(self, name):
		for device in self._AllDevices:
			if device['name'] == name: return device
		return {'result':None, 'error':'Unfound device'}
	#
	def getRuleByName(self, name):
		if len(self._AllRules) == 0: self.getRules()
		for rule in self._AllRules:
			if rule['name'] == name: return rule
		return {'result':None, 'error':'Unfound rule'}
	#
	def getTimerByName(self, name):
		if len(self._AllTimers) == 0: self.getTimers()
		for timer in self._AllTimers:
			if timer['name'] == name:return timer
		return {'result':None, 'error':'Unfound timer'}
	#
	def getSceneByName(self, name):
		if len(self._AllScenes) == 0: self.getScenes()
		for scene in self._AllScenes:
			if scene['name'] == name:return scene
		return {'result':None, 'error':'Unfound scene'}
	#
	def getGroupByName(self, name):
		for group in self._AllGroups:
			if group['name'] == name:return group
		return {'result':None, 'error':'Unfound group'}
	#
	def getMessageByName(self, name):
		if len(self._AllMessages) == 0: self.getMessages()
		for message in self._AllMessages['customMessages']:
			if message['name'] == name: return message
		return {'result':None, 'error':'Unfound message'}
	#

	#______________________internal mixture
	def getSensorType(self, sensor):
		#devolo.BinarySensor:hdm:ZWave:D8F7DDE2/10 -> BinarySensor
		sensorType = sensor.split('devolo.')
		if len(sensorType) == 0: return None
		sensorType = sensorType[1].split(':')
		sensorType = sensorType[0]
		return sensorType
	#
	def getValuesByType(self, sensorType):
		for thisType in self._SensorValuesByType:
			if thisType == sensorType: return self._SensorValuesByType[thisType]
		return None
	#
	def debugDevice(self, device):
		device = self.getDeviceByName(device)
		if 'error' in device: return device

		import pprint
		pp = pprint.PrettyPrinter(indent=4)

		jsonArray = self.fetchItems([device['uid']])
		pp.pprint(jsonArray)

		elements = jsonArray['result']['items'][0]['properties']['elementUIDs']
		elementsArray = self.fetchItems(elements)
		pp.pprint(elementsArray)

		settings = jsonArray['result']['items'][0]['properties']['settingUIDs']
		settingsArray = self.fetchItems(settings)
		pp.pprint(settingsArray)
	#
	def resetSessionTimeout(self):
		#cookie expire in 30min, anyway Devolo Central send resetSessionTimeout every 10mins
		if self._uuid == None:
			jsonString = '{"jsonrpc":"2.0", "method":"FIM/getFunctionalItemUIDs","params":["(objectClass=com.devolo.fi.page.Dashboard)"]}'
			answer = self.sendCommand(jsonString)
			try:
				uuid = answer['result'][0]
				self._uuid = uuid.split('devolo.Dashboard.')[1]
			except:
				return {'error':{'message':"can't find uuid!"}}

		jsonString = '{"jsonrpc":"2.0", "method":"FIM/invokeOperation","params":["devolo.UserPrefs.'+self._uuid+'","resetSessionTimeout",[]]}'
		answer = self.sendCommand(jsonString)
		try:
			return {'result':None, 'error':answer['error']['message']}
		except:
			return {'result':answer['result']}
	#

	#______________________getter functions
	def getDevices(self): #First call after connection, ask all zones and register all devices into self._AllDevices
		if len(self._AllZones) == 0:
			result = self.getZones()
			if 'error' in result: return result

		#get all devices from all zones:
		UIDSarray = []
		for zone in self._AllZones:
			devices = zone['deviceUIDs']
			for device in devices:
				UIDSarray.append(device)

		#request all infos for all devices at once:
		jsonArray = self.fetchItems(UIDSarray)

		#store devices:
		devices = []
		for thisDevice in jsonArray['result']['items']:
			try:
				uid = thisDevice['UID']
			except:
				uid = 'None'
			try:
				elementUIDs = thisDevice['properties']['elementUIDs']
			except:
				elementUIDs = 'None'

			device = {
					'name': thisDevice['properties'].get('itemName', 'None'),
					'uid': uid,
					'sensors': elementUIDs,
					'zoneId': thisDevice['properties'].get('zoneId', 'None'),
					'statUID': thisDevice['properties'].get('statisticsUID', 'None'),
					'batteryLevel': thisDevice['properties'].get('batteryLevel', 'None'),
					'model': thisDevice['properties'].get('deviceModelUID', 'None'),
					'icon': thisDevice['properties'].get('icon', 'None')
					}
			devices.append(device)

		self._AllDevices = devices
	#
	def getZones(self): #called by getDevices(), register all zones into self._AllZones and groups into self._AllGroups
		jsonString = '{"jsonrpc":"2.0","method":"FIM/getFunctionalItems","params":[["devolo.Grouping"],0]}'
		jsonAnswer = self.request('POST', self._dhcUrl, '/remote/json-rpc', jsonString)

		#avoid account with just demo gateway:
		if not jsonAnswer['result']["items"][0]['properties']['zones']:
			self.error = 'Seems a demo Gateway, or no zones ?'
			return {'result':None, 'error':self.error}


		#Store zones infos:
		zones = jsonAnswer['result']["items"][0]['properties']['zones']
		for zone in zones:
			thisID = zone['id']
			thisName = zone['name']
			thisDevices = zone['deviceUIDs']
			zone = {'name':thisName, 'id': thisID, 'deviceUIDs':thisDevices}
			self._AllZones.append(zone)

		#get and store Groups:
		jsonArray = self.fetchItems(jsonAnswer['result']['items'][0]['properties']['smartGroupWidgetUIDs'])
		for group in jsonArray['result']['items']:
			thisID = group['UID']
			thisName = group['properties']['itemName']
			thisOurOfSync = group['properties']['outOfSync']
			thisSync = group['properties']['synchronized']
			thisDevices = group['properties']['deviceUIDs']
			group = {'name':thisName, 'id': thisID, 'deviceUIDs':thisDevices, 'outOfSync':thisOurOfSync, 'synchronized':thisSync}
			self._AllGroups.append(group)

		return {'result':True}
	#
	def getScenes(self): #called if necessary, register all scenes into self._AllScenes
		jsonString = '{"jsonrpc":"2.0","method":"FIM/getFunctionalItems","params":[["devolo.Scene"],0]}'
		jsonAnswer = self.request('POST', self._dhcUrl, '/remote/json-rpc', jsonString)

		#request datas for all scenes:
		if 'result' in jsonAnswer:
			jsonArray = self.fetchItems(jsonAnswer['result']['items'][0]['properties']['sceneUIDs'])
			scenes = jsonArray['result']['items']
			for scene in scenes:
				thisScene = {
							'name': scene['properties']['itemName'],
							'id': scene['UID'],
							'element': scene['UID'].replace('Scene', 'SceneControl')
							}
				self._AllScenes.append(thisScene)
	#
	def getTimers(self): #called if necessary, register all timers into self._AllTimers
		jsonString = '{"jsonrpc":"2.0","method":"FIM/getFunctionalItems","params":[["devolo.Schedules"],0]}'
		jsonAnswer = self.request('POST', self._dhcUrl, '/remote/json-rpc', jsonString)

		#request datas for all timers:
		if 'result' in jsonAnswer:
			jsonArray = self.fetchItems(jsonAnswer['result']['items'][0]['properties']['scheduleUIDs'])
			timers = jsonArray['result']['items']
			for timer in timers:
				thisTimer = {
							'name': timer['properties']['itemName'],
							'id': timer['UID'],
							'element': timer['UID'].replace('Schedule', 'ScheduleControl')
							}
				self._AllTimers.append(thisTimer)
	#
	def getRules(self): #called if necessary, register all rules into self._AllRules
		jsonString = '{"jsonrpc":"2.0","method":"FIM/getFunctionalItems","params":[["devolo.Services"],0]}'
		jsonAnswer = self.request('POST', self._dhcUrl, '/remote/json-rpc', jsonString)

		#request datas for all rules:
		if 'result' in jsonAnswer:
			jsonArray = self.fetchItems(jsonAnswer['result']['items'][0]['properties']['serviceUIDs'])
			rules = jsonArray['result']['items']
			for rule in rules:
				thisRule = {
							'name': rule['properties']['itemName'],
							'id': rule['UID'],
							'element': rule['UID'].replace('Service', 'ServiceControl')
							}
				self._AllRules.append(thisRule)
	#
	def getMessages(self): #called if necessary, register all messages into self._AllMessages
		jsonString = '{"jsonrpc":"2.0","method":"FIM/getFunctionalItems","params":[["devolo.Messages"],0]}'
		jsonAnswer = self.request('POST', self._dhcUrl, '/remote/json-rpc', jsonString)

		if 'result' in jsonAnswer:
			self._AllMessages['pnEndpoints'] = jsonAnswer['result']['items'][0]['properties']['pnEndpoints']
			self._AllMessages['phoneNumbers'] = jsonAnswer['result']['items'][0]['properties']['phoneNumbers']
			self._AllMessages['emailExt'] = jsonAnswer['result']['items'][0]['properties']['emailExt']
			self._AllMessages['emailAddresses'] = jsonAnswer['result']['items'][0]['properties']['emailAddresses']
			self._AllMessages['customMessages'] = []

			#fetch custom Messages:
			jsonArray = self.fetchItems(jsonAnswer['result']['items'][0]['properties']['customMessageUIDs'])
			for msg in jsonArray['result']['items']:
				thisMsg = {
							'name': msg['properties']['itemName'],
							'id': msg['UID'],
							'description': msg['properties']['description'],
							'base': msg['properties']['base'],
							'element': msg['properties']['elementUIDs'][0]
							}
				self._AllMessages['customMessages'].append(thisMsg)
	#
	def formatStates(self, sensorType, key, value): #string formating accordingly to type of data. May support units regarding timezone in the future...
		if (sensorType == 'Meter' and key == 'totalValue'): return str(value)+'kWh'
		if (sensorType == 'Meter' and key == 'currentValue'): return str(value)+'W'
		if (sensorType == 'Meter' and key == 'voltage'): return str(value)+'V'

		if key == 'sinceTime':
			ts = str(value)[:-3]
			date = strftime("%d %b %Y %H:%M", gmtime(float(ts)))
			return date

		if (sensorType == 'LastActivity' and key == 'lastActivityTime'):
			if value == -1: return 'Never'
			ts = str(value)[:-3]
			date = strftime("%d %b %Y %H:%M", gmtime(float(ts)))
			return date

		return value
	#

	#______________________calling functions
	def request(self, method, host, path, jsonString=None, postinfo=None): #standard function handling all get/post request with curl | return string
		if self._reqHdl == None:
			self._reqHdl = urllib2.build_opener(urllib2.HTTPCookieProcessor(self.cookieJar))
			self._reqHdl.addheaders = [('User-agent', 'Mozilla/5.0 (Windows NT 6.1; Win64; x64; rv:51.0) Gecko/20100101 Firefox/51.0')]

		url = host+'/'+path

		if method == 'GET':
			answer = self._reqHdl.open(url, timeout = 1)

		if jsonString != None:
			jsonString = jsonString.replace('"jsonrpc":"2.0",', '"jsonrpc":"2.0", "id":'+str(self._POSTid)+',')
			self._POSTid += 1
			answer = self._reqHdl.open(url, jsonString, timeout = 3)

		if postinfo != None:
			data = urllib.urlencode(postinfo)
			answer = self._reqHdl.open(url, data, timeout = 3)

		self.cookieJar.save(self._cookFile, ignore_discard=True)
		if jsonString != None: return json.load(answer)
		return answer
	#
	def fetchItems(self, UIDSarray): #get infos from central for array of device, sensor, timer etc | return array
		devicesJson = json.dumps(UIDSarray)
		jsonString = '{"jsonrpc":"2.0","method":"FIM/getFunctionalItems","params":['+devicesJson+',0]}'
		answer = self.request('POST', self._dhcUrl, '/remote/json-rpc', jsonString)
		return answer
	#
	def invokeOperation(self, sensor, operation, value=''): #sensor string, authorized operation string | return array
		value = '['+value+']'
		jsonString = '{"jsonrpc":"2.0", "method":"FIM/invokeOperation", "params":["'+sensor+'","'+operation+'",'+value+']}'
		data = self.request('POST', self._dhcUrl, '/remote/json-rpc', jsonString)
		return data
	#
	def sendCommand(self, jsonString): #directly send json to central. Only works when all required authorisations are set | return array
		data = self.request('POST', self._dhcUrl, '/remote/json-rpc', jsonString)
		return data
	#

	#functions authorization=============================================
	def __init__(self, login='', password='', gateIdx=0):
		self._version = 1.0
		self.error = None
		self._userInfos = None
		self._centralInfos = None
		self._gateway = None
		self._gateIdx = gateIdx;
		self._uuid = None
		self._token = None
		self._wasCookiesLoaded = False
		self._cookFile = ''
		self.cookieJar = LWPCookieJar()

		#central stuff stuff(!):
		self._AllDevices = []
		self._AllZones = []
		self._AllGroups = []
		self._AllRules = []
		self._AllTimers = []
		self._AllScenes = []
		self._AllMessages = {}
		self._Weather = None

		#authentication:
		self._login = login
		self._password = password
		self._authUrl = 'https://www.mydevolo.com'
		self._dhcUrl =  'https://homecontrol.mydevolo.com'
		self._lang = '/en'
		self._POSTid = 0
		self._reqHdl = None

		#types stuff:
		"""
		Devolo Home Control Portal (web interface or app interface to access HCB Home Control Box)
			-> HCB
				->Device
					- sensor (type, data), handle operations ?
					- sensor (type, data), handle operations ?
				->Zone
					- deviceUIDs
				->Group
					- deviceUIDs
				etc
		"""

		"""
		UNTESTED:
			devolo.model.Dimmer / Dimmer
			devolo.model.Relay / Relay
			HueBulbSwitch / HueBulbSwitch
			HueBulbColor / HueBulbColor
		"""
		self._MeteringDevices     = ['devolo.model.Wall:Plug:Switch:and:Meter', 'devolo.model.Shutter', 'devolo.model.Dimmer', 'devolo.model.Relay'] #devices for consumption loging !
		#Sensors Operations:
		self._SensorsOnOff        = ['BinarySwitch', 'BinarySensor', 'HueBulbSwitch', 'Relay'] #supported sensor types for 'turnOn'/'turnOff' operation
		self._SensorsSendValue    = ['MultiLevelSwitch', 'SirenMultiLevelSwitch', 'Blinds', 'Dimmer'] #supported sensor types for 'sendValue' operation
		self._SensorsPressKey     = ['RemoteControl'] #supported sensor types for 'pressKey' operation
		self._SensorsSendHSB      = ['HueBulbColor'] #supported sensor types for 'sendHSB' operation
		self._SensorsSend         = ['HttpRequest'] #supported sensor types for 'send' operation
		self._SensorsNoValues     = ['HttpRequest'] #virtual device sensor
		#Sensors Values:
		self._SensorValuesByType  = {
									'Meter'                     :['sensorType', 'currentValue', 'totalValue', 'sinceTime'],
									'BinarySwitch'              :['switchType', 'state', 'targetState'],
									'Relay'                     :['switchType', 'state', 'targetState'],
									'MildewSensor'              :['sensorType', 'state'],
									'BinarySensor'              :['sensorType', 'state'],
									'SirenBinarySensor'         :['sensorType', 'state'],
									'MultiLevelSensor'          :['sensorType', 'value'],
									'HumidityBarZone'           :['sensorType', 'value'],
									'DewpointSensor'            :['sensorType', 'value'],
									'HumidityBarValue'          :['sensorType', 'value'],
									'SirenMultiLevelSensor'     :['sensorType', 'value'],
									'SirenMultiLevelSwitch'     :['switchType', 'value', 'targetValue', 'min', 'max'],
									'MultiLevelSwitch'          :['switchType', 'value', 'targetValue', 'min', 'max'],
									'RemoteControl'             :['keyCount', 'keyPressed'],
									'Blinds'                    :['switchType', 'value', 'targetValue', 'min', 'max'],
									'Dimmer'                    :['switchType', 'value', 'targetValue', 'min', 'max'],
									'HueBulbSwitch'             :['sensorType', 'state'],
									'HueBulbColor'              :['switchType', 'hue', 'sat', 'bri', 'targetHsb'],
									'LastActivity'              :['lastActivityTime'],
									'WarningBinaryFI'           :['sensorType', 'state', 'type'],
									'VoltageMultiLevelSensor'   :['sensorType', 'value' ],
									}

		if self.connect() == True:
			self.getDevices()
	#

	def connect(self):
		if self.cookies_are_hot(): return True
		#No young cookie file, full authentication:

		#___________get CSRF_______________________________________________________
		answer = self.request('GET', self._authUrl, self._lang)
		html = answer.read()
		lines = html.split('\n')
		csrf = None
		for line in lines:
			if '<input type="hidden" name="_csrf"' in line:
				csrf = line.split('value=')[1]
				csrf = csrf.replace('"', '')
				csrf = csrf.replace('/>', '')
				break

		if csrf == None:
			self.error = "Couldn't find Devolo CSRF."
			return False

		#___________post login/password____________________________________________
		postinfo = {'_csrf': csrf, 'username': self._login, 'password': self._password}
		answer = self.request('POST', self._authUrl, self._lang, None, postinfo)

		#___________get gateway____________________________________________________
		answer = self.request('GET', self._authUrl, self._lang+'/hc/gateways/status')
		try:
			jsonAnswer = json.load(answer)
			gateway = jsonAnswer['data'][self._gateIdx]['id']
			self._gateway = gateway
		except:
			self.error = "Couldn't find Devolo gateway."
			return False

		#___________get open Gateway_______________________________________________
		answer = self.request('GET', self._authUrl, self._lang+'/hc/gateways/'+gateway+'/open')

		return True
	#

	def cookies_are_hot(self):
		if os.access('/', os.W_OK):
			APIfolder = os.path.dirname(os.path.realpath(__file__))
			self._cookFile = APIfolder+'/pyDHC_cookies.txt'
		else:
			return False

		try:
			if os.path.isfile(self._cookFile):
				self.cookieJar.load(self._cookFile, ignore_discard=True)
				answer = self.resetSessionTimeout()
				if not 'error' in answer:
					self._wasCookiesLoaded = True
					return True
				else:
					self._reqHdl = None
					self._wasCookiesLoaded = False
					os.remove(self._cookFile)
					return False
		except Exception as e:
			self.error = e
			self._reqHdl = None
			self._wasCookiesLoaded = False
			os.remove(self._cookFile)

		return False
	#
#pyDHC]

def main():
	pass

if __name__ == "__main__":
   main()
