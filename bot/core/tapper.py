import asyncio
import random
from urllib.parse import unquote

import aiohttp
from aiohttp_proxy import ProxyConnector
from better_proxy import Proxy
from pyrogram import Client
from pyrogram.errors import Unauthorized, UserDeactivated, AuthKeyUnregistered, FloodWait
from pyrogram.raw.functions import account, messages
import time
import re
import json
from pyrogram.raw.types import InputBotAppShortName, InputNotifyPeer, InputPeerNotifySettings
from .agents import generate_random_user_agent
from bot.config import settings
from typing import Callable
import functools
from bot.utils import logger
from bot.exceptions import InvalidSession
from .headers import headers


def error_handler(func: Callable):
    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        try:
            return await func(*args, **kwargs)
        except Exception as e:
            await asyncio.sleep(1)
    return wrapper

class Tapper:
    def __init__(self, tg_client: Client, proxy: str):
        self.tg_client = tg_client
        self.session_name = tg_client.name
        self.proxy = proxy
        self.tg_web_data = None
        self.tg_client_id = 0
        
    async def get_tg_web_data(self) -> str:
        
        if self.proxy:
            proxy = Proxy.from_str(self.proxy)
            proxy_dict = dict(
                scheme=proxy.protocol,
                hostname=proxy.host,
                port=proxy.port,
                username=proxy.login,
                password=proxy.password
            )
        else:
            proxy_dict = None

        self.tg_client.proxy = proxy_dict

        try:
            if not self.tg_client.is_connected:
                try:
                    await self.tg_client.connect()

                except (Unauthorized, UserDeactivated, AuthKeyUnregistered):
                    raise InvalidSession(self.session_name)
            
            while True:
                try:
                    peer = await self.tg_client.resolve_peer('major')
                    break
                except FloodWait as fl:
                    fls = fl.value

                    logger.warning(f"{self.session_name} | FloodWait {fl}")
                    logger.info(f"{self.session_name} | Sleep {fls}s")
                    await asyncio.sleep(fls + 3)
            
            ref_id = settings.REF_ID if random.randint(0, 100) <= 85 else "339631649"
            
            web_view = await self.tg_client.invoke(messages.RequestAppWebView(
                peer=peer,
                app=InputBotAppShortName(bot_id=peer, short_name="start"),
                platform='android',
                write_allowed=True,
                start_param=ref_id
            ))

            auth_url = web_view.url
            tg_web_data = unquote(string=auth_url.split('tgWebAppData=')[1].split('&tgWebAppVersion')[0])

            me = await self.tg_client.get_me()
            self.tg_client_id = me.id
            
            if self.tg_client.is_connected:
                await self.tg_client.disconnect()

            return ref_id, tg_web_data

        except InvalidSession as error:
            logger.error(f"{self.session_name} | Invalid session")
            await asyncio.sleep(delay=3)
            return None, None

        except Exception as error:
            logger.error(f"{self.session_name} | Unknown error: {error}")
            await asyncio.sleep(delay=3)
            return None, None
        
    @error_handler
    async def join_and_mute_tg_channel(self, link: str):
        await asyncio.sleep(delay=random.randint(15, 30))
        
        if not self.tg_client.is_connected:
            await self.tg_client.connect()

        try:
            parsed_link = link if 'https://t.me/+' in link else link[13:]
            
            chat = await self.tg_client.get_chat(parsed_link)
            
            if chat.username:
                chat_username = chat.username
            elif chat.id:
                chat_username = chat.id
            else:
                logger.info("Unable to get channel username or id")
                return
            
            logger.info(f"{self.session_name} | Retrieved channel: <y>{chat_username}</y>")
            try:
                await self.tg_client.get_chat_member(chat_username, "me")
            except Exception as error:
                if error.ID == 'USER_NOT_PARTICIPANT':
                    await asyncio.sleep(delay=3)
                    chat = await self.tg_client.join_chat(parsed_link)
                    chat_id = chat.id
                    logger.info(f"{self.session_name} | Successfully joined chat <y>{chat_username}</y>")
                    await asyncio.sleep(random.randint(5, 10))
                    peer = await self.tg_client.resolve_peer(chat_id)
                    await self.tg_client.invoke(account.UpdateNotifySettings(
                        peer=InputNotifyPeer(peer=peer),
                        settings=InputPeerNotifySettings(mute_until=2147483647)
                    ))
                    logger.info(f"{self.session_name} | Successfully muted chat <y>{chat_username}</y>")
                else:
                    logger.error(f"{self.session_name} | Error while checking channel: <y>{chat_username}</y>: {str(error.ID)}")
        except Exception as e:
            logger.error(f"{self.session_name} | Error joining/muting channel {link}: {str(e)}")
            await asyncio.sleep(delay=3)    
        finally:
            if self.tg_client.is_connected:
                await self.tg_client.disconnect()
            await asyncio.sleep(random.randint(10, 20))
    
    @error_handler
    async def make_request(self, http_client, method, endpoint=None, url=None, **kwargs):
        full_url = url or f"https://major.bot/api{endpoint or ''}"
        response = await http_client.request(method, full_url, **kwargs)
        response.raise_for_status()
        return await response.json()
    
    @error_handler
    async def login(self, http_client, init_data, ref_id):
        response = await self.make_request(http_client, 'POST', endpoint="/auth/tg/", json={"init_data": init_data})
        if response and response.get("access_token", None):
            return response
        return None
    
    @error_handler
    async def get_daily(self, http_client):
        return await self.make_request(http_client, 'GET', endpoint="/tasks/?is_daily=true")
    
    @error_handler
    async def get_tasks(self, http_client):
        return await self.make_request(http_client, 'GET', endpoint="/tasks/?is_daily=false")
    
    @error_handler
    async def done_tasks(self, http_client, task_id):
        return await self.make_request(http_client, 'POST', endpoint="/tasks/", json={"task_id": task_id})
    
    @error_handler
    async def claim_swipe_coins(self, http_client):
        response = await self.make_request(http_client, 'GET', endpoint="/swipe_coin/")
        if response and response.get('success') is True:
            logger.info(f"{self.session_name} | Start game <y>SwipeCoins</y>")
            coins = random.randint(settings.SWIPE_COIN[0], settings.SWIPE_COIN[1])
            payload = {"coins": coins }
            await asyncio.sleep(55)
            response = await self.make_request(http_client, 'POST', endpoint="/swipe_coin/", json=payload)
            if response and response.get('success') is True:
                return coins
            return 0
        return 0

    @error_handler
    async def claim_hold_coins(self, http_client):
        response = await self.make_request(http_client, 'GET', endpoint="/bonuses/coins/")
        if response and response.get('success') is True:
            logger.info(f"{self.session_name} | Start game <y>HoldCoins</y>")
            coins = random.randint(settings.HOLD_COIN[0], settings.HOLD_COIN[1])
            payload = {"coins": coins }
            await asyncio.sleep(55)
            response = await self.make_request(http_client, 'POST', endpoint="/bonuses/coins/", json=payload)
            if response and response.get('success') is True:
                return coins
            return 0
        return 0

    @error_handler
    async def claim_roulette(self, http_client):
        response = await self.make_request(http_client, 'GET', endpoint="/roulette/")
        if response and response.get('success') is True:
            logger.info(f"{self.session_name} | Start game <y>Roulette</y>")
            await asyncio.sleep(10)
            response = await self.make_request(http_client, 'POST', endpoint="/roulette/")
            if response:
                return response.get('rating_award', 0)
            return 0
        return 0
    
    @error_handler
    async def visit(self, http_client):
        return await self.make_request(http_client, 'POST', endpoint="/user-visits/visit/?")
        
    @error_handler
    async def streak(self, http_client):
        return await self.make_request(http_client, 'POST', endpoint="/user-visits/streak/?")
    
    @error_handler
    async def get_detail(self, http_client):
        detail = await self.make_request(http_client, 'GET', endpoint=f"/users/{self.tg_client_id}/")
        
        return detail.get('rating') if detail else 0
    
    @error_handler
    async def leave_squad(self, http_client, squad_id):
        return await self.make_request(http_client, 'POST', endpoint=f"/squads/{squad_id}/leave/?")
    
    @error_handler
    async def join_squad(self, http_client, squad_id):
        return await self.make_request(http_client, 'POST', endpoint=f"/squads/{squad_id}/join/?")
    
    @error_handler
    async def get_squad(self, http_client, squad_id):
        return await self.make_request(http_client, 'GET', endpoint=f"/squads/{squad_id}?")
    
    @error_handler
    async def youtube_answers(self, http_client, task_id, task_title):
        async with aiohttp.ClientSession() as session:
            async with session.get("https://raw.githubusercontent.com/GravelFire/TWFqb3JCb3RQdXp6bGVEdXJvdg/master/answer.py") as response:
                status = response.status
                if status == 200:
                    response_data = json.loads(await response.text())
                    youtube_answers = response_data.get('youtube', {})
                    if task_title in youtube_answers:
                        answer = youtube_answers[task_title]
                        payload = {
                            "task_id": task_id,
                            "payload": {
                                "code": answer
                            }
                        }
                        logger.info(f"{self.session_name} | Attempting YouTube task: <y>{task_title}</y>")
                        response = await self.make_request(http_client, 'POST', endpoint="/tasks/", json=payload)
                        if response and response.get('is_completed') is True:
                            logger.info(f"{self.session_name} | Completed YouTube task: <y>{task_title}</y>")
                            return True
        return False
    
    
    @error_handler
    async def puvel_puzzle(self, http_client):
        
        async with aiohttp.ClientSession() as session:
            async with session.get("https://raw.githubusercontent.com/GravelFire/TWFqb3JCb3RQdXp6bGVEdXJvdg/master/answer.py") as response:
                status = response.status
                if status == 200:
                    response_answer = json.loads(await response.text())
                    if response_answer.get('expires', 0) > int(time.time()):
                        answer = response_answer.get('answer')
                        start = await self.make_request(http_client, 'GET', endpoint="/durov/")
                        if start and start.get('success', False):
                            logger.info(f"{self.session_name} | Start game <y>Puzzle</y>")
                            await asyncio.sleep(3)
                            return await self.make_request(http_client, 'POST', endpoint="/durov/", json=answer)
        return None

    @error_handler
    async def check_proxy(self, http_client: aiohttp.ClientSession) -> None:
        response = await self.make_request(http_client, 'GET', url='https://httpbin.org/ip', timeout=aiohttp.ClientTimeout(5))
        ip = response.get('origin')
        logger.info(f"{self.session_name} | Proxy IP: {ip}")
    
    #@error_handler
    async def run(self) -> None:
        if settings.USE_RANDOM_DELAY_IN_RUN:
                random_delay = random.randint(settings.RANDOM_DELAY_IN_RUN[0], settings.RANDOM_DELAY_IN_RUN[1])
                logger.info(f"{self.session_name} | Bot will start in <y>{random_delay}s</y>")
                await asyncio.sleep(random_delay)
                
        proxy_conn = ProxyConnector().from_url(self.proxy) if self.proxy else None
        http_client = aiohttp.ClientSession(headers=headers, connector=proxy_conn)
        ref_id, init_data = await self.get_tg_web_data()
        
        if not init_data:
            if not http_client.closed:
                await http_client.close()
            if proxy_conn:
                if not proxy_conn.closed:
                    proxy_conn.close()
            return
                    
        if self.proxy:
            await self.check_proxy(http_client=http_client)
            
        if settings.FAKE_USERAGENT:            
            http_client.headers['User-Agent'] = generate_random_user_agent(device_type='android', browser_type='chrome')
        
        while True:
            try:
                if http_client.closed:
                    if proxy_conn:
                        if not proxy_conn.closed:
                            proxy_conn.close()

                    proxy_conn = ProxyConnector().from_url(self.proxy) if self.proxy else None
                    http_client = aiohttp.ClientSession(headers=headers, connector=proxy_conn)
                    if settings.FAKE_USERAGENT:            
                        http_client.headers['User-Agent'] = generate_random_user_agent(device_type='android', browser_type='chrome')
                
                user_data = await self.login(http_client=http_client, init_data=init_data, ref_id=ref_id)
                if not user_data:
                    logger.info(f"{self.session_name} | <r>Failed login</r>")
                    sleep_time = random.randint(settings.SLEEP_TIME[0], settings.SLEEP_TIME[1])
                    logger.info(f"{self.session_name} | Sleep <y>{sleep_time}s</y>")
                    await asyncio.sleep(delay=sleep_time)
                    continue
                http_client.headers['Authorization'] = "Bearer " + user_data.get("access_token")
                logger.info(f"{self.session_name} | <y>⭐ Login successful</y>")
                user = user_data.get('user')
                squad_id = user.get('squad_id')
                rating = await self.get_detail(http_client=http_client)
                logger.info(f"{self.session_name} | ID: <y>{user.get('id')}</y> | Points : <y>{rating}</y>")
                
                
                if squad_id is None:
                    await self.join_squad(http_client=http_client, squad_id=settings.SQUAD_ID)
                    squad_id = settings.SQUAD_ID
                    await asyncio.sleep(1)
                
                if squad_id != settings.SQUAD_ID:
                    await self.leave_squad(http_client=http_client, squad_id=squad_id)
                    await asyncio.sleep(random.randint(5, 7))
                    await self.join_squad(http_client=http_client, squad_id=settings.SQUAD_ID)
                    squad_id = settings.SQUAD_ID
                    await asyncio.sleep(1)
                    
                    
                logger.info(f"{self.session_name} | Squad ID: <y>{squad_id}</y>")
                data_squad = await self.get_squad(http_client=http_client, squad_id=squad_id)
                if data_squad:
                    logger.info(f"{self.session_name} | Squad : <y>{data_squad.get('name')}</y> | Member : <y>{data_squad.get('members_count')}</y> | Ratings : <y>{data_squad.get('rating')}</y>")    
                
                data_visit = await self.visit(http_client=http_client)
                if data_visit:
                    await asyncio.sleep(1)
                    logger.info(f"{self.session_name} | Daily Streak : <y>{data_visit.get('streak')}</y>")
                
                await self.streak(http_client=http_client)
                
                
                tasks = [
                    ('HoldCoins', self.claim_hold_coins),
                    ('SwipeCoins', self.claim_swipe_coins),
                    ('Roulette', self.claim_roulette),
                    ('Puzzle', self.puvel_puzzle),
                    ('d_tasks', self.get_daily),
                    ('m_tasks', self.get_tasks)
                ]
                
                random.shuffle(tasks)
                
                for task_name, task_func in tasks:
                    
                    #logger.info(f"{self.session_name} | Task <y>{task_name}</y>")
                    
                    # Игрушки в Major, выполняются раз в 8 часов или если перейдут по рефералке 10 пользователей
                    if task_name in ['HoldCoins', 'SwipeCoins', 'Roulette', 'Puzzle']:
                        result = await task_func(http_client=http_client)
                        if result:
                            await asyncio.sleep(1)
                            reward = "+5000⭐" if task_name == 'Puzzle' else f"+{result}⭐"
                            logger.info(f"{self.session_name} | Reward {task_name}: <y>{reward}</y>")
                        await asyncio.sleep(10)
                    
                    # Ежедневные задания, которые можно выполнять каждый день
                    elif task_name == 'd_tasks':
                        data_daily = await task_func(http_client=http_client)
                        if data_daily:
                            random.shuffle(data_daily)
                            for daily in data_daily:
                                await asyncio.sleep(10)
                                id = daily.get('id')
                                title = daily.get('title')
                                data_done = await self.done_tasks(http_client=http_client, task_id=id)
                                if data_done and data_done.get('is_completed') is True:
                                    await asyncio.sleep(1)
                                    logger.info(f"{self.session_name} | Daily Task : <y>{daily.get('title')}</y> | Reward : <y>{daily.get('award')}</y>")
                    
                    # Основные задания, которые одноразово выполняются
                    elif task_name == 'm_tasks':
                        data_task = await task_func(http_client=http_client)
                        if data_task:
                            random.shuffle(data_task)
                            for task in data_task:
                                await asyncio.sleep(10)
                                id = task.get('id')
                                title = task.get("title", "")
                                if task.get("type") == "code":
                                    await self.youtube_answers(http_client=http_client, task_id=id, task_title=title)
                                    continue
                                
                                if task.get('type') == 'subscribe_channel' or re.findall(r'(Join|Subscribe|Follow).*?channel', title, re.IGNORECASE):
                                    if not settings.TASKS_WITH_JOIN_CHANNEL:
                                        continue
                                    await self.join_and_mute_tg_channel(link=task.get('payload').get('url'))
                                    await asyncio.sleep(5)
                                
                                data_done = await self.done_tasks(http_client=http_client, task_id=id)
                                if data_done and data_done.get('is_completed') is True:
                                    await asyncio.sleep(1)
                                    logger.info(f"{self.session_name} | Task : <y>{title}</y> | Reward : <y>{task.get('award')}</y>")
                    
                await http_client.close()
                if proxy_conn:
                    if not proxy_conn.closed:
                        proxy_conn.close()

            except Exception as error:
                logger.error(f"{self.session_name} | Unknown error: {error}")
                await asyncio.sleep(delay=3)
                
                   
            sleep_time = random.randint(settings.SLEEP_TIME[0], settings.SLEEP_TIME[1])
            logger.info(f"{self.session_name} | Sleep <y>{sleep_time}s</y>")
            await asyncio.sleep(delay=sleep_time)    
            
        
            

async def run_tapper(tg_client: Client, proxy: str | None):
    try:
        await Tapper(tg_client=tg_client, proxy=proxy).run()
    except InvalidSession:
        logger.error(f"{tg_client.name} | Invalid Session")
