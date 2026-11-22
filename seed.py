"""Receive kit inventories into PartsBin, merging by part name. Already-received kits are skipped."""
from partsbin import create_app
from partsbin.db import get_db
from partsbin.intake import receive

KITS = {
    "LAFVIN Super Starter (UNO R3)": [
        ("Boards", "Arduino UNO R3", 1, "atmega328p, 5v"),
        ("Boards", "UNO prototype expansion shield", 1, ""),
        ("Breadboards & Power", "Breadboard 830", 1, ""),
        ("Breadboards & Power", "Breadboard power supply module", 1, "3.3v, 5v"),
        ("Breadboards & Power", "9V battery connector (DC plug)", 1, ""),
        ("Displays", "LCD1602", 1, "parallel"),
        ("Displays", "7-segment display 4-digit", 1, ""),
        ("Displays", "7-segment display 1-digit", 1, ""),
        ("Motors & Actuators", "SG90 servo", 1, "pwm"),
        ("Motors & Actuators", "28BYJ-48 stepper motor", 1, "5v"),
        ("Motors & Actuators", "ULN2003 stepper driver", 1, ""),
        ("Motors & Actuators", "DC motor 3V + fan blade", 1, ""),
        ("Motors & Actuators", "Relay module 5V 1-channel", 1, ""),
        ("ICs", "L293D motor driver", 1, "h-bridge"),
        ("ICs", "74HC595 shift register", 1, ""),
        ("Input", "IR remote", 1, ""),
        ("Sensors", "IR receiver", 1, ""),
        ("Input", "Joystick module", 1, "analog"),
        ("Input", "4x4 membrane keypad", 1, ""),
        ("Input", "Potentiometer 10K", 1, "analog"),
        ("Input", "Push button (tactile)", 5, ""),
        ("Sensors", "Tilt switch", 1, ""),
        ("Sensors", "HC-SR04 ultrasonic", 1, "5v"),
        ("Sensors", "DHT11 temp/humidity", 1, ""),
        ("Sensors", "Sound sensor module", 1, "analog"),
        ("Sensors", "Water level sensor", 1, "analog"),
        ("Sensors", "Photoresistor (bare)", 2, "analog"),
        ("Sensors", "Thermistor (bare)", 1, "analog"),
        ("Sound", "Active buzzer", 1, ""),
        ("Sound", "Passive buzzer", 1, "pwm"),
        ("Discretes", "PN2222 transistor", 2, "npn"),
        ("Discretes", "1N4007 diode", 2, ""),
        ("Discretes", "Resistor assortment", 100, ""),
        ("LEDs", "RGB LED (bare)", 1, ""),
        ("LEDs", "LED red 5mm", 5, ""),
        ("LEDs", "LED yellow 5mm", 5, ""),
        ("LEDs", "LED blue 5mm", 5, ""),
        ("LEDs", "LED green 5mm", 5, ""),
        ("LEDs", "LED white 5mm", 5, ""),
        ("Wiring", "Jumper wire M-M", 65, ""),
        ("Wiring", "Dupont wire F-M", 10, ""),
    ],
    "LAFVIN ESP32 Basic Starter": [
        ("Boards", "ESP32 dev board (micro-USB)", 1, "wifi, bluetooth, 3.3v"),
        ("Breadboards & Power", "Micro-USB cable", 1, ""),
        ("Breadboards & Power", "Breadboard 830", 1, ""),
        ("Displays", "OLED 0.96in SSD1306", 1, "i2c"),
        ("Sensors", "HC-SR501 PIR motion", 1, ""),
        ("Sensors", "DHT11 temp/humidity", 1, ""),
        ("Sensors", "Obstacle avoidance IR module", 1, "digital"),
        ("Sensors", "Photoresistor module", 1, "analog, digital"),
        ("Input", "Push button (tactile, colored cap)", 6, ""),
        ("Input", "Potentiometer 10K", 1, "analog"),
        ("Motors & Actuators", "Relay module 5V 2-channel", 1, ""),
        ("Sound", "Active buzzer", 1, ""),
        ("Sound", "Passive buzzer", 1, "pwm"),
        ("LEDs", "RGB LED (bare)", 2, ""),
        ("LEDs", "LED red 5mm", 5, ""),
        ("LEDs", "LED yellow 5mm", 5, ""),
        ("LEDs", "LED green 5mm", 5, ""),
        ("Discretes", "Resistor assortment", 30, "220R, 1k, 10k"),
        ("Wiring", "Dupont wire F-M", 10, ""),
        ("Wiring", "Dupont wire F-F", 10, ""),
        ("Wiring", "Dupont wire M-M", 10, ""),
    ],
    "HiLetgo 37-in-1 Sensors #1": [
        ("Input", "Joystick module", 1, "analog"),
        ("Input", "Button module", 1, ""),
        ("Sensors", "Touch sensor module", 1, ""),
        ("Input", "Rotary encoder module", 1, ""),
        ("Sensors", "Photoresistor module", 1, "analog, digital"),
        ("Sensors", "Light blocking (photo interrupter)", 1, "tripwire"),
        ("LEDs", "IR emitter module", 1, ""),
        ("Sensors", "IR receiver", 1, ""),
        ("LEDs", "Laser emitter module", 1, "tripwire"),
        ("Sensors", "Flame sensor", 1, ""),
        ("Sensors", "Line tracking sensor", 1, ""),
        ("Sensors", "Obstacle avoidance IR module", 1, "digital"),
        ("Sensors", "Big sound sensor (high sensitivity)", 1, "analog, digital"),
        ("Sensors", "Small sound sensor", 1, "analog, digital"),
        ("Sound", "Active buzzer", 1, ""),
        ("Sound", "Passive buzzer", 1, "pwm"),
        ("Sensors", "Hall magnetic sensor (digital)", 1, "magnet"),
        ("Sensors", "Linear hall sensor", 1, "magnet"),
        ("Sensors", "Analog hall sensor", 1, "magnet"),
        ("Sensors", "Reed switch module", 1, "magnet"),
        ("Sensors", "Mini reed module", 1, "magnet"),
        ("Sensors", "Tilt switch (mercury)", 1, ""),
        ("Sensors", "Ball tilt switch", 1, ""),
        ("Sensors", "Shock / vibration switch", 1, ""),
        ("Sensors", "Tap / knock module", 1, ""),
        ("Sensors", "Magic light cup", 2, ""),
        ("Sensors", "DS18B20 temp", 1, "1-wire"),
        ("Sensors", "Digital temp module", 1, ""),
        ("Sensors", "Analog temp module", 1, "analog"),
        ("Sensors", "DHT11 temp/humidity", 1, ""),
        ("Sensors", "Heartbeat sensor", 1, "analog"),
        ("LEDs", "RGB LED module", 1, ""),
        ("LEDs", "SMD RGB module", 1, ""),
        ("LEDs", "Two-color LED module", 1, ""),
        ("LEDs", "Mini two-color LED module", 1, ""),
        ("LEDs", "7-color flash LED module", 1, ""),
        ("Motors & Actuators", "Relay module 5V 1-channel", 1, ""),
    ],
    "Amazon 2026-11-18 loose boards": [
        ("Boards", "ESP32 dev board (ELEGOO ESP-WROOM-32, USB-C)", 3, "wifi, bluetooth, 3.3v, usb-c",
         "https://www.amazon.com/dp/B0D8T53CQ5"),
        ("Boards", "Digispark ATtiny85 (micro-USB)", 5, "attiny85, usb-hid, 5v",
         "https://www.amazon.com/dp/B0836WXQQR"),
    ],
}


def main():
    app = create_app()
    with app.app_context():
        db = get_db()
        for source, parts in KITS.items():
            if receive(db, source, parts):
                print(f"received {source}: {len(parts)} lines")
            else:
                print(f"skip {source} (already received)")


if __name__ == "__main__":
    main()
