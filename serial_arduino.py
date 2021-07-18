import serial
import io
ser = serial.serial_for_url('/dev/ttyUSB1', timeout=0.5)
sio = io.TextIOWrapper(io.BufferedRWPair(ser, ser))
arduino_keys = {"powerPV", "powerHeat", "pwm_setpoint", "tempHigh", "tempLow"}
arduino_values ={}


def pwm_setpoint(val):
    print("pwm_setpoint...")
    assert(val>=0 and val<=255)
    sio.write("pwm_setpoint:" + str(val) + "\n")
    sio.flush();
        

def print_values():
    print(arduino_values)
             
def read_loop(): 
    print("Starting read_loop")
    for test_key in arduino_keys:
        arduino_values[test_key] = -10.0
    while 1:
        line = sio.readline()
        try:
            key, val = line.split(":")
            #print("pair: >>" + key + "<< >>" + val + "<<")
            for test_key in arduino_keys:
                if key == test_key : #if it exists you can use it
                    #print("matcH: "+ key)
                    arduino_values[test_key] = float(val) 
                    #print(key + " " + val)
                #else:
                    #print("mismatch: " + key)
        except:
            #print("except")
            pass
        
        
        
