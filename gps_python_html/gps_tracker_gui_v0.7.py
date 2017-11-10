import time
import serial
import webbrowser
import os
from serial.tools import list_ports
import datetime
from tkinter import *
from tkinter import ttk
from tkinter import messagebox
from tkinter.filedialog import askopenfilename
from tkinter.filedialog import asksaveasfilename
from serial.tools import list_ports
import csv
import re

# 
# /******************************************************************************
 
# @file gps_tracker_gui.py
 
# @brief front end file
 
# Group: WCS LPC
# $Target Device: DEVICES $
 
# ******************************************************************************
# $License: BSD3 2016 $
# ******************************************************************************
# $Release Name: PACKAGE NAME $
# $Release Date: PACKAGE RELEASE DATE $
# *****************************************************************************/
# 

class App:

    # GLOBALS
    nodes = []
    known_addresses = []
    gpsTurnedOn = FALSE
    gpsStayOn = FALSE
    ser = serial.Serial()
    comport = ''
    csvName = ''
    append = FALSE
    cancel = FALSE
    serReads = [1]

    # DEFINITIONS
    class Node:
        def __init__(self, address):
            self.addr = address
            self.gps = []

    class Fix:
        lat = ''
        lng = ''
        latDM = ''
        lngDM = ''
        alt = ''
        rssi = ''
        fixTime = ''    # Time GPS fix was taken
        plotTime = ''   # Time fix is plotted

    # FUNCTIONS
    def writeData(self, addr, fix, overwrite_csv):
        f = open('gpsdata.js', 'rb+')
        f.seek(-1, 2)
        f.truncate()
        f.close()
        f = open('gpsdata.js', 'r+')
        f.seek(0, 2)
        f.write('{ addr: ' + str(addr) + ', ' \
                + 'lat: ' + fix.lat + ', ' \
                + 'lng: ' + fix.lng + ', ' \
                + 'alt: ' + fix.alt + ', ' \
                + 'rssi: ' + fix.rssi + ', ' \
                + 'time: \'' + fix.fixTime + '\' },\n]')
        f.close()
        now = datetime.datetime.utcnow()

        #if(not overwrite_csv):
        with open(self.csvName, 'a', newline='') as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow((str(addr), fix.lat, fix.lng, fix.alt, fix.rssi, fix.fixTime, str(now.year) \
                            + '-' + str(now.month).zfill(2) \
                            + '-' + str(now.day).zfill(2), fix.latDM, fix.lngDM, fix.plotTime))

    def addFix(self, addr, fix, overwrite_csv):
        if addr not in self.known_addresses:
            self.nodes.append(self.Node(addr))
            self.known_addresses.append(addr)
        self.nodes[self.known_addresses.index(addr)].gps.append(fix)
        self.writeData(addr, fix, overwrite_csv)

    def serialUpdate(self, event):
        ports = sorted(list_ports.comports())
        self.port_names = []
        for i, port in enumerate(ports):
            if "Application" in port.description:
                self.port_names.append(port.device)
        self.serialBox['values'] = self.port_names

    def serialGet(self, event):
        self.comport = self.serialBox.get()

    def overwriteCSV(self, ow):
        self.overwrite = TRUE
        ow.destroy()

    def appendCSV(self, ow):
        self.overwrite = FALSE
        ow.destroy()

    def cancelCSV(self, ow):
        self.cancel = TRUE
        ow.destroy()

    # MAIN PROGRAM FUNCTIONS
    def startGPS(self):

        self.serialBox.state = "disabled"

        if(self.gpsTurnedOn == FALSE):
            self.gpsTurnedOn = TRUE
            self.overwrite = FALSE
            self.cancel = FALSE

            self.csvName = asksaveasfilename(initialdir = "/csv", title = "New csv File", defaultextension = ".csv",filetypes = (("csv files","*.csv"),("all files","*.*")))

            # Overwrite or append file?
            if os.path.isfile(self.csvName):
                ow = Toplevel()
                ow.title('Overwrite')
                ow.geometry('300x100')
                frame1 = Frame(ow)
                frame2 = Frame(ow)
                frame1.place(relx=0.05, rely=0.1, relheight=0.4, relwidth=0.9)
                frame2.place(relx=0.05, rely=0.5, relheight=0.4, relwidth=0.9)

                Label(frame1, text="Overwrite or append to existing file?").place(relx=0.5, rely=0, anchor=N)
                Button(frame2, text='Overwrite', command=lambda: self.overwriteCSV(ow)).place(relx=0, relwidth=0.3, anchor=NW)
                Button(frame2, text='Append', command=lambda: self.appendCSV(ow)).place(relx=0.5, relwidth=0.3, anchor=N)
                Button(frame2, text='Cancel', command=lambda: self.cancelCSV(ow)).place(relx=1, relwidth=0.3, anchor=NE)
                self.master.wait_window(ow)
            else:
                self.overwrite = TRUE

            if self.cancel == FALSE:
                if self.overwrite:
                    f = open(self.csvName, 'w')
                    f.truncate()
                    f.close()
                    with open(self.csvName, 'w', newline='') as csvfile:
                        writer = csv.writer(csvfile)
                        writer.writerow(('Node Address', 'Latitude (°)', 'Longitude (°)', \
                                        'Altitude (m)', 'RSSI (dBm)', 'Time of Fix (UTC)', 'Date', \
                                        'Latitude (DM)', 'Longitude (DM)', 'Time of Plot (UTC)'))

                self.ser = serial.Serial(self.comport, 115200, timeout=0.5)

                # Erase js file
                f = open('gpsdata.js', 'r+')
                f.truncate()
                f.write('var gps = [\n]')
                f.close()

                webbrowser.open('cc13xx_map.html')

                self.gpsStayOn = TRUE

            else:
                self.stopGPS()

        if self.gpsStayOn:
            in_str = ''

            if self.ser.in_waiting > 0:
                try:
                    in_byte = self.ser.read(1)

                except:
                    self.stopGPS()

                else:
                    in_str = in_byte.decode('utf-8')

            if in_str == '$':
                try:
                    in_byte = self.ser.read(18)

                except TypeError as e:
                    in_str = ''
                    messagebox.showinfo('Error', 'COM Port Disconnected')
                    self.stopGPS()

                else:
                    address = in_byte[0]
                    rssi = int.from_bytes(bytes([in_byte[1]]), byteorder='little', signed=True)
                    latDM = int.from_bytes(in_byte[2:4], byteorder='little', signed=True)
                    latm = int.from_bytes(in_byte[4:7], byteorder='little', signed=False)
                    lngDM = int.from_bytes(in_byte[7:9], byteorder='little', signed=True)
                    lngm = int.from_bytes(in_byte[9:12], byteorder='little', signed=False)
                    altA = int.from_bytes(in_byte[12:14], byteorder='little', signed=False)
                    alta = in_byte[14]
                    time = in_byte[15:]

                    gps = self.Fix()

                    latmstr = str(latm).zfill(6)
                    lngmstr = str(lngm).zfill(6)

                    gps.latDM = str(latDM)[0:-2] + ' ' + str(latDM)[-2:] + '.' + latmstr
                    gps.lngDM = str(lngDM)[0:-2] + ' ' + str(lngDM)[-2:] + '.' + lngmstr
                    gps.lat = str(latDM)[0:-2] \
                            + str(float(str(latDM)[-2:] \
                            + '.' + latmstr)/60)[1:10]
                    gps.lng = str(lngDM)[0:-2] \
                            + str(float(str(lngDM)[-2:] \
                            + '.' \
                            + lngmstr)/60)[1:10]
                    gps.alt = str(altA) + '.' + str(alta)
                    gps.fixTime = str(time[0]).zfill(2) + ':' \
                                + str(time[1]).zfill(2) + ':' \
                                + str(time[2]).zfill(2)
                    gps.rssi = str(rssi)

                    now = datetime.datetime.utcnow()
                    gps.plotTime = str(now.hour).zfill(2) + ':' \
                                + str(now.minute).zfill(2) + ':' \
                                + str(now.second).zfill(2)

                    self.addFix(address, gps, self.overwrite)

            self.master.after(100, self.startGPS)
        else:
            self.gpsTurnedOn = FALSE

    def stopGPS(self):
        if self.gpsStayOn:
            self.ser.close()
            self.serialBox.set('')
            self.serialBox.state = "enabled"
            self.gpsStayOn = FALSE
            self.csvName = ''

    def saveCSV(self):
        f_name = asksaveasfilename(initialdir="/", title="Filename to save as", \
                                    defaultextension=".csv", \
                                    filetypes=(("csv files", "*.csv"), ("all files", "*.*")))
        with open(f_name, 'w', newline='') as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow(('Node Address', 'Latitude (°)', 'Longitude (°)', 'Altitude (m)', \
                            'RSSI (dBm)', 'Time of Fix (UTC)', 'Date', 'Latitude (DM)', \
                            'Longitude (DM)', 'Time of Plot (UTC)'))
            for n in self.nodes:
                for fix in n.gps:
                    writer.writerow((str(n.addr), fix.lat, fix.lng, fix.alt, fix.rssi, \
                    fix.fixTime, str(now.year) + '-' + str(now.month).zfill(2) \
                    + '-' + str(now.day).zfill(2), fix.latDM, fix.lngDM, fix.plotTime))

    def openCSV(self):
        # Reset variables
        self.nodes = []
        self.known_addresses = []

        f = open('gpsdata.js', 'r+')
        f.truncate()
        f.write('var gps = [\n]')
        f.close()

        f = open('gpsdata.js', 'rb+')
        f.seek(-1, 2)
        f.truncate()
        f = open('gpsdata.js', 'r+')
        f.seek(0, 2)

        self.csvName = askopenfilename(initialdir="/csv", title="Select file to open", \
                                        filetypes=(("csv files", "*.csv"), ("all files", "*.*")))
        with open(self.csvName) as csvfile:
            readCSV = csv.reader(csvfile)
            for i, row in enumerate(readCSV):
                if i > 0:
                    f.write('{ addr: ' + row[0] + ', ' \
                            + 'lat: ' + row[1] + ', ' \
                            + 'lng: ' + row[2] + ', ' \
                            + 'alt: ' + row[3] + ', ' \
                            + 'rssi: ' + row[4] + ', ' \
                            + 'time: \'' + row[5] + '\' },\n')
        f.write(']')
        f.close()
        self.csvName = ''

        webbrowser.open('cc13xx_map.html')

    def __init__(self, master):

        self.master = master
        self.master.title('GPS Range Test')
        self.master.resizable(width=False, height=False)
        self.master.geometry("275x240")

        #title = Label(root,text='TI CC13xx GPS to Map')
        self.frame1 = Frame(root)
        self.frame2 = Frame(root)
        self.frame4 = Frame(root)
        self.frame5 = Frame(root)

        self.frame1.place(relx=0.1, rely=0.1, relheight=0.15, relwidth=0.8)
        self.frame2.place(relx=0.1, rely=0.25, relheight=0.25, relwidth=0.8)
        self.frame4.place(relx=0.1, rely=0.5, relheight=0.2, relwidth=0.8)
        self.frame5.place(relx=0.1, rely=0.73, relheight=0.2, relwidth=0.8)

        # title
        self.Title = Label(self.frame1, text="TI CC13xx GPS Range Test", \
                            justify=CENTER, font=("Arial Bold", 10))
        self.Title.pack(fill=BOTH)

        # Buttons
        self.bStart = Button(self.frame4, state=NORMAL, text="Start", \
                            command=self.startGPS).place(rely=0.15, relheight=.7, relwidth=.45)
        self.bStop = Button(self.frame4, state=NORMAL, text="Stop", \
                            command=self.stopGPS).place(relx=0.55, rely=0.15, relheight=.7, relwidth=.45)
        self.bOpen = Button(self.frame5, state=NORMAL, text="Open .csv", \
                            command=self.openCSV).place(rely=0.15, relheight=.7, relwidth=1)
        
        # Get COM ports
        self.port_names = []
        ports = sorted(list_ports.comports())
        for i, port in enumerate(ports):
            if "Application" in port.description:
                self.port_names.append(port.device)

        # Com Ports Dropdown
        self.serialLabel = Label(self.frame2, text="Serial Port", font=("Arial", 8))
        self.serialLabel.place(rely=0)
        self.serialBox = ttk.Combobox(self.frame2)
        self.serialBox.bind("<<ComboboxSelected>>", self.serialGet)
        self.serialBox.bind("<Button-1>", self.serialUpdate)
        self.serialBox.place(rely=0.4, relwidth=1)
        self.serialBox['values'] = self.port_names

        # Create CSV Folder
        if not os.path.isdir('csv'):
            os.makedirs('csv')

# Start GUI
root = Tk()
app = App(root)
root.mainloop()
