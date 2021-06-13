##################################################################################
######                      BEGINING OF THE SETTINGS                        ###### 
##################################################################################

### ip and port of the printer
### 7125 is the default port of moonraker
PRINTER_IP='192.168.1.63'
PRINTER_PORT=7125

### ip and port of wled
### 21324 is the default port of wled
WLED_IP='192.168.1.131'
WLED_PORT=21324

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
### color for cold temperature
COLD_COLOR=BLUE
### color for hot temperature
HOT_COLOR=RED
### color of the background of temperature indicator when heating is in progress
TOO_HOT_COLOR=COLD_COLOR
### color of the background of temperature indicator when cooling is in progress
TOO_COLD_COLOR=HOT_COLOR
### color when filament is loaded
FILAMENT_SENSOR_OK=GREEN
### colors when filament is not loaded
FILAMENT_SENSOR_KO1=RED
FILAMENT_SENSOR_KO2=RED_DARK

### animations configuration
### speed of filament indicator animation
FILAMENT_ANIMATION_SPEED=0.3
### speed of temperature indicator animation
TEMPERATURE_ANIMATION_SPEED=0.1

### temperature thresholds
### definition of cold temperature for heater bed
HEATER_BED_TEMP_COLD=45
### defitinion of cold temperature for extruder
EXTRUDER_TEMP_COLD=50
### percentage of temperature target for considering that temperature target is reached
PERCENT_TARGET_TEMP=0.97

### EXPERT SETTINGS
### timeout for WLED udp communication (in seconds)
### after this time limit, wled stops the synchronization until a new udp data in received
WLED_UDP_WAIT=2
### wait time for the each step of the update leds threads
TIME_SLEEP=0.005

##################################################################################
######                         END OF THE SETTINGS                          ###### 
##################################################################################
WLED_UDP_MODE_WARLS = 1

COLD = 0
HOT = 1
TOO_HOT = 2
TOO_COLD = 3

PRINTER_OFF = 0
PRINT_ON = 1
PRINT_OFF = 2

STATUS_NONE = -1
STATUS_INIT = -2

TO_RIGHT = 1
TO_LEFT = 2

import json, socket, time, websocket, threading
import datetime as dt
try:
    import thread
except ImportError:
    import _thread as thread

from requests.models import parse_header_links

def on_message(ws, message):
    #print(message)

    json_message = json.loads(message)
    if 'result' in json_message:
        if 'status' in json_message['result']:
            status = json_message['result']['status']
            currentParams.heater_bed_target = status['heater_bed']['target']
            currentParams.heater_bed_temp = status['heater_bed']['temperature']
            currentParams.extruder_target = status['extruder']['target']
            currentParams.extruder_temp = status['extruder']['temperature']
            currentParams.filament_detected = status['filament_switch_sensor runout_sensor']['filament_detected']
            updateLedsOther.leds_status = PRINT_OFF
    elif 'method' in json_message:
        method=json_message['method']
        if method == 'notify_proc_stat_update':
            currentParams.klipper_ready = True
        if method == 'notify_status_update':
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
            updateLedsOther.leds_status = PRINT_OFF
            
    if currentParams.filament_detected != None:
        updateLedsFilament.leds_status = currentParams.filament_detected

    if currentParams.heater_bed_target == 0:
        if currentParams.heater_bed_temp < HEATER_BED_TEMP_COLD:
            updateLedsHeaterBed.leds_status = COLD
            updateLedsHeaterBed.progress = 100
        else:
            updateLedsHeaterBed.leds_status = TOO_COLD
            updateLedsHeaterBed.progress = HEATER_BED_TEMP_COLD / currentParams.heater_bed_temp
    else:
        if currentParams.heater_bed_temp < currentParams.heater_bed_target * PERCENT_TARGET_TEMP:
            updateLedsHeaterBed.leds_status = TOO_HOT
            updateLedsHeaterBed.progress = currentParams.heater_bed_temp / currentParams.heater_bed_target
        else:
            updateLedsHeaterBed.leds_status = HOT
            updateLedsHeaterBed.progress = 100

    if currentParams.extruder_target == 0:
        if currentParams.extruder_temp < EXTRUDER_TEMP_COLD:
            updateLedsExtruder.leds_status = COLD
            updateLedsExtruder.progress = 100
        else:
            updateLedsExtruder.leds_status = TOO_COLD
            updateLedsExtruder.progress = EXTRUDER_TEMP_COLD / currentParams.extruder_temp
    else:
        if currentParams.extruder_temp < currentParams.extruder_target * PERCENT_TARGET_TEMP:
            updateLedsExtruder.leds_status = TOO_HOT
            updateLedsExtruder.progress = currentParams.extruder_temp / currentParams.extruder_target
        else:
            updateLedsExtruder.leds_status = HOT
            updateLedsExtruder.progress = 100
    
    if False:
        updateLedsOther.leds_status = PRINT_ON

def on_error(ws, error):
    print(error)

def on_close(ws, close_status_code, close_msg):
    print("### closed ###")
    updateLedsExtruder.leds_status = STATUS_NONE
    updateLedsHeaterBed.leds_status = STATUS_NONE
    updateLedsFilament.leds_status = STATUS_NONE
    updateLedsOther.leds_status = STATUS_NONE
    currentParams.klipper_ready = False
    
def on_open(ws):
    def run(*args):
        print("### open ###")
        currentParams.klipper_ready = False
        while currentParams.klipper_ready == False:
            print("Waiting until klipper_ready")
            ws.send("""{
                "jsonrpc": "2.0",
                "method": "printer.objects.subscribe",
                "params": {
                    "objects": {
                        "heater_bed": ["target", "temperature"],
                        "extruder": ["target", "temperature"],
                        "filament_switch_sensor runout_sensor": ["filament_detected"]
                    }
                },
                "id": 5434
            }""")
            time.sleep(1)
    thread.start_new_thread(run, ())

class CurrentParams():
    def __init__(self):
        super(CurrentParams, self).__init__()
        self.klipper_ready = False
        self.heater_bed_temp = None
        self.heater_bed_target = None
        self.extruder_temp = None
        self.extruder_target = None
        self.filament_detected = None

class UpdateLedsFilament(threading.Thread):
    def __init__(self):
        super(UpdateLedsFilament, self).__init__()
        self.daemon = True 
        self.state = threading.Condition()
        self.leds_status = STATUS_NONE
      
    def run(self):
        current_pos = FILAMENT_SENSOR_BEGIN
        direction = 1

        clientSock = socket.socket (socket.AF_INET, socket.SOCK_DGRAM)
        now_filament = dt.datetime.now()
        current_status = STATUS_INIT

        while True:
            if self.leds_status == STATUS_NONE:
                filament_sensor_color = BACK_COLOR_OFF

            if self.leds_status == True:
                filament_sensor_color = FILAMENT_SENSOR_OK
            else:
                now_filament2 = dt.datetime.now()
                if (now_filament2-now_filament).total_seconds() > FILAMENT_ANIMATION_SPEED:
                    current_pos = current_pos + direction
                    if current_pos == FILAMENT_SENSOR_END:
                        direction = -1
                    if current_pos == FILAMENT_SENSOR_BEGIN:
                        direction = 1
                    now_filament = dt.datetime.now()
            v = [WLED_UDP_MODE_WARLS,WLED_UDP_WAIT]
            for i in range(FILAMENT_SENSOR_BEGIN,FILAMENT_SENSOR_END+1):
                v.extend([i])
                if self.leds_status == True or self.leds_status == STATUS_NONE:
                    color = filament_sensor_color
                elif i == current_pos:
                    color = FILAMENT_SENSOR_KO1
                else:
                    color = FILAMENT_SENSOR_KO2
                v.extend(color)

                '''
                now_filament2 = dt.datetime.now()
                if (now_filament2-now_filament).total_seconds() > FILAMENT_BLINK:
                    if filament_sensor_color == FILAMENT_SENSOR_KO1:
                        filament_sensor_color = FILAMENT_SENSOR_KO2
                    else:
                        filament_sensor_color = FILAMENT_SENSOR_KO1
                    now_filament = dt.datetime.now()

            v = [WLED_UDP_MODE,WLED_UDP_WAIT]
            for i in range(FILAMENT_SENSOR_BEGIN,FILAMENT_SENSOR_END+1):
                v.extend([i])
                v.extend(filament_sensor_color)
'''
            if self.leds_status != True or (self.leds_status == True and current_status != self.leds_status):
                current_status = self.leds_status
                Message = bytearray(v)
                clientSock.sendto (Message, (WLED_IP, WLED_PORT))
                time.sleep(TIME_SLEEP)

class UpdateLedsTemperature(threading.Thread):
    def __init__(self,begin,end,direction):
        super(UpdateLedsTemperature, self).__init__()
        self.daemon = True 
        self.state = threading.Condition()
        self.leds_status = STATUS_NONE
        self.begin = begin
        self.end = end
        self.progress = 100
        self.end_pos = begin - 1
        self.direction = direction

    def run(self):
        clientSock = socket.socket (socket.AF_INET, socket.SOCK_DGRAM)
        current_status = STATUS_INIT
        now = dt.datetime.now()
        direction = 1

        while True:
            if (self.leds_status == TOO_HOT or self.leds_status == TOO_COLD) or self.leds_status != current_status:
                current_status = self.leds_status
                if self.leds_status == STATUS_NONE:
                    color = BACK_COLOR_OFF

                if self.leds_status == COLD:
                    color = COLD_COLOR
                elif self.leds_status == HOT:
                    color = HOT_COLOR
                '''
                elif self.leds_status == TOO_HOT:
                    color = TOO_HOT_COLOR
                elif self.leds_status == TOO_COLD:
                    color = TOO_COLD_COLOR
                '''
                v = [WLED_UDP_MODE_WARLS,WLED_UDP_WAIT]

                for i in range(self.begin,self.end+1):
                    led_index = i
                    if self.leds_status == TOO_HOT or self.leds_status == TOO_COLD:
                        current_status = STATUS_INIT
                        if self.direction == TO_LEFT:
                            led_index = self.end - i + self.begin
                        now2 = dt.datetime.now()
                        if (now2-now).total_seconds() > TEMPERATURE_ANIMATION_SPEED:
                            now = dt.datetime.now()
                            self.end_pos += direction
                            if self.end_pos < self.begin:
                                direction = 1
                                self.end_pos = self.begin + 1
                            if self.end_pos > self.begin + (float(self.progress) * float(self.end + 1 - self.begin)):
                                direction = -1

                        if i < self.end_pos:
                            if self.leds_status == TOO_HOT:
                                color = HOT_COLOR
                            if self.leds_status == TOO_COLD:
                                color = COLD_COLOR
                        else:
                            if self.leds_status == TOO_HOT:
                                color = TOO_HOT_COLOR
                            if self.leds_status == TOO_COLD:
                                color = TOO_COLD_COLOR
                    v.extend([led_index])
                    v.extend(color)

                Message = bytearray(v)
                clientSock.sendto (Message, (WLED_IP, WLED_PORT))
                time.sleep(TIME_SLEEP)

class UpdateLedsOther(threading.Thread):
    def __init__(self):
        super(UpdateLedsOther, self).__init__()
        self.daemon = True 
        self.state = threading.Condition()
        self.leds_status = STATUS_NONE
       
    def run(self):
        printer_color = BACK_COLOR_OFF
        clientSock = socket.socket (socket.AF_INET, socket.SOCK_DGRAM)
        current_status = STATUS_INIT
        now = dt.datetime.now()

        while True:
            now2 = dt.datetime.now()
            if self.leds_status != current_status or (now2-now).total_seconds() > WLED_UDP_WAIT*0.9:
                current_status = self.leds_status            
                if self.leds_status == STATUS_NONE:
                    printer_color = BACK_COLOR_OFF
                if self.leds_status == PRINTER_OFF:
                    printer_color = BACK_COLOR_OFF
                elif self.leds_status == PRINT_OFF:
                    printer_color = BACK_COLOR_PRINT_OFF
                elif self.leds_status == PRINT_ON:
                    printer_color = BACK_COLOR_PRINT_ON

                v = [WLED_UDP_MODE_WARLS,WLED_UDP_WAIT]
                for i in range(NB_LEDS):
                    if (i < EXTRUDER_BEGIN or i > EXTRUDER_END) and (i < HEATER_BED_BEGIN or i > HEATER_BED_END) and (i < FILAMENT_SENSOR_BEGIN or i > FILAMENT_SENSOR_END):
                        v.extend([i])
                        v.extend(printer_color)

                Message = bytearray(v)
                clientSock.sendto (Message, (WLED_IP, WLED_PORT))

                time.sleep(TIME_SLEEP)

if __name__ == "__main__":
    currentParams = CurrentParams()
    updateLedsExtruder = UpdateLedsTemperature(begin=EXTRUDER_BEGIN,end=EXTRUDER_END,direction=TO_LEFT)
    updateLedsExtruder.start()
    updateLedsHeaterBed = UpdateLedsTemperature(begin=HEATER_BED_BEGIN,end=HEATER_BED_END,direction=TO_RIGHT)
    updateLedsHeaterBed.start()
    updateLedsFilament = UpdateLedsFilament()
    updateLedsFilament.start()
    updateLedsOther = UpdateLedsOther()
    updateLedsOther.start()
    #websocket.enableTrace(True)
    ws = websocket.WebSocketApp("ws://"+PRINTER_IP+":"+str(PRINTER_PORT)+"/websocket",
                              on_open=on_open,
                              on_message=on_message,
                              on_error=on_error,
                              on_close=on_close)
    while True:
        ws.run_forever() 