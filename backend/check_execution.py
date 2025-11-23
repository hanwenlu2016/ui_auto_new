import urllib.request
import urllib.parse
import json

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

def check_test_case():
    print("Checking test case...")
    
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

    # Get test case 1
    print("Getting test case 1...")
    status, case = request("GET", f"{BASE_URL}/cases/1", headers=headers)
    if status == 404:
        print("Test case 1 not found. Creating test data...")
        
        # Create project
        status, project = request("POST", f"{BASE_URL}/projects/", 
                                 data={"name": "Test Project", "base_url": "https://example.com"}, 
                                 headers=headers)
        if status != 200:
            print(f"Failed to create project: {status}")
            return
        
        # Create module
        status, module = request("POST", f"{BASE_URL}/modules/", 
                                data={"name": "Test Module", "project_id": project["id"]}, 
                                headers=headers)
        if status != 200:
            print(f"Failed to create module: {status}")
            return
        
        # Create page
        status, page = request("POST", f"{BASE_URL}/pages/", 
                              data={"name": "Test Page", "module_id": module["id"]}, 
                              headers=headers)
        if status != 200:
            print(f"Failed to create page: {status}")
            return
        
        # Create element
        status, element = request("POST", f"{BASE_URL}/elements/", 
                                 data={"name": "Test Element", "page_id": page["id"], 
                                      "locator_type": "xpath", "locator_value": "//body"}, 
                                 headers=headers)
        if status != 200:
            print(f"Failed to create element: {status}")
            return
        
        # Create test case with steps
        steps = [
            {"action": "goto", "value": "https://example.com"},
            {"action": "wait", "value": "1000"}
        ]
        status, case = request("POST", f"{BASE_URL}/cases/", 
                              data={"name": "Test Case", "module_id": module["id"], "steps": steps}, 
                              headers=headers)
        if status != 200:
            print(f"Failed to create test case: {status} {case}")
            return
        
        print(f"Created test case: {case['id']}")
    else:
        print(f"Test case found: {json.dumps(case, indent=2)}")
    
    # Try to run the test case
    print(f"\nRunning test case {case['id']}...")
    status, result = request("POST", f"{BASE_URL}/execution/cases/{case['id']}/run", headers=headers)
    if status == 200:
        print(f"Execution started: {json.dumps(result, indent=2)}")
        
        # Check task status
        task_id = result.get("task_id")
        if task_id:
            import time
            time.sleep(3)
            print(f"\nChecking task status...")
            status, task_status = request("GET", f"{BASE_URL}/execution/status/{task_id}", headers=headers)
            print(f"Task status: {json.dumps(task_status, indent=2)}")
    else:
        print(f"Execution failed: {status} {result}")

if __name__ == "__main__":
    check_test_case()
