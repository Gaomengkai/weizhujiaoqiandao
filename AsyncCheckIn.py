from asyncio.tasks import wait
import random
import time
import json
import asyncio

import httpx

URL_CHECKIN = 'https://v18.teachermate.cn/wechat-api/v1/class-attendance/student-sign-in'
URL_COURSES = 'https://v18.teachermate.cn/wechat-api/v1/students/courses'
URL_ACTIVESIGNS = 'https://v18.teachermate.cn/wechat-api/v1/class-attendance/student/active_signs'
URL_REFERER_T = 'https://v18.teachermate.cn/wechat-pro-ssr/student/sign?openid={}'

FILENAME_USEROPENID = "users.json"

TIME_INTERVAL = 46
RANDOM_BASE = 15

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

def get_header(host='v18.teachermate.cn', openid='',isCheckin:bool=False,courseId = ''):
    x = headers
    x['User-Agent'] = random.choice(UA)
    if openid:
        x['openid']=openid
        if isCheckin:
            x['Referer']='https://v18.teachermate.cn/wechat-pro-ssr/student/sign/list/{}'.format(courseId)
        else:
            x['Referer']=URL_REFERER_T.format(openid)
    return x

# read user_data into a list
with open(FILENAME_USEROPENID) as f:
    userData = json.load(f)

class ColorPrint:
    @staticmethod
    def green(s:str):
        return '\033[32m'+s+'\033[0m'
    @staticmethod
    def yellow(s:str):
        return '\033[33m'+s+'\033[0m'
    @staticmethod
    def red(s:str):
        return '\033[31m'+s+'\033[0m'

async def check_check_in_loop(user):
    s = httpx.Client()
    openid = user['openid']
    for i in range(200):
        print(f"[{user['name']}] 的 第{i}次检测")
        r = s.get(URL_ACTIVESIGNS,headers=get_header(openid=openid))
        is_open_id_ok = r.status_code == 200
        while not is_open_id_ok:
            print(ColorPrint.red(f"[{user['name']}]登录信息失效"))
            openid = input("在这里重新输入您的openid:").strip()
            # Update openid info so that it can be stored in json file
            for index in range(len(userData)):
                if userData[index]['name'] == user['name']:
                    userData[index]['openid'] = openid
            # re-save json file
            with open(FILENAME_USEROPENID,"w") as f:
                json.dump(userData,f)
            r = s.get(URL_ACTIVESIGNS,headers=get_header(openid=openid))
            is_open_id_ok = r.status_code == 200
        js = r.json()
        print(f"[{user['name']}] 有{len(js)}个签到！")
        for j in js:
            print(f"[{user['name']}] 课堂：{j['name']}")
            courseId = j['courseId']
            signId = j['signId']
            d = {
                'courseId':courseId,
                'signId':signId
            }
            r = s.post(URL_CHECKIN,data=d,headers=get_header(openid=openid,courseId=courseId,isCheckin=True))
            if 'Rank' in r.text:
                print(ColorPrint.green(f"-------------[{user['name']}] {j['name']}-签到成功！"))
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
        tasks.append(asyncio.create_task(check_check_in_loop(u)))
    for task in tasks:
        await task
        time.sleep(3)
if __name__ == '__main__':
    asyncio.run(main())