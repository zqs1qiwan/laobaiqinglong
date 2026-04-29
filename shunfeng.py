# cron: 1 7 * * *
# new Env('顺丰签到');
"""
顺丰速运每日签到 & 积分任务脚本（青龙面板）

环境变量:
  SF_COOKIES      - 从顺丰 App 抓包获取的完整 Cookie 字符串
                    格式: JSESSIONID=xxx; sessionId=xxx; _login_user_id_=xxx; _login_mobile_=xxx
                    多账号用换行分隔（每行一个账号的完整 cookie）
  PUSH_PLUS_TOKEN - PushPlus 推送 token（可选）
  BARK_URL        - Bark 推送地址（可选，如 https://api.day.app/xxxxx）

鉴权说明:
  直接使用 SF_COOKIES 中的 JSESSIONID 等 cookie 进行鉴权。
  在顺丰 App 中打开任意页面时抓包，找到 mcs-mimp-web.sf-express.com 的请求，
  复制请求头中的 Cookie 值即可。
  每次运行成功后，如果响应中有新的 Set-Cookie，会自动更新到青龙环境变量。
"""

import hashlib
import json
import os
import random
import re
import sys
import time
import uuid
import base64
import traceback
from datetime import datetime, timezone, timedelta
from urllib.parse import quote

import requests
from requests.packages.urllib3.exceptions import InsecureRequestWarning

requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

# ============ 常量 ============
BASE_URL = "https://mcs-mimp-web.sf-express.com"
IF_LOGIN_PATH = "/mcs-mimp/ifLogin"
API_POST_PATH = "/mcs-mimp/commonPost/"
API_ROUTE_POST_PATH = "/mcs-mimp/commonRoutePost/"
API_NO_LOGIN_POST_PATH = "/mcs-mimp/commonNoLoginPost/"
SYS_CODE = "MCS-MIMP-CORE"
SIGN_TOKEN = "wwesldfs29aniversaryvdld29"
SW8_APP_CODE = "fb40817085be4e398e0b6f4b08177746"
USER_AGENT = "SFMainland_Store_Pro/9.89.0.1 CFNetwork/3860.500.112 Darwin/25.4.0"

CST = timezone(timedelta(hours=8))

# 青龙面板 API（用于自动更新环境变量）
QL_URL = os.environ.get("QL_URL", "http://localhost:5700")
QL_CLIENT_ID = os.environ.get("QL_CLIENT_ID", "")
QL_CLIENT_SECRET = os.environ.get("QL_CLIENT_SECRET", "")


# ============ 工具函数 ============

def log(msg=""):
    ts = datetime.now(CST).strftime("%H:%M:%S")
    print(f"[{ts}] {msg}")


def gen_signature(timestamp):
    raw = f"token={SIGN_TOKEN}&timestamp={timestamp}&sysCode={SYS_CODE}"
    return hashlib.md5(raw.encode()).hexdigest()


def gen_sw8(url_path):
    def b64(s):
        return base64.b64encode(s.encode()).decode()
    trace_id = b64(str(uuid.uuid4()).replace("-", ""))
    segment_id = b64(str(uuid.uuid4()).replace("-", ""))
    app_code = b64(SW8_APP_CODE)
    service = b64("web")
    page_path = b64("/superWelfare")
    target = b64(url_path)
    return f"1-{trace_id}-{segment_id}-0-{app_code}-{service}-{page_path}-{target}"


def gen_device_id():
    chars = "abcdef0123456789"
    result = ""
    for c in "xxxxxxxx-xxxx-xxxx":
        result += random.choice(chars) if c == "x" else c
    return result


# ============ 青龙面板 API ============

def ql_get_token():
    """获取青龙面板 API token"""
    if not QL_CLIENT_ID or not QL_CLIENT_SECRET:
        return None
    try:
        resp = requests.get(
            f"{QL_URL}/open/auth/token",
            params={"client_id": QL_CLIENT_ID, "client_secret": QL_CLIENT_SECRET},
            timeout=10,
        )
        data = resp.json()
        if data.get("code") == 200:
            return data["data"]["token"]
    except Exception as e:
        log(f"  获取青龙 token 失败: {e}")
    return None


def ql_update_env(name, value, remarks=""):
    """更新或创建青龙环境变量"""
    token = ql_get_token()
    if not token:
        log(f"  ⚠ 无法更新环境变量 {name}（未配置青龙 API）")
        return False

    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

    try:
        # 查找现有变量
        resp = requests.get(
            f"{QL_URL}/open/envs",
            params={"searchValue": name},
            headers=headers,
            timeout=10,
        )
        envs = resp.json().get("data", [])
        existing = [e for e in envs if e.get("name") == name]

        if existing:
            # 更新现有变量
            env_id = existing[0]["id"]
            resp = requests.put(
                f"{QL_URL}/open/envs",
                headers=headers,
                json={"id": env_id, "name": name, "value": value, "remarks": remarks or existing[0].get("remarks", "")},
                timeout=10,
            )
        else:
            # 创建新变量
            resp = requests.post(
                f"{QL_URL}/open/envs",
                headers=headers,
                json=[{"name": name, "value": value, "remarks": remarks}],
                timeout=10,
            )

        result = resp.json()
        if result.get("code") == 200:
            log(f"  ✅ 环境变量 {name} 已更新")
            return True
        else:
            log(f"  ⚠ 更新环境变量失败: {result}")
    except Exception as e:
        log(f"  ⚠ 更新环境变量异常: {e}")
    return False


def ql_delete_env(name):
    """删除青龙环境变量"""
    token = ql_get_token()
    if not token:
        return False

    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

    try:
        resp = requests.get(
            f"{QL_URL}/open/envs",
            params={"searchValue": name},
            headers=headers,
            timeout=10,
        )
        envs = resp.json().get("data", [])
        existing = [e for e in envs if e.get("name") == name]

        if existing:
            env_id = existing[0]["id"]
            resp = requests.delete(
                f"{QL_URL}/open/envs",
                headers=headers,
                json=[env_id],
                timeout=10,
            )
            result = resp.json()
            if result.get("code") == 200:
                log(f"  ✅ 环境变量 {name} 已删除")
                return True
            else:
                log(f"  ⚠ 删除环境变量失败: {result}")
        else:
            log(f"  📝 环境变量 {name} 不存在，无需删除")
    except Exception as e:
        log(f"  ⚠ 删除环境变量异常: {e}")
    return False


# ============ 推送通知 ============

def push_notification(title, content):
    push_plus_token = os.environ.get("PUSH_PLUS_TOKEN", "")
    bark_url = os.environ.get("BARK_URL", "")

    if push_plus_token:
        try:
            resp = requests.post(
                "http://www.pushplus.plus/send",
                json={
                    "token": push_plus_token,
                    "title": title,
                    "content": content.replace("\n", "<br>"),
                    "template": "html",
                },
                timeout=10,
            )
            log(f"PushPlus 推送: {resp.json().get('msg', 'unknown')}")
        except Exception as e:
            log(f"PushPlus 推送失败: {e}")

    if bark_url:
        try:
            bark_url = bark_url.rstrip("/")
            resp = requests.get(
                f"{bark_url}/{quote(title)}/{quote(content)}", timeout=10
            )
            log(f"Bark 推送: {resp.json().get('message', 'unknown')}")
        except Exception as e:
            log(f"Bark 推送失败: {e}")


# ============ SF Express 客户端 ============

class SFClient:
    def __init__(self, cookies_str, index=1):
        """
        cookies_str: 完整的 cookie 字符串，如 JSESSIONID=xxx; sessionId=xxx; ...
        """
        self.cookies_str = cookies_str.strip()
        self.index = index
        self.session = requests.Session()
        self.session.verify = False
        self.device_id = gen_device_id()
        self.logged_in = False
        self.mobile = ""
        self.user_id = ""
        self.report_lines = []

    def _report(self, msg):
        log(msg)
        self.report_lines.append(msg)

    def _mask_mobile(self, mobile):
        if len(mobile) >= 7:
            return mobile[:3] + "****" + mobile[-4:]
        return mobile or "未知"

    # ---- Cookie 序列化 ----

    def _export_cookies(self):
        """导出当前 session 的关键 cookies 为字符串"""
        cookie_dict = self.session.cookies.get_dict()
        key_cookies = ["JSESSIONID", "sessionId", "_login_user_id_", "_login_mobile_"]
        parts = []
        for k in key_cookies:
            if k in cookie_dict:
                parts.append(f"{k}={cookie_dict[k]}")
        return "; ".join(parts)

    def _import_cookies(self, cookies_str):
        """从字符串导入 cookies 到 session"""
        for part in cookies_str.split(";"):
            part = part.strip()
            if "=" in part:
                name, value = part.split("=", 1)
                self.session.cookies.set(name.strip(), value.strip())

    # ---- 登录验证 ----

    def login(self):
        """使用 cookies 验证登录状态"""
        log(f"账号{self.index}: 使用 SF_COOKIES 验证登录状态...")
        self._import_cookies(self.cookies_str)

        try:
            resp = self.session.post(
                f"{BASE_URL}{IF_LOGIN_PATH}",
                headers={"User-Agent": USER_AGENT, "Content-Type": "application/json"},
                json={},
                timeout=15,
            )
            data = resp.json()
            if data.get("success") and data.get("obj", {}).get("loginStatus") == 1:
                self.mobile = data["obj"].get("mobile", "").replace("*", "")
                self.user_id = self.session.cookies.get("_login_user_id_", "")
                full_mobile = self.session.cookies.get("_login_mobile_", "")
                self.logged_in = True
                self._report(
                    f"👤 账号{self.index}:【{self._mask_mobile(full_mobile)}】Cookie 登录成功"
                )
                # 更新 cookies（可能有新的 Set-Cookie）
                self.cookies_str = self._export_cookies()
                return True
            else:
                err_msg = data.get("errorMessage", "loginStatus != 1")
                self._report(
                    f"❌ 账号{self.index}: SF_COOKIES 已过期，请重新抓包更新"
                    f"（{err_msg}）"
                )
                return False
        except Exception as e:
            self._report(f"❌ 账号{self.index}: Cookie 验证异常: {e}")
            return False

    # ---- 通用请求 ----

    def _build_headers(self, api_path):
        ts = str(int(time.time() * 1000))
        return {
            "User-Agent": USER_AGENT,
            "Content-Type": "application/json",
            "syscode": SYS_CODE,
            "channel": "appqiandao",
            "platform": "SFAPP",
            "timestamp": ts,
            "signature": gen_signature(ts),
            "sw8": gen_sw8(api_path),
        }

    def _api_post(self, service_path, body=None, prefix=API_POST_PATH, retry=True):
        if body is None:
            body = {}
        full_path = prefix + service_path
        url = f"{BASE_URL}{full_path}"
        headers = self._build_headers(full_path)

        for attempt in range(2 if retry else 1):
            try:
                resp = self.session.post(url, json=body, headers=headers, timeout=30)
                result = resp.json()

                # 检测 cookie 过期（接口返回未登录）
                if not result.get("success"):
                    err_msg = result.get("errorMessage", "")
                    err_code = result.get("errorCode", "")
                    if any(kw in str(err_msg) for kw in ["未登录", "登录", "session", "401"]) or \
                       err_code in ["NOT_LOGIN", "SESSION_EXPIRED", "401"]:
                        self._report(f"  ⚠ SF_COOKIES 已过期，请重新抓包更新（{err_msg}）")

                return result
            except Exception as e:
                log(f"  请求失败 [{service_path}] (第{attempt + 1}次): {e}")
                if attempt == 0 and retry:
                    time.sleep(2)
        return None

    # ---- 签到 ----

    def do_sign(self):
        """执行每日签到（automaticSignFetchPackage 接口）"""
        self._report("🎯 开始签到...")
        data = self._api_post(
            "~memberNonactivity~integralTaskSignPlusService~automaticSignFetchPackage",
            {"comeFrom": "vioin", "channelFrom": "SFAPP"},
        )
        if not data:
            self._report("  ❌ 签到请求失败")
            return

        if data.get("success"):
            obj = data.get("obj", {})
            has_finish = obj.get("hasFinishSign", 0)
            count_day = obj.get("countDay", 0)
            packages = obj.get("integralTaskSignPackageVOList", [])
            pkg_names = [p.get("packetName", "") for p in packages if p.get("packetName")]

            if has_finish == 1:
                msg = f"  📝 今日已签到，连续签到 {count_day} 天"
            else:
                msg = f"  ✅ 签到成功! 连续签到 {count_day} 天"
            if pkg_names:
                msg += f" | 礼包: {', '.join(pkg_names)}"
            self._report(msg)
        else:
            err_msg = data.get("errorMessage", "未知错误")
            if "已" in err_msg and "签" in err_msg:
                self._report(f"  📝 {err_msg}")
            else:
                self._report(f"  ❌ 签到失败: {err_msg}")

    # ---- 超值福利签到 ----

    def super_welfare_sign(self):
        """超值福利签到红包"""
        log("🎁 超值福利签到...")
        data = self._api_post(
            "~memberActLengthy~redPacketActivityService~superWelfare~receiveRedPacket",
            {"channel": "czflqdlhbxcx"},
        )
        if not data:
            return
        if data.get("success"):
            gift_list = data.get("obj", {}).get("giftList", [])
            extra = data.get("obj", {}).get("extraGiftList", [])
            if extra:
                gift_list.extend(extra)
            gift_names = ", ".join(g.get("giftName", "?") for g in gift_list) or "无"
            status = "领取成功" if data.get("obj", {}).get("receiveStatus") == 1 else "已领取"
            self._report(f"  🎁 超值福利[{status}]: {gift_names}")
        else:
            log(f"  超值福利签到: {data.get('errorMessage', '失败')}")

    # ---- 积分任务 ----

    def query_task_list(self):
        """查询积分任务列表"""
        log("📋 查询积分任务...")
        data = self._api_post(
            "~memberNonactivity~integralTaskStrategyService~queryPointTaskAndSignFromES",
            {"channelType": "1", "deviceId": self.device_id},
        )
        if not data or not data.get("success"):
            log("  查询任务列表失败")
            return [], 0

        obj = data.get("obj", {})
        total_point = obj.get("totalPoint", 0)
        tasks = obj.get("taskTitleLevels", [])
        self._report(f"💰 当前积分: {total_point}")
        return tasks, total_point

    def do_tasks(self):
        """完成积分任务并领取奖励"""
        tasks, _ = self.query_task_list()
        if not tasks:
            return

        skip_titles = ["用行业模板寄件下单", "去新增一个收件偏好", "参与积分活动",
                       "去寄快递", "开通至尊会员", "充值速运通", "开通亲情卡"]
        done_count = 0
        skip_count = 0

        for task in tasks:
            title = task.get("title", "?")
            task_code = task.get("taskCode", "")
            strategy_id = task.get("strategyId", "")
            task_id = task.get("taskId", "")
            status = task.get("status", 0)

            if status == 3:
                done_count += 1
                continue
            if any(s in title for s in skip_titles):
                skip_count += 1
                continue

            # 完成任务
            log(f"  ▶ 完成任务: {title}")
            finish_data = self._api_post(
                "memberEs/taskRecord/finishTask",
                {"taskCode": task_code},
                prefix=API_ROUTE_POST_PATH,
            )
            if finish_data and finish_data.get("success"):
                log(f"    ✅ {title} - 已完成")
            else:
                err = finish_data.get("errorMessage", "未知") if finish_data else "请求失败"
                log(f"    ❌ {title} - {err}")

            time.sleep(random.uniform(1.5, 3.0))

            # 领取奖励
            reward_data = self._api_post(
                "~memberNonactivity~integralTaskStrategyService~fetchIntegral",
                {
                    "strategyId": strategy_id,
                    "taskId": task_id,
                    "taskCode": task_code,
                    "deviceId": self.device_id,
                },
            )
            if reward_data and reward_data.get("success"):
                log(f"    🎁 {title} - 奖励已领取")
            else:
                err = reward_data.get("errorMessage", "未知") if reward_data else "请求失败"
                log(f"    ⚠ {title} - 领取奖励: {err}")

            time.sleep(random.uniform(1, 2))

        self._report(
            f"📋 积分任务: {done_count} 已完成, {len(tasks) - done_count - skip_count} 执行, {skip_count} 跳过"
        )

    # ---- 批量领取任务奖励 ----

    def fetch_tasks_reward(self):
        """批量领取积分任务奖励"""
        log("🎁 批量领取任务奖励...")
        data = self._api_post(
            "~memberNonactivity~integralTaskStrategyService~fetchTasksReward",
            {"channelType": "1", "deviceId": self.device_id},
            prefix=API_NO_LOGIN_POST_PATH,
        )
        if data and data.get("success"):
            log("  ✅ 批量领取完成")
        else:
            err = data.get("errorMessage", "未知") if data else "请求失败"
            log(f"  批量领取: {err}")

    # ---- 查询最终积分 ----

    def query_final_points(self):
        """查询执行后积分余额"""
        data = self._api_post(
            "~memberNonactivity~integralTaskStrategyService~queryPointTaskAndSignFromES",
            {"channelType": "1", "deviceId": self.device_id},
        )
        if data and data.get("success"):
            total_point = data.get("obj", {}).get("totalPoint", 0)
            self._report(f"💰 执行后积分: {total_point}")
            return total_point
        return 0

    # ---- 生活特权领券 ----

    def get_coupon_list(self):
        """遍历生活特权所有分组的券进行领券"""
        log("🎫 尝试领取生活特权券...")
        data = self._api_post(
            "~memberGoods~mallGoodsLifeService~list",
            {"memGrade": 2, "categoryCode": "SHTQ", "showCode": "SHTQWNTJ"},
        )
        if not data or not data.get("success"):
            return

        all_goods = []
        for obj in data.get("obj", []):
            all_goods.extend(obj.get("goodsList", []))

        for goods in all_goods:
            if goods.get("exchangeTimesLimit", 0) >= 1:
                result = self._api_post(
                    "~memberGoods~pointMallService~createOrder",
                    {
                        "from": "Point_Mall",
                        "orderSource": "POINT_MALL_EXCHANGE",
                        "goodsNo": goods["goodsNo"],
                        "quantity": 1,
                    },
                )
                if result and result.get("success"):
                    log(f"  ✅ 成功领取券: {goods.get('goodsName', '?')}")
                    return
        log("  📝 没有可领取的券")

    # ---- 主流程 ----

    def run(self):
        """单账号完整执行流程"""
        if not self.login():
            return self.get_report()

        wait = random.uniform(1, 3)
        time.sleep(wait)

        # 1. 每日签到
        self.do_sign()

        # 2. 超值福利签到
        self.super_welfare_sign()

        # 3. 积分任务
        self.do_tasks()

        # 4. 批量领取奖励
        self.fetch_tasks_reward()

        # 5. 生活特权领券
        self.get_coupon_list()

        # 6. 查询最终积分
        self.query_final_points()

        return self.get_report()

    def get_report(self):
        return {
            "account": self._mask_mobile(self.session.cookies.get("_login_mobile_", self.mobile)) or f"账号{self.index}",
            "lines": self.report_lines,
            "cookies": self.cookies_str,
            "logged_in": self.logged_in,
        }


# ============ 主入口 ============

def main():
    log("=" * 50)
    log("🚚 顺丰速运签到脚本 v4.0 (纯 Cookie 鉴权)")
    log("=" * 50)

    sf_cookies = os.environ.get("SF_COOKIES", "").strip()

    if not sf_cookies:
        log("❌ 未设置 SF_COOKIES 环境变量!")
        log("   请在青龙面板配置 SF_COOKIES 环境变量，值为从顺丰App抓包获取的完整cookie字符串")
        log("")
        log("   获取方法:")
        log("   1. 手机安装抓包工具（如 Stream、Charles、HttpCanary）")
        log("   2. 打开顺丰速运 App，进入任意页面")
        log("   3. 在抓包工具中找到 mcs-mimp-web.sf-express.com 的请求")
        log("   4. 复制请求头中的 Cookie 值")
        log("   5. 格式: JSESSIONID=xxx; sessionId=xxx; _login_user_id_=xxx; _login_mobile_=xxx")
        log("   6. 多账号用换行分隔（每行一个账号的完整 cookie）")
        sys.exit(1)

    # 按换行分隔多账号
    accounts = [line.strip() for line in sf_cookies.split("\n") if line.strip()]
    log(f"📝 从 SF_COOKIES 加载 {len(accounts)} 个账号")

    all_reports = []
    new_cookies = []  # 收集所有成功登录的 cookies

    for i, cookies_str in enumerate(accounts, 1):
        try:
            client = SFClient(cookies_str, i)
            report = client.run()
            all_reports.append(report)

            # 收集有效 cookies
            if report.get("logged_in") and report.get("cookies"):
                new_cookies.append(report["cookies"])
        except Exception as e:
            log(f"❌ 账号{i} 执行异常: {e}")
            traceback.print_exc()
            all_reports.append({
                "account": f"账号{i}",
                "lines": [f"❌ 执行异常: {e}"],
                "cookies": "",
                "logged_in": False,
            })

        if i < len(accounts):
            delay = random.uniform(3, 5)
            log(f"⏳ 等待 {delay:.1f} 秒...")
            time.sleep(delay)

    # 保存有效的 cookies 到环境变量（用换行分隔，用于下次运行）
    if new_cookies:
        cookies_value = "\n".join(new_cookies)
        log(f"\n🔑 保存 {len(new_cookies)} 个账号的 cookies...")
        ql_update_env("SF_COOKIES", cookies_value, "顺丰签到-自动维护的cookies")

    # 汇总
    summary_lines = [
        "🚚 顺丰签到结果",
        f"⏰ {datetime.now(CST).strftime('%Y-%m-%d %H:%M:%S')}",
        "",
    ]
    for report in all_reports:
        summary_lines.append(f"{'=' * 40}")
        summary_lines.append(f"👤 {report['account']}")
        summary_lines.extend(report["lines"])
        summary_lines.append("")

    summary = "\n".join(summary_lines)
    print("\n" + summary)

    # 推送通知
    push_notification("顺丰签到", summary)
    log("🎉 全部完成!")


if __name__ == "__main__":
    main()
