#!/usr/bin/env python

__author__ = "andreasschaeffer"
__author__ = "michaelkapuscik"

import socket
import time
import signal
import gi
import os
import threading

gi.require_version("Gtk", "3.0")
gi.require_version("AppIndicator3", "0.1")
gi.require_version('Notify', '0.7')

from gi.repository import Gtk as gtk
from gi.repository import Gdk as gdk
from gi.repository import AppIndicator3 as appindicator
from gi.repository import Notify as notify

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
SOUND_FIELD_NAMES = [ "twoChannelStereo", "aDirect", "multiStereo", "afd", "pl2Movie", "neo6Cinema", "hdDcs", "pl2Music", "neo6Music", "concertHallA", "concertHallB", "concertHallC", "jazzClub", "liveConcert", "stadium", "sports", "portableAudio" ]

CMD_MIN_VOLUME =  bytearray([0x02, 0x06, 0xA0, 0x52, 0x00, 0x03, 0x00, 0x00, 0x00])
CMD_MAX_VOLUME =  bytearray([0x02, 0x06, 0xA0, 0x52, 0x00, 0x03, 0x00, 0x4A, 0x00])
CMD_MUTE =        bytearray([0x02, 0x04, 0xA0, 0x53, 0x00, 0x01, 0x00])
CMD_UNMUTE =      bytearray([0x02, 0x04, 0xA0, 0x53, 0x00, 0x00, 0x00])

CMD_SOURCE_MAP = {
    "bdDvd":      bytearray([0x02, 0x04, 0xA0, 0x42, 0x00, 0x1b, 0x00]),
    "game":       bytearray([0x02, 0x04, 0xA0, 0x42, 0x00, 0x1c, 0x00]),
    "satCaTV":    bytearray([0x02, 0x04, 0xA0, 0x42, 0x00, 0x16, 0x00]),
    "video":      bytearray([0x02, 0x04, 0xA0, 0x42, 0x00, 0x10, 0x00]),
    "tv":         bytearray([0x02, 0x04, 0xA0, 0x42, 0x00, 0x1a, 0x00]),
    "saCd":       bytearray([0x02, 0x04, 0xA0, 0x42, 0x00, 0x02, 0x00]),
    "fmTuner":    bytearray([0x02, 0x04, 0xA0, 0x42, 0x00, 0x2e, 0x00]),
    "usb":        bytearray([0x02, 0x04, 0xA0, 0x42, 0x00, 0x34, 0x00]),
    "bluetooth":  bytearray([0x02, 0x04, 0xA0, 0x42, 0x00, 0x34, 0x00])
}

# TODO: find out OPCODES for sound fields
CMD_SOUND_FIELD_MAP = {
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

# FEEDBACK_POWER_ON =     bytearray([0x02, 0x07, 0xA8, 0x82, 0x00, 0x2E, 0x00, 0x10, 0x00])
FEEDBACK_POWER_OFF =    bytearray([0x02, 0x07, 0xA8, 0x82, 0x00, 0x2E, 0x00, 0x10, 0x00])

FEEDBACK_VOLUME =       bytearray([0x02, 0x06, 0xA8, 0x8b, 0x00, 0x03, 0x00])
FEEDBACK_MUTE =         bytearray([0x02, 0x07, 0xA8, 0x82, 0x00, 0x2E, 0x00, 0x13, 0x00])
FEEDBACK_UNMUTE =       bytearray([0x02, 0x07, 0xA8, 0x82, 0x00, 0x2E, 0x00, 0x11, 0x00])

FEEDBACK_SOURCE_MAP = {
    "bdDvd":            bytearray([0x02, 0x07, 0xA8, 0x82, 0x00, 0x1B, 0x00, 0x11, 0x00]),
    "game":             bytearray([0x02, 0x07, 0xA8, 0x82, 0x00, 0x1C, 0x00, 0x11, 0x00]),
    "satCaTV":          bytearray([0x02, 0x07, 0xA8, 0x82, 0x00, 0x16, 0x00, 0x11, 0x00]),
    "video":            bytearray([0x02, 0x07, 0xA8, 0x82, 0x00, 0xFF, 0x00, 0x11, 0x00]),
    "tv":               bytearray([0x02, 0x07, 0xA8, 0x82, 0x00, 0x1A, 0x00, 0x11, 0x00]),
    "saCd":             bytearray([0x02, 0x07, 0xA8, 0x82, 0x00, 0x02, 0x00, 0x11, 0x00]),
    "fmTuner":          bytearray([]),
    "usb":              bytearray([0x02, 0x07, 0xA8, 0x82, 0x00, 0x34, 0x00, 0x11, 0x00]),
    "bluetooth":        bytearray([0x02, 0x07, 0xA8, 0x82, 0x00, 0x33, 0x00, 0x11, 0x00])
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


current_power = True
current_source = "satCaTV"
current_sound_field = "twoChannelStereo"
current_volume = LOW_VOLUME
muted = False

scroll_volume = 2
slide_speed = 0.05
scroll_speed = 0.1

show_power_notifications = True
show_source_notifications = True
show_sound_field_notifications = False
show_volume_notifications = False

_indicator = None
_watcher_thread = None
_notification = notify.Notification.new("")


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


def update_power(power):
    global current_power
    current_power = power
    if show_power_notifications:
        print "Power state:", power
        if power:
            _notification.update("<b>Power ON</b>", "", None)
            _notification.show()
        else:
            _notification.update("<b>Power OFF</b>", "", None)
            _notification.show()

def update_source(source_name):
    global current_power
    current_source = source_name
    if show_source_notifications:
        print "Switched source:", source_name
        _notification.update("<b>Source</b>", SOURCE_MENU_MAP[source_name], None)
        _notification.show()

def select_source(source, source_name):
    send_command(CMD_SOURCE_MAP[source_name])
    update_source(source_name)


def update_sound_field(sound_field_name):
    current_sound_field = sound_field_name
    if show_sound_field_notifications:
        print "Switched sound field:", sound_field_name
        _notification.update("<b>Sound Field</b>", SOUND_FIELD_MENU_MAP[sound_field_name], None)
        _notification.show()

def select_sound_field(source, sound_field_name):
    send_command(CMD_SOUND_FIELD_MAP[sound_field_name])
    update_sound_field(sound_field_name)


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
    if show_volume_notifications:
        print "Volume ", vol

def update_muted(_muted):
    global muted
    global current_notification
    muted = _muted
    set_volume_icon(current_volume)
    if show_volume_notifications:
        if muted:
            _notification.update("<b>Muted</b>", "", get_volume_icon_path("audio-volume-muted-panel"))
            _notification.show()
        else:
            _notification.update("<b>Unmuted</b>", "", get_volume_icon_path(get_volume_icon(current_volume)))
            _notification.show()

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
    s.close()
    update_muted(True)

def unmute(source):
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.connect((TCP_IP, TCP_PORT))
    s.send(CMD_UNMUTE)
    s.close()
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
    menu = gtk.Menu()

    sources_menu = gtk.Menu()
    item_sources = gtk.MenuItem("Sources")
    item_sources.set_submenu(sources_menu)
    for source_name in SOURCE_NAMES:
        item_select_source = gtk.MenuItem(SOURCE_MENU_MAP[source_name])
        item_select_source.connect("activate", select_source, source_name)
        sources_menu.append(item_select_source)
    menu.append(item_sources)

    sound_field_menu = gtk.Menu()
    item_sound_field = gtk.MenuItem("Sound Field")
    item_sound_field.set_submenu(sound_field_menu)
    for sound_field_name in SOUND_FIELD_NAMES:
        item_select_sound_field = gtk.MenuItem(SOUND_FIELD_MENU_MAP[sound_field_name])
        item_select_sound_field.connect("activate", select_sound_field, sound_field_name)
        sound_field_menu.append(item_select_sound_field)
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


class FeedbackWatcher(threading.Thread):

    _ended = False

    def __init__(self):
        threading.Thread.__init__(self)

    def kill(self):
        self._ended = True

    def check_power(self, data):
        if FEEDBACK_POWER_OFF == data:
            update_power(False)
        else:
            return False
        return True

    def check_source(self, data):
        source_switched = False
        for source_name, source_feedback in FEEDBACK_SOURCE_MAP.iteritems():
            # print source_name
            # print source_feedback
            # print data
            if source_feedback == data:
                update_source(source_name)
                source_switched = True
        return source_switched

    def check_sound_field(self, data):
        sound_field_switched = False
        for sound_field_name, sound_field_feedback in FEEDBACK_SOUND_FIELD_MAP.iteritems():
            if sound_field_feedback == data:
                update_sound_field(sound_field_name)
                sound_field_switched = True
        return sound_field_switched

    def check_volume(self, data):
        if FEEDBACK_VOLUME == data[:-1]:
            update_volume(ord(data[-1]))
        elif FEEDBACK_MUTE == data:
            update_muted(True)
        elif FEEDBACK_UNMUTE == data:
            update_muted(False)
        else:
            return False
        return True

    def debug_data(self, data):
        print "Received unknown data:"
        for i in data:
            print hex(ord(i))

    def run(self):
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        # s.settimeout(0.2)
        s.connect((TCP_IP, TCP_PORT))
        while not self._ended:
            try:
                data = s.recv(BUFFER_SIZE)
                if not self.check_power(data) and not self.check_source(data) and not self.check_sound_field(data) and not self.check_volume(data):
                    self.debug_data(data)
            except:
                pass
        s.close()

def watch_feedback():
    global _feedback_watcher_thread
    _feedback_watcher_thread = FeedbackWatcher()
    _feedback_watcher_thread.start()


def main():
    global _indicator
    global _notification
    indicator = appindicator.Indicator.new(APPINDICATOR_ID, get_volume_icon_path(get_volume_icon(current_volume)), appindicator.IndicatorCategory.SYSTEM_SERVICES)
    indicator.set_status(appindicator.IndicatorStatus.ACTIVE)
    indicator.set_menu(build_menu(indicator))
    indicator.connect("scroll-event", scroll)
    notify.init(APPINDICATOR_ID)
    _notification = notify.Notification.new("")
    _indicator = indicator
    signal.signal(signal.SIGINT, signal.SIG_DFL)
    watch_feedback()
    gtk.main()


if __name__ == "__main__":
    main()
