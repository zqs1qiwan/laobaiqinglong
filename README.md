## 青龙订阅任务
```
名称：老白自用青龙任务
类型：公开仓库
链接：https://github.com/zqs1qiwan/laobaiqinglong.git
定时类型：crontab
定时规则：0 30 * * * *
文件后缀：py
```

## 顺丰签到脚本（shunfeng.py）

### 功能说明

- ✅ 每日自动签到（积分签到接口）
- ✅ 超值福利签到领红包
- ✅ 自动完成积分任务（浏览类任务）并领取奖励
- ✅ 批量领取任务奖励
- ✅ 生活特权自动领券
- ✅ 签到后查询积分余额
- ✅ 支持多账号（环境变量用换行分隔，每行一个账号的完整 cookie）
- ✅ 通知推送（PushPlus / Bark）
- ✅ 自动更新 cookies 到青龙环境变量
- ✅ 纯 Python 3 实现，无需 Node.js

### 使用方法

#### 1. 获取 Cookie

1. 手机安装抓包工具（如 Stream、Charles、HttpCanary）
2. 打开**顺丰速运 App**，进入任意页面
3. 在抓包工具中找到 `mcs-mimp-web.sf-express.com` 的请求
4. 复制请求头中的 **Cookie** 值，格式如下：
   ```
   JSESSIONID=xxx; sessionId=xxx; _login_user_id_=xxx; _login_mobile_=xxx
   ```

#### 2. 配置环境变量

在青龙面板 → **环境变量** 中添加：

| 变量名 | 说明 | 必填 |
|--------|------|------|
| `SF_COOKIES` | 抓包获取的完整 Cookie 字符串，多账号用换行分隔 | ✅ |
| `PUSH_PLUS_TOKEN` | PushPlus 推送 token | 可选 |
| `BARK_URL` | Bark 推送地址（如 `https://api.day.app/xxxxx`） | 可选 |

**多账号格式**（每行一个账号的完整 cookie）：
```
JSESSIONID=xxx1; sessionId=xxx1; _login_user_id_=xxx1; _login_mobile_=xxx1
JSESSIONID=xxx2; sessionId=xxx2; _login_user_id_=xxx2; _login_mobile_=xxx2
```

#### 3. 运行

脚本默认定时 `1 7 * * *`（每天早上 7:01 执行）。

也可以在青龙面板手动运行测试。

### Cookie 有效期

- JSESSIONID 有效期取决于服务器端 session 策略，通常可维持数小时到数天
- 每次脚本运行成功后会自动更新 cookies 到青龙环境变量，延长有效期
- 当脚本日志出现 **"SF_COOKIES 已过期，请重新抓包更新"** 时，需要重新抓包获取新的 Cookie
