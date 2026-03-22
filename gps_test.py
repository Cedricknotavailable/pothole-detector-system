import serial

port = "COM3"      # change this to your GPS COM port
baud = 4800

ser = serial.Serial(port, baud, timeout=1)

print("Reading GPS data... (press CTRL+C to stop)\n")

while True:
    line = ser.readline().decode("ascii", errors="replace").strip()
    if line:
        print(line)

