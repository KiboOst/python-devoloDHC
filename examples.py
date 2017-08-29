#!/usr/bin/python
# -*- coding: utf-8 -*-


"""
example file for different python-devoloDHC use cases

https://github.com/KiboOst/python-devoloDHC

"""

#start API and connect to your account:
import sys
sys.path.append(r'C:\path\to\api')
from pyDHC import pyDHC

DHC = pyDHC(DevoloLogin, DevoloPass)
if DHC.error: print DHC.error


#function to toggle the state or a rule:
def toggleRule(ruleName):
    isActive = DHC.isRuleActive(ruleName)['result']

    if isActive=='inactive':
        DHC.turnRuleOnOff(ruleName, 1)
    else:
        DHC.turnRuleOnOff(ruleName, 0)
#then simply call toggleRule('myRule')!



#Turn a light (wall plug) on:
DHC.turnDeviceOnOff('myLight', 1)

#Check if a device is on:
state = DHC.isDeviceOn('My Wall Plug')['result']

#Start a scene:
DHC.startScene('We go out')


