#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from setuptools import setup

setup(name = "sonyavindicator",
      packages = ["sonyavindicator"],
      version = "0.9.0",
      description = "Ubuntu indicator for Sony AV Receiver",
      keywords = ["sony", "avr", "indicator", "ubuntu", "mpris"],
      classifiers = [
          "Programming Language :: Python",
          "Programming Language :: Python :: 3",
      ],
      url = "https://github.com/aschaeffer/sony-av-indicator",
      author = "Andreas Schaeffer",
      license = "GPLv3",
      data_files = [
          ("/usr/share/applications", ["dist/share/applications/sonyavindicator.desktop"]),
          ("/usr/share/pixmaps", ["dist/share/pixmaps/sonyavindicator.png"]),
      ],
      entry_points = {"console_scripts": ["sonyavindicator = sonyavindicator.__main__:main"]}
)
