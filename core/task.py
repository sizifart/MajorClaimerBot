import requests

from smart_airdrop_claimer import base
from core.headers import headers


def check_in(token, proxies=None):
    url = f"https://major.glados.app/api/user-visits/visit/"

    try:
        response = requests.post(
            url=url, headers=headers(token=token), proxies=proxies, timeout=20
        )
        data = response.json()
        status = data["is_increased"]
        return status
    except:
        return None


def get_task(token, type, proxies=None):
    url = f"https://major.glados.app/api/tasks/?is_daily={type}"

    try:
        response = requests.get(
            url=url, headers=headers(token=token), proxies=proxies, timeout=20
        )
        data = response.json()
        return data
    except:
        return None


def do_task(token, task_id, proxies=None):
    url = "https://major.glados.app/api/tasks/"
    payload = {"task_id": task_id}

    try:
        response = requests.post(
            url=url,
            headers=headers(token=token),
            json=payload,
            proxies=proxies,
            timeout=20,
        )
        data = response.json()
        status = data["is_completed"]
        return status
    except:
        return None


def process_check_in(token, proxies=None):
    check_in_status = check_in(token=token, proxies=proxies)
    if check_in_status:
        base.log(f"{base.white}Auto Check-in: {base.green}Success")
    else:
        base.log(f"{base.white}Auto Check-in: {base.red}Checked in already")


def process_do_task(token, proxies=None):
    types = ["true", "false"]

    for type in types:
        task_list = get_task(token=token, type=type, proxies=proxies)
        for task in task_list:
            task_id = task["id"]
            task_name = task["title"].replace("\n", "")
            do_task_status = do_task(token=token, task_id=task_id, proxies=proxies)
            if do_task_status:
                base.log(f"{base.white}{task_name}: {base.green}Completed")
            else:
                base.log(f"{base.white}{task_name}: {base.red}Incomplete")
