# ServiceNow-on-Pico
pico_servicenowdemo.py is simple script which creates a ServiceNow ticket from a Raspberry Pi Pico W, lights the LED, and extinguishes the LED when the ticket is resolved.

pico-w_servicenow_reporter.py is a script which waits for a trigger (pushbutton) then raises an incident in ServiceNow, and illuminates a LED.  When the incident is resolved, the LED is extinguished.

pico-w_servicenow_resolver.py is a script which polls for incidents of given characteristics (State = New and Assignment Group = telemetry.devices), and for each one, adds a worklog comment, assigns it, and moves to state In Progress.
It then polls for another set of characteristics (State = In Progress and Assignment Group = telemetry.devices), and for each one, adds a worklog comment and resolution details and then moves it to state Resolved.

There is a video demonstration of pico-w_servicenow_reporter.py  and pico-w_servicenow_resolver.py running on Raspberry Pico W devices at https://www.youtube.com/watch?v=YYB5UvLNOlw
