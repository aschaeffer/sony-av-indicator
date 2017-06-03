# sonyavindicator

Indicator for Sony AV receivers in the local network. The indicator automatically detects the AV indicator by scanning for port 33335 in the local network.

Currently this indicator works well for the STR-DN860. It might work on other devices as well, but since I don't own other devices feedback is welcome. This project is open for pull requests.

## Installation

    $ git clone https://github.com/aschaeffer/sony-av-indicator.git
    $ cd sony-av-indicator
    $ sudo -H pip3 install . --no-cache-dir --upgrade

### Optional

Add `sony-av-indicator.desktop` to the list of `interested-media-players`:

    $ gsettings set com.canonical.indicator.sound interested-media-players "['sonyavindicator.desktop']"

## Usage

    $ sonyavindicator

## System requirements

* Ubuntu 16.04
* Sony STR-DN-860 (other devices might work, but not tested)

## Authors

* Andreas Schaeffer
* Michael Kapuscik

## License

GNU GENERAL PUBLIC LICENSE, Version 3
