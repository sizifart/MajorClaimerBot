import requests

from smart_airdrop_claimer import base
from core.headers import headers


def streak(token, proxies=None):
    url = "https://major.glados.app/api/user-visits/streak/"

    try:
        response = requests.get(
            url=url, headers=headers(token=token), proxies=proxies, timeout=20
        )
        data = response.json()
        user_id = data["user_id"]
        streak = data["streak"]
        base.log(
            f"{base.green}Telegram ID: {base.white}{user_id} - {base.green}Streak: {base.white}{streak}"
        )
        return user_id
    except:
        return None


def balance(token, tele_id, proxies=None):
    url = f"https://major.glados.app/api/users/{tele_id}/"

    try:
        response = requests.get(
            url=url, headers=headers(token=token), proxies=proxies, timeout=20
        )
        data = response.json()
        rating = data["rating"]
        return rating
    except:
        return None


def get_balance(token, proxies=None):
    tele_id = streak(token=token, proxies=proxies)

    current_balance = balance(token=token, tele_id=tele_id, proxies=proxies)

    base.log(f"{base.green}Balance: {base.white}{current_balance:,}")
