import serial
import io
ser = serial.serial_for_url('/dev/ttyUSB1', timeout=0.5)
sio = io.TextIOWrapper(io.BufferedRWPair(ser, ser))
keys = {"power_pv", "power_heat", "setpoint_pwm", "temp_high", "temp_low"}
values ={}


def pwm_setpoint(val):
    print("pwm_setpoint: " + str(val))
    val = round(val)
    if val<0:
        val=0
    if val >255:
        val=255
    sio.write("setpoint_pwm:" + str(val) + "\n")
    sio.flush()
    print("setpoint_pwm:" + str(val) + "\n")        

def print_values():
    print(values)
             
def read_loop(): 
    print("Starting read_loop")
    for test_key in keys:
        values[test_key] = -10.0
    while 1:
        line = sio.readline()
        try:
            key, val = line.split(":")
            #print("pair: >>" + key + "<< >>" + val + "<<")
            for test_key in keys:
                if key == test_key : #if it exists you can use it
                    #print("matcH: "+ key)
                    values[test_key] = float(val) 
                    #print(key + " " + val)
                #else:
                    #print("mismatch: " + key)
        except:
            #print("except")
            pass
        
        
        
