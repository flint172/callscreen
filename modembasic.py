import serial
import time
import threading
import atexit
import sys
import re
import wave
from datetime import datetime
import os
import fcntl
import subprocess

PORT = "/dev/ttyACM0"
RINGS_BEFORE_AUTO_ANSWER = 2 #Must be greater than 1
MODEM_RESPONSE_READ_TIMEOUT = 120  #Time in Seconds (Default 120 Seconds)
MODEM_NAME = 'U.S. Robotics'    # Modem Manufacturer, For Ex: 'U.S. Robotics' if the 'lsusb' cmd output is similar to "Bus 001 Device 004: ID 0baf:0303 U.S. Robotics"


# Record Voice Mail Variables
REC_VM_MAX_DURATION = 120  # Time in Seconds

# Used in global event listener
disable_modem_event_listener = True

# Global Modem Object
analog_modem = serial.Serial()

audio_file_name = ''

#=================================================================
# Set COM Port settings
#=================================================================
def set_COM_port_settings(com_port):
    analog_modem.port = com_port
    analog_modem.baudrate = 57600 #9600 #115200
    analog_modem.bytesize = serial.EIGHTBITS #number of bits per bytes
    analog_modem.parity = serial.PARITY_NONE #set parity check: no parity
    analog_modem.stopbits = serial.STOPBITS_ONE #number of stop bits
    analog_modem.timeout = 1          #non-block read
    analog_modem.xonxoff = False     #disable software flow control
    analog_modem.rtscts = False     #disable hardware (RTS/CTS) flow control
    analog_modem.dsrdtr = False      #disable hardware (DSR/DTR) flow control
    analog_modem.writeTimeout = 3     #timeout for write
#=================================================================

def exec_AT_cmd(modem_AT_cmd, expected_response="OK"):
    print("Command: " + modem_AT_cmd)
    global disable_modem_event_listener
    disable_modem_event_listener = True
    try:
        analog_modem.write((modem_AT_cmd + "\r").encode())
        execution_status = read_AT_cmd_response(expected_response)
        disable_modem_event_listener = False
        return execution_status
    except:
        print("there")
        disable_modem_event_listener = False
        print("Error: Failed to execute the command")
        return False
        
def read_AT_cmd_response(expected_response="OK"):
    start_time = datetime.now()
    try:
        while 1:
            modem_response = analog_modem.readline()
            print(modem_response)
            if expected_response == modem_response.decode().strip(' \t\n\r' + chr(16)):
                return True
            elif "ERROR" in modem_response.decode().strip(' \t\n\r' + chr(16)):
                return False
            elif (datetime.now()-start_time).seconds > MODEM_RESPONSE_READ_TIMEOUT:
                return False
    except Exception as e:
        print(e)
        print("Error in read_modem_response function...")
        return False
 
def init_modem_settings():
    print(PORT) 
    set_COM_port_settings(PORT) 
    analog_modem.open()  
    print("Port open!")
    try:
        analog_modem.flushInput()
        print("Flushed input")
        analog_modem.flushOutput()
        print("Flushed output")
        if not exec_AT_cmd("AT"):
            print("Error: Unable to access the Modem")
        if not exec_AT_cmd("ATZ3"):
            print("Error: Unable reset to factory default")
        if not exec_AT_cmd("ATV1"):
            print("Error: Unable set response in verbose form")	
        if not exec_AT_cmd("ATE1"):
            print("Error: Failed to enable Command Echo Mode")
        if not exec_AT_cmd("AT+VCID=1"):
            print("Error: Failed to enable formatted caller report.")
        analog_modem.flushInput()
        analog_modem.flushOutput()
    except:
        print ("Error: unable to Initialize the Modem")
        sys.exit()


def close_modem_port():
    try:
        exec_AT_cmd("ATH")
    except:
        pass
    try:
        if analog_modem.isOpen():
            analog_modem.close()
            print ("Serial Port closed...")
    except:
        print("Error: Unable to close the Serial Port.")
        sys.exit()
        
        
def read_data():  
    global disable_modem_event_listener
    ring_data = ""
    while 1:
            if not disable_modem_event_listener:
                modem_data = analog_modem.readline()
                if modem_data != "":
                    print(modem_data)
                
    
init_modem_settings()

atexit.register(close_modem_port)

read_data()