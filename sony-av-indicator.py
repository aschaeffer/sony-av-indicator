#!/usr/bin/env python

# TODO: request states (source, field, volume, ...) during startup

__author__ = "andreasschaeffer"
__author__ = "michaelkapuscik"

import socket
import time
import signal
import gi
import os
import threading
import logging
import traceback

gi.require_version("Gtk", "3.0")
gi.require_version("AppIndicator3", "0.1")
gi.require_version('Notify', '0.7')

from gi.repository import Gtk as gtk
from gi.repository import Gdk as gdk
from gi.repository import AppIndicator3 as appindicator
from gi.repository import Notify as notify

logging.basicConfig(level=logging.ERROR)

APPINDICATOR_ID = "sony-av-indicator"

# TCP_IP = "192.168.178.43"
TCP_PORT = 33335
BUFFER_SIZE = 1024

MIN_VOLUME = 0
LOW_VOLUME = 15
MEDIUM_VOLUME = 30
MAX_VOLUME = 45
ICON_PATH = "/usr/share/icons/ubuntu-mono-dark/status/24"

SOURCE_NAMES = [ "bdDvd", "game", "satCaTV", "video", "tv", "saCd", "fmTuner", "bluetooth", "usb", "homeNetwork", "screenMirroring" ]
SOUND_FIELD_NAMES = [ "twoChannelStereo", "aDirect", "multiStereo", "afd", "pl2Movie", "neo6Cinema", "hdDcs", "pl2Music", "neo6Music", "concertHallA", "concertHallB", "concertHallC", "jazzClub", "liveConcert", "stadium", "sports", "portableAudio" ]

CMD_SOURCE_MAP = {
    "bdDvd":            bytearray([0x02, 0x04, 0xA0, 0x42, 0x00, 0x1B, 0x00]),
    "game":             bytearray([0x02, 0x04, 0xA0, 0x42, 0x00, 0x1C, 0x00]),
    "satCaTV":          bytearray([0x02, 0x04, 0xA0, 0x42, 0x00, 0x16, 0x00]),
    "video":            bytearray([0x02, 0x04, 0xA0, 0x42, 0x00, 0x10, 0x00]),
    "tv":               bytearray([0x02, 0x04, 0xA0, 0x42, 0x00, 0x1A, 0x00]),
    "saCd":             bytearray([0x02, 0x04, 0xA0, 0x42, 0x00, 0x02, 0x00]),
    "fmTuner":          bytearray([0x02, 0x04, 0xA0, 0x42, 0x00, 0x2E, 0x00]),
    "bluetooth":        bytearray([0x02, 0x04, 0xA0, 0x42, 0x00, 0x33, 0x00]),
    "usb":              bytearray([0x02, 0x04, 0xA0, 0x42, 0x00, 0x34, 0x00]),
    "homeNetwork":      bytearray([0x02, 0x04, 0xA0, 0x42, 0x00, 0x3D, 0x00]),
    "screenMirroring":  bytearray([0x02, 0x04, 0xA0, 0x42, 0x00, 0x40, 0x00]),
}

# TODO: find out OPCODES for sound fields
CMD_SOUND_FIELD_MAP = {
    "twoChannelStereo": bytearray([0x02, 0x04, 0xA0, 0x42, 0x00, 0x00]),
    "aDirect":          bytearray([0x02, 0x04, 0xA0, 0x42, 0x02, 0x00]),
    "multiStereo":      bytearray([0x02, 0x04, 0xA0, 0x42, 0x27, 0x00]),
    "afd":              bytearray([0x02, 0x04, 0xA0, 0x42, 0x21, 0x00]),
    "pl2Movie":         bytearray([0x02, 0x04, 0xAB, 0x82, 0x23, 0x00]),
    "neo6Cinema":       bytearray([0x02, 0x04, 0xAB, 0x82, 0x25, 0x00]),
    "hdDcs":            bytearray([0x02, 0x04, 0xAB, 0x82, 0x33, 0x00]),
    "pl2Music":         bytearray([0x02, 0x04, 0xAB, 0x82, 0x24, 0x00]),
    "neo6Music":        bytearray([0x02, 0x04, 0xAB, 0x82, 0x26, 0x00]),
    "concertHallA":     bytearray([0x02, 0x04, 0xAB, 0x82, 0x1E, 0x00]),
    "concertHallB":     bytearray([0x02, 0x04, 0xAB, 0x82, 0x1F, 0x00]),
    "concertHallC":     bytearray([0x02, 0x04, 0xAB, 0x82, 0x38, 0x00]),
    "jazzClub":         bytearray([0x02, 0x04, 0xAB, 0x82, 0x16, 0x00]),
    "liveConcert":      bytearray([0x02, 0x04, 0xAB, 0x82, 0x19, 0x00]),
    "stadium":          bytearray([0x02, 0x04, 0xAB, 0x82, 0x1B, 0x00]),
    "sports":           bytearray([0x02, 0x04, 0xAB, 0x82, 0x20, 0x00]),
    "portableAudio":    bytearray([0x02, 0x04, 0xAB, 0x82, 0x30, 0x00]),
}

CMD_MIN_VOLUME =        bytearray([0x02, 0x06, 0xA0, 0x52, 0x00, 0x03, 0x00, 0x00, 0x00])
CMD_MAX_VOLUME =        bytearray([0x02, 0x06, 0xA0, 0x52, 0x00, 0x03, 0x00, 0x4A, 0x00])
CMD_MUTE =              bytearray([0x02, 0x04, 0xA0, 0x53, 0x00, 0x01, 0x00])
CMD_UNMUTE =            bytearray([0x02, 0x04, 0xA0, 0x53, 0x00, 0x00, 0x00])

FEEDBACK_POWER_ON =     bytearray([0x02, 0x07, 0xA8, 0x82, 0x00, 0x2E, 0x00, 0x10, 0x00])
FEEDBACK_POWER_OFF =    bytearray([0x02, 0x07, 0xA8, 0x82, 0x00, 0x16, 0x00, 0x10, 0x00])

FEEDBACK_TIMER_PREFIX = bytearray([0x02, 0x05, 0xA8, 0x90])
FEEDBACK_TIMER_SET =    bytearray([0x00])
FEEDBACK_TIMER_UPDATE = bytearray([0x3B])
FEEDBACK_TIMER_OFF =    bytearray([0xFF])

# "video" == Google Cast + Bluetooth
# two bytes follows 0x13/0x11
FEEDBACK_SOURCE_MAP = {
    "bdDvd":            bytearray([0x02, 0x07, 0xA8, 0x82, 0x00, 0x1B, 0x00]),
    "game":             bytearray([0x02, 0x07, 0xA8, 0x82, 0x00, 0x1C, 0x00]),
    "satCaTV":          bytearray([0x02, 0x07, 0xA8, 0x82, 0x00, 0x16, 0x00]),
    "video":            bytearray([0x02, 0x07, 0xA8, 0x82, 0x00, 0xFF, 0x00]),
    "tv":               bytearray([0x02, 0x07, 0xA8, 0x82, 0x00, 0x1A, 0x00]),
    "saCd":             bytearray([0x02, 0x07, 0xA8, 0x82, 0x00, 0x02, 0x00]),
    "fmTuner":          bytearray([0x02, 0x07, 0xA8, 0x82, 0x00, 0x2E, 0x00]),
    "bluetooth":        bytearray([0x02, 0x07, 0xA8, 0x82, 0x00, 0x33, 0x00]),
    "usb":              bytearray([0x02, 0x07, 0xA8, 0x82, 0x00, 0x34, 0x00]),
    "homeNetwork":      bytearray([0x02, 0x07, 0xA8, 0x82, 0x00, 0x3D, 0x00]),
    "screenMirroring":  bytearray([0x02, 0x07, 0xA8, 0x82, 0x00, 0x40, 0x00]),
}

FEEDBACK_SOUND_FIELD_MAP = {
    "twoChannelStereo": bytearray([0x02, 0x04, 0xAB, 0x82, 0x00, 0x00]),
    "aDirect":          bytearray([0x02, 0x04, 0xAB, 0x82, 0x02, 0x00]),
    "multiStereo":      bytearray([0x02, 0x04, 0xAB, 0x82, 0x27, 0x00]),
    "afd":              bytearray([0x02, 0x04, 0xAB, 0x82, 0x21, 0x00]),
    "pl2Movie":         bytearray([0x02, 0x04, 0xAB, 0x82, 0x23, 0x00]),
    "neo6Cinema":       bytearray([0x02, 0x04, 0xAB, 0x82, 0x25, 0x00]),
    "hdDcs":            bytearray([0x02, 0x04, 0xAB, 0x82, 0x33, 0x00]),
    "pl2Music":         bytearray([0x02, 0x04, 0xAB, 0x82, 0x24, 0x00]),
    "neo6Music":        bytearray([0x02, 0x04, 0xAB, 0x82, 0x26, 0x00]),
    "concertHallA":     bytearray([0x02, 0x04, 0xAB, 0x82, 0x1E, 0x00]),
    "concertHallB":     bytearray([0x02, 0x04, 0xAB, 0x82, 0x1F, 0x00]),
    "concertHallC":     bytearray([0x02, 0x04, 0xAB, 0x82, 0x38, 0x00]),
    "jazzClub":         bytearray([0x02, 0x04, 0xAB, 0x82, 0x16, 0x00]),
    "liveConcert":      bytearray([0x02, 0x04, 0xAB, 0x82, 0x19, 0x00]),
    "stadium":          bytearray([0x02, 0x04, 0xAB, 0x82, 0x1B, 0x00]),
    "sports":           bytearray([0x02, 0x04, 0xAB, 0x82, 0x20, 0x00]),
    "portableAudio":    bytearray([0x02, 0x04, 0xAB, 0x82, 0x30, 0x00]),
}

FEEDBACK_PURE_DIRECT_ON  = bytearray([0x02, 0x03, 0xAB, 0x98, 0x01])
FEEDBACK_PURE_DIRECT_OFF = bytearray([0x02, 0x03, 0xAB, 0x98, 0x00])

FEEDBACK_SOUND_OPTIMIZER_MAP = {
    "off":              bytearray([0x02, 0x04, 0xAB, 0x92, 0x48, 0x00]),
    "normal":           bytearray([0x02, 0x04, 0xAB, 0x92, 0x48, 0x01]),
    "low":              bytearray([0x02, 0x04, 0xAB, 0x92, 0x48, 0x02]),
}

FEEDBACK_VOLUME =       bytearray([0x02, 0x06, 0xA8, 0x8b, 0x00, 0x03, 0x00])
#FEEDBACK_MUTE =         bytearray([0x02, 0x07, 0xA8, 0x82, 0x00, 0x2E, 0x00, 0x13, 0x00])
#FEEDBACK_UNMUTE =       bytearray([0x02, 0x07, 0xA8, 0x82, 0x00, 0x2E, 0x00, 0x11, 0x00])

FEEDBACK_MUTE =         bytearray([0x13])
FEEDBACK_UNMUTE =       bytearray([0x11])

SOURCE_MENU_MAP = {
    "bdDvd": "Blueray / DVD",
    "game": "Game",
    "satCaTV": "Sat / Cable",
    "video": "Video",
    "tv": "TV",
    "saCd": "CD",
    "fmTuner": "FM Tuner",
    "bluetooth": "Bluetooth",
    "usb": "USB",
    "homeNetwork": "Home Network",
    "screenMirroring": "Screen Mirroring",
}

SOUND_FIELD_MENU_MAP = {
    "twoChannelStereo": "2 Channels",
    "aDirect": "A Direct",
    "multiStereo": "Multi Stereo",
    "afd": "A.F.D.",
    "pl2Movie": "PL-II Movie",
    "neo6Cinema": "Neo 6: Cinema",
    "hdDcs": "HD DCS",
    "pl2Music": "PL-II Music",
    "neo6Music": "Neo 6: Music",
    "concertHallA": "Concert Hall A",
    "concertHallB": "Concert Hall B",
    "concertHallC": "Concert Hall C",
    "jazzClub": "Jazz Club",
    "liveConcert": "Live Concert",
    "stadium": "Stadium",
    "sports": "Sports",
    "portableAudio": "Portable Audio"
}

SOUND_OPTIMIZER_MENU_MAP = {
    "off": "Off",
    "normal": "Normal",
    "low": "Low"
}

SOURCE_MENU_ITEMS = {}
SOUND_FIELD_MENU_ITEMS = {}

current_power = True
current_timer = False
timer_hours = 0
timer_minutes = 0
current_power = True
current_source = None
current_sound_field = None
current_pure_direct = False
current_sound_optimizer = None
current_volume = LOW_VOLUME
muted = False

scroll_volume = 2
slide_speed = 0.05
scroll_speed = 0.1

source_group = []
sound_field_group = []

show_source_name = True
show_power_notifications = True
show_timer_notifications = True
show_source_notifications = True
show_sound_field_notifications = False
show_pure_direct_notifications = True
show_sound_optimizer_notifications = True
show_muted_notifications = True
show_volume_notifications = False

debug_send_commands = True
debug_receive_commands = True

debug_power = True
debug_timer = True
debug_source = True
debug_sound_field = True
debug_pure_direct = True
debug_sound_optimizer = True
debug_muted = True
debug_volume = True

_indicator = None
_device_service = None
_watcher_thread = None
_notification = notify.Notification.new("")
_notifications_initialized = False
_initialized = False


def connect():
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.connect((_device_service.ip, TCP_PORT))
    return s

def disconnect(s):
    s.close()

def send_command(cmd):
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.connect((_device_service.ip, TCP_PORT))
    s.send(cmd)
    s.close()
    if debug_send_commands:
        print "[sending] " + ", ".join([hex(byte) for byte in cmd])

def show_notification(title, text, icon):
    if _notifications_initialized:
        _notification.update(title, text, icon)
        _notification.show()

def update_power(power):
    global current_power
    current_power = power
    if debug_power:
        print "Power state:", power
    if show_power_notifications:
        if power:
            show_notification("<b>Power ON</b>", "", None)
        else:
            show_notification("<b>Power OFF</b>", "", None)

def update_timer(hours, minutes, set_timer, was_updated):
    global current_timer
    global timer_hours
    global timer_minutes
    current_timer = True
    timer_hours = hours
    timer_minutes = minutes
    if debug_timer:
        print "Timer:", hours, minutes, set_timer, was_updated
    if show_timer_notifications:
        if not set_timer:
            show_notification("<b>Timer OFF</b>", "", None)
        elif not was_updated:
            show_notification("<b>Timer SET</b>", "Device will shutdown in %s:%s h"%(hours, minutes), None)
        elif hours == 0 and minutes < 15:
            show_notification("<b>Timer</b>", "Device will shutdown in %s:%s h"%(hours, minutes), None)

def update_source(source_name):
    global current_source
    changed = (source_name != current_source)
    current_source = source_name
    if show_source_name:
        _indicator.set_label(SOURCE_MENU_MAP[source_name], "x")
    if debug_source:
        print "Source:", source_name
    if show_source_notifications and changed:
        show_notification("<b>Source</b>", SOURCE_MENU_MAP[source_name], None)

def select_source(source, source_name):
    if _initialized and current_source != source_name and source.get_active():
        update_source(source_name)
        send_command(CMD_SOURCE_MAP[source_name])

def update_sound_field(sound_field_name):
    global current_sound_field
    current_sound_field = sound_field_name
    if debug_sound_field:
        print "Sound field:", sound_field_name
    if show_sound_field_notifications:
        show_notification("<b>Sound Field</b>", SOUND_FIELD_MENU_MAP[sound_field_name], None)

def select_sound_field(source, sound_field_name):
    if _initialized and current_sound_field != sound_field_name and source.get_active():
        update_sound_field(sound_field_name)
        send_command(CMD_SOUND_FIELD_MAP[sound_field_name])

def update_pure_direct(pure_direct):
    global current_pure_direct
    current_pure_direct = pure_direct
    if debug_pure_direct:
        print "Pure Direct:", pure_direct
    if show_pure_direct_notifications:
        if pure_direct:
            show_notification("<b>Pure Direct ON</b>", "", None)
        else:
            show_notification("<b>Pure Direct OFF</b>", "", None)

def update_sound_optimizer(sound_optimizer_name):
    global current_sound_optimizer
    current_sound_optimizer = sound_optimizer_name
    if debug_sound_optimizer:
        print "Sound Optimizer:", sound_optimizer_name
    if show_sound_optimizer_notifications:
        show_notification("<b>Sound Optimizer</b>", SOUND_OPTIMIZER_MENU_MAP[sound_optimizer_name], None)

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
    if _initialized:
        if vol > current_volume:
            muted = False
        current_volume = vol
        set_volume_icon(vol)
        if debug_volume:
            print "Volume ", vol
        if show_volume_notifications:
            pass

def update_muted(_muted):
    global muted
    global current_notification
    if _initialized:
        changed = (_muted != muted)
        muted = _muted
        set_volume_icon(current_volume)
        if debug_muted:
            if muted:
                print "Muted"
            else:
                print "Unmuted"
        if show_muted_notifications and changed:
            if muted:
                show_notification("<b>Muted</b>", "", get_volume_icon_path("audio-volume-muted-panel"))
            else:
                show_notification("<b>Unmuted</b>", "", get_volume_icon_path(get_volume_icon(current_volume)))

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
        set_volume(None, target_volume)

def scroll_volume_down():
    target_volume = current_volume - scroll_volume
    if target_volume >= MIN_VOLUME:
        set_volume(None, target_volume)

def mute(source):
    if _initialized:
        send_command(CMD_MUTE)
        update_muted(True)

def unmute(source):
    if _initialized:
        send_command(CMD_UNMUTE)
        update_muted(False)

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
    global source_group
    global sound_field_group
    menu = gtk.Menu()

    sources_menu = gtk.Menu()
    item_sources = gtk.MenuItem("Sources")
    item_sources.set_submenu(sources_menu)
    for source_name in SOURCE_NAMES:
        item_select_source = gtk.RadioMenuItem.new_with_label(source_group, SOURCE_MENU_MAP[source_name])
        source_group = item_select_source.get_group()
        item_select_source.connect("activate", select_source, source_name)
        sources_menu.append(item_select_source)
        SOURCE_MENU_ITEMS[source_name] = item_select_source
    menu.append(item_sources)

    sound_field_menu = gtk.Menu()
    item_sound_field = gtk.MenuItem("Sound Field")
    item_sound_field.set_submenu(sound_field_menu)
    for sound_field_name in SOUND_FIELD_NAMES:
        item_select_sound_field = gtk.RadioMenuItem.new_with_label(sound_field_group, SOUND_FIELD_MENU_MAP[sound_field_name])
        sound_field_group = item_select_sound_field.get_group()
        item_select_sound_field.connect("activate", select_sound_field, sound_field_name)
        sound_field_menu.append(item_select_sound_field)
        SOUND_FIELD_MENU_ITEMS[sound_field_name] = item_select_sound_field
    menu.append(item_sound_field)

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
    _feedback_watcher_thread.kill()
    _feedback_watcher_thread.join(8)
    gtk.main_quit()

class ScanPort(threading.Thread):

    ip = None
    result = -1

    def __init__(self, ip):
        threading.Thread.__init__(self)
        self.ip = ip

    def run(self):
        _socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        _socket.settimeout(3)
        self.result = _socket.connect_ex((self.ip, TCP_PORT))
        _socket.close()

class DeviceService():

    my_ip = None
    my_network = None

    ip = None

    def __init__(self):
        self.my_ip = [l for l in ([ip for ip in socket.gethostbyname_ex(socket.gethostname())[2] if not ip.startswith("127.")][:1], [[(s.connect(('8.8.8.8', 53)), s.getsockname()[0], s.close()) for s in [socket.socket(socket.AF_INET, socket.SOCK_DGRAM)]][0][1]]) if l][0][0]
        self.my_network = self.my_ip.rsplit(".", 1)[0]

    def find_device(self):
        threads = []
        for last_octet in range(1, 254):
            device_ip = "%s.%s" %(self.my_network, last_octet)
            thread = ScanPort(device_ip)
            thread.start()
            threads.append(thread)

        for last_octet in range(1, 254):
            threads[last_octet - 1].join()
            if threads[last_octet - 1].result == 0:
                self.ip = threads[last_octet - 1].ip
                print "Detected device on %s:%s" %(self.ip, TCP_PORT)

class FeedbackWatcher(threading.Thread):

    _ended = False
    _socket = None

    def __init__(self):
        threading.Thread.__init__(self)

    def kill(self):
        self._ended = True
        self._socket.shutdown(socket.SHUT_WR)

    def check_power(self, data):
        if FEEDBACK_POWER_OFF == data:
            update_power(False)
            return True
        elif FEEDBACK_POWER_ON == data:
            update_power(True)
            return True
        return False

    def check_timer(self, data):
        if FEEDBACK_TIMER_PREFIX == data[:-3]:
            if FEEDBACK_TIMER_SET == data[-1]:
                update_timer(ord(data[-3]), ord(data[-2]), True, False)
                return True
            elif FEEDBACK_TIMER_UPDATE == data[-1]:
                update_timer(ord(data[-3]), ord(data[-2]), True, True)
                return True
            elif FEEDBACK_TIMER_OFF == data[-1]:
                update_timer(ord(data[-3]), ord(data[-2]), False, False)
                return True
        return False

    def check_source(self, data):
        source_switched = False
        for source_name, source_feedback in FEEDBACK_SOURCE_MAP.iteritems():
            if source_feedback == data[:-2]:
                SOURCE_MENU_ITEMS[source_name].set_active(True)
                source_switched = True
                # The command also contains the muted state
                if FEEDBACK_MUTE == data[-2]: 
                    update_muted(True)
                elif FEEDBACK_UNMUTE == data[-2]:
                    update_muted(False)
        return source_switched

    def check_sound_field(self, data):
        sound_field_switched = False
        for sound_field_name, sound_field_feedback in FEEDBACK_SOUND_FIELD_MAP.iteritems():
            if sound_field_feedback == data:
                SOUND_FIELD_MENU_ITEMS[sound_field_name].set_active(True)
                sound_field_switched = True
        return sound_field_switched

    def check_pure_direct(self, data):
        if FEEDBACK_PURE_DIRECT_ON == data:
            update_pure_direct(True)
            return True
        elif FEEDBACK_PURE_DIRECT_OFF == data:
            update_pure_direct(False)
            return True
        return False

    def check_sound_optimizer(self, data):
        sound_optimizer_switched = False
        for sound_optimizer_name, sound_optimizer_feedback in FEEDBACK_SOUND_OPTIMIZER_MAP.iteritems():
            if sound_optimizer_feedback == data:
                update_sound_optimizer(sound_optimizer_name)
                sound_optimizer_switched = True
        return sound_optimizer_switched

    def check_volume(self, data):
        if FEEDBACK_VOLUME == data[:-1]:
            update_volume(ord(data[-1]))
            return True
        return False

    def debug_data(self, data, prepend_text="[receiving] "):
        opcode = ", ".join([hex(ord(byte)) for byte in data])
        print "%s%s" %(prepend_text, opcode)

    def connect(self):
        self._socket.connect((_device_service.ip, TCP_PORT))
        print "Connected"
        
    def reconnect(self):
        self._socket.close()
        self._socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._socket.connect((_device_service.ip, TCP_PORT))
        print "Reconnected"

    def run(self):
        self._socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.connect()
        while not self._ended:
            try:
                data = self._socket.recv(BUFFER_SIZE)
                if debug_receive_commands:
                    self.debug_data(data)
                if not self.check_power(data) and \
                   not self.check_timer(data) and \
                   not self.check_source(data) and \
                   not self.check_sound_field(data) and \
                   not self.check_pure_direct(data) and \
                   not self.check_sound_optimizer(data) and \
                   not self.check_volume(data):
                    self.debug_data(data, "[unknown data packet]\n")
            except Exception, err:
                print "Socket read error: ", err
                traceback.print_exc()
                self.reconnect()
        self._socket.close()
        print "Connection closed"

def main():
    global _initialized
    global _indicator
    global _notification
    global _notifications_initialized
    global _device_service
    global _feedback_watcher_thread
    indicator = appindicator.Indicator.new(APPINDICATOR_ID, get_volume_icon_path(get_volume_icon(current_volume)), appindicator.IndicatorCategory.SYSTEM_SERVICES)
    indicator.set_status(appindicator.IndicatorStatus.ACTIVE)
    indicator.set_menu(build_menu(indicator))
    indicator.connect("scroll-event", scroll)
    notify.init(APPINDICATOR_ID)
    _notification = notify.Notification.new("")
    _notifications_initialized = True
    _indicator = indicator
    signal.signal(signal.SIGINT, signal.SIG_DFL)
    
    _device_service = DeviceService()
    _device_service.find_device()

    _feedback_watcher_thread = FeedbackWatcher()
    _feedback_watcher_thread.start()

    _initialized = True

    gtk.main()


if __name__ == "__main__":
    main()
