import time
import smbus
import os
import paho.mqtt.client as mqtt
import requests

# Functie om gewenste waarde op te halen van ThingSpeak
def haal_gewenste_waarde_van_thingspeak():
    try:
        url = f"https://api.thingspeak.com/channels/{THINGSPEAK_CHANNEL_ID}/fields/2/last.json?api_key={THINGSPEAK_READ_API_KEY}"
        response = requests.get(url)
        if response.status_code == 200:
            data = response.json()
            return float(data["field2"])
        else:
            print(f"Fout bij ophalen van gewenste waarde: HTTP {response.status_code}")
            return 20.0  # Standaardwaarde bij fout
    except Exception as e:
        print(f"Fout bij ophalen van gewenste waarde: {e}")
        return 20.0  # Standaardwaarde bij fout

# Configuratie BH1750
BH1750_ADDRESS = 0x23
BH1750_CONT_HIGH_RES_MODE = 0x10

# GPIO-configuratie via sysfs
LED_PIN = 120  # GPIO-pin voor LED
BUTTON_UP = 119  # GPIO-pin voor knop omhoog
BUTTON_DOWN = 111  # GPIO-pin voor knop omlaag

# MQTT-configuratie
MQTT_HOST = "mqtt3.thingspeak.com"
MQTT_PORT = 1883
MQTT_KEEPALIVE_INTERVAL = 60
MQTT_TOPIC = "channels/2792379/publish"  # Luxwaarde topic
MQTT_TOPIC_GEWENST = "channels/2792381/publish"  # Gewenste waarde topic
MQTT_CLIENT_ID = "FSAYKSskHAw3CR8lKiczGAM"
MQTT_USER = "FSAYKSskHAw3CR8lKiczGAM"
MQTT_PWD = "R+I6VlXCXDQeCmUeQ10kx/VV"

# ThingSpeak Read API-configuratie
THINGSPEAK_READ_API_KEY = "94U2IKT6YRPREMPN"  # Vervang door jouw ThingSpeak Read API Key
THINGSPEAK_CHANNEL_ID = "2792381"  # Kanaal-ID voor gewenste waarde

# Initialiseer I2C-bus
bus = smbus.SMBus(0)  # Gebruik I2C-bus 0

# Haal de initiële gewenste waarde op
DREMPEL_LUX = haal_gewenste_waarde_van_thingspeak()
print(f"Initiële gewenste waarde opgehaald van ThingSpeak: {DREMPEL_LUX:.2f}")

# Functie om GPIO te configureren via sysfs
def configure_gpio(pin, direction):
    try:
        if os.path.exists(f"/sys/class/gpio/gpio{pin}"):
            with open("/sys/class/gpio/unexport", "w") as f:
                f.write(str(pin))

        with open("/sys/class/gpio/export", "w") as f:
            f.write(str(pin))

        with open(f"/sys/class/gpio/gpio{pin}/direction", "w") as f:
            f.write(direction)
    except Exception as e:
        print(f"Fout bij GPIO-configuratie: {e}")
        exit(1)

# Functie om GPIO-waarde te lezen via sysfs
def read_gpio(pin):
    try:
        with open(f"/sys/class/gpio/gpio{pin}/value", "r") as f:
            return int(f.read().strip())
    except Exception as e:
        print(f"Fout bij GPIO-waarde lezen: {e}")
        return 0

# Functie om GPIO-waarde te schrijven via sysfs
def write_gpio(pin, value):
    try:
        with open(f"/sys/class/gpio/gpio{pin}/value", "w") as f:
            f.write(str(value))
    except Exception as e:
        print(f"Fout bij GPIO-waarde schrijven: {e}")

# Functie om lux-waarden van de BH1750 te lezen
def lees_lux():
    try:
        bus.write_byte(BH1750_ADDRESS, BH1750_CONT_HIGH_RES_MODE)
        time.sleep(0.2)  # Wacht op meting
        data = bus.read_i2c_block_data(BH1750_ADDRESS, 2)
        lux = (data[0] << 8 | data[1]) / 1.2  # Omrekenen naar lux
        return lux
    except Exception as e:
        print(f"Fout bij het lezen van de lichtsensor: {e}")
        return 0

# Functie om MQTT-bericht te publiceren
def publiceer_naar_mqtt(client, topic, bericht):
    try:
        client.publish(topic, bericht)
    except Exception as e:
        print(f"Fout bij het publiceren naar MQTT: {e}")

# Functie om gewenste waarde op te halen van ThingSpeak
def haal_gewenste_waarde_van_thingspeak():
    try:
        url = f"https://api.thingspeak.com/channels/{THINGSPEAK_CHANNEL_ID}/fields/2/last.json?api_key={THINGSPEAK_READ_API_KEY}"
        response = requests.get(url)
        if response.status_code == 200:
            data = response.json()
            return float(data["field2"])
        else:
            print(f"Fout bij ophalen van gewenste waarde: HTTP {response.status_code}")
            return DREMPEL_LUX  # Standaardwaarde bij fout
    except Exception as e:
        print(f"Fout bij ophalen van gewenste waarde: {e}")
        return DREMPEL_LUX  # Standaardwaarde bij fout

# GPIO configureren
configure_gpio(LED_PIN, "out")
configure_gpio(BUTTON_UP, "in")
configure_gpio(BUTTON_DOWN, "in")

# MQTT-client instellen
client = mqtt.Client(client_id=MQTT_CLIENT_ID)
client.username_pw_set(MQTT_USER, MQTT_PWD)

try:
    client.connect(MQTT_HOST, MQTT_PORT, MQTT_KEEPALIVE_INTERVAL)
    print("Verbonden met MQTT-broker")
except Exception as e:
    print(f"Kan niet verbinden met MQTT-broker: {e}")
    exit(1)

# Publiceer de gewenste lux-waarde in field2
publiceer_naar_mqtt(client, MQTT_TOPIC_GEWENST, f"field2={DREMPEL_LUX:.2f}")

# Testprogramma
try:
    while True:
        lux = lees_lux()
        print(f"Lichtintensiteit: {lux:.2f} lux")

        # Haal de gewenste waarde op van ThingSpeak
        DREMPEL_LUX = haal_gewenste_waarde_van_thingspeak()
        print(f"De gewenste lux waarde op ThingSpeak is: {DREMPEL_LUX:.2f}")

        # Publiceer lux-waarde naar MQTT in field2
        publiceer_naar_mqtt(client, MQTT_TOPIC, f"field2={lux:.2f}")

        # Controleer drukknoppen
        if read_gpio(BUTTON_UP) == 1:
            DREMPEL_LUX += 10
            if DREMPEL_LUX > 200:
                DREMPEL_LUX = 200
            publiceer_naar_mqtt(client, MQTT_TOPIC_GEWENST, f"field2={DREMPEL_LUX:.2f}")
            print(f"Gewenste waarde verhoogd naar: {DREMPEL_LUX}")
            time.sleep(0.3)  # Debounce

        if read_gpio(BUTTON_DOWN) == 1:
            DREMPEL_LUX -= 10
            if DREMPEL_LUX < 0:
                DREMPEL_LUX = 0
            publiceer_naar_mqtt(client, MQTT_TOPIC_GEWENST, f"field2={DREMPEL_LUX:.2f}")
            print(f"Gewenste waarde verlaagd naar: {DREMPEL_LUX}")
            time.sleep(0.3)  # Debounce

        # LED aanzetten als de lux-waarde onder de drempel is
        if lux < DREMPEL_LUX:
            write_gpio(LED_PIN, 1)  # LED aan
            print("LED AAN")
        else:
            write_gpio(LED_PIN, 0)  # LED uit
            print("LED UIT")

        time.sleep(1)  # Wacht 1 seconde voordat de volgende meting wordt uitgevoerd

except KeyboardInterrupt:
    print("Programma gestopt")
    write_gpio(LED_PIN, 0)  # Zet de LED uit

    # GPIO vrijgeven
    try:
        with open("/sys/class/gpio/unexport", "w") as f:
            f.write(str(LED_PIN))
            f.write(str(BUTTON_UP))
            f.write(str(BUTTON_DOWN))
    except Exception as e:
        print(f"Fout bij het vrijgeven van GPIO: {e}")

    client.disconnect()
    print("MQTT-verbinding verbroken")
