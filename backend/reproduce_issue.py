import urllib.request
import urllib.parse
import json
import sys

BASE_URL = "http://localhost:8000/api/v1"

def request(method, url, data=None, headers=None):
    if headers is None:
        headers = {}
    
    if data:
        if headers.get("Content-Type") == "application/x-www-form-urlencoded":
            pass
        else:
            data = json.dumps(data).encode("utf-8")
            headers["Content-Type"] = "application/json"
    
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req) as response:
            return response.status, json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8")
        try:
            return e.code, json.loads(body)
        except:
            print(f"Raw Error Body: {body}")
            return e.code, None
    except Exception as e:
        print(f"Error: {e}")
        return 0, None

def reproduce():
    print("Checking port 8000...")
    
    # Login
    print("Logging in...")
    login_data = urllib.parse.urlencode({"username": "admin@example.com", "password": "admin"}).encode("utf-8")
    headers = {"Content-Type": "application/x-www-form-urlencoded"}
    status, data = request("POST", f"{BASE_URL}/login/access-token", data=login_data, headers=headers)

    if status != 200:
        print(f"Login failed: {status} {data}")
        return
    
    token = data["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    print("Login successful.")

    # Get Projects
    print("Getting Projects...")
    status, data = request("GET", f"{BASE_URL}/projects/", headers=headers)
    if status != 200:
        print(f"Get Projects failed: {status} {data}")
    else:
        print("Get Projects successful.")
        print(json.dumps(data, indent=2))

    # Create Project
    print("Creating Project...")
    status, data = request("POST", f"{BASE_URL}/projects/", data={"name": "Repro Project", "description": "Test", "base_url": "http://repro.test"}, headers=headers)
    if status != 200:
        print(f"Create Project failed: {status} {data}")
    else:
        print("Create Project successful.")
        print(json.dumps(data, indent=2))

if __name__ == "__main__":
    reproduce()
