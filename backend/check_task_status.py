import urllib.request
import json

task_id = "f37c350e-7837-458f-be28-c22d1f286022"
url = f"http://localhost:8000/api/v1/execution/status/{task_id}"

try:
    with urllib.request.urlopen(url) as response:
        data = json.loads(response.read().decode("utf-8"))
        print(json.dumps(data, indent=2, ensure_ascii=False))
except Exception as e:
    print(f"Error: {e}")
