Servicenow-on-Pico

A proof of concept which creates a ServiceNow ticket from a Raspberry Pi Pico W, lights the LED, and extinguishes the LED when the ticket is resolved.

at https://github.com/contrarotator/Servicenow-on-Pico

To make it work:
    Browse to https://developer.servicenow.com
    Sign in as yourself
    Create a developer instance.  ( For this demo I used Quebec release. )
    Sign in to your instance as admin
    Select a user to act as the web API access security entity.
        set a pessword for this user
        assign the itil role to this user
    Sign it to the dev instance as this user
        (actually you can sign in as any user with the itil role)
    Unbox your Raspberry Pi Pico W
    Following the instructions on raspberrypi.com, download and install the Micropython firmware (.uf2 file)
    Connect your Pico to the computer and IDE of your choice ( I used a Mac running Thonny. )
    Download the pico-servicenowdemo.py file and open it in your editor or IDE (Thonny)
    In the appropriate variables, set the appropriate
        WLAN SSID, WLAN password,
        your Servicenow instance URL, 
        your chosen user ID and their password
    Save and run.
    If all goes well, there will be no error message and on the Pico the LED will light
    Note the INC incident number in the Python console
    In your browser, refresh the incident view
        at yourinstance.service-now.com/nav_to.do?uri=%2Fincident_list.do
           %3Fsysparm_first_row%3D1%26sysparm_query%3D%26sysparm_view%3Dess
    Identify the incident by number
    Open the incident, enter a work note, and resolve it.
    Admire your Pico W.
    The LED should go out within a few seconds.

