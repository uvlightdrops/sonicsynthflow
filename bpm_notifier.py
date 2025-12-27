import requests
import traceback

class BPMChangeNotifier:
    def __init__(self, url, http_method='GET', extra_data=None):
        self.url = url
        self.http_method = http_method
        self.extra_data = extra_data or {}
        self.last_sent_bpm = None

    def notify(self, bpm, prev_bpm):
        if self.last_sent_bpm is None or abs(self.last_sent_bpm - bpm) > 0.1:
            data = {'bpm': bpm, 'prev_bpm': prev_bpm}
            data.update(self.extra_data)
            print(self.http_method, self.url, ' send  bpm=', bpm)
            try:
                if self.http_method.upper() == 'POST':
                    response = requests.post(self.url, json=data, timeout=2)
                else:
                    response = requests.get(self.url, params=data, timeout=2)
                    if response:
                        print(self.http_method, ' send:   bpm=', bpm, response)
            except Exception as e:
                print('Exception in BPMChangeNotifier.notify:', e)
                traceback.print_exc()
                raise
            self.last_sent_bpm = bpm
