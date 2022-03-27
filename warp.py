import requests
import time
from requests.exceptions import HTTPError
from requests.structures import CaseInsensitiveDict

#get
#evse/energy_meter_values / power [W]
#evse/state / vehicle_state

#set 
#evse/current_limit / current
#evse/stop_charging
#evse/start_charging



url_meter       = 'http://192.168.178.43/meter/state'
url_controller  = 'http://192.168.178.43/evse/state'
#payload = open("request.json")
#headers = {'content-type': 'application/json', 'Accept-Charset': 'UTF-8'}
#r = requests.post(url, data=payload, headers=headers)

url_limit = 'http://192.168.178.43/evse/current_limit'
url_stop = 'http://192.168.178.43/evse/stop_charging'
url_start = 'http://192.168.178.43/evse/start_charging'
headers = CaseInsensitiveDict()
headers["Content-Type"] = "application/json"

data = '{"current":14000}'
data_null = 'null'


try:
    response = requests.get(url_meter)
    response.raise_for_status()
    # access JSOn content
    jsonResponse = response.json()
    print("Entire JSON response")
    print(jsonResponse)
    print("Print each key-value pair from JSON response")
    for key, value in jsonResponse.items():
        print(key, ":", value)

except HTTPError as http_err:
    print(f'HTTP error occurred: {http_err}')
except Exception as err:
    print(f'Other error occurred: {err}')
    
try:
    response = requests.get(url_controller)
    response.raise_for_status()
    # access JSOn content
    jsonResponse = response.json()
    print("Entire JSON response")
    print(jsonResponse)
    print("Print each key-value pair from JSON response")
    for key, value in jsonResponse.items():
        print(key, ":", value)

except HTTPError as http_err:
    print(f'HTTP error occurred: {http_err}')
except Exception as err:
    print(f'Other error occurred: {err}')
    
    
try:
    response = requests.put(url_start, headers=headers, data=data_null)
    print(response.status_code)
    response.raise_for_status()
    print("done")
except HTTPError as http_err:
    print(f'HTTP error occurred: {http_err}')
except Exception as err:
    print(f'Other error occurred: {err}')




