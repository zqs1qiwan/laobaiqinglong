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

- ✅ 每日自动签到（积分签到 v2 接口）
- ✅ 超值福利签到领红包
- ✅ 自动完成积分任务（浏览类任务）并领取奖励
- ✅ 批量领取任务奖励
- ✅ 生活特权自动领券
- ✅ 签到后查询积分余额
- ✅ 支持多账号（环境变量用 `&` 或换行分隔）
- ✅ 通知推送（PushPlus / Bark）
- ✅ 纯 Python 3 实现，无需 Node.js

### 使用方法

#### 1. 获取 sign 参数

1. 手机安装抓包工具（如 Stream、Charles、HttpCanary）
2. 打开**顺丰速运 App** → **我的** → **会员中心** → **积分**
3. 在抓包工具中找到以下请求：
   ```
   GET https://mcs-mimp-web.sf-express.com/mcs-mimp/share/app/activityRedirect?sign=xxx&source=SFAPP&bizCode=622
   ```
4. 复制 URL 中 `sign=` 后面的值（到下一个 `&` 之前的部分）

#### 2. 配置环境变量

在青龙面板 → **环境变量** 中添加：

| 变量名 | 说明 | 必填 |
|--------|------|------|
| `SF_SIGN` | 抓包获取的 sign 值，多账号用 `&` 或换行分隔 | ✅ |
| `PUSH_PLUS_TOKEN` | PushPlus 推送 token | 可选 |
| `BARK_URL` | Bark 推送地址（如 `https://api.day.app/xxxxx`） | 可选 |

#### 3. 运行

脚本默认定时 `1 7 * * *`（每天早上 7:01 执行）。

也可以在青龙面板手动运行测试。

### sign 有效期

- sign 有效期一般为 **数周到数月**，取决于服务器端策略
- 当脚本日志出现 **"sign 可能已过期，请重新抓包"** 时，需要重复上述抓包步骤获取新的 sign
- 建议定期检查运行日志，确保签到正常

### 旧脚本说明

旧的 `顺丰20251028.py` 已停用，由 `shunfeng.py` 替代。新脚本采用 `activityRedirect` 接口自动登录，不再依赖手动 cookie 或微信扫码。
