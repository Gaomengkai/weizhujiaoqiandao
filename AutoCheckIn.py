import requests

URL_CHECKIN = 'https://v18.teachermate.cn/wechat-api/v1/class-attendance/student-sign-in'
URL_COURSES = 'https://v18.teachermate.cn/wechat-api/v1/students/courses'
URL_ACTIVESIGNS = 'https://v18.teachermate.cn/wechat-api/v1/class-attendance/student/active_signs'
URL_REFERER = 'https://v18.teachermate.cn/wechat-pro-ssr/student/sign?openid={}'


headers = {
    'User-Agent':r'Mozilla/5.0 (iPhone; CPU iPhone OS 12_4 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148 MicroMessenger/7.0.5(0x17000523) NetType/WIFI Language/zh_CN',
    'Accept':r'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9',
    'Accept-Language': 'zh-CN,zh;q=0.9,en-US;q=0.8,en;q=0.7',
    # 'Connection': 'keep-alive',
    'Host': 'v18.teachermate.cn',
    # 'Origin': 'https://v18.teachermate.cn',
}


with open("user.txt") as f:
    userData = f.read().strip()

openid = userData

def getHeader(host='v18.teachermate.cn', openid='',isCheckin:bool=False,courseId = ''):
    x = headers
    if openid:
        x['openid']=openid
        if isCheckin:
            x['Referer']='https://v18.teachermate.cn/wechat-pro-ssr/student/sign/list/{}'.format(courseId)
        else:
            x['Referer']=URL_REFERER.format(openid)
    return x

s = requests.Session()
r = s.get(URL_ACTIVESIGNS,headers=getHeader(openid=openid))
isOpenIdOk = r.ok
while not isOpenIdOk:
    print("登录信息失效")
    openid = input("在这里重新输入您的openid:").strip()
    r = s.get(URL_ACTIVESIGNS,headers=getHeader(openid=openid))
    isOpenIdOk = r.ok
js = r.json()
print("现在你有{}个签到！".format(len(js)))
for j in js:
    print("课堂：{}".format(j['name']))
    courseId = j['courseId']
    signId = j['signId']
    d = {
        'courseId':courseId,
        'signId':signId
    }
    r = s.post(URL_CHECKIN,data=d,headers=getHeader(openid=openid,courseId=courseId,isCheckin=True))
    print(r.text)
