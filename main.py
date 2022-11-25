import machine
from machine import Pin, PWM
import utime
from umqtt.simple import MQTTClient
import rp2
import network
import ubinascii
import urequests as requests
import time
import socket
import secrets
import gc

gc.collect()

rp2.country('US')


# Wi-Fi and MQTT
wlan = network.WLAN(network.STA_IF)
wlan.active(True)

mac = ubinascii.hexlify(network.WLAN().config('mac'),':').decode()
print('mac = ' + mac)

ssid = secrets.ssid
password = secrets.pw
wlan.connect(ssid, password)

timeout = 10
while timeout > 0:
    if wlan.status() < 0 or wlan.status() >= 3:
        break
    timeout -= 1
    print('Waiting for connection...')
    time.sleep(1)
    
def blink_onboard_led(num_blinks):
    led = machine.Pin('LED', machine.Pin.OUT)
    for i in range(num_blinks):
        led.on()
        time.sleep(.2)
        led.off()
        time.sleep(.2)
        
wlan_status = wlan.status()
blink_onboard_led(wlan_status)

if wlan_status != 3:
    raise RuntimeError('Wi-Fi connection failed')
else:
    print('Connected')
    status = wlan.ifconfig()
    print('ip = ' + status[0])

mqtt_server = secrets.mqtt_id
client_id = ubinascii.hexlify(machine.unique_id())
topic_sub = b'Room 37'
topic_pub = b'Main'
topic_msg = b'Room 37 has connected.'

## MQTT Sub not working at the moment
# def sub_cb(topic, msg):
#     print("New message on topic {}".format(topic.decode('utf-8')))
#     msg = msg.decode('utf-8')
#     print(msg)
#     if msg == '21-1 On':
#         LED1.freq(600)
#         LED1.duty_u16(10000)
#         buzzer.freq(300)
#         buzzer.duty_u16(60000)
#         utime.sleep_ms(400)
#     elif msg == '21-1 Off':
#         LED1.duty_u16(0)
#         buzzer.duty_u16(0)
#         utime.sleep_ms(400)

def mqtt_connect():
    client = MQTTClient(client_id, mqtt_server)
    client.connect()
    print ('Connected to %s MQTT Broker'%(mqtt_server))
    return client

def reconnect():
    print('Failed to connect to the MQTT Broker. Reconnecting...')
    time.sleep(5)
    machine.reset()
    
try:
    client = mqtt_connect()
except OSError as e:
    reconnect()
    
client.publish(topic_pub, topic_msg)


def mqtt_connect():
    client = MQTTClient(client_id, mqtt_server)
    client.connect()
    print ('Connected to %s MQTT Broker'%(mqtt_server))
    return client

def reconnect():
    print('Failed to connect to the MQTT Broker. Reconnecting...')
    time.sleep(5)
    machine.reset()

# LEDs, Buttons, and Button Handlers

LED1 = PWM(Pin(0))
LED2 = PWM(Pin(15))
buzzer = PWM(Pin(22))

bed1_btn = Pin(1,Pin.IN,Pin.PULL_DOWN)
bed1_prev_state = bed1_btn.value()
bed2_btn = Pin(14,Pin.IN,Pin.PULL_DOWN)
bed2_prev_state = bed2_btn.value()
bed3_btn = Pin(27,Pin.IN,Pin.PULL_DOWN)
bed3_prev_state = bed3_btn.value()
bed4_btn = Pin(17,Pin.IN,Pin.PULL_DOWN)
bed4_prev_state = bed4_btn.value()
bth_btn = Pin(21,Pin.IN,Pin.PULL_DOWN)
bth_prev_state = bth_btn.value()
off_btn = Pin(4,Pin.IN,Pin.PULL_DOWN)
off_prev_state = off_btn.value()

# Button handlers
def bed1_handler():    
    global bed1_prev_state
    if (bed1_btn.value() == True) and (bed1_prev_state == False):
        bed1_prev_state = True
        utime.sleep_ms(400)

    elif (bed1_btn.value() == False) and (bed1_prev_state == True):
        bed1_prev_state = False
        LED1.freq(600)
        LED1.duty_u16(10000)
        buzzer.freq(300)
        buzzer.duty_u16(60000)
        utime.sleep_ms(400)
        client.publish('37-1', 'Room 37-1 has been pressed')
        print("Bed 1 has been pressed")
        
def bed2_handler():
    global bed2_prev_state
    if (bed2_btn.value() == True) and (bed2_prev_state == False):
        bed2_prev_state = True
        utime.sleep_ms(400)

    elif (bed2_btn.value() == False) and (bed2_prev_state == True):
        bed2_prev_state = False
        LED1.freq(600)
        LED1.duty_u16(10000)
        buzzer.freq(300)
        buzzer.duty_u16(60000)
        utime.sleep_ms(400)
        client.publish('37-2', 'Room 37-2 has been pressed')
        print("Bed 2 has been pressed")
        
# def bed3_handler():
#     global bed3_prev_state
#     if (bed3_btn.value() == True) and (bed3_prev_state == False):
#         bed3_prev_state = True
#         utime.sleep_ms(400)
# 
#     elif (bed3_btn.value() == False) and (bed3_prev_state == True):
#         bed3_prev_state = False
#         LED1.freq(600)
#         LED1.duty_u16(10000)
#         buzzer.freq(300)
#         buzzer.duty_u16(60000)
#         utime.sleep_ms(400)
#         client.publish('37-3', 'Room 37-3 has been pressed')
#         print("Bed 3 has been pressed")
        
# def bed4_handler():
#     global bed4_prev_state
#     if (bed4_btn.value() == True) and (bed4_prev_state == False):
#         bed4_prev_state = True
#         utime.sleep_ms(400)
# 
#     elif (bed4_btn.value() == False) and (bed4_prev_state == True):
#         bed4_prev_state = False
#         LED1.freq(600)
#         LED1.duty_u16(10000)
#         buzzer.freq(300)
#         buzzer.duty_u16(60000)
#         utime.sleep_ms(400)
#         client.publish('37-4', 'Room 37-4 has been pressed')
#         print("Bed 4 has been pressed")
        
def bth_handler():
    global bth_prev_state
    if (bth_btn.value() == True) and (bth_prev_state == False):
        bth_prev_state = True
        utime.sleep_ms(400)

    elif (bth_btn.value() == False) and (bth_prev_state == True):
        bth_prev_state = False
        LED2.freq(600)
        LED2.duty_u16(10000)
        buzzer.freq(300)
        buzzer.duty_u16(60000)
        utime.sleep_ms(400)
        client.publish('Bathroom 37 & 39', 'Bathroom 37 & 39 has been pressed')
        print("Bathroom 37 & 39 has been pressed")  
              
def off_handler():
    global off_prev_state
    if (off_btn.value() == True) and (off_prev_state == False):
        off_prev_state = True
        utime.sleep_ms(400)
        
    elif (off_btn.value() == False) and (off_prev_state == True):
        off_prev_state = False
        LED1.duty_u16(0)
        LED2.duty_u16(0)
        buzzer.duty_u16(0)
        utime.sleep_ms(400)
        client.publish('37-Off', 'Room 37 has been answered')
        print("Room 37 has been answered")

# Main Loop
while True:
    bed1_handler()
    bed2_handler()
#     bed3_handler()
#     bed4_handler()
    bth_handler()
    off_handler()

