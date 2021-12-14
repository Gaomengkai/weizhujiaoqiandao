# -*-coding:utf-8 -*-
import logging
import random
import time
import json
import asyncio
import re
from typing import Union

import httpx

FILENAME_USEROPENID = "users.json"

TIME_INTERVAL = 30
RANDOM_BASE = 15
DELAY_TO_CHECKIN = 6

LOOPS_COUNTS = 2000
IGNORE_INVALID_OPENID = 1

URL_CHECKIN = 'https://v18.teachermate.cn/wechat-api/v1/class-attendance/student-sign-in'
URL_COURSES = 'https://v18.teachermate.cn/wechat-api/v1/students/courses'
URL_ACTIVESIGNS = 'https://v18.teachermate.cn/wechat-api/v1/class-attendance/student/active_signs'
URL_REFERER_T = 'https://v18.teachermate.cn/wechat-pro-ssr/student/sign?openid={}'
URL_GETNAME_T = 'https://v18.teachermate.cn/wechat-pro-ssr/?openid={}&from=wzj'
URL_CHECKINREFER_T = 'https://v18.teachermate.cn/wechat-pro-ssr/student/sign/list/{}'


class Location:
    def __init__(self, lat, lon):
        self.lat = lat
        self.lon = lon

    def getLat(self):
        return "{:.6f}".format(self.lat + random.randint(-4, 4)*0.000001)

    def getLon(self):
        return "{:.6f}".format(self.lon + random.randint(-4, 4)*0.000001)


x12 = Location(30.511189, 114.401665)
UA = [
    r"Mozilla/5.0 (iPhone; CPU iPhone OS 12_4 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148 MicroMessenger/7.0.5(0x17000523) NetType/WIFI Language/zh_CN",
    r"Mozilla/5.0 (iPad; U; CPU OS 13_3_1 like Mac OS X; zh-cn) AppleWebKit/533.17.9 (KHTML, like Gecko) Version/5.0.2 Mobile/8C148 Safari/6533.18.5",
    r"Mozilla/5.0 (iPad; U; CPU OS 15_0_1 like Mac OS X; en-us) AppleWebKit/533.17.9 (KHTML, like Gecko) Version/5.0.2 Mobile/8J2 Safari/6533.18.5",
    r"MQQBrowser/26 Mozilla/5.0 (linux; U; Android 2.3.7; zh-cn; MB200 Build/GRJ22; CyanogenMod-7) AppleWebKit/533.1 (KHTML, like Gecko) Version/4.0 Mobile Safari/533.1",
    r"Mozilla/5.0 (Linux; Android 7.1.1; OPPO R9sk Build/NMF26F; wv) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/70.0.3538.80 Mobile Safari/537.36 LieBaoFast/5.12.3"
]

headers = {
    'User-Agent': r'Mozilla/5.0 (Linux; Android 11; Mi 10 Build/RKQ1.200826.002; wv) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/86.0.4240.99 XWEB/3165 MMWEBSDK/20210902 Mobile Safari/537.36 MMWEBID/3949 MicroMessenger/8.0.15.2020(0x28000F3D) Process/toolsmp WeChat/arm64 Weixin NetType/WIFI Language/zh_CN ABI/arm64',
    'Accept': r'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9',
    'Accept-Language': 'zh-CN,zh;q=0.9,en-US;q=0.8,en;q=0.7',
    # 'Connection': 'keep-alive',
    'Host': 'v18.teachermate.cn',
    # 'Origin': 'https://v18.teachermate.cn',
}


class ColorPrint:
    @staticmethod
    def green(s):
        return '\033[32m'+str(s)+'\033[0m'

    @staticmethod
    def yellow(s):
        return '\033[33m'+str(s)+'\033[0m'

    @staticmethod
    def red(s):
        return '\033[31m'+str(s)+'\033[0m'


# read user_data into a list
with open(FILENAME_USEROPENID) as f:
    userData = json.load(f)
    for u in userData:
        if 'teachermate' in u['openid']:
            re_ptn = "openid=([^&]*)"
            u['openid'] = re.search(
                re_ptn, u['openid']).group().replace("openid=", "")


def resave_json_file(j):
    with open(FILENAME_USEROPENID, 'w') as f:
        json.dump(j, f, indent=4, ensure_ascii=False)


def get_header_checkin(openid, courseId):
    h = headers
    h['openid'] = openid
    h['Referer'] = URL_CHECKINREFER_T.format(courseId)
    return h


def get_header_common(openid=None, host='v18.teachermate.cn'):
    h = headers
    h['Referer'] = URL_REFERER_T.format(openid)
    if openid:
        h['openid'] = openid
    return h


def check_openid(s, user):
    openid = user['openid']
    r = s.get(URL_ACTIVESIGNS, headers=get_header_common(openid))
    return r.status_code == 200


def renew_openid(s, user):
    openid = user['openid']
    r = s.get(URL_ACTIVESIGNS, headers=get_header_common(openid))
    is_open_id_ok = r.status_code == 200
    while not is_open_id_ok:
        print(ColorPrint.red(f"[{user['name']}] 登录信息失效"))
        openid = input("在这里重新输入您的openid:").strip()
        # Check whether openid is a url or a true id
        if 'teachermate' in openid:
            re_ptn = "openid=([^&]*)"
            openid = re.search(re_ptn, openid).group().replace("openid=", "")

        # Update openid info so that it can be stored in json file
        print(ColorPrint.yellow(f"[{user['name']}] openid已经更新：{openid}"))
        for index in range(len(userData)):
            if userData[index]['name'] == user['name']:
                userData[index]['openid'] = openid
                break
        resave_json_file(userData)
        try:
            r = s.get(URL_ACTIVESIGNS, headers=get_header_common(openid))
        except Exception as e:
            print(ColorPrint.red("网络连接失败。重试。"))
            print(ColorPrint.red(e))
            continue
        is_open_id_ok = r.status_code == 200
    return user


async def check_in(s: httpx.Client, openid: str, courseId, signId, lat=None, lon=None):
    d = {
        'courseId': courseId,
        'signId': signId
    }
    if lat and lon:
        d['lat'] = lat
        d['lon'] = lon
    r = s.post(URL_CHECKIN, data=d,
               headers=get_header_checkin(openid, courseId))
    return r


async def check_check_in_loop(user):
    s = httpx.Client()
    while not check_openid(s, user):
        if IGNORE_INVALID_OPENID:
            print(ColorPrint.red(f"[{user['name']}] 不再询问。"))
            return
            # break
        user = renew_openid(s, user)
        print(ColorPrint.green(f"[{user['name']}] 登录信息已经更新"))
    openid = user['openid']
    r = s.get(URL_GETNAME_T.format(openid), headers=get_header_common(openid))
    re_name = r'name":"([^"]+)'
    new_name = re.search(re_name, r.text)
    if not new_name:
        return
    new_name = new_name.group().replace('name":"', '')
    print(ColorPrint.green(new_name))
    for index in range(len(userData)):
        if userData[index]['name'] == user['name']:
            userData[index]['name'] = new_name
            break
    resave_json_file(userData)
    user['name'] = new_name

    for i in range(LOOPS_COUNTS):
        print(f"[{user['name']}] 第{i}次检测")
        try:
            r = s.get(URL_ACTIVESIGNS, headers=get_header_common(openid))
        except httpx.NetworkError as e:
            print(ColorPrint.red(e))
            await asyncio.sleep(3)
            continue
        is_open_id_ok = r.status_code == 200
        while not is_open_id_ok:
            user = renew_openid(s, user)
            is_open_id_ok = True
            break
        js = r.json()
        # =====================DEBUG====================
        print(js)
        # ===================END DEBUG==================
        print(
            f"[{user['name']}] 有{ColorPrint.yellow(len(js)) if len(js) > 0 else 0}个签到！")
        for j in js:
            print(f"[{user['name']}] 课堂：{j['name']} 延时{DELAY_TO_CHECKIN}s")
            await asyncio.sleep(DELAY_TO_CHECKIN)
            if j['isGPS']:
                r = await check_in(s, openid, j['courseId'], j['signId'], lat=x12.getLat(), lon=x12.getLon())
            else:
                r = await check_in(s, openid, j['courseId'], j['signId'])
            if 'Rank' in r.text:
                print(ColorPrint.green(
                    f"-------------[{user['name']}] {j['name']}-签到成功！"))
                print(
                    f"[{user['name']}] 排名：{ColorPrint.yellow(r.json()['studentRank'])}")
                print(ColorPrint.yellow("休息20分钟"))
                await asyncio.sleep(20*60)
            elif "repeat" in r.text:
                print(ColorPrint.yellow(
                    f"[{user['name']}] {j['name']}-早已经签到成功！"))
            print(r.text)
            await asyncio.sleep(random.randint(3, 5))
        interval = TIME_INTERVAL + random.random()*RANDOM_BASE
        print(f"[{user['name']}] 暂停{round(interval)}s")
        await asyncio.sleep(interval)


async def main():
    tasks = []
    for u in userData:
        print(ColorPrint.yellow(f"[{u['name']}] 已经加载 openid= {u['openid']}"))
        tasks.append(asyncio.create_task(check_check_in_loop(u)))
    for task in tasks:
        await task
        time.sleep(3)
if __name__ == '__main__':
    asyncio.run(main())
