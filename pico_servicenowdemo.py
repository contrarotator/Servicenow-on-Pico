#
# pico_servicenow_demo.py
#
# minimum code necessary to:
#    create a ticket in servicenow
#    turn on the LED
#    wait until the ticket is marked resolved
#    turn the LED off
#
# it is expected that the code would be made more robust when being integrated into a larger device
#
# the documentation at github.com/contrarotator has more detail.
#
import network
import urequests
import time
import machine

#
# set some things
#
wlan_ssid = 'yourssid'
wlan_pass = 'yoursecret'

instance_url = 'https://devyourinstid.service-now.com'
create_url = instance_url + '/api/now/table/incident'
user = 'youruser.name'
pwd = 'youruserpw'
headers = {"Content-Type":"application/json","Accept":"application/json"}

led = machine.Pin("LED", machine.Pin.OUT)
led.on()
led.off()

#
# connect the network
#
wlan = network.WLAN(network.STA_IF)
wlan.active(True)
wlan.connect(wlan_ssid, wlan_pass)
if not wlan.isconnected():
  print("wlan did not connect")
print(wlan.status())  
#
# send a POST to your servicenow instance to create an incident ticket
#
response = urequests.post(create_url, auth=(user, pwd), headers=headers ,data="{\"caller_id\":\"abel.tuter\",\"short_description\":\"test incident\"}")
#
# analyse the response
#
if response.status_code != 201:
    print ("unexpected HTTTP response")
    print(response.status_code)
    print(response.headers)
    print(response.json())

# Decode the JSON response into a dictionary and use the data
data = response.json()
#print(data)
inc_sys_id = data["result"]["sys_id"]
inc_id = data["result"]["number"]
inc_state = data["result"]["state"]
print ("sys_id: ",inc_sys_id,"  incident number: ",inc_id," incident state: ",inc_state)
response.close() # release resources

# now you can see the list of incidents in ServiceNow:
# instance_url + /nav_to.do?uri=%2Fincident_list.do%3Fsysparm_first_row%3D1%26sysparm_query%3D%26sysparm_view%3Dess
# the LED will remain on until the incident state is set to any value other than New

led.on()

get_url = instance_url + "/api/now/table/incident/"+ inc_sys_id + "?sysparm_fields=state"

#now read it back and check state
#url = "https://dev119885.service-now.com/api/now/table/incident/f7aaa87d877911100234a97e0ebb35da?sysparm_fields=state"

print("waiting:")

while inc_state != "6":
    time.sleep(10)
    response = urequests.get(get_url, auth=(user, pwd), headers=headers)
    data = response.json()
    response.close()
    inc_state = data["result"]["state"]
    print (inc_state)
    
led.off()
print("done:")
