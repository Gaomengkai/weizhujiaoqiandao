# weizhujiaoqiandao

### 仅供学习使用

使用本脚本所造成的一切后果由使用者本人承担

禁止使用本脚本进行商业化！

### 增加了*使用GPS签到*选项
我设置的默认位置是西十二。如果想更改位置，就改`x12`.如果不想，直接给`None`传进去。

其实不传位置参数也没有任何问题。没啥问题的。真的。

### 关于openid的获取方法

参考[https://github.com/yun-mu/wzj-sign-in-weixin](https://github.com/yun-mu/wzj-sign-in-weixin)

### 异步多用户版本已经发布

```bash
python3 AsyncCheckIn.py
```

可以检查users.json来查看

需要以下第三方额外库：

`httpx`

`qrcode`

`websockets`

使用如下命令安装

```bash
$ pip install httpx qrcode websockets
```

或者

```bash
$ pip install -r requirements.txt
```
