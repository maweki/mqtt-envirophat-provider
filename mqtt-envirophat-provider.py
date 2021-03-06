#!/usr/bin/env python3

def init_argparser():
    import argparse
    parser = argparse.ArgumentParser(description="MQTT provider for envirophat")
    parser.add_argument('server', type=str, help="MQTT broker")
    parser.add_argument('topic', type=str, help="MQTT topic to publish into")
    parser.add_argument('--auth', type=str, help="Auth information (\"username\" or \"username:password\")")
    parser.add_argument('-t', type=float, help="temperature correction", default=0.0)
    parser.add_argument('-i', type=float, help="update interval", default=0.01)
    parser.add_argument('--mock', action='store_const', const=True)
    return parser

def split_server_argument(server_arg, default_port=1816):
    if ':' not in server_arg:
        return server_arg, int(default_port)
    s, p = server_arg.split(':')
    return s, int(p)

def split_auth_argument(auth_arg):
    if ':' not in auth_arg:
        return auth_arg, None
    u, p = auth_arg.split(':')
    return u, p

def motion_detector(threshold=0.1):
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

def temperature_detector(correction=0):
    from envirophat import weather
    while True:
        yield round(weather.temperature()+ correction, 1)

def suspender(amount=0.01):
    from time import sleep
    while True:
        sleep(amount)
        yield None

def mock_sender(server, port, topic):
    while True:
        data = yield
        print(data)

def mqtt_sender(server, port, topic, username=None, password=None):
    import paho.mqtt.client as mqtt
    import json
    client = mqtt.Client()
    if username:
        client.username_pw_set(username, password)

    client.connect(server, port, 60)

    l_motion, l_temp, _ = None, None, None
    while True:
        data = yield
        motion, temp, _ = data
        ret = 0
        if l_motion != motion:
            ret, _ = client.publish(topic + '/motion', payload=json.dumps({"data": motion}))
        if l_temp != temp:
            ret, _ = client.publish(topic + '/temp', payload=json.dumps({"data": temp}))
        l_motion, l_temp, _ = data
        if ret != 0:
            client.connect(server, port, 60)

def main(sender_constructor, server, port, username, password, topic, temp_correction, update_interval):
    from envirophat import leds, light

    sender = sender_constructor(server, port, topic, username, password)
    next(sender) # prime the generator

    motion = motion_detector()
    sleep = suspender(update_interval)
    temperature = temperature_detector(correction=temp_correction)

    data = zip(motion, temperature, sleep)
    last_d = None
    for d in data:
        if d != last_d:
            sender.send(d)
        last_d = d

if __name__ == "__main__":
    from time import sleep
    argpaser = init_argparser()
    args = argpaser.parse_args()
    server, port = split_server_argument(args.server)
    if "auth" in args:
        username, password = split_auth_argument(args.auth)
    else:
        username, password = None, None

    while True:
        sleep(10)
        try:
            main(mock_sender if args.mock else mqtt_sender, server, port, username, password, args.topic, args.t, args.i)
        except OSError:
            continue
        except KeyboardInterrupt:
            break
        except Exception:
            break
