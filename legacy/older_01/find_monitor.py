#!/usr/bin/env python

import pyaudio


def main():
    p = pyaudio.PyAudio()
    for i in range(p.get_device_count()):
        info = p.get_device_info_by_index(i)
        # print(i, p.get_device_info_by_index(i)["name"])
        # We only care about devices that can act as an Input
        if info["maxInputChannels"] > 0:
            print(f"{i:<5} | {info['name'][:40]:<40} | {info['maxInputChannels']}")


if __name__ == "__main__":
    main()
