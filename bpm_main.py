import argparse
from bpm_analyzer import BPMAnalyzer, BPMChangeNotifier
from sys import exit

notify_url = 'http://192.168.1.3:8080/notify_bpm_change/'

if __name__ == "__main__":
    parser = argparse.ArgumentParser(prog='bpm monitor', description='analyze bpm on audio input stream')
    parser.add_argument('-d', '--device', help="audio device index")
    parser.add_argument('-l', '--list-devices', action='store_true', help="list all audio devices")
    parser.add_argument('-n', '--notify', action='store_true', help="HTTP-URL für BPM-Änderungsbenachrichtigung")
    parser.add_argument('-t', '--tui', action='store_true', help="starte Console-TUI")
    args = parser.parse_args()

    print(args)

    import pyaudio
    if args.list_devices:
        pa = pyaudio.PyAudio()
        count = pa.get_device_count()
        print("num devices: ", count)
        for i in range(count):
            info = pa.get_device_info_by_index(i)
            if info.get('maxInputChannels', 0) > 0:
                print(info)
                print()
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
            while analyzer.running:
                pass
        except KeyboardInterrupt:
            analyzer.stop()
