from typing import Callable, Union
import websockets
import asyncio
import json
import re
import qrcode

url = "wss://www.teachermate.com.cn/faye"


def debug(s: str):
    print(s)
    pass


class Message:
    hello = {
        "channel": "/meta/handshake",
        "version": "1.0",
        "supportedConnectionTypes": [
            "websocket",
            "eventsource",
            "long-polling",
            "cross-origin-long-polling",
            "callback-polling"
        ],
        "id": 0
    }
    connect = {
        "channel": "/meta/connect",
        "clientId": "",
        "connectionType": "websocket",
        "id": 2
    }
    subscribe = {
        "channel": "/meta/subscribe",
        "clientId": "",
        "subscription": "/attendance/{}/{}/qr",
        "id": 1
    }

    @staticmethod
    def getSubscribe(courseId, signId):
        sub = Message.subscribe
        sub['subscription'] = sub['subscription'].format(courseId, signId)
        return sub


class Sender:
    def __init__(self, ws) -> None:
        self.ws = ws
        self._seqid = 0
        self.clientId = ''
        pass

    def getSeqid(self) -> int:
        self._seqid += 1
        return self._seqid-1

    async def hello(self):
        await self.ws.send(json.dumps(Message.hello))
        self._seqid += 1

    async def sendJSON(self, strjson: Union[dict, list]):
        try:
            strjson['id'] = self.getSeqid()
        except:
            pass
        while True:
            if self.clientId:
                break
            await asyncio.sleep(0.5)
        try:
            strjson['clientId'] = self.clientId
        except:
            pass
        await self.ws.send(json.dumps(strjson))

    async def enableHeartbeat(self, timeDelay):
        while True:
            await self.sendJSON([])
            await asyncio.sleep(timeDelay)

    async def setWebsocketListener(self, callbackFunction: Callable):
        while True:
            msg = await self.ws.recv()
            await callbackFunction(self, msg)


def QRHandler(s: str):
    qr = qrcode.QRCode()
    qr.add_data(s)
    # invert=True白底黑块,有些app不识别黑底白块.
    qr.print_ascii(invert=True)


async def msgHandler(sender: Sender, msg: str):
    if len(msg) == 0:
        return
    jsonmsg = json.loads(msg)
    if len(jsonmsg) == 0:
        debug("[]")
        return
    jsonmsg = jsonmsg[0]
    # handshake?
    if jsonmsg['channel'] == '/meta/handshake':
        sender.clientId = jsonmsg['clientId']
        debug(f"HANDSHAKE:,CLIENTID={jsonmsg['clientId']}")
        return
    # connect?
    if jsonmsg['channel'] == '/meta/connect':
        debug(f"CONNECT")
        await sender.sendJSON(Message.connect)
    # Attendance?
    if jsonmsg['channel'].startswith("/attendance"):
        if jsonmsg['data']['type'] == 1:
            qrURL = jsonmsg['data']['qrUrl']
            debug(f"QRURL = {qrURL}")
            QRHandler(qrURL)
        elif jsonmsg['data']['type'] == 3:
            stu = jsonmsg['data']['student']
            debug(f"STUDENT = {stu}")
        return

    debug(jsonmsg)


async def qrSign(courseId, signId):
    async with websockets.connect(url) as ws:
        sender = Sender(ws)
        await sender.hello()
        taskHeartbeat = asyncio.create_task(sender.enableHeartbeat(7.5))
        taskReceiverListener = asyncio.create_task(
            sender.setWebsocketListener(msgHandler))
        # first connect
        await sender.sendJSON(Message.connect)
        # subscribe
        await sender.sendJSON(Message.getSubscribe(courseId, signId))

        await taskHeartbeat
        await taskReceiverListener

if __name__ == "__main__":
    asyncio.run(qrSign(1212711, 2327453))
