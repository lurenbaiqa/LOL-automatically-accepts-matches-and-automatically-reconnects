import asyncio
import base64
import os
import re
import sys
import aiohttp
import urllib3


class LOL:
    def __init__(self):
        urllib3.disable_warnings()  # 禁用urllib3警告
        self.__headers = {
            "Accept": "application/json",  # 指定接受JSON格式的响应
            "Content-Type": "application/json",  # 指定发送JSON格式的请求
        }
        self.running = True

    async def update_credentials(self):
        # 更新认证信息（令牌和端口）
        result = os.popen('wmic PROCESS WHERE name="LeagueClientUx.exe" GET commandline')
        result = result.read().replace(' ', '').split(' ')
        token = re.findall(re.compile(r'"--remoting-auth-token=(.*?)"'), result[0])  # 使用正则表达式匹配令牌
        self.__port = re.findall(re.compile(r'"--app-port=(.*?)"'), result[0])  # 使用正则表达式匹配端口
        if token and self.__port:  # 如果成功获取到令牌和端口
            # 使用Base64编码生成令牌
            self.__token = base64.b64encode(("riot:" + token[0]).encode("UTF-8")).decode("UTF-8")
            self.__headers["Authorization"] = "Basic " + self.__token  # 设置HTTP请求头中的认证信息
            self.__url = 'https://127.0.0.1:' + str(self.__port[0])  # 构造请求的URL
            return True
        return False

    async def get(self, url):
        try:
            async with aiohttp.ClientSession(headers=self.__headers, trust_env=True) as session:
                async with session.get(self.__url + url, ssl=False) as response:
                    if response.status == 404:  # 如果响应状态为404，返回None
                        return None
                    response.raise_for_status()  # 检查请求是否成功
                    response_json = await response.json()  # 解析JSON格式的响应
                    return response_json
        except Exception as e:
            print(f"获取 {url} 时出错: {e}")
            return None

    async def post(self, url):
        try:
            async with aiohttp.ClientSession(headers=self.__headers, trust_env=True) as session:
                async with session.post(self.__url + url, ssl=False) as response:
                    response.raise_for_status()  # 检查请求是否成功
                    response_json = await response.json()  # 解析JSON格式的响应
                    return response_json
        except Exception as e:
            print(f"向 {url} 发送 POST 请求时出错: {e}")
            return None

    async def monitor(self):
        while self.running:
            if not await self.update_credentials():
                print("无法获取客户端信息，请确保《英雄联盟》客户端正在运行。")
                await asyncio.sleep(10)
                continue

            summoner_info = await self.get("/lol-summoner/v1/current-summoner")
            if summoner_info:
                print(f'召唤师名称: {summoner_info.get("displayName", "N/A")}')
                sys.stdout.flush()
            else:
                print("无法获取召唤师信息")

            try:
                phase = await self.get("/lol-gameflow/v1/gameflow-phase")
                print(f"阶段: {phase}")

                if phase == "ReadyCheck":
                    await self.accept_match()
                elif phase == "ChampSelect":
                    print("已经进入英雄选择阶段，无法接受准备检查。")
                elif phase == "Reconnect":
                    await self.reconnect()
                else:
                    print("当前不在准备检查阶段。")

                await asyncio.sleep(4)
            except Exception as e:
                print("出错:", e)

    async def accept_match(self):
        await self.post("/lol-matchmaking/v1/ready-check/accept")
        print("尝试接受对局")

    async def reconnect(self):
        await self.post("/lol-gameflow/v1/reconnect")
        print("已重新连接。")


if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    lol_project = LOL()
    loop.run_until_complete(lol_project.monitor())
