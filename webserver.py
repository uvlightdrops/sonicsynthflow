from flask import Flask, request
import sys

app = Flask(__name__)

@app.route('/', methods=['POST'])
def index():
    # Versuche JSON-Daten zu lesen, sonst Fallback auf Formulardaten
    params = request.get_json(silent=True)
    if params is None:
        params = request.form.to_dict()
    print(f"Empfangene POST-Daten: {params}", file=sys.stdout, flush=True)
    return f"Empfangene POST-Daten: {params}\n"

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)

