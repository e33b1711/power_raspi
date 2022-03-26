import requests
from requests.exceptions import HTTPError
from requests.structures import CaseInsensitiveDict


url_a = 'http://192.168.178.43/evse/max_charging_current'
#payload = open("request.json")
#headers = {'content-type': 'application/json', 'Accept-Charset': 'UTF-8'}
#r = requests.post(url, data=payload, headers=headers)

url_b = 'http://192.168.178.43/evse/current_limit'
headers = CaseInsensitiveDict()
headers["Content-Type"] = "application/json"

data = '{"current":14000}'


try:
    response = requests.get(url_a)
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
    
resp = requests.put(url_b, headers=headers, data=data)

print(resp.status_code)


