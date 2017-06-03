# sony-av-indicator

## Configuration

Adjust the port of your AVR:

* Port 8080 (STR-DA1800, STR-DN1030)
* Port 50001 (STR-DN1060)
* Port 33335 (All Others)

    TCP_PORT = 33335

## Installation

Add `sony-av-indicator.desktop` to the list of `interested-media-players`:

    gsettings get com.canonical.indicator.sound interested-media-players

## Usage

    ./sony-av-indicator.py

## System requirements

* Ubuntu 16.04
* Sony STR-DN-860

## Authors

* Andreas Schaeffer
* Michael Kapuscik

## License

GNU GENERAL PUBLIC LICENSE, Version 3
