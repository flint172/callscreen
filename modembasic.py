import serial
import logging
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
import csv

LOG_LEVEL = logging.INFO
LOG_FILE = "/var/log/callscreen.log"
LOG_FORMAT = "%(asctime)s %(levelname)s %(message)s"
logging.basicConfig(filename=LOG_FILE, format=LOG_FORMAT, level=LOG_LEVEL)

PORT = "/dev/ttyACM0"
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
    analog_modem.timeout = 2          #non-block read
    analog_modem.xonxoff = False     #disable software flow control
    analog_modem.rtscts = False     #disable hardware (RTS/CTS) flow control
    analog_modem.dsrdtr = False      #disable hardware (DSR/DTR) flow control
    analog_modem.writeTimeout = 3     #timeout for write
#=================================================================

def exec_AT_cmd(modem_AT_cmd, expected_response="OK"):
    logging.info("Command: " + modem_AT_cmd)
    global disable_modem_event_listener
    disable_modem_event_listener = True
    try:
        analog_modem.write((modem_AT_cmd + "\r").encode())
        execution_status = read_AT_cmd_response(expected_response)
        disable_modem_event_listener = False
        return execution_status
    except:
        disable_modem_event_listener = False
        logging.error("Error: Failed to execute the command")
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
        logging.error(e)
        logging.error("Error in read_modem_response function...")
        return False
 
def init_modem_settings():
    logging.info(PORT) 
    set_COM_port_settings(PORT) 
    analog_modem.open()  
    logging.info("Port open!")
    try:
        analog_modem.flushInput()
        logging.info("Flushed input")
        analog_modem.flushOutput()
        logging.info("Flushed output")
        if not exec_AT_cmd("AT"):
            logging.error("Error: Unable to access the Modem")
        if not exec_AT_cmd("ATZ3"):
            logging.error("Error: Unable reset to factory default")
        if not exec_AT_cmd("ATV1"):
            logging.error("Error: Unable set response in verbose form")	
        if not exec_AT_cmd("ATE1"):
            logging.error("Error: Failed to enable Command Echo Mode")
        if not exec_AT_cmd("AT+VCID=1"):
            logging.error("Error: Failed to enable formatted caller report.")
        analog_modem.flushInput()
        analog_modem.flushOutput()
    except:
        logging.error("Error: unable to Initialize the Modem")
        sys.exit()


def close_modem_port():
    try:
        exec_AT_cmd("ATH")
    except:
        pass
    try:
        if analog_modem.isOpen():
            analog_modem.close()
            logging.info("Serial Port closed...")
    except:
        logging.error("Error: Unable to close the Serial Port.")
        sys.exit()
        
def readFile(fileName):
        fileObj = open(fileName, "r") #opens the file in read mode
        items = fileObj.read().splitlines() #puts the file into an array
        fileObj.close()
        return items

def pickupAndHangup():
    logging.info("ANSWERING")     
    if not exec_AT_cmd("AT+FCLASS=8","OK"):
        logging.error("Error: Failed to put modem into voice mode.")
    else:
        if not exec_AT_cmd("AT+VSD=128,0","OK"):
            logging.error("Error: Unable to disable silence detection")
        if not exec_AT_cmd("AT+VLS=1", "OK"):
            logging.error("Error: Unable to put modem into TAD mode. Tryied to answer call")
    print("HANGUP")
    if not exec_AT_cmd("ATH","OK"):
        logging.error("Error: Unable to hang-up the call")
    else:
        logging.error("Call Terminated")

def read_data():  
    global disable_modem_event_listener
    ring_data = ""
    while 1:
        modem_data = ""
        blacklist_array = readFile("/home/pi/workspace/callscreen/blacklist_numbers.csv")
        blacklist_names = readFile("/home/pi/workspace/callscreen/blacklist_names.csv")
        #print(blacklist_array)
        if not disable_modem_event_listener:
            modem_data = analog_modem.readline().decode()
        if modem_data != "" and modem_data != b'':
            logging.info("Modem data: " + str(modem_data))
            if ("NAME" in modem_data) or ("DATE" in modem_data) or ("TIME" in modem_data) or ("NMBR" in modem_data):
                if ("NMBR" in modem_data):
                    from_number = (modem_data[5:]).strip()
                    #print(from_number)
                    #print(blacklist_array)
                    if from_number in blacklist_array or from_number.startswith("800"):    
                        pickupAndHangup() 
                        
                if ("NAME" in modem_data):
                    from_name = (modem_data[5:]).strip().upper()
                    for blacklist_name in blacklist_names:
                            if len(blacklist_name) > 1:
                                if blacklist_name.upper() in from_name:
                                    logging.info("Name in blacklist")
                                    pickupAndHangup()
                                if len(from_name) < 3:
                                    logging.info("From name too short")
                                    pickupAndHangup()
                            
    
init_modem_settings()

atexit.register(close_modem_port)

read_data()
