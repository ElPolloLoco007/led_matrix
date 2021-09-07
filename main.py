#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright (c) 2017-18 Richard Hull and contributors
# See LICENSE.rst for details.

import re
import time
import argparse
import urllib
import requests
import json
import os
from luma.led_matrix.device import max7219
from luma.core.interface.serial import spi, noop
from luma.core.render import canvas
from luma.core.virtual import viewport
from luma.core.legacy import text, show_message
from luma.core.legacy.font import proportional, CP437_FONT, TINY_FONT, SINCLAIR_FONT, LCD_FONT
import psycopg2 as ps
import datetime
import configparser as cp
config = cp.ConfigParser()
config.read('config.ini')

import Adafruit_DHT

def getWeather():
    DHT_SENSOR = Adafruit_DHT.DHT22
    DHT_PIN = 4

    humidity, temperature = Adafruit_DHT.read_retry(DHT_SENSOR, DHT_PIN)

    if humidity is not None and temperature is not None:
        return "Inside: {0:0.1f}C  {1:0.1f}%".format(temperature, humidity)
    else:
        print("Failed to retrieve data from humidity sensor")

def connect():
    try:
        conn = ps.connect(host=config['PQ']['host'], port=config['PQ']['port'],
                          database=config['PQ']['database'], user=config['PQ']['user'], password=config['PQ']['password'])
        return conn
    except (Exception, ps.DatabaseError) as error:
        print(error)
        return 0

def getStocks():
    if connect() != 0: 
        conn = connect()
        cur = conn.cursor()
        cur.execute("select symbol from watchlist")
        rows = cur.fetchall()
        stocks=""
        for row in rows:
          stocks+=row[0] + ","

        return stocks[:-1]
    else:
        ticker=""
        with open('/home/pi/led_matrix/stocks.txt') as f:
            ticker = f.readlines()
        s=','.join(ticker)
        s=s.replace('\n','')
        return s


getStocks()

def runCmd(cmd):
    stream = os.popen(cmd)
    output = stream.read()
    return output

CHAR_UP = u"\u25B2"
CHAR_DOWN =u"\u25BC"

def arrow(val):
    arrow ="="
    if val > 0:
        arrow = CHAR_UP
    if val < 0:
        arrow = CHAR_DOWN
    return arrow

# create matrix device
serial = spi(port=0, device=0, gpio=noop())
device = max7219(serial, cascaded=8 , block_orientation=-90, rotate=2,contrast=10)


ahPrice=0
ahPercent=0
ah=""
d = datetime.datetime.now()
t1 = t2 = 0
period1 = 15*60 # do function1() every second
period2 = 60*60  # do function2() every hour

while True:
    t = time.time()
    if d.isoweekday() in range(1, 6) and d.hour in range(9, 22):
        if t - t1 >= period1:
            try:
                link = "curl --silent https://query1.finance.yahoo.com/v7/finance/quote?symbols="+getStocks()
                output_string = runCmd(link)
                stock_info = json.loads(output_string)
                #print(stock_info['quoteResponse']['result'][0])

                for stock in stock_info['quoteResponse']['result']:
                    symbol=stock['symbol']
                    price="{:.2f}".format(stock['regularMarketPrice'])
                    pricePercent="{:.2f}".format(stock['regularMarketChangePercent'])
                    x=symbol+" $" +str(price)+" " +str(pricePercent)+"%"
                    if "postMarketPrice" in stock:
                        ahPrice="{:.2f}".format(stock['postMarketPrice'])
                        ahPercent="{:.2f}".format(stock['postMarketChangePercent'])
                        ah="PostMarket:"
                    if "preMarketPrice" in stock:
                        ahPrice="{:.2f}".format(stock['preMarketPrice'])
                        ahPercent="{:.2f}".format(stock['preMarketChangePercent'])
                        ah="PreMarket:"
                    if not ah:
                        x+="  "+ah+" $"+ str(ahPrice) + " " + str(ahPercent)+"%"
                        show_message(device,x, fill="white",font=proportional(LCD_FONT),scroll_delay = 0.04)
                t1=time.time()
            except (Exception) as error:
                show_message(device,error, fill="white",font=proportional(LCD_FONT),scroll_delay = 0.04)
        else:
            print("not in rage")

    if d.hour in range(10,22):
        if t - t2 >= period2:
            w=getWeather()
            show_message(device,w,fill="white",font=proportional(LCD_FONT),scroll_delay = 0.04)
            t2 = time.time()




