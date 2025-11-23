import urllib.request
import urllib.parse
import json
import time

BASE_URL = "http://localhost:8003/api/v1"

def request(method, url, data=None, headers=None):
    if headers is None:
        headers = {}
    
    if data is not None:
        if headers.get("Content-Type") == "application/json":
            data = json.dumps(data).encode("utf-8")
        else:
            data = urllib.parse.urlencode(data).encode("utf-8")
    
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req) as response:
            resp_data = response.read().decode("utf-8")
            return response.status, json.loads(resp_data)
    except urllib.error.HTTPError as e:
        print(f"HTTP Error: {e.code} {e.reason}")
        print(e.read().decode("utf-8"))
        return e.code, None

def verify():
    # Login
    print("Logging in...")
    status, data = request("POST", f"{BASE_URL}/login/access-token", data={"username": "admin@example.com", "password": "admin"})
    if status != 200:
        print("Login failed")
        return
    token = data["access_token"]
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    print("Login successful.")

    # Create Project
    print("Creating Project...")
    status, data = request("POST", f"{BASE_URL}/projects/", data={"name": "Dist Project", "description": "Test"}, headers=headers)
    if status != 200:
        print("Create Project failed")
        return
    project_id = data["id"]
    print(f"Project created: {project_id}")

    # Create Module
    print("Creating Module...")
    status, data = request("POST", f"{BASE_URL}/modules/", data={"name": "Dist Module", "description": "Test", "project_id": project_id}, headers=headers)
    if status != 200:
        print("Create Module failed")
        return
    module_id = data["id"]
    print(f"Module created: {module_id}")

    # Create Page
    print("Creating Page...")
    status, data = request("POST", f"{BASE_URL}/pages/", data={"name": "Dist Page", "description": "Test", "module_id": module_id}, headers=headers)
    if status != 200:
        print("Create Page failed")
        return
    page_id = data["id"]
    print(f"Page created: {page_id}")

    # Create Element (Linked to Page)
    print("Creating Element...")
    status, data = request("POST", f"{BASE_URL}/elements/", data={
        "name": "Dist Element", 
        "description": "Test", 
        "page_id": page_id,
        "locator_type": "xpath",
        "locator_value": "//div"
    }, headers=headers)
    if status != 200:
        print("Create Element failed")
        return
    element_id = data["id"]
    print(f"Element created: {element_id}")

    # Create Case
    print("Creating Case...")
    status, data = request("POST", f"{BASE_URL}/cases/", data={
        "name": "Dist Case", 
        "description": "Test", 
        "module_id": module_id,
        "priority": "P0",
        "steps": [{"action": "click", "element_id": element_id, "value": ""}]
    }, headers=headers)
    if status != 200:
        print("Create Case failed")
        return
    case_id = data["id"]
    print(f"Case created: {case_id}")

    # Run Case
    print("Running Case...")
    status, data = request("POST", f"{BASE_URL}/execution/cases/{case_id}/run", headers=headers)
    if status != 200:
        print("Run Case failed")
        return
    task_id = data["task_id"]
    print(f"Task started: {task_id}")

    # Poll Status
    print("Polling Status...")
    for _ in range(20):
        status_code, data = request("GET", f"{BASE_URL}/execution/status/{task_id}", headers=headers)
        status = data["status"]
        print(f"Status: {status}")
        if status == "SUCCESS":
            print("Task Success!")
            print(data)
            return
        elif status == "FAILURE":
            print("Task Failed!")
            print(data)
            return
        time.sleep(1)
    
    print("Timeout waiting for task.")

if __name__ == "__main__":
    verify()
