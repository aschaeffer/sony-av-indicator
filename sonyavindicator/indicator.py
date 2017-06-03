#!/usr/bin/env python
# -*- coding: utf-8 -*-

# TODO: request sound field state during startup

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
import webbrowser
import time
import dbus
import dbus.service
import binascii

gi.require_version("Gtk", "3.0")
gi.require_version("AppIndicator3", "0.1")
gi.require_version('Notify', '0.7')

from gi.repository import Gtk as gtk
from gi.repository import Gdk as gdk
from gi.repository import AppIndicator3 as appindicator
from gi.repository import Notify as notify
from gi.repository import GObject

from dbus.mainloop.glib import DBusGMainLoop


logging.basicConfig(level = logging.DEBUG, format = "%(asctime)-15s [%(name)-5s] [%(levelname)-5s] %(message)s", datefmt="%Y-%m-%d %H:%M:%S")

APPINDICATOR_ID = "sonyavindicator"

IDENTITY = 'sonyavindicator'

DESKTOP = 'sonyavindicator'

BUS_NAME = 'org.mpris.MediaPlayer2.' + IDENTITY
OBJECT_PATH = '/org/mpris/MediaPlayer2'
ROOT_INTERFACE = 'org.mpris.MediaPlayer2'
PLAYER_INTERFACE = 'org.mpris.MediaPlayer2.Player'
PROPERTIES_INTERFACE = 'org.freedesktop.DBus.Properties'
PLAYLISTS_IFACE = 'org.mpris.MediaPlayer2.Playlists'

# 80, 5000, 8008, 8009, 10000, 22222, 33335, 33336, 35275, 41824, 50001, 50002, 52323, 54400
TCP_PORT_1 = 33335
TCP_PORT_2 = 33336
BUFFER_SIZE = 1024

MIN_VOLUME = 0
LOW_VOLUME = 15
MEDIUM_VOLUME = 30
MAX_VOLUME = 45
LIMIT_VOLUME = MAX_VOLUME

ICON_PATH = "/usr/share/icons/ubuntu-mono-dark/status/24"

SOURCE_NAMES = [ "bdDvd", "game", "satCaTV", "video", "tv", "saCd", "fmTuner", "bluetooth", "usb", "homeNetwork", "internetServices", "screenMirroring", "googleCast" ]
SOUND_FIELD_NAMES = [ [ "twoChannelStereo", "analogDirect", "multiStereo", "afd" ], [ "pl2Movie", "neo6Cinema", "hdDcs" ], [ "pl2Music", "neo6Music", "concertHallA", "concertHallB", "concertHallC", "jazzClub", "liveConcert", "stadium", "sports", "portableAudio" ] ]

# Byte 5 (0x00) seems to be the zone (not STR-DN-860, but maybe STR-DN-1060)
CMD_SOURCE_MAP = {
    "bdDvd":                bytearray([0x02, 0x04, 0xA0, 0x42, 0x00, 0x1B, 0x00]),
    "game":                 bytearray([0x02, 0x04, 0xA0, 0x42, 0x00, 0x1C, 0x00]),
    "satCaTV":              bytearray([0x02, 0x04, 0xA0, 0x42, 0x00, 0x16, 0x00]),
    "video":                bytearray([0x02, 0x04, 0xA0, 0x42, 0x00, 0x10, 0x00]),
    "tv":                   bytearray([0x02, 0x04, 0xA0, 0x42, 0x00, 0x1A, 0x00]),
    "saCd":                 bytearray([0x02, 0x04, 0xA0, 0x42, 0x00, 0x02, 0x00]),
    # "hdmi1":              bytearray([0x02, 0x04, 0xA0, 0x42, 0x00, 0x21, 0x00]),
    # "hdmi2":              bytearray([0x02, 0x04, 0xA0, 0x42, 0x00, 0x22, 0x00]),
    # "hdmi3":              bytearray([0x02, 0x04, 0xA0, 0x42, 0x00, 0x23, 0x00]),
    # "hdmi4":              bytearray([0x02, 0x04, 0xA0, 0x42, 0x00, 0x24, 0x00]),
    # "hdmi5":              bytearray([0x02, 0x04, 0xA0, 0x42, 0x00, 0x25, 0x00]),
    # "hdmi6":              bytearray([0x02, 0x04, 0xA0, 0x42, 0x00, 0x26, 0x00]),
    "fmTuner":              bytearray([0x02, 0x04, 0xA0, 0x42, 0x00, 0x2E, 0x00]),
    "amTuner":              bytearray([0x02, 0x04, 0xA0, 0x42, 0x00, 0x2F, 0x00]),
    # "shoutcast":          bytearray([0x02, 0x04, 0xA0, 0x42, 0x00, 0x32, 0x00]),
    "bluetooth":            bytearray([0x02, 0x04, 0xA0, 0x42, 0x00, 0x33, 0x00]),
    "usb":                  bytearray([0x02, 0x04, 0xA0, 0x42, 0x00, 0x34, 0x00]),
    "homeNetwork":          bytearray([0x02, 0x04, 0xA0, 0x42, 0x00, 0x3D, 0x00]),
    "internetServices":     bytearray([0x02, 0x04, 0xA0, 0x42, 0x00, 0x3E, 0x00]),
    "screenMirroring":      bytearray([0x02, 0x04, 0xA0, 0x42, 0x00, 0x40, 0x00]),
    "googleCast":           bytearray([0x02, 0x04, 0xA0, 0x42, 0x00, 0xFF, 0x00]),
}

# Byte 5 (0x00) seems to be the zone (not STR-DN-860, but maybe STR-DN-1060)
CMD_MUTE                  = bytearray([0x02, 0x04, 0xA0, 0x53, 0x00, 0x01, 0x00])
CMD_UNMUTE                = bytearray([0x02, 0x04, 0xA0, 0x53, 0x00, 0x00, 0x00])

# Byte 5 (0x00) seems to be the zone (not STR-DN-860, but maybe STR-DN-1060)
CMD_POWER_ON              = bytearray([0x02, 0x04, 0xA0, 0x60, 0x00, 0x01, 0x00])
CMD_POWER_OFF             = bytearray([0x02, 0x04, 0xA0, 0x60, 0x00, 0x00, 0x00])

CMD_HDMIOUT_ON            = bytearray([0x02, 0x03, 0xA0, 0x45, 0x00, 0x00])
CMD_HDMIOUT_OFF           = bytearray([0x02, 0x03, 0xA0, 0x45, 0x03, 0x00])

# Last byte seems to be zero (but was a checksum)
CMD_SOUND_FIELD_MAP = {
    "twoChannelStereo":     bytearray([0x02, 0x03, 0xA3, 0x42, 0x00, 0x00]),
    "analogDirect":         bytearray([0x02, 0x03, 0xA3, 0x42, 0x02, 0x00]),
    "multiStereo":          bytearray([0x02, 0x03, 0xA3, 0x42, 0x27, 0x00]),
    "afd":                  bytearray([0x02, 0x03, 0xA3, 0x42, 0x21, 0x00]),
    "pl2Movie":             bytearray([0x02, 0x03, 0xA3, 0x42, 0x23, 0x00]),
    "neo6Cinema":           bytearray([0x02, 0x03, 0xA3, 0x42, 0x25, 0x00]),
    "hdDcs":                bytearray([0x02, 0x03, 0xA3, 0x42, 0x33, 0x00]),
    "pl2Music":             bytearray([0x02, 0x03, 0xA3, 0x42, 0x24, 0x00]),
    "neo6Music":            bytearray([0x02, 0x03, 0xA3, 0x42, 0x26, 0x00]),
    "concertHallA":         bytearray([0x02, 0x03, 0xA3, 0x42, 0x1E, 0x00]),
    "concertHallB":         bytearray([0x02, 0x03, 0xA3, 0x42, 0x1F, 0x00]),
    "concertHallC":         bytearray([0x02, 0x03, 0xA3, 0x42, 0x38, 0x00]),
    "jazzClub":             bytearray([0x02, 0x03, 0xA3, 0x42, 0x16, 0x00]),
    "liveConcert":          bytearray([0x02, 0x03, 0xA3, 0x42, 0x19, 0x00]),
    "stadium":              bytearray([0x02, 0x03, 0xA3, 0x42, 0x1B, 0x00]),
    "sports":               bytearray([0x02, 0x03, 0xA3, 0x42, 0x20, 0x00]),
    "portableAudio":        bytearray([0x02, 0x03, 0xA3, 0x42, 0x30, 0x00]),
}

# not working ? only preset up and down are working currently
CMD_FMTUNER = [
                            bytearray([0x02, 0x04, 0xA1, 0x42, 0x01, 0x01, 0x17]),
                            bytearray([0x02, 0x04, 0xA1, 0x42, 0x01, 0x02, 0x16]),
                            bytearray([0x02, 0x04, 0xA1, 0x42, 0x01, 0x03, 0x15]),
]

CMD_FMTUNER_PRESET_DOWN   = bytearray([0x02, 0x02, 0xA1, 0x0C, 0x51, 0x00])
CMD_FMTUNER_PRESET_UP     = bytearray([0x02, 0x02, 0xA1, 0x0B, 0x52, 0x00])

CMD_VOLUME_MIN            = bytearray([0x02, 0x06, 0xA0, 0x52, 0x00, 0x03, 0x00, 0x00, 0x00])
CMD_VOLUME_MAX            = bytearray([0x02, 0x06, 0xA0, 0x52, 0x00, 0x03, 0x00, 0x4A, 0x00])
CMD_VOLUME_UP             = bytearray([0x02, 0x03, 0xA0, 0x55, 0x00, 0x00])
CMD_VOLUME_DOWN           = bytearray([0x02, 0x03, 0xA0, 0x56, 0x00, 0x00])

# three bytes follows:
# - hours
# - minutes
# - seconds
# if hours, minutes and seconds are 0xFF, the timer was set to OFF
FEEDBACK_TIMER_PREFIX     = bytearray([0x02, 0x05, 0xA8, 0x90])
FEEDBACK_TIMER_SET        = bytearray([0x00])
FEEDBACK_TIMER_UPDATE     = bytearray([0x3B])
FEEDBACK_TIMER_OFF        = bytearray([0xFF])

# "video" == Google Cast + Bluetooth
# two bytes follows:
# - power off / unmuted / muted
# - zero byte
# byte 5 normally 0x00, but seldom 0x03
FEEDBACK_SOURCE_MAP = {
    "bdDvd":                bytearray([0x02, 0x07, 0xA8, 0x82, 0x00, 0x1B, 0x00]),
    "game":                 bytearray([0x02, 0x07, 0xA8, 0x82, 0x00, 0x1C, 0x00]),
    "satCaTV":              bytearray([0x02, 0x07, 0xA8, 0x82, 0x00, 0x16, 0x00]),
    "video":                bytearray([0x02, 0x07, 0xA8, 0x82, 0x00, 0xFF, 0x00]),
    "tv":                   bytearray([0x02, 0x07, 0xA8, 0x82, 0x00, 0x1A, 0x00]),
    "saCd":                 bytearray([0x02, 0x07, 0xA8, 0x82, 0x00, 0x02, 0x00]),
    "fmTuner":              bytearray([0x02, 0x07, 0xA8, 0x82, 0x00, 0x2E, 0x00]),
    "amTuner":              bytearray([0x02, 0x07, 0xA8, 0x82, 0x00, 0x2F, 0x00]),
    "bluetooth":            bytearray([0x02, 0x07, 0xA8, 0x82, 0x00, 0x33, 0x00]),
    "usb":                  bytearray([0x02, 0x07, 0xA8, 0x82, 0x00, 0x34, 0x00]),
    "homeNetwork":          bytearray([0x02, 0x07, 0xA8, 0x82, 0x00, 0x3D, 0x00]),
    "internetServices":     bytearray([0x02, 0x07, 0xA8, 0x82, 0x00, 0x3E, 0x00]),
    "screenMirroring":      bytearray([0x02, 0x07, 0xA8, 0x82, 0x00, 0x40, 0x00]),
    "googleCast":           bytearray([0x02, 0x07, 0xA8, 0x82, 0x00, 0xFF, 0x00]),
}
FEEDBACK_POWER_OFF        = bytearray([0x10])
FEEDBACK_MUTE_OFF         = bytearray([0x11])
FEEDBACK_MUTE_ON          = bytearray([0x13])

FEEDBACK_SOUND_FIELD_MAP = {
    "twoChannelStereo":     bytearray([0x02, 0x04, 0xAB, 0x82, 0x00, 0x00]),
    "analogDirect":         bytearray([0x02, 0x04, 0xAB, 0x82, 0x02, 0x00]),
    "multiStereo":          bytearray([0x02, 0x04, 0xAB, 0x82, 0x27, 0x00]),
    "afd":                  bytearray([0x02, 0x04, 0xAB, 0x82, 0x21, 0x00]),
    "pl2Movie":             bytearray([0x02, 0x04, 0xAB, 0x82, 0x23, 0x00]),
    "neo6Cinema":           bytearray([0x02, 0x04, 0xAB, 0x82, 0x25, 0x00]),
    "hdDcs":                bytearray([0x02, 0x04, 0xAB, 0x82, 0x33, 0x00]),
    "pl2Music":             bytearray([0x02, 0x04, 0xAB, 0x82, 0x24, 0x00]),
    "neo6Music":            bytearray([0x02, 0x04, 0xAB, 0x82, 0x26, 0x00]),
    "concertHallA":         bytearray([0x02, 0x04, 0xAB, 0x82, 0x1E, 0x00]),
    "concertHallB":         bytearray([0x02, 0x04, 0xAB, 0x82, 0x1F, 0x00]),
    "concertHallC":         bytearray([0x02, 0x04, 0xAB, 0x82, 0x38, 0x00]),
    "jazzClub":             bytearray([0x02, 0x04, 0xAB, 0x82, 0x16, 0x00]),
    "liveConcert":          bytearray([0x02, 0x04, 0xAB, 0x82, 0x19, 0x00]),
    "stadium":              bytearray([0x02, 0x04, 0xAB, 0x82, 0x1B, 0x00]),
    "sports":               bytearray([0x02, 0x04, 0xAB, 0x82, 0x20, 0x00]),
    "portableAudio":        bytearray([0x02, 0x04, 0xAB, 0x82, 0x30, 0x00]),
}

FEEDBACK_PURE_DIRECT_ON   = bytearray([0x02, 0x03, 0xAB, 0x98, 0x01])
FEEDBACK_PURE_DIRECT_OFF  = bytearray([0x02, 0x03, 0xAB, 0x98, 0x00])

# one byte follows
FEEDBACK_SOUND_OPTIMIZER_PREFIX = bytearray([0x02, 0x04, 0xAB, 0x92, 0x48])
FEEDBACK_SOUND_OPTIMIZER_OFF    = bytearray([0x00])
FEEDBACK_SOUND_OPTIMIZER_NORMAL = bytearray([0x01])
FEEDBACK_SOUND_OPTIMIZER_LOW    = bytearray([0x02])

FEEDBACK_FMTUNER_PREFIX   = bytearray([0x02, 0x07, 0xA9, 0x82, 0x80]);
FEEDBACK_FMTUNER_STEREO   = bytearray([0x00])
FEEDBACK_FMTUNER_MONO     = bytearray([0x80])

FEEDBACK_VOLUME           = bytearray([0x02, 0x06, 0xA8, 0x8b, 0x00, 0x03, 0x00])

FEEDBACK_AUTO_STANDBY_ON  = bytearray([0x02, 0x03, 0xA8, 0xA4, 0xCC])
FEEDBACK_AUTO_STANDBY_OFF = bytearray([0x02, 0x03, 0xA8, 0xA4, 0x4C])

FEEDBACK_AUTO_PHASE_MATCHING_AUTO = bytearray([0x2, 0x4, 0xab, 0x97, 0x48, 0x2])
FEEDBACK_AUTO_PHASE_MATCHING_OFF  = bytearray([0x2, 0x4, 0xab, 0x97, 0x48, 0x0])


SOURCE_MENU_MAP = {
    "bdDvd": "Blueray / DVD",
    "game": "Game",
    "satCaTV": "Sat / Cable",
    "video": "Video",
    "tv": "TV",
    "saCd": "CD",
    "fmTuner": "FM Tuner",
    "amTuner": "AM Tuner",
    "bluetooth": "Bluetooth",
    "usb": "USB",
    "homeNetwork": "Home Network",
    "internetServices": "Internet Services",
    "screenMirroring": "Screen Mirroring",
    "googleCast": "Google Cast",
}

SOUND_FIELD_MENU_MAP = {
    "twoChannelStereo": "2 Channels",
    "analogDirect": "Analog Direct",
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

FM_TUNER_MENU_MAP = {
    "1": "FM4",
    "2": "FM4",
    "3": "",
    "4": "",
    "5": "",
    "6": "",
    "7": "",
    "8": "",
    "9": "",
    "10": "",
    "11": "",
    "12": "",
    "13": "",
    "14": "",
    "15": "",
    "16": "",
    "17": "",
    "18": "",
    "19": "",
    "20": "",
    "21": "",
    "22": "",
    "23": "",
    "24": "",
    "25": "",
    "26": "",
    "27": "",
    "28": "",
    "29": "",
    "30": "",
}


class StateService():
    
    sony_av_indicator = None
    initialized = False

    logger = logging.getLogger("state")

    states = {
        "power": True,
        "hdmiout": True,
        "volume": LOW_VOLUME,
        "muted": False,
        "source": None,
        "sound_field": None,
        "pure_direct": False,
        "sound_optimizer": None,
        "timer": False,
        "timer_hours": 0,
        "timer_minutes": 0,
        "fmtuner": None,
        "fmtunerstereo": None,
        "fmtunerfreq": None,
        "auto_standby": True,
        "auto_phase_matching": True,
    }

    notifications = {
        "power": True,
        "hdmiout": True,
        "volume": False,
        "muted": True,
        "source": True,
        "sound_field": False,
        "pure_direct": True,
        "sound_optimizer": True,
        "timer": True,
        "fmtuner": True,
        "auto_standby": True,
        "auto_phase_matching": True,
    }

    def __init__(self, sony_av_indicator):
        self.sony_av_indicator = sony_av_indicator

    def __getattr__(self, key):
        try:
            return self.states[key]
        except KeyError as err:
            raise AttributeError(key)

    def __setattr_(self, key, value):
        try:
            self.states[key] = value
        except KeyError as err:
            raise AttributeError(key)

    def update_power(self, power, state_only = False):
        if self.initialized:
            changed = (power != self.power)
            self.power = power
            if not state_only:
                self.sony_av_indicator.update_label()
            if changed:
                self.logger.debug("Power state: %s" % power)
            if self.notifications["power"] and changed and not state_only:
                if power:
                    self.sony_av_indicator.show_notification("<b>Power ON</b>", "", None)
                else:
                    self.sony_av_indicator.show_notification("<b>Power OFF</b>", "", None)

    def update_hdmiout(self, hdmiout, state_only = False):
        if self.initialized:
            changed = (hdmiout != self.hdmiout)
            self.hdmiout = hdmiout
            if changed:
                self.logger.debug("HDMI Out: %s" % hdmiout)
            if self.notifications["hdmiout"] and changed and not state_only:
                if hdmiout:
                    self.sony_av_indicator.show_notification("<b>HDMI Out ON</b>", "", None)
                else:
                    self.sony_av_indicator.show_notification("<b>HDMI Out OFF</b>", "", None)

    def update_volume(self, vol):
        if self.initialized:
            if vol > self.volume:
                self.muted = False
            self.volume = vol
            self.sony_av_indicator.set_volume_icon(vol)
            self.logger.debug("Volume %d" % vol)
            if self.notifications["volume"]:
                # TODO: Show volume slider notification
                pass

    def update_muted(self, muted):
        if self.initialized:
            changed = (muted != self.muted)
            self.muted = muted
            self.sony_av_indicator.set_volume_icon(self.volume)
            if changed:
                if self.muted:
                    self.logger.debug("Muted")
                else:
                    self.logger.debug("Unmuted")
            if self.notifications["muted"] and changed:
                if self.muted:
                    self.sony_av_indicator.show_notification("<b>Muted</b>", "", self.sony_av_indicator.get_volume_icon_path("audio-volume-muted-panel"))
                else:
                    self.sony_av_indicator.show_notification("<b>Unmuted</b>", "", self.sony_av_indicator.get_volume_icon_path(self.sony_av_indicator.get_volume_icon(self.volume)))

    def update_source(self, source, state_only = False):
        changed = (source != self.source)
        self.source = source
        if not state_only:
            self.update_power(True, True)
            self.sony_av_indicator.update_label()
        if changed:
            self.logger.debug("Source: %s" % source)
        if self.notifications["source"] and changed and not state_only:
            self.sony_av_indicator.show_notification("<b>Source</b>", SOURCE_MENU_MAP[source], None)

    def update_sound_field(self, sound_field, state_only = False):
        changed = (sound_field != self.sound_field)
        self.sound_field = sound_field
        if changed:
            self.logger.debug("Sound field: %s" % sound_field)
        if self.notifications["sound_field"] and changed and not state_only:
            self.sony_av_indicator.show_notification("<b>Sound Field</b>", SOUND_FIELD_MENU_MAP[sound_field], None)

    def update_pure_direct(self, pure_direct):
        if self.initialized:
            self.pure_direct = pure_direct
            self.logger.debug("Pure Direct: %s" % pure_direct)
            if self.notifications["pure_direct"]:
                if self.pure_direct:
                    self.sony_av_indicator.show_notification("<b>Pure Direct ON</b>", "", None)
                else:
                    self.sony_av_indicator.show_notification("<b>Pure Direct OFF</b>", "", None)
    
    def update_sound_optimizer(self, sound_optimizer):
        if self.initialized:
            self.sound_optimizer = sound_optimizer
            self.logger.debug("Sound Optimizer: %s" % sound_optimizer)
            if self.notifications["sound_optimizer"]:
                self.sony_av_indicator.show_notification("<b>Sound Optimizer</b>", SOUND_OPTIMIZER_MENU_MAP[sound_optimizer], None)

    def update_timer(self, hours, minutes, seconds, set_timer, was_updated):
        self.timer = set_timer
        self.timer_hours = hours
        self.timer_minutes = minutes
        self.logger.debug("Timer: %d:%d:%d Set: %s Updated: %s" %(hours, minutes, seconds, set_timer, was_updated))
        if self.notifications["timer"]:
            if not set_timer:
                self.sony_av_indicator.show_notification("<b>Timer OFF</b>", "", None)
            elif not was_updated:
                self.sony_av_indicator.show_notification("<b>Timer SET</b>", "Device will shutdown in %s:%s h"%(hours, minutes), None)
            elif hours == 0 and minutes < 15 and seconds == 0:
                self.sony_av_indicator.show_notification("<b>Timer</b>", "Device will shutdown in %s:%s h"%(hours, minutes), None)

    def update_fmtuner(self, fmtuner, stereo, freq):
        if self.initialized:
            self.fmtuner = fmtuner
            self.fmtunerstereo = stereo
            self.fmtunerfreq = freq
            self.logger.debug("FM Tuner: %d (%3.2f MHz) Stereo: %s", fmtuner, freq, stereo)
            if self.notifications["fmtuner"]:
                if fmtuner != 255:
                    self.sony_av_indicator.show_notification("<b>FM Tuner %d</b>" %(fmtuner), "%s (%3.2f MHz)" %(FM_TUNER_MENU_MAP[str(fmtuner)], freq), None)
                else:
                    self.sony_av_indicator.show_notification("<b>FM Tuner</b>", "%3.2f MHz" %(freq), None)

    def update_auto_standby(self, auto_standby):
        if self.initialized:
            self.auto_standby = auto_standby
            self.logger.debug("Auto Standby: %s" % auto_standby)
            if self.notifications["auto_standby"]:
                if auto_standby:
                    self.sony_av_indicator.show_notification("<b>Auto Standby</b>", "ON", None)
                else:
                    self.sony_av_indicator.show_notification("<b>Auto Standby</b>", "OFF", None)

    def update_auto_phase_matching(self, auto_phase_matching):
        if self.initialized:
            self.auto_phase_matching = auto_phase_matching
            self.logger.debug("Auto Phase Matching: %s", auto_phase_matching)
            if self.notifications["auto_phase_matching"]:
                if auto_phase_matching:
                    self.sony_av_indicator.show_notification("<b>Auto Phase Matching</b>", "AUTO", None)
                else:
                    self.sony_av_indicator.show_notification("<b>Auto Phase Matching</b>", "OFF", None)


class CommandService():

    device_service = None
    state_service = None
    initialized = False
    block_sending = False

    scroll_step_volume = 2

    logger = logging.getLogger("cmd")
    data_logger = logging.getLogger("send")

    def __init__(self, device_service, state_service):
        self.device_service = device_service
        self.state_service = state_service

    def connect(self):
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.connect((_device_service.ip, TCP_PORT_1))
        return s

    def disconnect(self, s):
        s.close()

    def send_command(self, cmd):
        if not self.block_sending:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.connect((self.device_service.ip, TCP_PORT_1))
            s.send(cmd)
            s.close()
            self.data_logger.debug("%s", ", ".join([hex(byte) for byte in cmd]))
        else:
            # Wait on this thread or get a segmentation fault!
            time.sleep (50.0 / 1000.0);
            # self.data_logger.debug("%s", ", ".join([hex(byte) for byte in cmd]))

    def send_command_2(self, cmd):
        if not self.block_sending:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.connect((self.device_service.ip, TCP_PORT_2))
            s.send(cmd)
            s.close()
            self.data_logger.debug("%s", ", ".join([hex(byte) for byte in cmd]))
        else:
            # Wait on this thread or get a segmentation fault!
            time.sleep (50.0 / 1000.0);
            # self.data_logger.debug("%s", ", ".join([hex(byte) for byte in cmd]))

    def send_command_w(self, widget, cmd):
        self.send_command(cmd)

    def power_on(self):
        self.send_command(CMD_POWER_ON)

    def power_off(self):
        self.send_command(CMD_POWER_OFF)

    def toggle_power(self, widget):
        if self.initialized:
            if self.state_service.power:
                self.power_off()
                self.state_service.update_power(False)
            else:
                self.power_on()
                self.state_service.update_power(True)

    def hdmiout_on(self):
        self.send_command(CMD_HDMIOUT_ON)

    def hdmiout_off(self):
        self.send_command(CMD_HDMIOUT_OFF)

    def toggle_hdmiout(self, widget):
        if self.initialized:
            if self.state_service.hdmiout:
                self.hdmiout_off()
                self.state_service.update_hdmiout(False)
            else:
                self.hdmiout_on()
                self.state_service.update_hdmiout(True)

    def set_volume(self, widget, vol):
        cmd = bytearray([0x02, 0x06, 0xA0, 0x52, 0x00, 0x03, 0x00, min(vol, LIMIT_VOLUME), 0x00])
        self.send_command(cmd)
        self.state_service.update_volume(vol)

    def volume_up(self):
        target_volume = self.state_service.volume + self.scroll_step_volume
        if target_volume <= MAX_VOLUME:
            self.set_volume(None, target_volume)

    def volume_down(self):
        target_volume = self.state_service.volume - self.scroll_step_volume
        if target_volume >= MIN_VOLUME:
            self.set_volume(None, target_volume)

    def mute(self, widget):
        if self.initialized:
            self.send_command(CMD_MUTE)
            self.state_service.update_muted(True)

    def unmute(self, widget):
        if self.initialized:
            self.send_command(CMD_UNMUTE)
            self.state_service.update_muted(False)

    def toggle_mute(self, widget):
        if not self.state_service.power:
            self.toggle_power(widget)
        elif self.state_service.muted:
            self.unmute(widget)
        else:
            self.mute(widget)

    def select_source(self, source):
        if self.initialized and self.state_service.source != source:
            self.state_service.update_source(source)
            self.send_command(CMD_SOURCE_MAP[source])

    def select_source_w(self, widget, source):
        if widget.get_active():
            self.select_source(source)

    def source_up(self):
        for i in range(len(SOURCE_NAMES)):
            if self.state_service.source == SOURCE_NAMES[i]:
                if i < len(SOURCE_NAMES) - 1:
                    self.select_source(SOURCE_NAMES[i + 1])
                    return
                else:
                    self.select_source(SOURCE_NAMES[0])
                    return

    def source_down(self):
        for i in range(len(SOURCE_NAMES)):
            if self.state_service.source == SOURCE_NAMES[i]:
                if i > 0:
                    self.select_source(SOURCE_NAMES[i - 1])
                    return
                else:
                    self.select_source(SOURCE_NAMES[len(SOURCE_NAMES) - 1])
                    return

    def select_sound_field(self, sound_field):
        if self.initialized and self.state_service.sound_field != sound_field:
            self.state_service.update_sound_field(sound_field)
            self.send_command(CMD_SOUND_FIELD_MAP[sound_field])

    def select_sound_field_w(self, widget, sound_field):
        if widget.get_active():
            self.select_sound_field(sound_field)

    def set_fmtuner(self, widget, fmtuner):
        self.send_command(CMD_FMTUNER[fmtuner])

    def fmtuner_preset_up(self, widget):
        if self.initialized:
            if self.state_service.source != "fmTuner":
                self.send_command(CMD_SOURCE_MAP["fmTuner"])
            self.send_command(CMD_FMTUNER_PRESET_UP)

    def fmtuner_preset_down(self, widget):
        if self.initialized:
            if self.state_service.source != "fmTuner":
                self.send_command(CMD_SOURCE_MAP["fmTuner"])
            self.send_command(CMD_FMTUNER_PRESET_DOWN)


class ScanPort(threading.Thread):

    ip = None
    result = -1

    def __init__(self, ip):
        threading.Thread.__init__(self)
        self.ip = ip

    def run(self):
        _socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        _socket.settimeout(3)
        self.result = _socket.connect_ex((self.ip, TCP_PORT_1))
        _socket.close()


class GtkUpdater(threading.Thread):
    
    ended = False

    def __init__(self):
        threading.Thread.__init__(self)
    
    def run(self):
        while not self.ended:
            gtk.main_iteration_do(False)

    def kill(self):
        self.ended = True


class DeviceService():

    initialized = False
    my_ip = None
    my_network = None

    ip = None

    logger = logging.getLogger("dev")

    def __init__(self):
        self.my_ip = [l for l in ([ip for ip in socket.gethostbyname_ex(socket.gethostname())[2] if not ip.startswith("127.")][:1], [[(s.connect(('8.8.8.8', 53)), s.getsockname()[0], s.close()) for s in [socket.socket(socket.AF_INET, socket.SOCK_DGRAM)]][0][1]]) if l][0][0]
        self.my_network = self.my_ip.rsplit(".", 1)[0]
        self.logger.debug("Network: %s IP: %s" %(self.my_network, self.my_ip))

    def find_device(self):
        self.logger.debug("Searching for devices in %s.*" %(self.my_network))
        threads = []
        for last_octet in range(1, 254):
            device_ip = "%s.%s" %(self.my_network, last_octet)
            thread = ScanPort(device_ip)
            thread.start()
            threads.append(thread)

        gtk_updater = GtkUpdater()
        gtk_updater.start()

        for last_octet in range(1, 254):
            threads[last_octet - 1].join()
            if threads[last_octet - 1].result == 0:
                self.ip = threads[last_octet - 1].ip
                self.logger.info("Detected device on %s:%d" %(self.ip, TCP_PORT_1))

        gtk_updater.kill()

        if self.ip == None:
            self.logger.error("No device found in the local network!")


class FeedbackWatcher(threading.Thread):

    device_service = None
    state_service = None
    command_service = None
    ended = False
    socket = None
    port = None

    logger = logging.getLogger("feed")
    data_logger = logging.getLogger("recv")

    def __init__(self, sony_av_indicator, device_service, state_service, command_service, port):
        threading.Thread.__init__(self)
        self.sony_av_indicator = sony_av_indicator
        self.device_service = device_service
        self.state_service = state_service
        self.command_service = command_service
        self.port = port
        self.data_logger = logging.getLogger("recv:%s"%(port))

    def kill(self):
        self.ended = True
        self.socket.shutdown(socket.SHUT_WR)

    def check_volume(self, data):
        if FEEDBACK_VOLUME == data[:-1]:
            vol = data[-1]
            if vol < LIMIT_VOLUME:
                self.state_service.update_volume(vol)
            else:
                self.command_service.block_sending = False
                self.command_service.set_volume(None, LIMIT_VOLUME)
                self.command_service.block_sending = True
            return True
        return False

    def check_source(self, data):
        source_switched = False
        for source, source_feedback in FEEDBACK_SOURCE_MAP.items():
            if source_feedback == data[:-2]:
                self.sony_av_indicator.update_source(source)
                # The command also contains the power and muted states
                if FEEDBACK_POWER_OFF == data[-2]:
                    self.state_service.update_power(False, True)
                elif FEEDBACK_MUTE_OFF == data[-2]:
                    self.state_service.update_power(True, True)
                    self.state_service.update_muted(False)
                elif FEEDBACK_MUTE_ON == data[-2]:
                    self.state_service.update_power(True, True)
                    self.state_service.update_muted(True)
                source_switched = True
        return source_switched

    def check_sound_field(self, data):
        sound_field_switched = False
        for sound_field, sound_field_feedback in FEEDBACK_SOUND_FIELD_MAP.items():
            if sound_field_feedback == data:
                self.sony_av_indicator.update_sound_field(sound_field)
                sound_field_switched = True
        return sound_field_switched

    def check_pure_direct(self, data):
        if FEEDBACK_PURE_DIRECT_ON == data:
            self.state_service.update_pure_direct(True)
            return True
        elif FEEDBACK_PURE_DIRECT_OFF == data:
            self.state_service.update_pure_direct(False)
            return True
        return False

    def check_sound_optimizer(self, data):
        if FEEDBACK_SOUND_OPTIMIZER_PREFIX == data[:-1]:
            if FEEDBACK_SOUND_OPTIMIZER_OFF == data[-1]:
                self.state_service.update_sound_optimizer("off")
            elif FEEDBACK_SOUND_OPTIMIZER_NORMAL == data[-1]:
                self.state_service.update_sound_optimizer("normal")
            elif FEEDBACK_SOUND_OPTIMIZER_LOW == data[-1]:
                self.state_service.update_sound_optimizer("low")
            return True
        return False

    def check_timer(self, data):
        if FEEDBACK_TIMER_PREFIX == data[:-3]:
            if FEEDBACK_TIMER_SET == data[-1]:
                self.state_service.update_timer(data[-3], data[-2], data[-1], True, False)
                return True
            elif FEEDBACK_TIMER_UPDATE == data[-1]:
                self.state_service.update_timer(data[-3], data[-2], data[-1], True, True)
                return True
            elif FEEDBACK_TIMER_OFF == data[-1]:
                self.state_service.update_timer(data[-3], data[-2], data[-1], False, False)
                return True
            else:
                return True
        return False

    def check_fmtuner(self, data):
        if FEEDBACK_FMTUNER_PREFIX == data[0:5]:
            fmtuner = data[5]
            stereo = True
            if data[6] == FEEDBACK_FMTUNER_MONO:
                stereo = False
            freq = round(((data[7] * 255 + data[8]) / 99.5) - 0.1, 1)
            self.state_service.update_fmtuner(fmtuner, stereo, freq)
            self.state_service.update_source("fmTuner")
            return True
        return False

    def check_auto_standby(self, data):
        if FEEDBACK_AUTO_STANDBY_OFF == data:
            self.state_service.update_auto_standby(False)
            return True
        elif FEEDBACK_AUTO_STANDBY_ON == data:
            self.state_service.update_auto_standby(True)
            return True
        return False

    def check_auto_phase_matching(self, data):
        if FEEDBACK_AUTO_PHASE_MATCHING_OFF == data:
            self.state_service.update_auto_phase_matching(False)
            return True
        elif FEEDBACK_AUTO_PHASE_MATCHING_AUTO == data:
            self.state_service.update_auto_phase_matching(True)
            return True
        return False

    def probe_volume(self):
        time.sleep(0.1)
        self.command_service.send_command(CMD_VOLUME_DOWN)
        time.sleep(0.1)
        self.command_service.send_command(CMD_VOLUME_UP)

    def probe_input(self):
        time.sleep(0.1)
        self.command_service.send_command(CMD_MUTE)
        time.sleep(0.1)
        self.command_service.send_command(CMD_UNMUTE)

    def debug_data(self, data, prepend_text=""):
        self.data_logger.debug("%s%s" %(prepend_text, binascii.hexlify(data)))

    def connect(self):
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        #self.socket.connect((self.device_service.ip, TCP_PORT_1))
        #self.logger.info("Connected to %s:%d" % (self.device_service.ip, TCP_PORT_1))
        self.socket.connect((self.device_service.ip, self.port))
        self.socket.settimeout(60.0)
        self.logger.info("Connected to %s:%d" % (self.device_service.ip, self.port))
        
    def reconnect(self):
        self.socket.close()
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.connect((self.device_service.ip, TCP_PORT_1))
        self.socket.settimeout(60.0)
        self.command_service.block_sending = False
        self.logger.info("Reconnected")

    def run(self):
        self.connect()
        while not self.ended:
            try:
                time.sleep(0.1)
                data = self.socket.recv(BUFFER_SIZE)
                # Prevent feedback loops by block sending commands
                self.command_service.block_sending = True
                if not self.ended:
                    self.debug_data(data)
                if not self.check_timer(data) and \
                   not self.check_source(data) and \
                   not self.check_sound_field(data) and \
                   not self.check_pure_direct(data) and \
                   not self.check_sound_optimizer(data) and \
                   not self.check_fmtuner(data) and \
                   not self.check_volume(data) and \
                   not self.check_auto_standby(data) and \
                   not self.check_auto_phase_matching(data) and \
                   not self.ended:
                    self.debug_data(data, "[unknown data packet]\n")
            except socket.timeout as e:
                self.logger.debug("Timeout: reconnecting...")
                self.reconnect()
            except Exception as e:
                self.logger.exception("Failed to process data: reconnecting...")
                self.reconnect()
            finally:
                # Unblock sending commands after processing
                self.command_service.block_sending = False
        self.socket.close()
        self.logger.info("Connection closed")


class MprisServer(threading.Thread, dbus.service.Object):

    sony_av_indicator = None
    device_service = None
    state_service = None
    command_service = None
    properties = None
    bus = None
    ended = False

    def __init__(self, sony_av_indicator, device_service, state_service, command_service):
        threading.Thread.__init__(self)
        self.sony_av_indicator = sony_av_indicator
        self.device_service = device_service
        self.state_service = state_service
        self.command_service = command_service
        self.properties = {
            ROOT_INTERFACE: self._get_root_iface_properties(),
            PLAYER_INTERFACE: self._get_player_iface_properties()
        }
        self.main_loop = dbus.mainloop.glib.DBusGMainLoop(set_as_default = True)
        # self.main_loop = GObject.MainLoop()
        self.bus = dbus.SessionBus(mainloop = self.main_loop)
        self.bus_name = self._connect_to_dbus()
        dbus.service.Object.__init__(self, self.bus_name, OBJECT_PATH)

    def _get_root_iface_properties(self):
        return {
            'CanQuit': (True, None),
            'Fullscreen': (False, None),
            'CanSetFullscreen': (False, None),
            'CanRaise': (False, None),
            # NOTE Change if adding optional track list support
            'HasTrackList': (False, None),
            'Identity': (IDENTITY, None),
            'DesktopEntry': (DESKTOP, None),
            'SupportedUriSchemes': (dbus.Array([], 's', 1), None),
            # NOTE Return MIME types supported by local backend if support for
            # reporting supported MIME types is added
            'SupportedMimeTypes': (dbus.Array([], 's', 1), None),
        }

    def _get_player_iface_properties(self):
        return {
            'PlaybackStatus': (self.get_playback_status, None),
            'LoopStatus': (self.get_loop_status, None),
            'Rate': (1.0, None),
            'Shuffle': (None, None),
            'Metadata': (self.get_metadata, None),
            'Volume': (self.get_volume, self.set_volume),
            'Position': (None, None),
            'MinimumRate': (1.0, None),
            'MaximumRate': (1.0, None),
            'CanGoNext': (self.can_go_next, None),
            'CanGoPrevious': (self.can_go_previous, None),
            'CanPlay': (self.can_play, None),
            'CanPause': (self.can_pause, None),
            'CanSeek': (self.can_seek, None),
            'CanControl': (self.can_control, None),
        }

    def _connect_to_dbus(self):
        # bus_type = self.config['mpris']['bus_type']
        self.bus = dbus.SessionBus()
        bus_name = dbus.service.BusName(BUS_NAME, self.bus)
        return bus_name

    def get_playback_status(self):
        return 'Playing'

    def get_loop_status(self):
        return 'None'

    def can_go_next(self):
        return True

    def can_go_previous(self):
        return True

    def can_play(self):
        return True

    def can_pause(self):
        return True

    def can_seek(self):
        return True

    def can_control(self):
        return True

    def get_metadata(self):
        metadata = {
            'mpris:trackid': self.state_service.source,
            'mpris:length': 60000
        }
        return dbus.Dictionary(metadata, signature = 'sv')

    def get_volume(self):
        volume = self.state_service.volume
        if volume is None:
            return 0
        return volume / 100.0

    def set_volume(self, value):
        volume = int(value * 100)
        if volume < 0:
            volume = 0
        elif volume > MAX_VOLUME:
            volume = MAX_VOLUME
        self.command_service.set_volume(None, volume)

    @dbus.service.method(PLAYER_INTERFACE)
    def Pause(self):
        pass

    @dbus.service.method(PLAYER_INTERFACE)
    def PlayPause(self):
        pass

    @dbus.service.method(PLAYER_INTERFACE)
    def Play(self):
        pass

    @dbus.service.method(PLAYER_INTERFACE)
    def Stop(self):
        pass

    @dbus.service.method(PLAYER_INTERFACE)
    def Next(self):
        self.command_service.source_up()

    @dbus.service.method(PLAYER_INTERFACE)
    def Previous(self):
        self.command_service.source_down()

    # --- Properties interface

    @dbus.service.method(dbus_interface=PROPERTIES_INTERFACE, in_signature='ss', out_signature='v')
    def Get(self, interface, prop):
        print('%s.Get(%s, %s) called' %(dbus.PROPERTIES_IFACE, repr(interface), repr(prop)))
        (getter, _) = self.properties[interface][prop]
        if callable(getter):
            return getter()
        else:
            return getter

    @dbus.service.method(dbus_interface=PROPERTIES_INTERFACE, in_signature='s', out_signature='a{sv}')
    def GetAll(self, interface):
        print('%s.GetAll(%s) called' %(PROPERTIES_INTERFACE, repr(interface)))
        getters = {}
        for key, (getter, _) in self.properties[interface].items():
            getters[key] = getter() if callable(getter) else getter
        return getters

    @dbus.service.method(dbus_interface=PROPERTIES_INTERFACE, in_signature='ssv', out_signature='')
    def Set(self, interface, prop, value):
        print( '%s.Set(%s, %s, %s) called' %(PROPERTIES_INTERFACE, repr(interface), repr(prop), repr(value)))
        _, setter = self.properties[interface][prop]
        if setter is not None:
            setter(value)
            self.PropertiesChanged(interface, {prop: self.Get(interface, prop)}, [])

    @dbus.service.signal(dbus_interface=PROPERTIES_INTERFACE, signature='sa{sv}as')
    def PropertiesChanged(self, interface, changed_properties, invalidated_properties):
        print('%s.PropertiesChanged(%s, %s, %s) signaled' %(PROPERTIES_INTERFACE, interface, changed_properties, invalidated_properties))

    # --- Root interface methods

    @dbus.service.method(dbus_interface=ROOT_INTERFACE)
    def Raise(self):
        print('%s.Raise called' %(ROOT_INTERFACE))
        # Do nothing, as we do not have a GUI

    @dbus.service.method(dbus_interface=ROOT_INTERFACE)
    def Quit(self):
        print('%s.Quit called' %(ROOT_INTERFACE))
        self.sony_av_indicator.quit(None)

    def kill(self):
        self.ended = True

    def run(self):
        while not self.ended:
            try:
                time.sleep(0.1)
            except Exception as e:
                pass


class SonyAvIndicator():

    indicator = None
    device_service = None
    mpris_server = None
    feedback_watcher_1 = None
    feedback_watcher_2 = None
    command_service = None
    notification = notify.Notification.new("")
    notifications_initialized = False
    initialized = False

    source_menu_items = {}
    sound_field_menu_items = {}

    source_group = []
    sound_field_group = []

    show_source_name = True

    def __init__(self):
        
        self.device_service = DeviceService()
        self.state_service = StateService(self)
        self.command_service = CommandService(self.device_service, self.state_service)
        self.mpris_server = MprisServer(self, self.device_service, self.state_service, self.command_service)
        self.feedback_watcher_1 = FeedbackWatcher(self, self.device_service, self.state_service, self.command_service, TCP_PORT_1)
        self.feedback_watcher_2 = FeedbackWatcher(self, self.device_service, self.state_service, self.command_service, TCP_PORT_2)

        self.indicator = appindicator.Indicator.new(APPINDICATOR_ID, self.get_volume_icon_path(self.get_volume_icon(LOW_VOLUME)), appindicator.IndicatorCategory.SYSTEM_SERVICES)
        self.indicator.set_status(appindicator.IndicatorStatus.ACTIVE)
        self.indicator.set_menu(self.build_menu())
        self.indicator.connect("scroll-event", self.scroll)

        notify.init(APPINDICATOR_ID)
        self.notification = notify.Notification.new("")
        self.notifications_initialized = True

        signal.signal(signal.SIGINT, signal.SIG_DFL)

        self.initialize_device()

        if self.mpris_server != None:
            self.mpris_server.start()
        if self.feedback_watcher_1 != None:
            self.feedback_watcher_1.start()
        if self.feedback_watcher_2 != None:
            self.feedback_watcher_2.start()
        
        self.set_initialized(True)
        
        self.feedback_watcher_1.probe_volume()
        self.feedback_watcher_1.probe_input()

    def quit(self, source):
        self.update_label("Disconnecting...")
        self.set_initialized(False)
        if self.feedback_watcher_1 != None:
            self.feedback_watcher_1.kill()
            self.feedback_watcher_1.join(8)
        if self.feedback_watcher_2 != None:
            self.feedback_watcher_2.kill()
            self.feedback_watcher_2.join(8)
        if self.mpris_server != None:
            self.mpris_server.kill()
            self.mpris_server.join(8)
        gtk.main_quit()

    def initialize_device(self):
        self.update_label("Searching")
        self.device_service.find_device()
        self.update_label("Connected")
        self.device_service.initialized = True

    def poll_state(self):
        self.command_service.mute(None)
        self.command_service.unmute(None)

    def set_initialized(self, initialized):
        self.initialized = initialized
        self.device_service.initialized = initialized
        self.state_service.initialized = initialized
        self.command_service.initialized = initialized

    def get_volume_icon(self, vol):
        if self.state_service.muted:
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
    
    def get_volume_icon_path(self, icon_name):
        return os.path.abspath("%s/%s.svg" %(ICON_PATH, icon_name))
    
    def set_volume_icon(self, vol):
        self.indicator.set_icon(self.get_volume_icon_path(self.get_volume_icon(vol)))

    def show_notification(self, title, text, icon):
        if self.notifications_initialized:
            self.notification.update(title, text, icon)
            self.notification.show()

    def update_label(self, text = None):
        if text != None:
            self.indicator.set_label(text, "")
        elif self.show_source_name:
            if not self.state_service.power:
                label = "Power Off"
            elif self.state_service.source == "fmTuner" and self.state_service.fmtuner != None:
                if self.state_service.fmtuner != 255:
                    label = "%s %s (%s)" %(SOURCE_MENU_MAP[self.state_service.source], self.state_service.fmtuner, self.state_service.fmtunerfreq)
                else:
                    label = "%s (%s)" %(SOURCE_MENU_MAP[self.state_service.source], self.state_service.fmtunerfreq)
            elif self.state_service.source != None:
                label = SOURCE_MENU_MAP[self.state_service.source]
            else:
                label = ""
            self.indicator.set_label(label, "")

    def update_source(self, source, propagate = True):
        self.source_menu_items[source].set_active(True)

    def update_sound_field(self, sound_field):
        self.sound_field_menu_items[sound_field].set_active(True)

    def scroll(self, indicator, steps, direction):
        if self.initialized:
            if direction == gdk.ScrollDirection.DOWN:
                self.command_service.volume_down()
            elif direction == gdk.ScrollDirection.UP:
                self.command_service.volume_up()
            elif direction == gdk.ScrollDirection.LEFT:
                if self.state_service.source == "fmTuner":
                    self.command_service.fmtuner_preset_down(None)
                else:
                    self.command_service.source_up()
            elif direction == gdk.ScrollDirection.RIGHT:
                if self.state_service.source == "fmTuner":
                    self.command_service.fmtuner_preset_up(None)
                else:
                    self.command_service.source_down()

    def open_web_ui(self, widget):
        webbrowser.open("http://%s/" %(self.device_service.ip), 2)

    def create_menu_item(self, menu, name, cmd):
        item = gtk.MenuItem(name)
        item.connect("activate", self.command_service.send_command_w, cmd)
        menu.append(item)

    def build_menu(self):
        menu = gtk.Menu()
    
        sources_menu = gtk.Menu()
        item_sources = gtk.MenuItem("Sources")
        item_sources.set_submenu(sources_menu)
        for source in SOURCE_NAMES:
            item_select_source = gtk.RadioMenuItem.new_with_label(self.source_group, SOURCE_MENU_MAP[source])
            self.source_group = item_select_source.get_group()
            item_select_source.connect("activate", self.command_service.select_source_w, source)
            sources_menu.append(item_select_source)
            self.source_menu_items[source] = item_select_source
        menu.append(item_sources)
    
        sound_field_menu = gtk.Menu()
        item_sound_field = gtk.MenuItem("Sound Field")
        item_sound_field.set_submenu(sound_field_menu)
        first = True
        for sound_field_group in SOUND_FIELD_NAMES:
            if first:
               first = False
            else:
                sound_field_group_item = gtk.SeparatorMenuItem()
                sound_field_menu.append(sound_field_group_item)
            for sound_field in sound_field_group:
                item_select_sound_field = gtk.RadioMenuItem.new_with_label(self.sound_field_group, SOUND_FIELD_MENU_MAP[sound_field])
                self.sound_field_group = item_select_sound_field.get_group()
                item_select_sound_field.connect("activate", self.command_service.select_sound_field_w, sound_field)
                sound_field_menu.append(item_select_sound_field)
                self.sound_field_menu_items[sound_field] = item_select_sound_field
        menu.append(item_sound_field)
    
        volume_menu = gtk.Menu()
        item_volume = gtk.MenuItem("Volume")
        item_volume.set_submenu(volume_menu)
        item_mute = gtk.MenuItem("Mute")
        item_mute.connect("activate", self.command_service.mute)
        volume_menu.append(item_mute)
        item_unmute = gtk.MenuItem("Unmute")
        item_unmute.connect("activate", self.command_service.unmute)
        volume_menu.append(item_unmute)
        item_toggle_mute = gtk.MenuItem("Toggle Mute")
        item_toggle_mute.connect("activate", self.command_service.toggle_mute)
        volume_menu.append(item_toggle_mute)
        self.indicator.set_secondary_activate_target(item_toggle_mute)
        menu.append(item_volume)

        fmtuner_menu = gtk.Menu()
        item_fmtuner = gtk.MenuItem("FM Tuner")
        item_fmtuner.set_submenu(fmtuner_menu)
        item_fmtuner_up = gtk.MenuItem("Preset Up")
        item_fmtuner_up.connect("activate", self.command_service.fmtuner_preset_up)
        fmtuner_menu.append(item_fmtuner_up)
        item_fmtuner_down = gtk.MenuItem("Preset Down")
        item_fmtuner_down.connect("activate", self.command_service.fmtuner_preset_down)
        fmtuner_menu.append(item_fmtuner_down)
        menu.append(item_fmtuner)

        menu.append(gtk.SeparatorMenuItem())

        item_power = gtk.MenuItem("Toggle Power")
        item_power.connect("activate", self.command_service.toggle_power)
        menu.append(item_power)

        item_hdmiout = gtk.MenuItem("Toggle HDMI Out")
        item_hdmiout.connect("activate", self.command_service.toggle_hdmiout)
        menu.append(item_hdmiout)

        menu.append(gtk.SeparatorMenuItem())

        item_web_ui = gtk.MenuItem("Open Web Configuration")
        item_web_ui.connect("activate", self.open_web_ui)
        menu.append(item_web_ui)

        menu.append(gtk.SeparatorMenuItem())

        item_quit = gtk.MenuItem("Quit")
        item_quit.connect("activate", self.quit)
        menu.append(item_quit)

        menu.append(gtk.SeparatorMenuItem())

        menu.show_all()
        return menu

    def main(self):
        gtk.main()


#if __name__ == "__main__":
#    sony_av_indicator = SonyAvIndicator()
#    sony_av_indicator.main()


