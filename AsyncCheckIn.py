# -*-coding:utf-8 -*- 
import logging
import random
import time
import json
import asyncio
import re

import httpx

URL_CHECKIN = 'https://v18.teachermate.cn/wechat-api/v1/class-attendance/student-sign-in'
URL_COURSES = 'https://v18.teachermate.cn/wechat-api/v1/students/courses'
URL_ACTIVESIGNS = 'https://v18.teachermate.cn/wechat-api/v1/class-attendance/student/active_signs'
URL_REFERER_T = 'https://v18.teachermate.cn/wechat-pro-ssr/student/sign?openid={}'
URL_GETNAME_T = 'https://v18.teachermate.cn/wechat-pro-ssr/?openid={}&from=wzj'
URL_CHECKINREFER_T = 'https://v18.teachermate.cn/wechat-pro-ssr/student/sign/list/{}'

FILENAME_USEROPENID = "users.json"

TIME_INTERVAL = 60
RANDOM_BASE = 30
DELAY_TO_CHECKIN = 13
LOOPS_COUNTS = 2000
IGNORE_INVALID_OPENID = 1

UA = [
    r"Mozilla/5.0 (iPhone; CPU iPhone OS 12_4 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148 MicroMessenger/7.0.5(0x17000523) NetType/WIFI Language/zh_CN",
    r"Mozilla/5.0 (iPad; U; CPU OS 13_3_1 like Mac OS X; zh-cn) AppleWebKit/533.17.9 (KHTML, like Gecko) Version/5.0.2 Mobile/8C148 Safari/6533.18.5",
    r"Mozilla/5.0 (iPad; U; CPU OS 15_0_1 like Mac OS X; en-us) AppleWebKit/533.17.9 (KHTML, like Gecko) Version/5.0.2 Mobile/8J2 Safari/6533.18.5",
    r"MQQBrowser/26 Mozilla/5.0 (linux; U; Android 2.3.7; zh-cn; MB200 Build/GRJ22; CyanogenMod-7) AppleWebKit/533.1 (KHTML, like Gecko) Version/4.0 Mobile Safari/533.1",
    r"Mozilla/5.0 (Linux; Android 7.1.1; OPPO R9sk Build/NMF26F; wv) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/70.0.3538.80 Mobile Safari/537.36 LieBaoFast/5.12.3"
]

headers = {
    'User-Agent':r'Mozilla/5.0 (iPhone; CPU iPhone OS 12_4 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148 MicroMessenger/7.0.5(0x17000523) NetType/WIFI Language/zh_CN',
    'Accept':r'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9',
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

def resave_json_file(j):
    with open(FILENAME_USEROPENID,'w') as f:
        json.dump(j,f,indent=4,ensure_ascii=False)

def get_header(host='v18.teachermate.cn', openid='',isCheckin:bool=False,courseId = ''):
    x = headers
    # x['User-Agent'] = random.choice(UA)
    if openid:
        x['openid']=openid
        if isCheckin:
            x['Referer']=URL_CHECKINREFER_T.format(courseId)
        else:
            x['Referer']=URL_REFERER_T.format(openid)
    return x


def check_openid(s,user):
    openid = user['openid']
    r = s.get(URL_ACTIVESIGNS,headers=get_header(openid=openid))
    return r.status_code == 200

def renew_openid(s,user):
    openid = user['openid']
    r = s.get(URL_ACTIVESIGNS,headers=get_header(openid=openid))
    is_open_id_ok = r.status_code == 200
    while not is_open_id_ok:
        print(ColorPrint.red(f"[{user['name']}] 登录信息失效"))
        openid = input("在这里重新输入您的openid:").strip()
        # Check whether openid is a url or a true id
        if 'teachermate' in openid:
            re_ptn = "openid=([^&]*)"
            openid = re.search(re_ptn,openid).group().replace("openid=","")

        # Update openid info so that it can be stored in json file
        print(ColorPrint.yellow(f"[{user['name']}] openid已经更新：{openid}"))
        for index in range(len(userData)):
            if userData[index]['name'] == user['name']:
                userData[index]['openid'] = openid
                break
        resave_json_file(userData)
        r = s.get(URL_ACTIVESIGNS,headers=get_header(openid=openid))
        is_open_id_ok = r.status_code == 200
    return user


async def check_check_in_loop(user):
    s = httpx.Client()
    while not check_openid(s,user):
        if IGNORE_INVALID_OPENID:
            print(ColorPrint.red(f"[{user['name']}] 不再询问。"))
            return
            break
        user = renew_openid(s,user)
        print(ColorPrint.green(f"[{user['name']}] 登录信息已经更新"))
    openid = user['openid']
    r = s.get(URL_GETNAME_T.format(openid),headers=get_header(openid=openid))
    re_name = r'name":"([^"]+)'
    new_name = re.search(re_name,r.text)
    if not new_name:
        return
    new_name = new_name.group().replace('name":"','')
    print(ColorPrint.green(new_name))
    for index in range(len(userData)):
        if userData[index]['name'] == user['name']:
            userData[index]['name'] = new_name
            break
    resave_json_file(userData)
    user['name'] = new_name

    for i in range(LOOPS_COUNTS):
        print(f"[{user['name']}] 第{i}次检测")
        r = s.get(URL_ACTIVESIGNS,headers=get_header(openid=openid))
        is_open_id_ok = r.status_code == 200
        while not is_open_id_ok:
            user = renew_openid(s,user)
            is_open_id_ok = True
            break
        js = r.json()
        print(f"[{user['name']}] 有{ColorPrint.yellow(len(js)) if len(js) > 0 else 0}个签到！")
        for j in js:
            print(f"[{user['name']}] 课堂：{j['name']} 延时{DELAY_TO_CHECKIN}s")
            await asyncio.sleep(DELAY_TO_CHECKIN)
            courseId = j['courseId']
            signId = j['signId']
            d = {
                'courseId':courseId,
                'signId':signId
            }
            r = s.post(URL_CHECKIN,data=d,headers=get_header(openid=openid,courseId=courseId,isCheckin=True))
            if 'Rank' in r.text:
                print(ColorPrint.green(f"-------------[{user['name']}] {j['name']}-签到成功！"))
                print(f"[{user['name']}] 排名：{ColorPrint.yellow(r.json()['studentRank'])}")
            elif "repeat" in r.text:
                print(ColorPrint.yellow(f"[{user['name']}] {j['name']}-早已经签到成功！"))
            print(r.text)
            await asyncio.sleep(random.randint(3,5))
        interval = TIME_INTERVAL + random.random()*RANDOM_BASE
        print(f"[{user['name']}] 暂停{round(interval)}s")
        await asyncio.sleep(interval)

async def main():
    tasks = []
    for u in userData:
        print(ColorPrint.yellow(f"[{u['name']}] 已经加载 openid= {u['openid']}" ))
        tasks.append(asyncio.create_task(check_check_in_loop(u)))
    for task in tasks:
        await task
        time.sleep(3)
if __name__ == '__main__':
    asyncio.run(main())
