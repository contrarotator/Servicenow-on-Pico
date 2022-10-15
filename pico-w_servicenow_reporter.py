#
# pico_servicenow_reporter.py
#
# on startup:
#
#    flash g_build_id to show which software is installed
#    turn on user LED
#    connect to wifi
#    turn off user LED
#    while 1 == 1:
#        wait until user button is pressed
#        turn on user LED
#        create ServiceNow ticket
#        wait until ticket is marked Resolved
#        turn off user LED
#
#    while running, the on-board LED on the Pico flashes state information
#    if a fault occurs, the on-board LED will flash a fault code
#
#
#  known bugs & limitations
#    doesn't check to see that the created incident still exists, only whether it is resolved
#
#
# the documentation at github.com/contrarotator has more detail.
#
#
######################
g_build_id = 204
######################

import machine
import time
import network
import urequests
import gc
import yconfig  #local module containing config & credentials

picoled = machine.Pin("LED", machine.Pin.OUT)
picoled.off()
picoled.on()

pin_button = 16
button = machine.Pin(pin_button, machine.Pin.IN, machine.Pin.PULL_UP)
pin_userled = 15
userled = machine.Pin(pin_userled, machine.Pin.OUT)

wlan = network.WLAN(network.STA_IF)
wlan.config(pm = 0xa11140)

# state indicators and exported identifiers start with 2
# this makes it easy to identify which controller in a multicontroller cluster

state_fault                    = const(211)
state_init                     = const(212)
state_activating               = const(213)
state_connecting               = const(214)
state_ready                    = const(216)
state_wait                     = const(221)
state_create_ticket            = const(222)
state_wait_ticket              = const(223)

fn_blink                       = const(2000)
fn_loop                        = const(2001)
fault_blink_underflow          = const(2002)
fault_blink_overflow           = const(2003)
fault_invalid_state            = const(2004)
log_wlan_ip                    = const(2005)
log_state                      = const(2006)
log_wlan_state                 = const(2007)
log_fault                      = const(2008)
log_time                       = const(2009) 
blink_state_internumber        = const(2010)
blink_state_interdigit         = const(2011)
blink_state_on                 = const(2012)
blink_state_off                = const(2013)
blink_state_fault              = const(2014)

fault_wlan_badauth             = const(2028)
fault_wlan_nonet               = const(2029)
fault_wlan_noip                = const(2030)
fault_wlan_join                = const(2031)
fault_wlan_down                = const(2032)
fault_wlan_disconnected        = const(2033)
fault_wlan_fail                = const(2034)
fn_check_wlan                  = const(2035)
fault_wlan_status              = const(2036)

log_inc_number                 = const(2044)
log_inc_state                  = const(2045)
log_http_code                  = const(2046)
log_sysid                      = const(2049)

log_freemem                    = const(2063)

fn_create_incident             = const(2064)
fault_create_http              = const(2065)
fn_check_incident              = const(2066)
fault_check_http               = const(2067)

labels = {

    211: "state_fault",
    212: "state_init",
    213: "state_activating",
    214: "state_connecting",
    216: "state_ready",
    221: "state_wait",
    222: "state_create_incident",
    223: "state_wait_ticket",

    2000: "fn_blink",
    2001: "fn_loop",
    2002: "fault_blink_underflow",
    2003: "fault_blink_overflow",
    2004: "fault_invalid_state",
    2005: "log_wlan_ip",
    2006: "log_state",
    2007: "log_wlan_state",
    2008: "log_fault",
    2009: "log_time" ,
    2028: "fault_wlan_badauth",
    2029: "fault_wlan_nonet",
    2030: "fault_wlan_noip",
    2031: "fault_wlan_join",
    2032: "fault_wlan_down",
    2033: "fault_wlan_disconnected",
    2034: "fault_wlan_fail",
    2035: "fn_check_wlan",
    2036: "fault_wlan_status",
    2044: "log_inc_number",
    2045: "log_inc_state",
    2046: "log_http_code",
    2049: "log_sysid",
    2063: "log_freemem",
    2064: "fn_create_incident",
    2065: "fault_create_http",
    2066: "fn_check_incident",
    2067: "fault_check_http"
    }

g_fault   = 0
g_now     = 0
g_dwell   = 0
g_start   = 0
g_freemem = 999999

param_wlan_ssid         = yconfig.wlan_ssid
param_wlan_password     = yconfig.wlan_pass

param_snow_instance_url = yconfig.snow_url
param_snow_user         = yconfig.snow_user
param_snow_pwd          = yconfig.snow_pass

param_json_headers = {"Content-Type":"application/json","Accept":"application/json"}

#
# blink(n) blinks a multidigit number.
#
# digit zero is blinked as ten flashes
#
# returns true if the number has been displayed (that is, we are in internumber gap),
# otherwise returns false
#

# parameters
blink_wait_on     = 100 
blink_wait_off    = 300
blink_wait_digit  = blink_wait_on + blink_wait_off
blink_wait_number = blink_wait_digit * 3
# variables
blink_now         = 0
blink_start       = 0
blink_dwell       = 0.1
blink_posn        = 0
blink_max         = 99999 
blink_digit       = 0 # this digit to blink 
blink_remainder   = 0     # remainder
blink_prev        = 0

blink_wait        = blink_wait_off
blink_state       = blink_state_off

def blink (n):

    global blink_posn, blink_remainder, blink_prev
    global blink_wait, blink_state
    global blink_digit, blink_now, blink_dwell, blink_start
    
    blink_now = time.ticks_ms() # milliseconds
    blink_dwell = time.ticks_diff(blink_now,blink_start)
    
    if blink_dwell > blink_wait:
        blink_start = blink_now
        if blink_prev != n:
            blink_digit = 0
            blink_remainder = 0
            blink_prev = n
        if blink_digit == 0:
            if blink_remainder == 0:
                if n < 0:
                    n = 0
                    g_fault = fault_blink_underflow
                elif n > blink_max:
                    n = blink_max
                    blink_state = blink_state_fault
                    g_fault = fault_blink_overflow
                blink_remainder = n
                blink_posn = 6
                while (10**blink_posn > n):
                    blink_posn -= 1
                blink_state = blink_state_internumber
            else:
                blink_power = 10**blink_posn
                blink_posn -= 1
                blink_digit = int(blink_remainder/blink_power)
                blink_remainder = blink_remainder - (blink_power * blink_digit)
                if blink_digit == 0:
                   blink_digit = 10 # if digit is zero then blink ten times
                blink_state = blink_state_interdigit
            #if blink_remainder == 0:
        #if blink_digit == 0:
            
        
        if blink_state == blink_state_internumber:
            blink_start  = blink_now
            blink_state  = blink_state_off
            blink_wait   = blink_wait_number
            blink_retval = True
            picoled.off()  
        elif blink_state == blink_state_interdigit:
            blink_start = blink_now
            blink_state = blink_state_off
            blink_wait = blink_wait_digit
            picoled.off()  
        elif blink_state == blink_state_off:
            blink_start = blink_now
            blink_state = blink_state_on
            blink_wait = blink_wait_on
            blink_retval = False
            picoled.on()  
        elif blink_state == blink_state_on:
            blink_start = blink_now
            blink_state = blink_state_off
            blink_wait = blink_wait_off
            picoled.off()
            blink_digit -= 1
        elif blink_state == blink_state_fault:
            #do nothing, but be nice meanwhile
            time.sleep(10)
        else:
            blink_state = blink_state_fault
            g_fault = fault_blink_state
            write_log(fn_blink, log_fault, g_fault)
            g_state == state_fault
            write_log(fn_blink, log_state, g_state)
            picoled.on()
        #if blink_state ==
    #if blink_dwell > blink_wait:

    if blink_digit == 0 and blink_remainder == 0:
        retval = True
    else:
        retval = False
    return retval
# def blink()

#
# write_log(fn, code, value)
#
# write out a message.  here it just prints to serial but can be modified to put out to other destinations
#
# function mnames and other message flags are integers to minimise number of bytes.
#

write_log_count = 0

def write_log (fn, code, value):
    global labels,write_log_count
    write_log_count += 1
    if fn in labels:
        fn1 = labels.get(fn)
    else:
        fn1 = fn
    if code in labels:
        fn2 = labels.get(code)
    else:
        fn2 = code
    if value in labels:
        fn3 = labels.get(value)
    else:
        fn3 = value
    print("log: ",write_log_count," : ",fn1," : ",fn2," : ",fn3)
    return
#def write_log()

#
# check_wlan() checks the wlan,
#              if it is up and working, return true
#              if not, log fault once only
#                  and return false
#              
#

check_wlan_flag = 0

def check_wlan():
    global wlan, check_wlan_flag
    retval = False
    wlan_status = wlan.status()
    log_status = 0   
    if wlan_status == 3: # 3 CYW43_LINK_UP
        wlan_status = wlan.ifconfig()
        write_log(fn_check_wlan, log_wlan_ip, wlan_status[0])
        check_wlan_flag = 0
        retval = True
    elif wlan_status == 2: # CYW43_LINK_NOIP:  # 2
        if check_wlan_flag != wlan_status:
            write_log(fn_check_wlan, log_fault, fault_wlan_noip)
            check_wlan_flag = wlan_status # only log once
    elif wlan_status == 1: #CYW43_LINK_JOIN:  # 1
        if check_wlan_flag != wlan_status:
            write_log(fn_check_wlan, log_fault, fault_wlan_join)
            check_wlan_flag = wlan_status # only log once 
    elif wlan_status == 0: #CYW43_LINK_DOWN:  # 0
        if check_wlan_flag != wlan_status:
            write_log(fn_check_wlan, log_fault, fault_wlan_down)
            check_wlan_flag = wlan_status # only log once
    elif wlan_status == -1: # CYW43_LINK_FAIL:  # -1
        if check_wlan_flag != wlan_status:
            write_log(fn_check_wlan, log_fault, fault_wlan_fail)
            check_wlan_flag = wlan_status # only log once
    elif wlan_status == -2: # CYW43_LINK_NONET:  # -2
        if check_wlan_flag != wlan_status:
            write_log(fn_check_wlan, log_fault, fault_wlan_nonet)
            check_wlan_flag = wlan_status # only log once
        # this might not be a hard fault
        #g_state = state_fault
        #write_log(fn_check_wlan, log_state, g_state)
    elif wlan_status == -3: # CYW43_LINK_BADAUTH:  # -3
        if check_wlan_flag != wlan_status:
            write_log(fn_check_wlan, log_fault, fault_wlan_badauth)
            check_wlan_flag = wlan_status # only log once
        #this is likely a hard fault
        g_state = state_fault 
        write_log(fn_check_wlan, log_state, g_state)
    else:
        write_log(fn_check_wlan, log_wlan_state, wlan_status)
        write_log(fn_check_wlan, log_fault, fault_wlan_status)
        g_state = state_fault 
        write_log(fn_check_wlan, log_state, g_state)
    return retval
#def check_wlan()

#
#  create_incident(code) creates a servicenow incident and returns zero if failed, sys_id if successful
#

def create_incident(faultcode):
    gc.collect()
    retval = False
    create_url = param_snow_instance_url  + '/api/now/table/incident'
    response = urequests.post(create_url, auth=(param_snow_user, param_snow_pwd), headers=param_json_headers ,data="{\"caller_id\":\""+ param_snow_user+ "\",\"short_description\":\"RTU reports fault code " + str(faultcode) + " \",\"assignment_group\":\"telemetry.devices\"}")
    if response.status_code != 201:
        write_log(fn_create_incident, log_fault, fault_create_http)
        write_log(fn_create_incident, log_http_code, response.status_code)
        retval = False
    else:
        # Decode the JSON response into a dictionary and use the data
        data = response.json()
        #print(data)
        inc_sysid = data["result"]["sys_id"]
        inc_id = data["result"]["number"]
        write_log(fn_create_incident, log_inc_number, inc_id)
        write_log(fn_create_incident, log_sysid, inc_sysid)
        retval = inc_sysid
       
    response.close() # release resources
    gc.collect()
    return retval
#def create_incident()

#
# check_incident(sysid) checks the incident with given sys_id
#                       returns true if it is in state Resolved (6)
#                       otherwise returns false
# 
#

def check_incident(sysid):
    gc.collect()
    retval = False
    get_url = param_snow_instance_url + "/api/now/table/incident/"+ sysid + "?sysparm_fields=state"
    response = urequests.get(get_url, auth=(param_snow_user, param_snow_pwd), headers=param_json_headers)
    if response.status_code != 200:
        write_log(fn_check_incident, log_fault, fault_check_http)
        write_log(fn_check_incident, log_http_code, response.status_code)
        retval = False
    else:
        # Decode the JSON response into a dictionary and use the data
        data = response.json()
        inc_state = data["result"]["state"]
        #write_log(fn_check_incident, log_inc_state, inc_state)
        if inc_state == "6":
            retval = True
        else:
            retval = False
            
    response.close()
    gc.collect()
    return retval
#def check_incident

loop_run_flag = True
g_state = state_init
g_wait = 9999   # in ms
                # used for loop step timing and retry timing
                # set to a long enough time that you do not unfairly load the cloud service
                #
param_wlan_retry_limit = 10
g_wlan_retries = 0
write_log(fn_loop, log_state, g_state)
g_sys_id = 0


while loop_run_flag:
    
    g_now = time.ticks_ms() # milliseconds
    #g_dwell = g_now - g_start
    g_dwell = time.ticks_diff(g_now,g_start)
    
    if g_state == state_init:
        if blink(g_build_id):
            #if g_dwell > g_wait:
            g_start = g_now
            wlan.active(False)
            g_state = state_activating
            write_log(fn_loop, log_state, g_state)
            userled.on()
    elif g_state == state_activating:
        blink(state_activating)
        if g_dwell > g_wait:
            g_start = g_now
            wlan.active(True)
            wlan.scan()
            g_state = state_connecting
            write_log(fn_loop, log_state, g_state)
    elif g_state == state_connecting:
        blink(state_connecting)
        if g_dwell > g_wait:
            g_start = g_now
            wlan.connect(param_wlan_ssid, param_wlan_password)
            if check_wlan():
                g_wlan_retries = 0
                g_state = state_ready
                write_log(fn_loop, log_state, g_state)
                userled.off()
            else:
                g_wlan_retries += 1
                if g_wlan_retries > param_wlan_retry_limit:
                    g_state = state_init
                    write_log(fn_loop, log_state, g_state)
        #else do nothing
    elif g_state == state_ready:
        if blink(state_ready):
            g_state = state_wait
            write_log(fn_loop, log_state, g_state)
    elif g_state == state_wait:
        blink(state_wait)
        if not button.value(): #button is low, pressed
            g_start = g_now
            if wlan.isconnected():
                g_state = state_create_ticket
                write_log(fn_loop, log_state, g_state)
                userled.on()
            else:
                write_log(fn_loop, log_wlan_state, fault_wlan_disconnected)
                g_state = state_init
                write_log(fn_loop, log_state, g_state)      
        #else:
            #wait till button pressed
    elif g_state == state_create_ticket:  
        #blink(state_create_ticket)
        if g_dwell > g_wait:
            g_start = g_now
            g_sys_id = create_incident(3456)
            if g_sys_id:  # if not == 0
                g_state = state_wait_ticket
                write_log(fn_loop, log_state, g_state)
                userled.on()
            #else wait and try again

    elif g_state == state_wait_ticket:
        blink(state_wait_ticket)
        if g_dwell > g_wait:
            g_start = g_now
            if check_incident(g_sys_id):
                g_state = state_ready
                write_log(fn_loop, log_state, g_state)
                userled.off()
        # else process another one

    elif g_state == state_fault:
        blink(g_fault)
    else:
        g_state = state_fault
        write_log(fn_loop, log_state, g_state)
        g_fault = fault_invalid_state
        write_log(fn_loop, log_fault, g_fault)
        
#while loop_run_flag

# stop gracefully & clean up
picoled.off()
userled.off()
wlan.disconnect()
wlan.active(False)
# end



