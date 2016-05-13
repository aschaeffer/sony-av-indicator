#!/usr/bin/env python

__author__ = 'andreasschaeffer'
__author__ = 'michaelkapuscik'

import socket
import time
import signal
import gi
import os

gi.require_version('Gtk', '3.0')
from gi.repository import Gtk as gtk
from gi.repository import Gdk as gdk
gi.require_version('AppIndicator3', '0.1')
from gi.repository import AppIndicator3 as appindicator

APPINDICATOR_ID = 'sony-av-indicator'

TCP_IP = '192.168.178.43'
TCP_PORT = 33335
BUFFER_SIZE = 1024

minVolume = bytearray([0x02, 0x06, 0xA0, 0x52, 0x00, 0x03, 0x00, 0x00, 0x00])
maxVolume = bytearray([0x02, 0x06, 0xA0, 0x52, 0x00, 0x03, 0x00, 0x4A, 0x00])
cmd_mute = bytearray([0x02, 0x04, 0xA0, 0x53, 0x00, 0x01, 0x00])
cmd_unmute = bytearray([0x02, 0x04, 0xA0, 0x53, 0x00, 0x00, 0x00])

cmd_source_bdDvd = bytearray([0x02, 0x04, 0xA0, 0x42, 0x00, 0x1b, 0x00])
cmd_source_game = bytearray([0x02, 0x04, 0xA0, 0x42, 0x00, 0x1c, 0x00])
cmd_source_satCaTV = bytearray([0x02, 0x04, 0xA0, 0x42, 0x00, 0x16, 0x00])
cmd_source_video = bytearray([0x02, 0x04, 0xA0, 0x42, 0x00, 0x10, 0x00])
cmd_source_tv = bytearray([0x02, 0x04, 0xA0, 0x42, 0x00, 0x1a, 0x00])
cmd_source_saCd = bytearray([0x02, 0x04, 0xA0, 0x42, 0x00, 0x02, 0x00])
cmd_source_fmTuner = bytearray([0x02, 0x04, 0xA0, 0x42, 0x00, 0x2e, 0x00])
cmd_source_amTuner = bytearray([0x02, 0x04, 0xA0, 0x42, 0x00, 0x2f, 0x00])
cmd_source_usb = bytearray([0x02, 0x04, 0xA0, 0x42, 0x00, 0x34, 0x00])
cmd_source_bluetooth = bytearray([0x02, 0x04, 0xA0, 0x42, 0x00, 0x34, 0x00])

source_names = [ "bdDvd", "game", "satCaTV", "video", "tv", "saCd", "fmTuner", "usb", "bluetooth" ]

cmd_source_map = {
    "bdDvd": cmd_source_bdDvd,
    "game": cmd_source_game,
    "satCaTV": cmd_source_satCaTV,
    "video": cmd_source_video,
    "tv": cmd_source_tv,
    "saCd": cmd_source_saCd,
    "fmTuner": cmd_source_fmTuner,
    "usb": cmd_source_usb,
    "bluetooth": cmd_source_bluetooth
}

source_menu_map = {
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

min_volume = 0
low_volume = 15
medium_volume = 30
max_volume = 45
current_volume = low_volume
scroll_volume = 2
slide_speed = 0.05
scroll_speed = 0.1
muted = False
_indicator = None
icon_path = "/usr/share/icons/ubuntu-mono-dark/status/24"

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
    print "Switch to source: ", source_name
    send_command(cmd_source_map[source_name])

def get_volume_icon(vol):
    if muted:
        icon_name = "audio-volume-muted-panel"
    elif vol == min_volume:
        icon_name = "audio-volume-low-zero-panel"
    elif vol > min_volume and vol <= low_volume:
        icon_name = "audio-volume-low-panel"
    elif vol > low_volume and vol <= medium_volume:
        icon_name = "audio-volume-medium-panel"
    else:
        icon_name = "audio-volume-high-panel"
    return icon_name
    
def get_volume_icon_path(icon_name):
    return os.path.abspath("%s/%s.svg" %(icon_path, icon_name))

def set_volume_icon(vol):
    # print get_volume_icon_path(get_volume_icon(vol))
    _indicator.set_icon(get_volume_icon_path(get_volume_icon(vol)))

def update_volume(vol):
    global current_volume
    global muted
    if vol > current_volume:
        muted = False
    current_volume = vol
    set_volume_icon(vol)
    print "volume: ", vol
    
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
    if target_volume <= max_volume:
        # slide_volume_up(current_volume, target_volume, scroll_speed)
        set_volume(None, target_volume)

def scroll_volume_down():
    target_volume = current_volume - scroll_volume
    if target_volume >= min_volume:
        # slide_volume_down(current_volume, target_volume, scroll_speed)
        set_volume(None, target_volume)

def mute(source):
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.connect((TCP_IP, TCP_PORT))
    s.send(cmd_mute)
    data = s.recv(BUFFER_SIZE)
    s.close()
    global muted
    muted = True
    set_volume_icon(current_volume)

def unmute(source):
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.connect((TCP_IP, TCP_PORT))
    s.send(cmd_unmute)
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
    item_sources = gtk.MenuItem('Sources')
    item_sources.set_submenu(sources_menu)
    for source_name in source_names:
        item_select_source = gtk.MenuItem(source_menu_map[source_name])
        item_select_source.connect('activate', select_source, source_name)
        sources_menu.append(item_select_source)
    menu.append(item_sources)

    volume_menu = gtk.Menu()
    item_volume = gtk.MenuItem('Volume')
    item_volume.set_submenu(volume_menu)
    for vol in range(min_volume, max_volume, 5):
        item_set_volume = gtk.MenuItem('Volume %s'%(vol))
        item_set_volume.connect('activate', slide_to_volume, vol)
        volume_menu.append(item_set_volume)
    item_mute = gtk.MenuItem('Mute')
    item_mute.connect('activate', mute)
    volume_menu.append(item_mute)
    item_unmute = gtk.MenuItem('Unmute')
    item_unmute.connect('activate', unmute)
    volume_menu.append(item_unmute)
    item_toggle_mute = gtk.MenuItem('Toggle Mute')
    item_toggle_mute.connect('activate', toggle_mute)
    volume_menu.append(item_toggle_mute)
    indicator.set_secondary_activate_target(item_toggle_mute)
    menu.append(item_volume)

    item_quit = gtk.MenuItem('Quit')
    item_quit.connect('activate', quit)
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
