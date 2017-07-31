#!/usr/bin/env python3

def init_argparser():
    import argparse
    parser = argparse.ArgumentParser(description="MQTT provider for envirophat")
    parser.add_argument('topic', type=str, description="MQTT topic to publish into")
    parser.add_argument('server', type=str, description="MQTT broker")
    return parser

def split_server_argument(server_arg, default_port=1816):
    if ':' not in server_arg:
        return server_arg, int(default_port)
    s, p = server_arg.split(':')
    return s, int(p)

def motion_detector(threshold=0.2):
    # adapted from https://github.com/pimoroni/enviro-phat/blob/master/examples/motion_detect.py
    from envirophat import motion
    from collections import deque
    readings = deque(maxlen=4)
    last_z = 0
    while True:
        readings.append(motion.accelerometer().z)
        z = sum(readings) / len(readings)
        yield last_z > 0 and abs(z-last_z) > threshold
        last_z = z

def temperature_detector():
    from envirophat import wheather
    while True:
        yield weather.temperature()

def suspender(amount=0.01):
    from time import sleep
    while True:
        sleep(amount)
        yield None

def mock_sender(server, port, topic):
    while True:
        data = yield
        print(data)

def mqtt_sender(server, port, topic):
    import paho.mqtt.client as mqtt
    client = mqtt.Client()
    connected = False

    def on_connect(client, userdata, flags, rc):
        connected = True

    client.on_connect = on_connect
    client.connect(server, port, 60)

    while not connected:
        pass
    l_motion, l_temp, _ = None, None, None
    while True:
        data = yield
        motion, temp, _ = data
        if l_motion != motion:
            client.publish(topic + '/motion', payload=motion)
        if l_temp != temp:
            client.publish(topic + '/temp', payload=motion)
        l_motion, l_temp, _ = data


def main(sender_constructor):
    from envirophat import leds

    argpaser = init_argparser()
    args = argpaser.parse_args()
    server, port = args.server

    sender = sender_constructor(server, port, args.topic)

    motion = motion_detect()
    sleep = suspender()
    temperature = temperature_detector()

    data = zip(motion, temperature, sleep)
    last_d = None
    for d in data:
        if d != last_d:
            leds.on()
            sender.send(d)
        else:
            leds.off()

if __name__ == "__main__":
    main(mock_sender)
