import requests
import random

from smart_airdrop_claimer import base
from core.headers import headers


def hold_coin(token, coins, proxies=None):
    url = "https://major.glados.app/api/bonuses/coins/"
    payload = {"coins": coins}

    try:
        response = requests.post(
            url=url,
            headers=headers(token=token),
            json=payload,
            proxies=proxies,
            timeout=20,
        )
        data = response.json()
        status = data["success"]
        return status
    except:
        return None


def spin(token, proxies=None):
    url = "https://major.glados.app/api/roulette"

    try:
        response = requests.post(
            url=url,
            headers=headers(token=token),
            proxies=proxies,
            timeout=20,
        )
        data = response.json()
        point = data["rating_award"]
        return point
    except:
        return None


def process_hold_coin(token, proxies=None):
    coins = random.randint(800, 900)
    hold_coin_status = hold_coin(token=token, coins=coins, proxies=proxies)
    if hold_coin_status:
        base.log(f"{base.white}Auto Play Hold Coin: {base.green}Success")
    else:
        base.log(
            f"{base.white}Auto Play Hold Coin: {base.red}Not time to play, invite more friends"
        )


def process_spin(token, proxies=None):
    point = spin(token=token, proxies=proxies)
    if point:
        base.log(f"{base.white}Auto Spin: {base.green}Success | Added {point:,} points")
    else:
        base.log(
            f"{base.white}Auto Spin: {base.red}Not time to spin, invite more friends"
        )
