import argparse
from bpm_analyzer import BPMAnalyzer
from bpm_notifier import BPMChangeNotifier
from sys import exit
import os
#from time import sleep
import time

uname = os.uname()
port = 8080
homewlan = False
uvchakras= True

if homewlan:
    s7pi    = '192.168.2.218'
    flowpad7= '192.168.2.194'
    flowpad = '192.168.2.80'
if uvchakras:
    s7pi    = '192.168.43.3'
    flowpad = '192.168.43.5'
    esp32   = '192.168.43.10'


if uname.nodename == 's7pi':
    target_ip = flowpad


notify_url = 'http://'+target_ip+':'+str(port)+'/'


if __name__ == "__main__":
    parser = argparse.ArgumentParser(prog='bpm monitor', description='analyze bpm on audio input stream')
    parser.add_argument('-d', '--device', help="audio device index")
    parser.add_argument('-l', '--list-devices', action='store_true', help="list all audio devices")
    parser.add_argument('-n', '--notify', action='store_true', help="HTTP-URL für BPM-Änderungsbenachrichtigung")
    parser.add_argument('-t', '--tui', action='store_true', help="starte Console-TUI")
    args = parser.parse_args()

    print(args)


    if args.list_devices:
        import pyaudio
        from pprint import pprint
        pa = pyaudio.PyAudio()
        count = pa.get_device_count()
        print("num devices: ", count)
        for i in range(count):
            info = pa.get_device_info_by_index(i)
            if info.get('maxInputChannels', 0) > 0:
                print("INDEX=",i)
                print(pprint(info))
        exit()

    #exit()
    di = 3
    if args.device:
        di = int(args.device)
    analyzer = BPMAnalyzer(device_index=di)

    notifier = None
    if args.notify:
        notifier = BPMChangeNotifier(url=notify_url)
        analyzer.start(on_bpm_callback=notifier.notify)
    else:
        analyzer.start()

    if args.tui:
        from bpm_console_tui import BPMConsoleGUI
        gui = BPMConsoleGUI(analyzer)
        gui.run()
    else:
        try:
            while analyzer.running is True:
                #print('X', end='')
                time.sleep(0.01)
                #pass
        except KeyboardInterrupt:
            analyzer.stop()
