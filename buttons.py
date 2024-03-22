from neopixel import Neopixel
from mqtt_as import MQTTClient, config
import secrets
import uasyncio as asyncio
import utime as time
from machine import PWM, Pin
from logging import Logging
import gc

log = Logging()
# Buzzer
buzzer = PWM(Pin(28))
buzz_freq = 250
buzz_duty = 10000

pixels = Neopixel(4, 0, 27, "GRB")

magenta = (255,0,255)
orange = (255, 50, 0)
green = (0, 255, 0)
blue = (0, 0, 255)
red = (255, 0, 0)

bed1_btn = Pin(20,Pin.IN,Pin.PULL_UP)
bed1_prev_state = bed1_btn.value()
bed2_btn = Pin(18,Pin.IN,Pin.PULL_UP) #PCB layout reverses bed2 & off buttons
bed2_prev_state = bed2_btn.value()
bed3_btn = Pin(17,Pin.IN,Pin.PULL_UP)
bed3_prev_state = bed3_btn.value()
bed4_btn = Pin(16,Pin.IN,Pin.PULL_UP)
bed4_prev_state = bed4_btn.value()
bth_btn = Pin(19,Pin.IN,Pin.PULL_UP)
bth_prev_state = bth_btn.value()
off_btn = Pin(21,Pin.IN,Pin.PULL_UP) #PCB layout reverses bed2 & off buttons
off_prev_state = off_btn.value()
onboard_led = Pin('LED', Pin.OUT)

client = MQTTClient(config)


class ButtonController:
    def __init__(self):
        self.status = {'1': 'off', '2': 'off', '3': 'off', '4': 'off', secrets.BATHROOM: 'off'} # Initialize button state
    
    async def gc_clear(self):
        if gc.mem_free() <= 30000:
            gc.collect()
            # m.update_ram_count()
            await asyncio.sleep(0)

    def get_button_status(self, bed):
        return self.status.get(bed, 'off')

    def button_status(self, bed, current_status): # Handles button status per bed/bathroom.
        if bed in self.status and current_status in ('on', 'off'):
            self.status[bed] = current_status
            return True
        else:
            return False

    async def button_handler(self, bed, button, previous_state):
        while True:
            await asyncio.sleep(0)
            if not button.value() and not previous_state:
                if bed != secrets.BATHROOM:
                    await log.post(f"{secrets.ROOM_NUMBER}-{bed} pre-debounce triggered") # Logs pre-debounce. If pre-debounce is triggered and not followed by post-debounce, adjust debounce_ms.
                else:
                    await log.post(f'Bathroom {secrets.BATHROOM} pre-debounce triggered')
                time.sleep_ms(250) # Adds debounce - adjust accordingly.
                if not button.value() and not previous_state:
                    previous_state = True
                    await self.button_pressed(bed)
                    self.button_status(bed, 'on')
                    if bed != secrets.BATHROOM:
                        await log.post(f"{secrets.ROOM_NUMBER}-{bed} post-debounce triggered")
                    else:
                        await log.post(f'Bathroom {secrets.BATHROOM} post-debounce triggered')
            elif button.value() and previous_state:
                previous_state = False
                if bed != secrets.BATHROOM:
                    await log.post(f"{secrets.ROOM_NUMBER}-{bed} button released")
                else:
                    await log.post(f"Bathroom {secrets.BATHROOM} button released")
                await log.post(f'{self.status}')
                await self.gc_clear()
                await asyncio.sleep(0)
            await asyncio.sleep_ms(0)

    async def button_pressed(self, bed):
        await self.pixel_buzzer_on(bed)

    async def pixel_buzzer_on(self, bed):
        await asyncio.sleep_ms(0)
        if bed == "1":
            pixels.set_pixel_line(0, 0, orange)
        elif bed == "2":
            pixels.set_pixel_line(1, 1, magenta)
        elif bed == "3":
            pixels.set_pixel_line(2, 2, blue)
        elif bed == "4":
            pixels.set_pixel_line(3, 3, green)
        elif bed == secrets.BATHROOM:
            pixels.set_pixel_line(0, 3, red)
        pixels.show()
        buzzer.freq(buzz_freq)
        buzzer.duty_u16(buzz_duty)
        await log.post(f'{secrets.ROOM_NUMBER}-{bed} buzzer and light are on')
        await asyncio.sleep(0)

    async def off_handler(self, button, previous_state):
        while True:
            await asyncio.sleep(0)
            if not button.value() and not previous_state:
                await log.post(f'{secrets.ROOM_NUMBER}-off button pre-debounce triggered')
                time.sleep_ms(250)
                if not button.value() and not previous_state:
                    previous_state = True
                    await self.turn_off_all_beds()
                    await self.keep_on_if_still_pressed("1", bed1_btn.value())
                    await self.keep_on_if_still_pressed("2", bed2_btn.value())
                    await self.keep_on_if_still_pressed(secrets.BATHROOM, bth_btn.value())
                    if secrets.NUMBER_OF_BEDS > 2:
                        await self.keep_on_if_still_pressed("3", bed3_btn.value())
                        await self.keep_on_if_still_pressed("4", bed4_btn.value())
                    await log.post(f'{secrets.ROOM_NUMBER}-off button post-debounce triggered')
            elif button.value() and previous_state:
                previous_state = False
                await log.post(f'{secrets.ROOM_NUMBER}-off button released')
                await self.gc_clear()
                await asyncio.sleep(0)
            await asyncio.sleep_ms(0)

    async def turn_off_all_beds(self):
        pixels.clear()
        pixels.show()
        buzzer.duty_u16(0)
        for bed in self.status:
            self.button_status(bed, 'off')
            await log.post(f'{secrets.ROOM_NUMBER} all lights and buzzers are turned off')

    async def keep_on_if_still_pressed(self, bed, prev):
        if prev == False:
            await self.pixel_buzzer_on(bed)
            await log.post(f'{secrets.ROOM_NUMBER}-{bed} button still pressed')

    async def test_values(self):
        beds_to_check = ['1', '2', '3', '4', secrets.BATHROOM]
        previous_statuses = {bed: None for bed in beds_to_check}  # type: dict[str, Optional[str]]
        mqtt_sent_flags = {bed: False for bed in beds_to_check}  # Flag to track if MQTT message has been sent

        while True:
            for bed_to_check in beds_to_check:
                current_status = self.get_button_status(bed_to_check)

                if current_status != previous_statuses[bed_to_check]:

                    if current_status == "on" and not mqtt_sent_flags[bed_to_check]:
                        await self.publish_mqtt_if_connected("on", bed_to_check)
                        mqtt_sent_flags[bed_to_check] = True
                    elif current_status == "off" and mqtt_sent_flags[bed_to_check]:
                        await self.publish_mqtt_if_connected("off")
                        mqtt_sent_flags[bed_to_check] = False  # Reset the flag when status is "off"
                    previous_statuses[bed_to_check] = current_status 
            await asyncio.sleep_ms(0)

    async def publish_mqtt_if_connected(self, status, bed=None):
        retries = 10
        retry_count = 0

        if client.isconnected() == True:
            await asyncio.sleep(0)
            try:
                if status == "on":
                    if bed == secrets.BATHROOM:
                        await client.publish(f'Bathroom {secrets.BATHROOM}', f'Bathroom {secrets.BATHROOM} has been pressed', qos=1)
                    else:
                        await client.publish(f'{secrets.ROOM_NUMBER}-{bed}', f'Room {secrets.ROOM_NUMBER}-{bed} has been pressed', qos=1)
                elif status == 'off':
                    await client.publish(f'{secrets.ROOM_NUMBER}-Off', f'Room {secrets.ROOM_NUMBER} has been answered', qos=1)
            except Exception as e:
                # Handle the exception here
                log.dprint('Error publishing message: %s', e)
        else:
            while client.isconnected() == False and retry_count < retries:
                try:
                    if status == "on":
                        if bed == secrets.BATHROOM:
                            await client.publish(f'Bathroom {secrets.BATHROOM}', f'Bathroom {secrets.BATHROOM} has been pressed', qos=1)
                        else:
                            await client.publish(f'{secrets.ROOM_NUMBER}-{bed}', f'Room {secrets.ROOM_NUMBER}-{bed} has been pressed', qos=1)
                    elif status == 'off':
                        await client.publish(f'{secrets.ROOM_NUMBER}-Off', f'Room {secrets.ROOM_NUMBER} has been answered', qos=1)
                    retry_count += 1
                except Exception as e:
                    # Handle the exception here
                    log.dprint('Error publishing message: %s', e)
            # log.dprint('Outages Detected: %s', o.outages_count)
            await asyncio.sleep_ms(0)


    async def button_action_mapping(self, decoded_msg):
        print(decoded_msg)
        action_mapping = {
            f"Room {secrets.ROOM_NUMBER}-1 has been pressed": lambda: self.handle_room_pressed(0, 0, orange),
            f"Room {secrets.ROOM_NUMBER}-2 has been pressed": lambda: self.handle_room_pressed(1, 1, magenta),
            f"Room {secrets.ROOM_NUMBER}-3 has been pressed": lambda: self.handle_room_pressed(2, 2, blue),
            f"Room {secrets.ROOM_NUMBER}-4 has been pressed": lambda: self.handle_room_pressed(3, 3, green),
            f"Bathroom {secrets.BATHROOM} has been pressed": lambda: self.handle_room_pressed(0, 3, red),
            f"Room {secrets.ROOM_NUMBER} has been answered": lambda: self.handle_answered(),
        }

        if decoded_msg in action_mapping:
            await action_mapping[decoded_msg]()  # Execute the corresponding function
            await asyncio.sleep(0)

    async def handle_room_pressed(self, pixel_line, pixel_index, color):
        pixels.set_pixel_line(pixel_line, pixel_index, color)
        pixels.show()
        buzzer.freq(buzz_freq)
        buzzer.duty_u16(buzz_duty)
        await asyncio.sleep(0)
    
    async def handle_answered(self):
        await self.turn_off_all_beds()
        await asyncio.sleep(0)
