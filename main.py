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

LED1 = Pin(0, Pin.OUT)
LED2 = Pin(15, Pin.OUT)
buzzer = PWM(Pin(22))

bed1_btn = Pin(1,Pin.IN,Pin.PULL_DOWN)
bed1_prev_state = bed1_btn.value()
off_btn = Pin(4,Pin.IN,Pin.PULL_DOWN)
off_prev_state = off_btn.value()

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
topic_sub = b'21 Sub'
topic_pub = b'21'
topic_msg = b'Test Msg'


def sub_cb(topic, msg):
    print("New message on topic {}".format(topic.decode('utf-8')))
    msg = msg.decode('utf-8')
    print(msg)
    if msg == '21-1 On':
        LED1.value(1)
        buzzer.freq(300)
        buzzer.duty_u16(60000)
        utime.sleep_ms(400)
    elif msg == '21-1 Off':
        LED1.value(0)
        buzzer.duty_u16(0)
        utime.sleep_ms(400)

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
    
# Button handlers


def bed1_handler():
    global bed1_prev_state
    if (bed1_btn.value() == True) and (bed1_prev_state == False):
        bed1_prev_state = True

    elif (bed1_btn.value() == False) and (bed1_prev_state == True):
        bed1_prev_state = False
        LED1.value(1)
        buzzer.freq(300)
        buzzer.duty_u16(60000)
        client.publish('21', 'Room 21-1 has been pressed')
        utime.sleep_ms(400)
        print("Bed 1 has been pressed")

def off_handler():
    global off_prev_state
    if (off_btn.value() == True) and (off_prev_state == False):
        off_prev_state = True
        
    elif (off_btn.value() == False) and (off_prev_state == True):
        off_prev_state = False
        LED1.value(0)
        buzzer.duty_u16(0)
        client.publish('21', 'Room 21 has been answered')
        utime.sleep_ms(400)
        print("Bed 1 has been answered")


while True:
        
    client.set_callback(sub_cb)
    client.subscribe(topic_sub)
    
    bed1_handler()
    off_handler()
