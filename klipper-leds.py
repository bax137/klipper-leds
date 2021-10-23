DEBUG = False
SERIAL = 0
WIFI = 1
##################################################################################
######                      BEGINING OF THE SETTINGS                        ###### 
##################################################################################

# link mode = SERIAL or WIFI
LINK_MODE = SERIAL

### ip and port of the printer
### 7125 is the default port of moonraker
PRINTER_IP='192.168.1.63'
PRINTER_PORT=7125

### ip and port of wled for WIFI Llink
### 21324 is the default port of wled
WLED_IP='192.168.1.131'
WLED_PORT=21324

### for SERIAL link
WLED_SERIAL='/dev/serial/by-id/usb-Silicon_Labs_CP2102_USB_to_UART_Bridge_Controller_0001-if00-port0'

### led strip configuration
### number of leds on the strip
NB_LEDS=84

### area of heater bed temperature indicator (position of the leds on the strip)
HEATER_BED_BEGIN=1
HEATER_BED_END=9
### area of heater bed indicator (position of the leds on the strip)
EXTRUDER_BEGIN=13
EXTRUDER_END=21
### area of filament (position of the leds on the strip)
FILAMENT_SENSOR_BEGIN=10
FILAMENT_SENSOR_END=12

### definition of the colors
RED = [255,0,0]
RED_DARK = [20,0,0]
ORANGE = [255,70,00]
BLUE = [0,0,255]
BLUE_DARK = [0,5,30]
GREEN = [0,255,0]
PINK = [45,11,48]
WHITE = [255,255,255]
GREEN_YELLOW = [120,200,0]
YELLOW = [255,255,0]

### defitinion of the colors on the indicators
### color when the printer is not reachable (printer off or klipper/moonraker not yet started)
BACK_COLOR_OFF=BLUE_DARK
### color when the printer is ON and not print is in progress
BACK_COLOR_PRINT_OFF=PINK
### color when the printer is ON and a print is in progress
BACK_COLOR_PRINT_ON=WHITE
### color when the printer is ON and the print is complete
BACK_COLOR_PRINT_COMPLETE1=GREEN
BACK_COLOR_PRINT_COMPLETE2=BACK_COLOR_PRINT_OFF
### duration in seconds for a complete blink for print complete
COMPLETE_BLINK = 1
### color for cold temperature
COLD_COLOR=BLUE
### color for hot temperature
HOT_COLOR=RED
### color of the background of temperature indicator when heating is in progress
TO_HOT_COLOR=ORANGE
### color of the background of temperature indicator when cooling is in progress
TO_COLD_COLOR=ORANGE
### color when filament is loaded
FILAMENT_SENSOR_OK=GREEN
### colors when filament is not loaded
FILAMENT_SENSOR_KO1=RED
FILAMENT_SENSOR_KO2=RED_DARK

### animations configuration
### speed of filament indicator animation
FILAMENT_ANIMATION_SPEED=0.3
### speed of temperature indicator animation
TEMPERATURE_ANIMATION_SPEED=0.15

### temperature thresholds
### definition of cold temperature for heater bed
HEATER_BED_TEMP_COLD=45
### defitinion of cold temperature for extruder
EXTRUDER_TEMP_COLD=50
### percentage of temperature target for considering that temperature target is reached
PERCENT_TARGET_TEMP=0.99

### EXPERT SETTINGS
### timeout for WLED udp communication (in seconds)
### after this time limit, wled stops the synchronization until a new udp data in received
WLED_UDP_WAIT=5
WLED_UDP_WAIT_PERCENT=0.8
SERIAL_TIMEOUT = 0

### wait time for the each step of the update leds threads
TIME_SLEEP_WLED=0.01
TIME_SLEEP_SERIAL=0.05

##################################################################################
######                         END OF THE SETTINGS                          ###### 
##################################################################################
SERIAL_BAUDRATE=115200
WLED_UDP_MODE_WARLS = 1

COLD = 0
HOT = 1
TO_HOT = 2
TO_COLD = 3

PRINTER_OFF = 0
PRINT_ON = 1
PRINT_OFF = 2
PRINT_COMPLETE = 3

STATUS_NONE = -1
STATUS_INIT = -2
STATUS_FALSE = -3
STATUS_TRUE = -4

TO_RIGHT = 1
TO_LEFT = 2

hiInt = (NB_LEDS << 8) & int.from_bytes(b'\xFF', byteorder="big")
hi = hiInt.to_bytes(2, byteorder="big")

loInt = NB_LEDS & int.from_bytes(b'\xFF', byteorder="big")
lo = loInt.to_bytes(2, byteorder="big")
checksumInt = hiInt ^ loInt ^ int.from_bytes(b'\x55', byteorder="big")

checksum = checksumInt.to_bytes(2, byteorder="big")

import json, socket, time, websocket, serial, threading, random
import datetime as dt
import _thread as thread

from requests.models import parse_header_links

def on_message(ws, message):
    #print(message)

    json_message = json.loads(message)
    if 'result' in json_message:
        if 'status' in json_message['result']:
            print("subscription ok")
            #réponse à la subscription
            status = json_message['result']['status']
            currentParams.heater_bed_target = status['heater_bed']['target']
            currentParams.heater_bed_temp = status['heater_bed']['temperature']
            currentParams.extruder_target = status['extruder']['target']
            currentParams.extruder_temp = status['extruder']['temperature']
            currentParams.filament_detected = status['filament_switch_sensor runout_sensor']['filament_detected']
            currentParams.printer_state = status['print_stats']['state']
            currentParams.klipper_ready = True
        elif 'software_version' in json_message['result']:
            #réponse au printer.info pour vérifier au démarrage si l'imprimante est prête
            if json_message['result']['state'] == "ready":
                currentParams.printer_ready = True
    elif 'method' in json_message:
        method=json_message['method']
        if method == 'notify_klippy_disconnected':
            print("klippy disconnected")
            currentParams.klipper_ready = False
        if method == 'notify_klippy_ready':
            print("klippy ready")
            moonrakerSubscribe()
        if method == 'notify_status_update':
            #currentParams.klipper_ready = True
            params=json_message['params'][0]
            if 'heater_bed' in params:
                if 'target' in params['heater_bed']:
                    currentParams.heater_bed_target=params['heater_bed']['target']
                if 'temperature' in params['heater_bed']:
                    currentParams.heater_bed_temp=params['heater_bed']['temperature']
            if 'extruder' in params:
                if 'target' in params['extruder']:
                    currentParams.extruder_target=params['extruder']['target']
                if 'temperature' in params['extruder']:
                    currentParams.extruder_temp=params['extruder']['temperature']
            if 'filament_switch_sensor runout_sensor' in params:
                currentParams.filament_detected=params['filament_switch_sensor runout_sensor']['filament_detected']
            if 'print_stats' in params:
                if 'state' in params['print_stats']:
                    currentParams.printer_state=params['print_stats']['state']

    if currentParams.klipper_ready == False:
        UpdateLedsParams.filament_leds_status = STATUS_NONE
        UpdateLedsParams.extruder_leds_status = STATUS_NONE
        UpdateLedsParams.heater_leds_status = STATUS_NONE
        UpdateLedsParams.others_leds_status = STATUS_NONE
    else:
        if currentParams.filament_detected != None:
            if currentParams.filament_detected == False:
                UpdateLedsParams.filament_leds_status = STATUS_FALSE
            elif currentParams.filament_detected == True:
                UpdateLedsParams.filament_leds_status = STATUS_TRUE
            else:
                UpdateLedsParams.filament_leds_status = STATUS_NONE

        if currentParams.heater_bed_target == 0:
            if currentParams.heater_bed_temp < HEATER_BED_TEMP_COLD:
                UpdateLedsParams.heater_leds_status = COLD
                UpdateLedsParams.heater_progress = 100
            else:
                UpdateLedsParams.heater_leds_status = TO_COLD
                UpdateLedsParams.heater_progress = HEATER_BED_TEMP_COLD / currentParams.heater_bed_temp
        else:
            if currentParams.heater_bed_temp < currentParams.heater_bed_target * PERCENT_TARGET_TEMP:
                UpdateLedsParams.heater_leds_status = TO_HOT
                UpdateLedsParams.heater_progress = currentParams.heater_bed_temp / currentParams.heater_bed_target
            elif currentParams.heater_bed_temp > currentParams.heater_bed_target * (1+PERCENT_TARGET_TEMP):
                UpdateLedsParams.heater_leds_status = TO_HOT
                UpdateLedsParams.heater_progress = currentParams.heater_bed_target / currentParams.heater_bed_temp
            else:
                UpdateLedsParams.heater_leds_status = HOT
                UpdateLedsParams.heater_progress = 100

        if currentParams.extruder_target == 0:
            if currentParams.extruder_temp < EXTRUDER_TEMP_COLD:
                UpdateLedsParams.extruder_leds_status = COLD
                UpdateLedsParams.extruder_progress = 100
            else:
                UpdateLedsParams.extruder_leds_status = TO_COLD
                UpdateLedsParams.extruder_progress = EXTRUDER_TEMP_COLD / currentParams.extruder_temp
        else:
            if currentParams.extruder_temp < currentParams.extruder_target * PERCENT_TARGET_TEMP:
                UpdateLedsParams.extruder_leds_status = TO_HOT
                UpdateLedsParams.extruder_progress = currentParams.extruder_temp / currentParams.extruder_target
            elif currentParams.extruder_temp > currentParams.extruder_target * (1+PERCENT_TARGET_TEMP):
                UpdateLedsParams.extruder_leds_status = TO_HOT
                UpdateLedsParams.extruder_progress = currentParams.extruder_target / currentParams.extruder_temp
            else:
                UpdateLedsParams.extruder_leds_status = HOT
                UpdateLedsParams.extruder_progress = 100

        if currentParams.printer_state == 'standby' or currentParams.printer_state == None or (currentParams.extruder_target == 0 and currentParams.heater_bed_target == 0):
            UpdateLedsParams.others_leds_status = PRINT_OFF
        elif currentParams.printer_state == 'complete':
            UpdateLedsParams.others_leds_status = PRINT_COMPLETE
        else:
            UpdateLedsParams.others_leds_status = PRINT_ON

def on_error(ws, error):
    print(error)

def on_close(ws, close_status_code, close_msg):
    print("### closed ###")
    UpdateLedsParams.extruder_leds_status = STATUS_NONE
    UpdateLedsParams.heater_leds_status = STATUS_NONE
    UpdateLedsParams.filament_leds_status = STATUS_NONE
    UpdateLedsParams.others_leds_status = STATUS_NONE
    currentParams.klipper_ready = False
    currentParams.printer_ready = False

def on_open(ws):
    def run(*args):
        print("### open ###")
        moonrakerSubscribe()

    thread.start_new_thread(run, ())

class CurrentParams():
    def __init__(self):
        super(CurrentParams, self).__init__()
        self.klipper_ready = False
        self.printer_ready = False
        self.heater_bed_temp = None
        self.heater_bed_target = None
        self.extruder_temp = None
        self.extruder_target = None
        self.filament_detected = None
        self.printer_state = None
        self.now = dt.datetime.now()

class UpdateLedsParams():
    def __init__(self,extruder_begin,extruder_end,extruder_direction,heater_begin,heater_end,heater_direction):
        super(UpdateLedsParams, self).__init__()
        self.filament_leds_status = STATUS_NONE
        self.others_leds_status = STATUS_NONE

        self.extruder_leds_status = STATUS_NONE
        self.extruder_begin = extruder_begin
        self.extruder_end = extruder_end
        self.extruder_progress = 100
        self.extruder_end_pos = extruder_begin - 1
        self.extruder_direction = extruder_direction

        self.heater_leds_status = STATUS_NONE
        self.heater_begin = heater_begin
        self.heater_end = heater_end
        self.heater_progress = 100
        self.heater_end_pos = heater_begin - 1
        self.heater_direction = heater_direction

def UpdateLeds():
    if LINK_MODE == WIFI:
        clientSock = socket.socket (socket.AF_INET, socket.SOCK_DGRAM)
        TIME_SLEEP = TIME_SLEEP_WLED
        UPDATE_TIMEOUT = WLED_UDP_WAIT * WLED_UDP_WAIT_PERCENT
    else:
        ser = serial.Serial(WLED_SERIAL,baudrate=SERIAL_BAUDRATE)
        TIME_SLEEP = TIME_SLEEP_SERIAL
        UPDATE_TIMEOUT = SERIAL_TIMEOUT

    #filament
    filament_current_pos = FILAMENT_SENSOR_BEGIN
    filament_direction = 1
    filament_current_status = STATUS_INIT
    filament_now_animation = dt.datetime.now()

    #extruder
    extruder_current_status = STATUS_INIT
    extruder_now_animation = dt.datetime.now()
    extruder_direction = 1

    #heater
    heater_current_status = STATUS_INIT
    heater_now_animation = dt.datetime.now()
    heater_direction = 1

    #others
    printer_color = BACK_COLOR_OFF
    others_current_status = STATUS_INIT
    others_now_blink = dt.datetime.now()
    others_direction = 1

    vLedsMatrix = [[0 for x in range(3)] for y in range(NB_LEDS+1)] 
    while True:
        if LINK_MODE == SERIAL:
            v = [WLED_UDP_MODE_WARLS,WLED_UDP_WAIT]
        #update filament leds
        now2 = dt.datetime.now()
        filament_now_animation_update = False
        if UpdateLedsParams.filament_leds_status != filament_current_status or UpdateLedsParams.filament_leds_status == STATUS_FALSE or (now2-currentParams.now).total_seconds() > UPDATE_TIMEOUT:
            filament_current_status = UpdateLedsParams.filament_leds_status
            if UpdateLedsParams.filament_leds_status == STATUS_NONE:
                filament_sensor_color = BACK_COLOR_OFF

            if UpdateLedsParams.filament_leds_status == STATUS_TRUE:
                filament_sensor_color = FILAMENT_SENSOR_OK
            else:
                if (now2-filament_now_animation).total_seconds() > FILAMENT_ANIMATION_SPEED:
                    filament_current_pos += filament_direction
                    if filament_current_pos == FILAMENT_SENSOR_END:
                        filament_direction = -1
                    if filament_current_pos == FILAMENT_SENSOR_BEGIN:
                        filament_direction = 1
                    filament_now_animation_update = True
            if LINK_MODE == WIFI:
                v = [WLED_UDP_MODE_WARLS,WLED_UDP_WAIT]
            
            for i in range(FILAMENT_SENSOR_BEGIN,FILAMENT_SENSOR_END+1):
                if LINK_MODE == WIFI:
                    v.extend([i])
                if UpdateLedsParams.filament_leds_status == STATUS_TRUE or UpdateLedsParams.filament_leds_status == STATUS_NONE:
                    color = filament_sensor_color
                elif i == filament_current_pos:
                    color = FILAMENT_SENSOR_KO1
                else:
                    color = FILAMENT_SENSOR_KO2
                if LINK_MODE == WIFI:
                    v.extend(color)
                else:
                    vLedsMatrix[i] = color

            filament_current_status = UpdateLedsParams.filament_leds_status
            
            if LINK_MODE == WIFI:
                Message = bytearray(v)
                sendByWifi(clientSock,Message)

            if filament_now_animation_update:
                filament_now_animation = dt.datetime.now()

        #update extruder leds
        now2 = dt.datetime.now()
        if (UpdateLedsParams.extruder_leds_status == TO_HOT or UpdateLedsParams.extruder_leds_status == TO_COLD) or UpdateLedsParams.extruder_leds_status != extruder_current_status or (now2-currentParams.now).total_seconds() > UPDATE_TIMEOUT:
            extruder_current_status = UpdateLedsParams.extruder_leds_status
            if UpdateLedsParams.extruder_leds_status == STATUS_NONE:
                color = BACK_COLOR_OFF

            if UpdateLedsParams.extruder_leds_status == COLD:
                color = COLD_COLOR
            elif UpdateLedsParams.extruder_leds_status == HOT:
                color = HOT_COLOR
            if LINK_MODE == WIFI:
                v = [WLED_UDP_MODE_WARLS,WLED_UDP_WAIT]

            for i in range(UpdateLedsParams.extruder_begin,UpdateLedsParams.extruder_end+1):
                led_index = i
                if UpdateLedsParams.extruder_leds_status == TO_HOT or UpdateLedsParams.extruder_leds_status == TO_COLD:
                    extruder_current_status = STATUS_INIT
                    if UpdateLedsParams.extruder_direction == TO_LEFT:
                        led_index = UpdateLedsParams.extruder_end - i + UpdateLedsParams.extruder_begin
                    now2 = dt.datetime.now()
                    if (now2-extruder_now_animation).total_seconds() > TEMPERATURE_ANIMATION_SPEED:
                        extruder_now_animation = dt.datetime.now()
                        UpdateLedsParams.extruder_end_pos += extruder_direction
                        if UpdateLedsParams.extruder_end_pos < UpdateLedsParams.extruder_begin:
                            extruder_direction = 1
                            UpdateLedsParams.extruder_end_pos = UpdateLedsParams.extruder_begin + 1
                        if UpdateLedsParams.extruder_end_pos > UpdateLedsParams.extruder_begin + (float(UpdateLedsParams.extruder_progress) * float(UpdateLedsParams.extruder_end + 1 - UpdateLedsParams.extruder_begin)):
                            extruder_direction = -1

                    if i < UpdateLedsParams.extruder_end_pos:
                        if UpdateLedsParams.extruder_leds_status == TO_HOT:
                            color = HOT_COLOR
                        if UpdateLedsParams.extruder_leds_status == TO_COLD:
                            color = COLD_COLOR
                    else:
                        if UpdateLedsParams.extruder_leds_status == TO_HOT:
                            color = TO_HOT_COLOR
                        if UpdateLedsParams.extruder_leds_status == TO_COLD:
                            color = TO_COLD_COLOR
                if LINK_MODE == WIFI:            
                    v.extend([led_index])
                    v.extend(color)
                else:
                    vLedsMatrix[led_index] = color

            if LINK_MODE == WIFI:
                Message = bytearray(v)
                sendByWifi(clientSock,Message)

        #update heater leds
        now2 = dt.datetime.now()
        if (UpdateLedsParams.heater_leds_status == TO_HOT or UpdateLedsParams.heater_leds_status == TO_COLD) or UpdateLedsParams.heater_leds_status != heater_current_status or (now2-currentParams.now).total_seconds() > UPDATE_TIMEOUT:
            heater_current_status = UpdateLedsParams.heater_leds_status
            if UpdateLedsParams.heater_leds_status == STATUS_NONE:
                color = BACK_COLOR_OFF

            if UpdateLedsParams.heater_leds_status == COLD:
                color = COLD_COLOR
            elif UpdateLedsParams.heater_leds_status == HOT:
                color = HOT_COLOR
            if LINK_MODE == WIFI:
                v = [WLED_UDP_MODE_WARLS,WLED_UDP_WAIT]

            for i in range(UpdateLedsParams.heater_begin,UpdateLedsParams.heater_end+1):
                led_index = i
                if UpdateLedsParams.heater_leds_status == TO_HOT or UpdateLedsParams.heater_leds_status == TO_COLD:
                    heater_current_status = STATUS_INIT
                    if UpdateLedsParams.heater_direction == TO_LEFT:
                        led_index = UpdateLedsParams.heater_end - i + UpdateLedsParams.heater_begin
                    now2 = dt.datetime.now()
                    if (now2-heater_now_animation).total_seconds() > TEMPERATURE_ANIMATION_SPEED:
                        heater_now_animation = dt.datetime.now()
                        UpdateLedsParams.heater_end_pos += heater_direction
                        if UpdateLedsParams.heater_end_pos < UpdateLedsParams.heater_begin:
                            heater_direction = 1
                            UpdateLedsParams.heater_end_pos = UpdateLedsParams.heater_begin + 1
                        if UpdateLedsParams.heater_end_pos > UpdateLedsParams.heater_begin + (float(UpdateLedsParams.heater_progress) * float(UpdateLedsParams.heater_end + 1 - UpdateLedsParams.heater_begin)):
                            heater_direction = -1

                    if i < UpdateLedsParams.heater_end_pos:
                        if UpdateLedsParams.heater_leds_status == TO_HOT:
                            color = HOT_COLOR
                        if UpdateLedsParams.heater_leds_status == TO_COLD:
                            color = COLD_COLOR
                    else:
                        if UpdateLedsParams.heater_leds_status == TO_HOT:
                            color = TO_HOT_COLOR
                        if UpdateLedsParams.heater_leds_status == TO_COLD:
                            color = TO_COLD_COLOR
                if LINK_MODE == WIFI:
                    v.extend([led_index])
                    v.extend(color)
                else:
                    vLedsMatrix[led_index] = color

            if LINK_MODE == WIFI:
                Message = bytearray(v)
                sendByWifi(clientSock,Message)

        #update other leds
        now2 = dt.datetime.now()
        if UpdateLedsParams.others_leds_status != others_current_status or UpdateLedsParams.others_leds_status == PRINT_COMPLETE or (now2-currentParams.now).total_seconds() > UPDATE_TIMEOUT:
            others_current_status = UpdateLedsParams.others_leds_status            
            if UpdateLedsParams.others_leds_status == STATUS_NONE:
                printer_color = BACK_COLOR_OFF
            elif UpdateLedsParams.others_leds_status == PRINTER_OFF:
                printer_color = BACK_COLOR_OFF
            elif UpdateLedsParams.others_leds_status == PRINT_OFF:
                printer_color = BACK_COLOR_PRINT_OFF
            elif UpdateLedsParams.others_leds_status == PRINT_ON:
                printer_color = BACK_COLOR_PRINT_ON
            elif UpdateLedsParams.others_leds_status == PRINT_COMPLETE:
                if (now2-others_now_blink).total_seconds() > COMPLETE_BLINK:
                    others_now_blink = dt.datetime.now()
                    others_direction *= -1
                if others_direction == 1:
                    r = BACK_COLOR_PRINT_COMPLETE1[0] + (BACK_COLOR_PRINT_COMPLETE2[0]-BACK_COLOR_PRINT_COMPLETE1[0]) * (now2-others_now_blink).total_seconds() / COMPLETE_BLINK
                    g = BACK_COLOR_PRINT_COMPLETE1[1] + (BACK_COLOR_PRINT_COMPLETE2[1]-BACK_COLOR_PRINT_COMPLETE1[1]) * (now2-others_now_blink).total_seconds() / COMPLETE_BLINK
                    b = BACK_COLOR_PRINT_COMPLETE1[2] + (BACK_COLOR_PRINT_COMPLETE2[2]-BACK_COLOR_PRINT_COMPLETE1[2]) * (now2-others_now_blink).total_seconds() / COMPLETE_BLINK
                else:
                    r = BACK_COLOR_PRINT_COMPLETE2[0] + (BACK_COLOR_PRINT_COMPLETE1[0]-BACK_COLOR_PRINT_COMPLETE2[0]) * (now2-others_now_blink).total_seconds() / COMPLETE_BLINK
                    g = BACK_COLOR_PRINT_COMPLETE2[1] + (BACK_COLOR_PRINT_COMPLETE1[1]-BACK_COLOR_PRINT_COMPLETE2[1]) * (now2-others_now_blink).total_seconds() / COMPLETE_BLINK
                    b = BACK_COLOR_PRINT_COMPLETE2[2] + (BACK_COLOR_PRINT_COMPLETE1[2]-BACK_COLOR_PRINT_COMPLETE2[2]) * (now2-others_now_blink).total_seconds() / COMPLETE_BLINK
                if r < 0: r = 0
                if r > 255: r = 255
                if g < 0: g = 0
                if g > 255: g = 255
                if b < 0: b = 0
                if b > 255: b = 255
                printer_color = [round(r),round(g),round(b)]
            if LINK_MODE == WIFI:
                v = [WLED_UDP_MODE_WARLS,WLED_UDP_WAIT]
            for i in range(1,NB_LEDS+1):
                if (i < EXTRUDER_BEGIN or i > EXTRUDER_END) and (i < HEATER_BED_BEGIN or i > HEATER_BED_END) and (i < FILAMENT_SENSOR_BEGIN or i > FILAMENT_SENSOR_END):
                    if LINK_MODE == WIFI:
                        v.extend([i])
                        v.extend(printer_color)
                    else:
                        vLedsMatrix[i] = printer_color
    
            if LINK_MODE == WIFI:
                Message = bytearray(v)
                sendByWifi(clientSock,Message)
            else:
                v = [int.from_bytes(b'\x41', byteorder="big"),int.from_bytes(b'\x64', byteorder="big"),int.from_bytes(b'\x61', byteorder="big"),hiInt,loInt,checksumInt]
                for j in range(NB_LEDS):
                    v.extend(vLedsMatrix[j])
                Message = bytearray(v)
                #print(str(Message))
                sendBySerial(ser,Message)
        
        time.sleep(TIME_SLEEP)

def sendByWifi(clientSock, Message):
    clientSock.sendto(Message, (WLED_IP, WLED_PORT))
    currentParams.now = dt.datetime.now()

def sendBySerial(ser, Message):
    ser.write(Message)
    currentParams.now = dt.datetime.now()

def moonrakerSubscribe():
    print("moonraker subscription")
    currentParams.klipper_ready = False
    currentParams.printer_ready = False
    text = "Waiting until printer ready"
    while currentParams.printer_ready == False:
        print(text, end = "\r")
        ws.send("""{
                "jsonrpc": "2.0",
                "method": "printer.info",
                "id": 5434
            }""")
        time.sleep(1)
        text += "."
    print("")

    print("Printer is ready / asking subscription")
    ws.send("""{
        "jsonrpc": "2.0",
        "method": "printer.objects.subscribe",
        "params": {
            "objects": {
                "heater_bed": ["target", "temperature"],
                "extruder": ["target", "temperature"],
                "filament_switch_sensor runout_sensor": ["filament_detected"],
                "print_stats": ["state"]
            }
        },
        "id": 5434
    }""")

class MoonrakerWS(threading.Thread):
    def __init__(self,ws):
        super(MoonrakerWS, self).__init__()
        self.ws = ws 

    def run(self):
        while True:
            self.ws.run_forever()

#websocket.enableTrace(True)
ws = websocket.WebSocketApp("ws://"+PRINTER_IP+":"+str(PRINTER_PORT)+"/websocket",
                            on_open=on_open,
                            on_message=on_message,
                            on_error=on_error,
                            on_close=on_close)
moonrakerWS = MoonrakerWS(ws)
moonrakerWS.start()

currentParams = CurrentParams()
UpdateLedsParams = UpdateLedsParams(extruder_begin=EXTRUDER_BEGIN,extruder_end=EXTRUDER_END,extruder_direction=TO_LEFT,heater_begin=HEATER_BED_BEGIN,heater_end=HEATER_BED_END,heater_direction=TO_RIGHT)
UpdateLeds()