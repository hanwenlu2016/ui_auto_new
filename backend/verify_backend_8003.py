import urllib.request
import urllib.parse
import json
import sys

BASE_URL = "http://localhost:8003/api/v1"

def request(method, url, data=None, headers=None):
    if headers is None:
        headers = {}
    
    if data:
        if headers.get("Content-Type") == "application/x-www-form-urlencoded":
            # data is already encoded bytes
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

def verify():
    print("Checking port 8003...")
    
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

    # Get Modules
    print("Getting Modules...")
    status, data = request("GET", f"{BASE_URL}/modules/", headers=headers)
    if status != 200:
        print(f"Get Modules failed: {status} {data}")
        return
    
    if not data:
        print("No modules found. Creating one...")
        status, projects = request("GET", f"{BASE_URL}/projects/", headers=headers)
        if not projects:
             status, project = request("POST", f"{BASE_URL}/projects/", data={"name": "Test Project", "description": "Test", "base_url": "http://localhost:5173"}, headers=headers)
             project_id = project["id"]
             if project.get("base_url") == "http://localhost:5173":
                 print("Project created with base_url successfully.")
             else:
                 print(f"Warning: base_url mismatch: {project.get('base_url')}")
        else:
             project_id = projects[0]["id"]
        
        status, module = request("POST", f"{BASE_URL}/modules/", data={"name": "Test Module", "description": "Test", "project_id": project_id}, headers=headers)
        module_id = module["id"]
    else:
        module_id = data[0]["id"]
    
    print(f"Using Module ID: {module_id}")

    # Create Page
    print("Creating Page...")
    status, data = request("POST", f"{BASE_URL}/pages/", data={"name": "Port 8003 Page", "description": "Test", "module_id": module_id}, headers=headers)
    if status != 200:
        print(f"Create Page failed: {status} {data}")
        return
    
    print(f"Page created: {data['id']}")
    print("Backend on port 8003 is working correctly.")

if __name__ == "__main__":
    verify()
