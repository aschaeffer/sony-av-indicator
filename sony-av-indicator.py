#!/usr/bin/env python

__author__ = "andreasschaeffer"
__author__ = "michaelkapuscik"

import socket
import time
import signal
import gi
import os

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk as gtk
from gi.repository import Gdk as gdk
gi.require_version("AppIndicator3", "0.1")
from gi.repository import AppIndicator3 as appindicator


APPINDICATOR_ID = "sony-av-indicator"

TCP_IP = "192.168.178.43"
TCP_PORT = 33335
BUFFER_SIZE = 1024

MIN_VOLUME = 0
LOW_VOLUME = 15
MEDIUM_VOLUME = 30
MAX_VOLUME = 45
ICON_PATH = "/usr/share/icons/ubuntu-mono-dark/status/24"

SOURCE_NAMES = [ "bdDvd", "game", "satCaTV", "video", "tv", "saCd", "fmTuner", "usb", "bluetooth" ]

CMD_MIN_VOLUME = bytearray([0x02, 0x06, 0xA0, 0x52, 0x00, 0x03, 0x00, 0x00, 0x00])
CMD_MAX_VOLUME = bytearray([0x02, 0x06, 0xA0, 0x52, 0x00, 0x03, 0x00, 0x4A, 0x00])
CMD_MUTE = bytearray([0x02, 0x04, 0xA0, 0x53, 0x00, 0x01, 0x00])
CMD_UNMUTE = bytearray([0x02, 0x04, 0xA0, 0x53, 0x00, 0x00, 0x00])
CMD_SOURCE_MAP = {
    "bdDvd": bytearray([0x02, 0x04, 0xA0, 0x42, 0x00, 0x1b, 0x00]),
    "game": bytearray([0x02, 0x04, 0xA0, 0x42, 0x00, 0x1c, 0x00]),
    "satCaTV": bytearray([0x02, 0x04, 0xA0, 0x42, 0x00, 0x16, 0x00]),
    "video": bytearray([0x02, 0x04, 0xA0, 0x42, 0x00, 0x10, 0x00]),
    "tv": bytearray([0x02, 0x04, 0xA0, 0x42, 0x00, 0x1a, 0x00]),
    "saCd": bytearray([0x02, 0x04, 0xA0, 0x42, 0x00, 0x02, 0x00]),
    "fmTuner": bytearray([0x02, 0x04, 0xA0, 0x42, 0x00, 0x2e, 0x00]),
    "usb": bytearray([0x02, 0x04, 0xA0, 0x42, 0x00, 0x34, 0x00]),
    "bluetooth": bytearray([0x02, 0x04, 0xA0, 0x42, 0x00, 0x34, 0x00])
}

SOURCE_MENU_MAP = {
    "bdDvd": "Blueray / DVD",
    "game": "Game",
    "satCaTV": "Sat / Cable",
    "video": "Video",
    "tv": "TV",
    "saCd": "CD",
    "fmTuner": "FM Tuner",
    "usb": "USB",
    "bluetooth": "Bluetooth"
}


current_volume = LOW_VOLUME
scroll_volume = 2
slide_speed = 0.05
scroll_speed = 0.1
muted = False
_indicator = None


def connect():
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.connect((TCP_IP, TCP_PORT))
    return s

def disconnect(s):
    s.close()

def send_command(cmd):
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.connect((TCP_IP, TCP_PORT))
    s.send(cmd)
    s.close()

def select_source(source, source_name):
    send_command(CMD_SOURCE_MAP[source_name])

def get_volume_icon(vol):
    if muted:
        icon_name = "audio-volume-muted-panel"
    elif vol == MIN_VOLUME:
        icon_name = "audio-volume-low-zero-panel"
    elif vol > MIN_VOLUME and vol <= LOW_VOLUME:
        icon_name = "audio-volume-low-panel"
    elif vol > LOW_VOLUME and vol <= MEDIUM_VOLUME:
        icon_name = "audio-volume-medium-panel"
    else:
        icon_name = "audio-volume-high-panel"
    return icon_name
    
def get_volume_icon_path(icon_name):
    return os.path.abspath("%s/%s.svg" %(ICON_PATH, icon_name))

def set_volume_icon(vol):
    _indicator.set_icon(get_volume_icon_path(get_volume_icon(vol)))

def update_volume(vol):
    global current_volume
    global muted
    if vol > current_volume:
        muted = False
    current_volume = vol
    set_volume_icon(vol)

def set_volume(source, vol):
    cmd = bytearray([0x02, 0x06, 0xA0, 0x52, 0x00, 0x03, 0x00, vol, 0x00])
    send_command(cmd)
    update_volume(vol)

def slide_volume_up(vol_from, vol_to, speed):
    s = connect()
    for vol in range(vol_from, vol_to):
        cmd = bytearray([0x02, 0x06, 0xA0, 0x52, 0x00, 0x03, 0x00, vol, 0x00])
        s.send(cmd)
        update_volume(vol)
        time.sleep(speed)
    disconnect(s)

def slide_volume_down(vol_from, vol_to, speed):
    s = connect()
    for vol in range(vol_from, vol_to, -1):
        cmd = bytearray([0x02, 0x06, 0xA0, 0x52, 0x00, 0x03, 0x00, vol, 0x00])
        s.send(cmd)
        update_volume(vol)
        time.sleep(speed)
    disconnect(s)

def slide_to_volume(source, vol):
    if current_volume <= vol:
        slide_volume_up(current_volume, vol, slide_speed)
    elif current_volume >= vol:
        slide_volume_down(current_volume, vol, slide_speed)

def scroll_volume_up():
    target_volume = current_volume + scroll_volume
    if target_volume <= MAX_VOLUME:
        # slide_volume_up(current_volume, target_volume, scroll_speed)
        set_volume(None, target_volume)

def scroll_volume_down():
    target_volume = current_volume - scroll_volume
    if target_volume >= MIN_VOLUME:
        # slide_volume_down(current_volume, target_volume, scroll_speed)
        set_volume(None, target_volume)

def mute(source):
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.connect((TCP_IP, TCP_PORT))
    s.send(CMD_MUTE)
    data = s.recv(BUFFER_SIZE)
    s.close()
    global muted
    muted = True
    set_volume_icon(current_volume)

def unmute(source):
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.connect((TCP_IP, TCP_PORT))
    s.send(CMD_UNMUTE)
    data = s.recv(BUFFER_SIZE)
    s.close()
    global muted
    muted = False
    set_volume_icon(current_volume)

def toggle_mute(source):
    if muted:
        unmute(source)
    else:
        mute(source)

def scroll(indicator, steps, direction):
    if direction == gdk.ScrollDirection.DOWN:
        scroll_volume_down()
    elif direction == gdk.ScrollDirection.UP:
        scroll_volume_up()
    elif direction == gdk.ScrollDirection.LEFT:
        scroll_volume_up()
    elif direction == gdk.ScrollDirection.RIGHT:
        scroll_volume_up()

def build_menu(indicator):
    menu = gtk.Menu()

    sources_menu = gtk.Menu()
    item_sources = gtk.MenuItem("Sources")
    item_sources.set_submenu(sources_menu)
    for source_name in SOURCE_NAMES:
        item_select_source = gtk.MenuItem(SOURCE_MENU_MAP[source_name])
        item_select_source.connect("activate", select_source, source_name)
        sources_menu.append(item_select_source)
    menu.append(item_sources)

    volume_menu = gtk.Menu()
    item_volume = gtk.MenuItem("Volume")
    item_volume.set_submenu(volume_menu)
    for vol in range(MIN_VOLUME, MAX_VOLUME, 5):
        item_set_volume = gtk.MenuItem("Volume %s"%(vol))
        item_set_volume.connect("activate", slide_to_volume, vol)
        volume_menu.append(item_set_volume)
    item_mute = gtk.MenuItem("Mute")
    item_mute.connect("activate", mute)
    volume_menu.append(item_mute)
    item_unmute = gtk.MenuItem("Unmute")
    item_unmute.connect("activate", unmute)
    volume_menu.append(item_unmute)
    item_toggle_mute = gtk.MenuItem("Toggle Mute")
    item_toggle_mute.connect("activate", toggle_mute)
    volume_menu.append(item_toggle_mute)
    indicator.set_secondary_activate_target(item_toggle_mute)
    menu.append(item_volume)

    item_quit = gtk.MenuItem("Quit")
    item_quit.connect("activate", quit)
    menu.append(item_quit)

    menu.show_all()
    return menu

def quit(source):
    gtk.main_quit()

def main():
    indicator = appindicator.Indicator.new(APPINDICATOR_ID, get_volume_icon_path(get_volume_icon(current_volume)), appindicator.IndicatorCategory.SYSTEM_SERVICES)
    indicator.set_status(appindicator.IndicatorStatus.ACTIVE)
    indicator.set_menu(build_menu(indicator))
    indicator.connect("scroll-event", scroll)
    global _indicator
    _indicator = indicator
    signal.signal(signal.SIGINT, signal.SIG_DFL)
    gtk.main()

if __name__ == "__main__":
    main()
