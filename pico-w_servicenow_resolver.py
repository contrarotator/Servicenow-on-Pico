#
# pico-w-servicenow-resolver.py
#
# on startup,
#    blink g_build_id to show which SW is installed
#    connect to WiFi
#    for each incident in state New
#        add comment in worklog
#        assign to telemetry.resolver1
#        move to In Progress
#    for each incident in state In Progress
#        add comment in worklog
#        add resolution code
@        move to Resolved 
# 

g_build_id = 314

import machine
import time
import network
import urequests
import gc
import yconfig  #local module containing config & credentials

led = machine.Pin("LED", machine.Pin.OUT)
led.off()
led.on()

wlan = network.WLAN(network.STA_IF)
wlan.config(pm = 0xa11140)

# state indicators and exported identifiers start with 3
# this makes it easy to identify which controller in a multicontroller cluster

state_fault             = const(311)
state_init              = const(312)
state_activating        = const(313)
state_connecting        = const(314)
state_ready             = const(316)
state_wait              = const(321)
state_inc_new           = const(322)
state_inc_progress      = const(323)


fn_blink                = const(3000)
fn_loop                 = const(3001)
fault_blink_underflow   = const(3002)
fault_blink_overflow    = const(3003)
fault_invalid_state     = const(3004)
log_wlan_ip             = const(3005)
log_state               = const(3006)
log_wlan_state          = const(3007)
log_fault               = const(3008)
log_time                = const(3009) 
blink_state_internumber = const(3010)
blink_state_interdigit  = const(3011)
blink_state_on          = const(3012)
blink_state_off         = const(3013)
blink_state_fault       = const(3014)

act_retry               = const(3020)              
act_finished            = const(3022)
fn_send_event           = const(3026)
fault_wlan_badauth      = const(3028)
fault_wlan_nonet        = const(3029)
fault_wlan_noip         = const(3030)
fault_wlan_join         = const(3031)
fault_wlan_down         = const(3032)
fault_wlan_disconnected = const(3033)
fault_wlan_fail                = const(3034)
fn_check_wlan                  = const(3035)
fault_wlan_status              = const(3036)

fn_process_new                 = const(3038)
fn_process_inprogress          = const(3039)

process_new_ready              = const(3040)
process_new_update             = const(3041)
process_new_done               = const(3042)
process_new_fault              = const(3043)

log_inc_number                 = const(3044)
fault_process_new_put          = const(3045)
log_http_code                  = const(3046)
fault_process_new_state        = const(3047)
fault_process_new_get          = const(3048)
log_sysid                      = const(3049)

process_inprogress_ready       = const(3050)
process_inprogress_update      = const(3051)
process_inprogress_done        = const(3052)
process_inprogress_fault       = const(3053)

fault_process_inprogress_put   = const(3054)
fault_process_inprogress_state = const(3055)
fault_process_inprogress_get   = const(3056)

log_get_oserror                = const(3057)
log_put_oserror                = const(3058)
log_get_exception              = const(3059)
log_put_exception              = const(3060)
fault_oserror_12_memory        = const(3061)
fault_oserror_104_connreset    = const(3062)
log_freemem                    = const(3063)
log_json_exception             = const(3064)

labels = {

    311: "state_fault",
    312: "state_init",
    313: "state_activating",
    314: "state_connecting",
    316: "state_ready",
    321: "state_wait",
    322: "state_inc_new",
    323: "state_inc_progress",

    3000: "fn_blink",
    3001: "fn_loop",
    3002: "fault_blink_underflow",
    3003: "fault_blink_overflow",
    3004: "fault_invalid_state",
    3005: "log_wlan_ip",
    3006: "log_state",
    3007: "log_wlan_state",
    3008: "log_fault",
    3009: "log_time" ,
    3020: "act_retry",
    3022: "act_finished",
    3026: "fn_send_event",
    3028: "fault_wlan_badauth",
    3029: "fault_wlan_nonet",
    3030: "fault_wlan_noip",
    3031: "fault_wlan_join",
    3032: "fault_wlan_down",
    3033: "fault_wlan_disconnected",
    3034: "fault_wlan_fail",
    3035: "fn_check_wlan",
    3036: "fault_wlan_status",
    3037: "fn_set_ntptime",
    3038: "fn_process_new",
    3039: "fn_process_inprogress",
    3040: "process_new_ready" ,
    3041: "process_new_update",
    3042: "process_new_done",
    3043: "process_new_fault",
    3044: "log_inc_number",
    3045: "fault_process_new_put",
    3046: "log_http_code",
    3047: "fault_process_new_state",
    3048: "fault_process_new_get",
    3049: "log_sysid",
    3050: "process_inprogress_ready" ,
    3051: "process_inprogress_update",
    3052: "process_inprogress_done",
    3053: "process_inprogress_fault",
    3054: "fault_process_inprogress_put",
    3055: "fault_process_inprogress_state",
    3056: "fault_process_inprogress_get",
    3057: "log_get_oserror",
    3058: "log_put_oserror",
    3059: "log_get_exception",
    3060: "log_put_exception",
    3061: "fault_oserror_12_memory",
    3062: "fault_oserror_104_connreset",
    3063: "log_freemem",
    3064: "log_json_exception"
}

g_fault                        = 0
g_now                          = 0
g_dwell                        = 0
g_start                        = 0
g_freemem                      = 999999

param_json_headers             = {"Content-Type":"application/json","Accept":"application/json"}

param_wlan_ssid                = yconfig.wlan_ssid
param_wlan_password            = yconfig.wlan_pass

param_snow_instance_url        = yconfig.snow_url
param_snow_user                = yconfig.snow_resolver_user
param_snow_pwd                 = yconfig.snow_resolver_pass

#
# blink(n) blinks a multidigit number.
#
# digit zero is blinked as ten flashes
#
# returns true if the number has been displayed (that is, we are in internumber gap),
# otherwise returns false
#

# parameters
blink_wait_on                  = 100 
blink_wait_off                 = 300
blink_wait_digit               = blink_wait_on + blink_wait_off
blink_wait_number              = blink_wait_digit * 3
# variables
blink_now                      = 0
blink_start                    = 0
blink_dwell                    = 0.1
blink_posn                     = 0
blink_max                      = 99999 
blink_digit                    = 0 # this digit to blink 
blink_remainder                = 0     # remainder
blink_prev                     = 0

blink_wait                     = blink_wait_off
blink_state                    = blink_state_off

def blink (n):

    global blink_posn, blink_remainder, blink_prev
    global blink_wait, blink_state
    global blink_digit, blink_now, blink_dwell, blink_start
    
    blink_now = time.ticks_ms() # milliseconds
    #blink_dwell = blink_now - blink_start
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
                #    blink_posn = int(math.log(blink_remainder,10))
                #print(" blink: blinking ", blink_remainder, "starting at ", blink_posn )
                blink_state = blink_state_internumber
                #retval = True
            else:
                blink_power = 10**blink_posn
                blink_posn -= 1
                blink_digit = int(blink_remainder/blink_power)
                blink_remainder = blink_remainder - (blink_power * blink_digit)
                #print(" blink: digit:",blink_digit ," remainder:",blink_remainder)
                if blink_digit == 0:
                   blink_digit = 10 # if digit is zero then blink ten times
                #blink_wait = blink_wait_digit
                blink_state = blink_state_interdigit
            #if blink_remainder == 0:
        #if blink_digit == 0:
            
        
        if blink_state == blink_state_internumber:
            blink_start  = blink_now
            blink_state  = blink_state_off
            blink_wait   = blink_wait_number
            blink_retval = True
            led.off()  
        elif blink_state == blink_state_interdigit:
            blink_start = blink_now
            blink_state = blink_state_off
            blink_wait = blink_wait_digit
            led.off()  
        elif blink_state == blink_state_off:
            blink_start = blink_now
            blink_state = blink_state_on
            blink_wait = blink_wait_on
            blink_retval = False
            led.on()  
        elif blink_state == blink_state_on:
            blink_start = blink_now
            blink_state = blink_state_off
            blink_wait = blink_wait_off
            led.off()
            blink_digit -= 1
            #print(" blink: dit:",blink_digit)
        elif blink_state == blink_state_fault:
            #do nothing, but be nice meanwhile
            time.sleep(10)
        else:
            blink_state = blink_state_fault
            g_fault = fault_blink_state
            write_log(fn_blink, log_fault, g_fault)
            g_state == state_fault
            write_log(fn_blink, log_state, g_state)
            led.on()
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

write_log_count                = 0

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
    #print("log: ",write_log_count," : ",fn1," : ",fn2," : ",fn3)
    return
#def write_log()

#
# check_wlan() checks the wlan,
#              if it is up and working, return true
#              if not, log fault once only
#                  and return false
#              
#

check_wlan_flag                = 0

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
# process_new()
#
# interrogate the ServiceNow instance for incident tickets which match the queue we want
# (assignment group = telemetry.devices and state = New)
# return only one, in no particular order
# if there is one, add a work log comment, assign it to telemetry.resolver1, and set it to In Progress
# return True when all done
# will be called many times by main loop during process, therefore maintain internal state
# and do one subtask per call.
#

process_new_sysid = 0
process_new_state = process_new_ready
process_new_oserror = 0
#
#param_snow_create_url = instance_url + '/api/now/table/incident'

def process_new():
    
    global param_snow_instance_url,param_snow_user,param_snow_pwd, param_json_headers, process_new_state, process_new_sysid
    
    retval = False
    gc.collect()    
    if process_new_state == process_new_ready:

        #retrieve one record where active=true and assignment group = telemetry.devices and state = new
        #records can come in any order

        #get_url = param_snow_instance_url + "/api/now/table/incident?" + "sysparm_query=active%3Dtrue%5Estate%3D1%5Eassignment_group%3D8a5055c9c61122780043563ef53438e3&sysparm_exclude_reference_link=true&sysparm_fields=number%2Csys_id&sysparm_limit=1"
        get_url = param_snow_instance_url + "/api/now/table/incident?" + "sysparm_query=active%3Dtrue%5Estate%3D1%5Eassignment_group%3Daaccc971c0a8001500fe1ff4302de101&sysparm_display_value=false&sysparm_fields=number%2Csys_id&sysparm_limit=1&sysparm_no_count=true"

        try:
            response = urequests.get(get_url, auth=(param_snow_user, param_snow_pwd), headers=param_json_headers)
        #except OSError as e:
        ##    # log it and wait to try again
        #    if process_new_oserror != e.args[0]:
        #       write_log(fn_process_new, log_get_oserror, e.args[0])
        #       process_new_oserror = e.args[0]
        except Exception as e:
            # log it and wait to try again
            write_log(fn_process_new, log_get_exception, e.args[0])
            retval = True
        else:
            if response.status_code != 200:
                write_log(fn_process_new, log_http_code, response.status_code)
                write_log(fn_process_new, log_fault, fault_process_new_get)
                # don't make this a hard fault, just retry next time.  ? count retries
                #process_new_state = process_new_fault
                #write_log(fn_process_new, log_state, process_new_state)
                retval = True
            else:
                try:
                    data = response.json()
                except Exception as e:
                    # if no JSON, move on
                    write_log(fn_process_new, log_json_exception, e.args[0])
                    retval = True
                else:
                    #print(data)
                    if len(data["result"]) > 0:
                        inc_number        = data["result"][0]["number"] # always item zero, first one in the list
                        process_new_sysid = data["result"][0]["sys_id"]
                       
                        write_log(fn_process_new, log_inc_number, inc_number)
                        write_log(fn_process_new, log_sysid, process_new_sysid)
                        #if there is a new incident, record its sys_id, if not, set retval = true
                        process_new_state = process_new_update
                        #process_new_state = process_new_done
                        write_log(fn_process_new, log_state, process_new_state)
                    else:
                        retval = True #finished, no more to process
                #try
            #if
            response.close()
            gc.collect()
        #try
    elif process_new_state == process_new_update:
        
        #for incident sys_id, assign to user, add a work note and update state to in progress
        #response = urequests.post(create_url, auth=(user, pwd), headers=headers ,data="{\"caller_id\":\"abel.tuter\",\"short_description\":\"test incident\"}")
        
        put_url = param_snow_instance_url + "/api/now/table/incident/" + process_new_sysid + "?sysparm_exclude_reference_link=true"
        try:    
            response = urequests.put(put_url, auth=(param_snow_user, param_snow_pwd), headers=param_json_headers ,data="{\"assigned_to\":\"telemetry.resolver1\",\"state\":\"2\",\"work_notes\":\"updated by Pico_W\"}")
        except OSError as e:
            # log it and wait to try again
            write_log(fn_process_new, log_put_oserror, e.args[0])
        except Exception as e:
            # log it and wait to try again
            write_log(fn_process_new, log_put_exception, e.args[0])
        else:
            # no error
            if response.status_code != 200:
                write_log(fn_process_new, log_http_code, response.status_code)
                write_log(fn_process_new, log_fault, fault_process_new_put)
                process_new_state = process_new_fault
                write_log(fn_process_new, log_state, process_new_state)
            else:
                process_new_state = process_new_done
                write_log(fn_process_new, log_state, process_new_state)
            response.close()
            gc.collect()
    elif process_new_state == process_new_done:
        process_new_sysid = 0
        process_new_state = process_new_ready
        write_log(fn_process_new, log_state, process_new_state)
    elif process_new_state == process_new_fault:
        retval = True
    else:
        write_log(fn_process_new, log_fault, fault_process_new_state)
        write_log(fn_process_new, log_state, process_new_state)        
        process_new_state = process_new_fault
        write_log(fn_process_new, log_state, process_new_state)        
    
    return retval
#def process_new

#
# process_inprogress()
#
# interrogate the ServiceNow instance for incident tickets which match the queue we want
# (assignment group = telemetry.devices and state = In Progress and assigned to = telemetry.resolver1)
# return only one, in no particular order
#
# do something.  if successful, add a comment and mark it resolved.
#
# will be called many times by main loop during process, therefore maintain internal state
# and do one subtask per call.
#
# return True when all done. (note thsi means it won't look for new tickets until all existing
# ones are resolved.  this might not be what you want in a real world application.
#

process_inprogress_state = process_inprogress_ready
process_inprogress_sysid = 0
process_inprogress_oserror = 0

def process_inprogress():
    global process_inprogress_state,process_inprogress_sysid,process_inprogress_oserror
    global param_snow_instance_url,param_snow_user,param_snow_pwd, param_json_headers
    
    retval = False
    gc.collect()   
    if process_inprogress_state == process_inprogress_ready:
        get_url = param_snow_instance_url + "/api/now/table/incident?" + "sysparm_query=active%3Dtrue%5Estate%3D2%5Eassignment_group%3Daaccc971c0a8001500fe1ff4302de101&sysparm_display_value=false&sysparm_fields=number%2Csys_id&sysparm_limit=1&sysparm_no_count=true"
        try:
            response = urequests.get(get_url, auth=(param_snow_user, param_snow_pwd), headers=param_json_headers)
        except OSError as e:
            # log it and wait to try again
            if e.args[0] != process_inprogress_oserror:
                write_log(fn_process_inprogress, log_get_oserror, e.args[0])
                process_inprogress_oserror = e.args[0]
        except Exception as e:
            # log it and wait to try again
            write_log(fn_process_inprogress, log_get_exception, e.args[0])
        else:
            # if no error
            if response.status_code != 200:
                write_log(fn_process_inprogress, log_http_code, response.status_code)
                write_log(fn_process_inprogress, log_fault, fault_process_inprogress_get)
                # don't make this a hard fault, just retry next time.  ? count retries
                #process_inprogress_state = process_inprogress_fault
                #write_log(fn_process_inprogress, log_state, process_inprogress_state)
                retval = True
            else:
                try:
                    data = response.json()
                except Exception as e:
                    # if no JSON, move on
                    write_log(fn_process_inprogress, log_json_exception, e.args[0])
                    retval = True
                else:
                    if len(data["result"]) > 0:
                        inc_number               = data["result"][0]["number"] # always item zero, first one in the list
                        process_inprogress_sysid = data["result"][0]["sys_id"]
                       
                        write_log(fn_process_inprogress, log_inc_number, inc_number)
                        write_log(fn_process_inprogress, log_sysid, process_inprogress_sysid)
                        #if there is a new incident, record its sys_id, if not, set retval = true
                        process_inprogress_state = process_inprogress_update
                        write_log(fn_process_inprogress, log_state, process_inprogress_state)
                    else:
                        retval = True #finished, no more to process
                #try
            response.close()
            gc.collect()
    elif process_inprogress_state == process_inprogress_update:
        
        #for incident sys_id, assign to user, add a work note and update state to in progress
        #response = urequests.post(create_url, auth=(user, pwd), headers=headers ,data="{\"caller_id\":\"abel.tuter\",\"short_description\":\"test incident\"}")
        
        put_url = param_snow_instance_url + "/api/now/table/incident/" + process_inprogress_sysid + "?sysparm_exclude_reference_link=true"
        #write_log(fn_process_inprogress, log_sysid, process_inprogress_sysid)
        try:    
            response = urequests.put(put_url, auth=(param_snow_user, param_snow_pwd), headers=param_json_headers ,data="{\"work_notes\":\"resolved by Pico W\",\"close_code\":\"Resolved by request\",\"state\":\"6\",\"close_notes\":\"resolved by Pico W\"}")
        except OSError as e:
            # log it and wait to try again
            write_log(fn_process_inprogress, log_put_oserror, e.args[0])
        except Exception as e:
            # log it and wait to try again
            write_log(fn_process_inprogress, log_put_exception, e.args[0])
        else:
            if response.status_code != 200:
                write_log(fn_process_inprogress, log_http_code, response.status_code)
                write_log(fn_process_inprogress, log_fault, fault_process_inprogress_put)
                process_inprogress_state = process_inprogress_fault
                write_log(fn_process_inprogress, log_state, process_inprogress_state)
            else:
                process_inprogress_state = process_inprogress_done
                write_log(fn_process_inprogress, log_state, process_inprogress_state)
            response.close()
            gc.collect()
    elif process_inprogress_state == process_inprogress_done:
        process_inprogress_sysid = 0
        process_inprogress_state = process_inprogress_ready
        write_log(fn_process_inprogress, log_state, process_inprogress_state)
    elif process_inprogress_state == process_inprogress_fault:
        retval = True
    else:
        write_log(fn_process_inprogress, log_fault, fault_process_inprogress_state)
        write_log(fn_process_inprogress, log_state, process_inprogress_state)        
        process_inprogress_state = process_inprogress_fault
        write_log(fn_process_inprogress, log_state, process_inprogress_state)
        
    return retval
  
#def process_inprogress

loop_run_flag = True
g_state = state_init
g_wait = 19999 # ms
              # make this enough that delay between retries is friendly to your cloud app provider
              # and in any case twice as long as the likely time an API transaction might take
              #

param_wlan_retry_limit = 10
g_wlan_retries = 0
write_log(fn_loop, log_state, g_state)       

while loop_run_flag:
    
    g_now = time.ticks_ms() # milliseconds
    #g_dwell = g_now - g_start
    g_dwell = time.ticks_diff(g_now,g_start)
    
    if g_state == state_init:
        if blink(g_build_id):
            g_start = g_now
            wlan.active(False)
            g_state = state_activating
            write_log(fn_loop, log_state, g_state)
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
            else:
                g_wlan_retries += 1
                if g_wlan_retries > param_wlan_retry_limit:
                    #loop_run_flag = False
                    g_state = state_init
                    write_log(fn_loop, log_state, g_state)
        #else do nothing
    elif g_state == state_ready:
        if blink(state_ready):
            g_state = state_wait
            write_log(fn_loop, log_state, g_state)
    elif g_state == state_wait:
        if blink(state_wait):
            if g_dwell > g_wait:
                g_start = g_now
                if wlan.isconnected():
                    g_state = state_inc_new
                    write_log(fn_loop, log_state, g_state)
                else:
                    write_log(fn_loop, log_wlan_state, fault_wlan_disconnected)
                    g_state = state_init
                    write_log(fn_loop, log_state, g_state)      
            #else wait till sample period
    elif g_state == state_inc_new:  # process incidents in state NEW, one by one, until there are't any
        blink(state_inc_new)
        if g_dwell > g_wait:
            g_start = g_now
            if process_new():
                g_state = state_inc_progress
                write_log(fn_loop, log_state, g_state)
            #else process another one

    elif g_state == state_inc_progress: # process incidents in state IN PROGRESS, one by one, until there are't any
        blink(state_inc_progress)
        if g_dwell > g_wait:
            g_start = g_now
            if process_inprogress():
                g_state = state_wait
                write_log(fn_loop, log_state, g_state)
        # else process another one

    elif g_state == state_fault:
        blink(g_fault)
    else:
        g_state = state_fault
        write_log(fn_loop, log_state, g_state)
        g_fault = fault_invalid_state
        write_log(fn_loop, log_fault, g_fault)
        
    #watchdog.feed()
        
    if gc.mem_free() < (g_freemem -1000):
        g_freemem = gc.mem_free()
        write_log(fn_loop, log_freemem, g_freemem)
#while loop_run_flag

# stop gracefully & clean up
#led.off()
wlan.disconnect()
wlan.active(False)
# end