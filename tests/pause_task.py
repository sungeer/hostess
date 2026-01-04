import httpx


def main():
    url = 'http://127.0.0.1:7788/task/run-task'
    payload = {"task_id": '1'}

    with httpx.Client(timeout=10.0) as client:
        resp = client.post(url, json=payload)
        resp.raise_for_status()
        try:
            data = resp.json()
        except ValueError:
            data = None

        print("status:", resp.status_code)
        print("response:", data)

if __name__ == "__main__":
    main()