use a raspberry pi and arduino to build a satellite simulator lab station

Building a satellite simulator with a Raspberry Pi and Arduino allows you to model both the computational "brain" (Flight Software) and the physical subsystems (sensors and actuators) of a spacecraft.
1. System Architecture
In this setup, the devices work together to simulate a complete satellite mission:

    Raspberry Pi (Flight Computer): Acts as the primary processor, running complex NASA Core Flight System (cFS) software, handling telemetry, and managing high-level mission logic.
    Arduino (Subsystem Controller): Handles real-time tasks like reading sensors (IMUs, temperature) or controlling servos for motion simulation.
    Interface: Use a standard USB cable for serial communication between the Pi and Arduino; the Pi can also power the Arduino this way.

2. Hardware Requirements

    Computing: Raspberry Pi 4 or 5 and an Arduino Uno or Nano.
    Sensors: IMU (for orientation), temperature, and pressure sensors.
    Radio (Optional): An RTL-SDR dongle for receiving simulated or real satellite signals, and a 433 MHz transmitter for sending telemetry.
    Motion: Servo motors and cables to build a cable-driven spacecraft motion simulator.

3. Software Setup

    Raspberry Pi OS: Flash the Raspberry Pi OS Lite using Raspberry Pi Imager.
    Telemetry Simulation: Install the CubeSat Simulator software to broadcast simulated telemetry via FM or Morse code.
    Arduino Programming: Install the Arduino IDE on the Pi to program the Arduino directly from your flight computer.
    Orbit Prediction: Use the SGP4 Python library to calculate the satellite's position based on TLE data from CelesTrak.

4. Implementation Steps

    Step 1: Communication Link. Connect the Arduino to the Pi via USB. Write a Python script on the Pi using the pySerial library to receive sensor data from the Arduino.
    Step 2: Simulation Logic. Run the orbit propagator on the Pi. Based on the "simulated" position, have the Arduino move servos to orient the "satellite" towards a target.
    Step 3: Ground Station Interface. Set up an SSH connection so you can monitor the simulator's health from your laptop, mimicking a ground control station

    URLs:
    https://ntrs.nasa.gov/api/citations/20150023353/downloads/20150023353.pdf
    https://www.rtl-sdr.com/buy-rtl-sdr-dvb-t-dongles/
    https://www.youtube.com/watch?v=g0Y6yKlDNdM
    https://www.raspberrypi.com/software/
    https://github.com/alanbjohnston/CubeSatSim
    https://www.arduino.cc/en/software
    https://pypi.org/project/sgp4/
    https://celestrak.org/
    https://pyserial.readthedocs.io/

    Items on hand:
    Raspberry Pi 3 32Gb (2)
    Arduino Uno R3
    Arduino Uno Q
    Arduino Sensor Kit
    Arduino Modulino Thermo
    MQ4 Methane Gas sensor (2)
    Adafruit KB2040
    Inventr.io Shields Kit
    Inventr.io 37 Sensor Kit
    Inventr.io Hero Board
    Canaduino WWVB/MSF 60kHz Atomic Clock AM receiver
    XIITIA GY-NEO7mV2 GPS Module (3)
    Meshnology 2 Set Wio Tracker L1 Board with 3000mAh Battery and Case Set SX1262 nRF52840 Kit
    Various breadboards, connectors, cables, and soldering station
