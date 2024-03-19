"""
Garage Door Controller code
By Kevin Chung @ Unidata Ptd Ltd 2022
V1.1 - added pin 21 door open (1=open, 0=close)  Pull high

only serves /garage /status and /siri

/siri require GET HEADER key PASS = passcode and key ACTION =[OPEN,CLOSE]

Adapted from examples in: https://datasheets.raspberrypi.com/picow/connecting-to-the-internet-with-pico-w.pdf
"""
import sys
import urequests
import time
import utime
import network
import uasyncio as asyncio
import json
from machine import Pin, WDT
import machine
from secret import ssid, password, duckdomains, ducktoken, passcode, doorpath, siripath, statuspath, doorsensor
# Hardware definitions
led = Pin(2, Pin.OUT, value=1)
pin_action = Pin(5, Pin.OUT, value=0)
#pin_door = Pin(21, Pin.IN, Pin.PULL_UP)

# Configure your WiFi SSID and password


check_interval_sec = 2.25

wlan = network.WLAN(network.STA_IF)

#<center> <button class="buttonRed" name="ACTION" value="CLOSE" type="submit"> CLOSE </button>
# The following HTML defines the webpage that is served
html = """<!DOCTYPE html><html>
<head><meta name="viewport" content="width=device-width, initial-scale=1">
<link rel="icon" href="data:,">
<style>html { font-family: Helvetica; display: inline-block; margin: 0px auto; text-align: center;}
.button { background-color: #4CAF50; border: 2px solid #000000;; color: white; padding: 15px 32px; text-align: center; text-decoration: none; display: inline-block; font-size: 16px; margin: 4px 2px; cursor: pointer; }
.buttonRed { background-color: #d11d53; border: 2px solid #000000;; color: white; padding: 15px 32px; text-align: center; text-decoration: none; display: inline-block; font-size: 16px; margin: 4px 2px; cursor: pointer; }
text-decoration: none; font-size: 30px; margin: 2px; cursor: pointer;}
</style></head>
<body><center><h1>Test Garage Door </h1></center>
<center><h3> Door Status : <Strong>%s</strong> </h3></center>
<center><h3> Uptime : %s </h3></center><br><br>
<form method="post"><center>
<center> <input class="button" name="PASS" type="password" placeholder="Password">
<br><br>
<center> <button class="buttonRed"  name="ACTION" value="MOVE" type="submit"> %s </button>

<br><br> </form>
</body></html>
"""


def blink_led(frequency = 0.5, num_blinks = 3):
    for _ in range(num_blinks):
        led.off()
        time.sleep(frequency)
        led.on()
        time.sleep(frequency)

def control_door(cmd):
      
    if cmd == 'move':
        pin_action.on()
        blink_led(0.1, 1)
        time.sleep(0.25)
        pin_action.off()
 
 
async def connect_to_wifi():
    wlan.active(True)
   # wlan.config(pm = 0xa11140)  # Disable powersave mode
    wlan.ifconfig(('192.168.100.113','255.255.255.0','192.168.100.1','192.168.1.1'))
    
    wlan.connect(ssid, password)

    # Wait for connect or fail
    max_wait = 30
    while max_wait > 0:
        if wlan.isconnected():
            break
        max_wait -= 1
        print('waiting for connection... ' +str(max_wait))
        time.sleep(2)

    # Handle connection error
    if not wlan.isconnected():
        blink_led(0.1, 10)
        print('WiFi connection failed')
        WDT()
    else:
        blink_led(0.5, 2)
        print('connected')
        status = wlan.ifconfig()
        print('ip = ' + status[0])
        if duckdomains != ' ' :
            while True:
                try:
                    print('Updating Duckdns...' + duckdomains)
                    response = urequests.get("https://www.duckdns.org/update?domains="+ duckdomains + "&token=" + ducktoken + "&ip=")
                    response.close()
                    print('Duckdns updated')
                    #print(response)
                    await asyncio.sleep(1800) # 60mins or 3600sec
                
                except:
                    await asyncio.sleep(60)
                    WDT()



async def serve_client(reader, writer):
    print("Client connected")
    request_line = await reader.readline()    # Read URL 
    request = str(request_line)
    body = request
    request_line = await reader.readline()    #Read Host line
    body = body + str(request_line)
    # Read more until blank line
    while request_line != b"\r\n":
        request_line = await reader.readline()
        body = body + str(request_line)
    
    #print("Request:", request)
    #print("Body:", body)
    # body = ''
    
    if request.find('POST') > 0:  #Post Method
        #l = body.find("Content-Length:")
        bodylist = body.split("\\r\\n'b'")
        
        for i in range(len(bodylist)):
            if str(bodylist[i]).startswith('Content-Length'):
                postlen = bodylist[i]
        rlen=int(str(postlen[16:(len(postlen))]))  # extract content length
        #print (rlen)
        postdata = await reader.read(rlen)
        request = request + str(postdata) # append POST data to request variable
        #print(postdata)
        print(request)
    #else:  # Not POST
    #    writer.write('HTTP/1.0 200 OK\r\nContent-type: text/html\r\n\r\n')
    #    return
     
     # Find which URL the call coming from
    garage_ok = request.find(doorpath)
    siri_ok = request.find(siripath)
    status_ok = request.find(statuspath)

# Set door status and uptime
    if doorsensor == 1:
        if pin_door.value() == 1:
            door_status = 'Opened'
            button = ' CLOSE  '
            door_open = 1
        else:
            door_status = 'Closed'
            button = ' OPEN '
            door_open = 0
    else:
        button = ' Open/Close '
        door_status = '** Unknown **'
        door_open = 2
        
    uptime =  str(time.time() - timeInit) + ' Sec'
    door_status ='NodeMCUv3 11xx:6164'
# print ("Door Status", door_status, door_open)
# find() valid garage-door commands within the request
 
    cmd_action = -1
    pass_ok = -1

    if garage_ok > 0:
        cmd_action = request.find('ACTION=MOVE')
        pass_ok = request.find(passcode)

    elif siri_ok > 0:
        cmd_open = request.find('ACTION=OPEN')
        cmd_close = request.find('ACTION=CLOSE')
        pass_ok = request.find(passcode)
        
    elif status_ok > 0:
        if doorsensor == 1 and door_open == 0:
         #print('Closed')
            writer.write('HTTP/1.0 200 OK\r\nContent-type: text/html\r\n\r\n')
            writer.write('<!DOCTYPE html 1.1><html><body>Garage Door is Closed</body></html>')
            #writer.write('closed')
        elif doorsensor == 1 and door_open == 1:
        #print('Open')
            writer.write('HTTP/1.0 200 OK\r\nContent-type: text/html\r\n\r\n')
            writer.write('<!DOCTYPE html 1.1><html><body>Garage Door is Opened</body></html>')
            #writer.write('open')
        elif doorsensor == 0:
            writer.write('HTTP/1.0 200 OK\r\nContent-type: text/html\r\n\r\n')
            writer.write('<!DOCTYPE html 1.1><html><body>Door status is Unknown</body></html>')
            #writer.write('unknown')
    else:  # unknown command
     #print('Open')
        writer.write('HTTP/1.0 200 OK\r\nContent-type: text/html\r\n\r\n')
        writer.write('<!DOCTYPE html 1.1><html><body>Unknown Command</body></html>')

    #Check if passcode is correct in Siri or Garage Mode
    if pass_ok > 0 and (garage_ok > 0 or siri_ok > 0 ):
        # See if we have a good path & command    
        if garage_ok > 0:
            control_door('move')
            response = html % (door_status, uptime, button)
            writer.write('HTTP/1.0 200 OK\r\nContent-type: text/html\r\n\r\n')
            writer.write(response)
        
        elif siri_ok > 0:    
        #  print(siri_ok, cmd_open, cmd_close, door_open)
            if doorsensor == 1 :
                if cmd_open > 0 and door_open == 0:
                    writer.write('HTTP/1.0 200 OK\r\nContent-type: text/html\r\n\r\n')
                    writer.write('<!DOCTYPE html 1.1><html><body>Garage Door Opening.</body></html>')
                    control_door('move')
                elif cmd_open > 0 and door_open == 1:
                    writer.write('HTTP/1.0 200 OK\r\nContent-type: text/html\r\n\r\n')
                    writer.write('<!DOCTYPE html 1.1><html><body>Not Possible, its already Opened.</body></html>')
                elif cmd_close > 0 and door_open == 1:
                    writer.write('HTTP/1.0 200 OK\r\nContent-type: text/html\r\n\r\n')
                    writer.write('<!DOCTYPE html><html><body>Garage Door Closing.</body></html>')
                    control_door('move')
                elif  cmd_close > 0 and door_open == 0:
                    writer.write('HTTP/1.0 200 OK\r\nContent-type: text/html\r\n\r\n')
                    writer.write('<!DOCTYPE html><html><body>Not Possible, Its already Closed.</body></html>')
                else:
                    writer.write('HTTP/1.0 200 OK\r\nContent-type: text/html\r\n\r\n')
                
            else: # Does not have door open sensor
                if cmd_open > 0 or cmd_close > 0:
                    writer.write('HTTP/1.0 200 OK\r\nContent-type: text/html\r\n\r\n')
                    writer.write('<!DOCTYPE html 1.1><html><body>Changing Garage Door status.</body></html>')
                    control_door('move')
        
        else:  # final catch
            writer.write('HTTP/1.0 200 OK\r\nContent-type: text/html\r\n\r\n')
    elif garage_ok > 0 :  #Passcode ERROR in Garage
        response = html % (door_status, uptime, button )
        writer.write('HTTP/1.0 200 OK\r\nContent-type: text/html\r\n\r\n')
        writer.write(response)
    elif status_ok < 0:
        writer.write('HTTP/1.0 200 OK\r\nContent-type: text/html\r\n\r\n')
        

    await writer.drain()
    await writer.wait_closed()


async def main():
    print('Connecting to WiFi...')
    asyncio.create_task(connect_to_wifi())


    print('Setting up webserver...')
    asyncio.create_task(asyncio.start_server(serve_client, "0.0.0.0", 6164))

    while True:
        await asyncio.sleep(check_interval_sec)
        if wlan.isconnected():
            blink_led(0.5, 1)
        else:
            blink_led(0.05, 10)
try:
    timeInit = time.time()
    asyncio.run(main())
finally:
    asyncio.new_event_loop()






