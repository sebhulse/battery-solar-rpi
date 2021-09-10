# !/usr/bin/env python
import time
import datetime
from ina219 import INA219, DeviceRangeError
from influxdb import InfluxDBClient
import Adafruit_DHT
from psutil import cpu_percent, disk_usage, virtual_memory, getloadavg
from gpiozero import CPUTemperature

# influx configuration
ifuser = ""
ifpass = ""
ifdb = "pi_energy"
ifhost = "localhost"
ifport = 8086
measurement_name = "energy_system2" # influxdb measurement table

# influx object
ifclient = InfluxDBClient(ifhost, ifport, ifuser, ifpass, ifdb)

# shunt resistor constants
SHUNT_OHMS = 0.00075
MAX_EXPECTED_AMPS = 100

# INA object instantiation with constants and i2c address
ina_battery = INA219(SHUNT_OHMS, MAX_EXPECTED_AMPS, address=0x40)
ina_battery.configure(ina_battery.RANGE_16V, ina_battery.GAIN_2_80MV)
ina_solar = INA219(SHUNT_OHMS, MAX_EXPECTED_AMPS, address=0x44)
ina_solar.configure(ina_solar.RANGE_16V, ina_solar.GAIN_2_80MV)

# DHT object instatiation
DHT_SENSOR = Adafruit_DHT.DHT22
DHT_PIN = 4


# get battery shunt data
def get_battery_power():
    return round((ina_battery.current())*(ina_battery.voltage()), 3)


def get_battery_bus_voltage():
    return round(ina_battery.voltage(), 3)


def get_battery_shunt_voltage():
    return round(ina_battery.shunt_voltage(), 4)


# get solar shunt data
def get_solar_power():
    return round((ina_solar.current())*(ina_solar.voltage()), 3)


def get_solar_bus_voltage():
    return round(ina_solar.voltage(), 3)


def get_solar_shunt_voltage():
    return round(ina_solar.shunt_voltage(), 4)


# the main loop to get the work done
def gather_readings():
    while True:
        # timestamp at the start of the loop
        starttime = time.time()

        # initiate all empty lists and variables before looping to populate them and calculate averages
        battery_power = []
        battery_bus_voltage = []
        battery_shunt_voltage = []

        solar_power = []
        solar_bus_voltage = []
        solar_shunt_voltage = []

        battery_power_av = 0
        battery_bus_voltage_av = 0
        battery_shunt_voltage_av = 0

        solar_power_av = 0
        solar_bus_voltage_av = 0
        solar_shunt_voltage_av = 0

        average_bus_voltage = 0
        system_load = 0

        count = 0

        # take 10 measurements from each sensor over approximately 1s, and calculate averages
        while count < 10:
            count += 1
            # get and insert data to lists for each sensor every 0.1s
            try:
                # battery
                battery_power.insert(0, get_battery_power())
                battery_bus_voltage.insert(0, get_battery_bus_voltage())
                battery_shunt_voltage.insert(0, get_battery_shunt_voltage())
            except DeviceRangeError as e:
                if count == 10:
                    print("Battery Current overflow")

            try:
                # solar
                solar_power.insert(0, get_solar_power())
                solar_bus_voltage.insert(0, get_solar_bus_voltage())
                solar_shunt_voltage.insert(0, get_solar_shunt_voltage())
            except DeviceRangeError as e:
                if count == 10:
                    print("Solar Current overflow")

            # calculate average values for each list of 10
            try:
                # battery
                battery_power_av = round(sum(battery_power)/len(battery_power), 3)
                battery_bus_voltage_av = round(sum(battery_bus_voltage)/len(battery_bus_voltage), 3)
                battery_shunt_voltage_av = round(sum(battery_shunt_voltage)/len(battery_shunt_voltage), 4)
            except ZeroDivisionError as e:
                if count == 10:
                    print("Battery Current overflow - Cant divide by zero")

            try:
                # solar
                solar_power_av = round(sum(solar_power)/len(solar_power), 3)
                solar_bus_voltage_av = round(sum(solar_bus_voltage)/len(solar_bus_voltage), 3)
                solar_shunt_voltage_av = round(sum(solar_shunt_voltage)/len(solar_shunt_voltage), 4)
            except ZeroDivisionError as e:
                if count == 10:
                    print("Solar Current overflow - Cant divide by zero")

            # calculate the average bus voltage using both INA219 sensors
            average_bus_voltage = round(((battery_bus_voltage_av + solar_bus_voltage_av) / 2), 3)

            # calculate the third energy flow point - the system load
            system_load = round((solar_power_av - battery_power_av), 3)

            # approximately first 1s (0.1*10) reserved for voltage sensor reads
            time.sleep(0.1)

        # next 2s (of 3s) reserved for temp, humidity and internal system reads

        # temp and humidity reads
        humidity, temperature = Adafruit_DHT.read_retry(DHT_SENSOR, DHT_PIN)
        try:
            temp = float(round(temperature, 1))
            hum = float(round(humidity, 1))
        except TypeError as e:
            print("Failed to retrieve data from DHT22")
            temp = 0.0
            hum = 0.0

        # get cpu usage, cpu temp, ram percentage and disk usage
        curr_cpu_perc = cpu_percent()
        load_avg = getloadavg()
        min1_ld_avg = load_avg[0]*100 # load average over 1 minute
        min5_ld_avg = load_avg[1]*100 # load average over 5 minutes
        min15_ld_avg = load_avg[2]*100 # load average over 15 minutes
        cpu_temp = CPUTemperature().temperature
        disk_used_perc = disk_usage('/').percent # disk usage of root directory
        ram_used_perc = virtual_memory().percent

        # take a timestamp for this measurement
        measurement_time = datetime.datetime.utcnow()

        # write to python dict
        try:
            body = [
                {
                    "measurement": measurement_name,
                    "time": measurement_time,
                    "fields": {
                        "bat_pwr": float(battery_power_av),
                        "bat_shnt_v": float(battery_shunt_voltage_av),
                        "slr_pwr": float(system_load), # this is actually the system load in this configuration (not slr_pwr)
                        "slr_shnt_v": float(solar_shunt_voltage_av),
                        "bus_v_avg": float(average_bus_voltage),
                        "slr_prod": float(solar_power_av),
                        "temp": temp,
                        "hum": hum,
                        "curr_cpu_perc": float(round(curr_cpu_perc, 1)),
                        "min1_ld_avg": float(round(min1_ld_avg, 1)),
                        "min5_ld_avg": float(round(min5_ld_avg, 1)),
                        "min15_ld_avg": float(round(min15_ld_avg, 1)),
                        "cpu_temp": float(round(cpu_temp, 1)),
                        "disk_used_perc": float(round(disk_used_perc, 1)),
                        "ram_used_perc": float(round(ram_used_perc, 1)),
                    }
                }
            ]
            # insert to database
            ifclient.write_points(body)
        except:
            print("Failed to round or convert types when inserting to database body")

        # wait for the remainder of the 3s loop time
        time.sleep(3.0 - ((time.time() - starttime) % 3.0))


if __name__ == "__main__":
    gather_readings()
