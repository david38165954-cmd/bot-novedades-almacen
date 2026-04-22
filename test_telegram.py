import urllib.request
import json

token = "8632469715:AAGLQG3mDgL0tBpV61jnG6n2Ds89YIEx0zY"
url = f"https://api.telegram.org/bot{token}/getUpdates"

try:
    with urllib.request.urlopen(url) as res:
        print(json.dumps(json.loads(res.read().decode("utf-8")), indent=2))
except Exception as e:
    print(f"Error: {e}")
