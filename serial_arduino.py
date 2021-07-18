import serial
import io
ser = serial.serial_for_url('/dev/ttyUSB1', timeout=0.5)
sio = io.TextIOWrapper(io.BufferedRWPair(ser, ser))
arduino_keys = ["powerUtility", "powerPV", "powerHeat", "pwm_setpoint", "tempHigh", "tempLow"]


def pwm_setpoint(val)
    print("pwm_setpoint...")
    assert(val>=0 and val<=255)
    sio.write("pwm_setpoint:" + str(val))
    sio.flush();
             
             
def read_loop(): 
    print("Starting read_loop")
    while true:
        line = sio.readline()
        for key in arduino_keys:
            value = input_dict.get(key,None)
            if value is not None: #if it exists you can use it
                print(key + " has value: " + value)



        
        
        
