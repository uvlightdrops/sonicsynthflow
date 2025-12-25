import requests

class BPMChangeNotifier:
    def __init__(self, url, http_method='POST', extra_data=None):
        self.url = url
        self.http_method = http_method
        self.extra_data = extra_data or {}
        self.last_sent_bpm = None

    def notify(self, bpm, prev_bpm):
        if self.last_sent_bpm is None or abs(self.last_sent_bpm - bpm) > 0.1:
            data = {'bpm': bpm, 'prev_bpm': prev_bpm}
            data.update(self.extra_data)
            print('send POST, bpm=', bpm)
            try:
                if self.http_method.upper() == 'POST':
                    requests.post(self.url, json=data, timeout=2)
                else:
                    requests.get(self.url, params=data, timeout=2)
            except Exception:
                pass
            self.last_sent_bpm = bpm

