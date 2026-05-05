## 青龙订阅任务
```
名称：老白自用青龙任务
类型：公开仓库
链接：https://github.com/zqs1qiwan/laobaiqinglong.git
定时类型：crontab
定时规则：0 30 * * * *
文件后缀：py
```

## 中国联通签到（chinaUnicom.py）

### 功能说明

- ✅ 首页签到（话费红包/积分）
- ✅ 联通祝福（各类抽奖）
- ✅ 天天领现金（每日打卡/立减金）
- ✅ 权益超市（任务/抽奖/浇水/领奖）
- ✅ 安全管家（日常任务/积分领取）
- ✅ 联通云盘（签到/AI互动/文件上传/抽奖）
- ✅ 联通阅读（心跳阅读/抽奖/查红包）
- ✅ 联通爱听（积分任务/自动签到/阅读挂机）
- ✅ 沃云手机（签到/任务/抽奖）
- ✅ 区域专区（新疆/河南/云南特有任务）
- ✅ 支持多账号（`&` 或换行分隔）
- ✅ 纯 Python 3 实现，依赖 `pycryptodome`、`requests`

### 使用方法

#### 1. 配置环境变量

在青龙面板 → **环境变量** 中添加：

| 变量名 | 说明 | 必填 |
|--------|------|------|
| `chinaUnicomCookie` | Token#AppId 或 手机号#密码 | ✅ |
| `UNICOM_PROXY_API` | 代理提取链接（支持 JSON/TXT） | 可选 |
| `UNICOM_GRAB_AMOUNT` | 抢兑面额，默认 `5` | 可选 |

**多账号格式**（`&` 或换行分隔）：
```
token1#appId1&token2#appId2
```

#### 2. 定时规则建议

```
0 7,20 * * *   # 每天早晚各跑一次（推荐）
0 58 9,17 * * * # 抢兑专用（需开启 run_grab_coupon）
```

### Python 依赖

```
pycryptodome
requests
```

---

## ~~顺丰签到（shunfeng.py）~~ *(已归档，暂不可用)*

<details>
<summary>点击展开历史说明</summary>

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

### 环境变量

| 变量名 | 说明 | 必填 |
|--------|------|------|
| `SF_COOKIES` | 抓包获取的完整 Cookie 字符串，多账号用换行分隔 | ✅ |
| `PUSH_PLUS_TOKEN` | PushPlus 推送 token | 可选 |
| `BARK_URL` | Bark 推送地址（如 `https://api.day.app/xxxxx`） | 可选 |

### Cookie 获取

1. 手机安装抓包工具（如 Stream、Charles、HttpCanary）
2. 打开**顺丰速运 App**，进入任意页面
3. 在抓包工具中找到 `mcs-mimp-web.sf-express.com` 的请求
4. 复制请求头中的 **Cookie** 值：
   ```
   JSESSIONID=xxx; sessionId=xxx; _login_user_id_=xxx; _login_mobile_=xxx
   ```

</details>
