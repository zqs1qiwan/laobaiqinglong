#!/usr/bin/env python3
"""
顺丰 App 签到脚本
环境变量：SF_APP_SIGN — sign 字符串，多账号用换行或 & 分隔
"""

import hashlib
import time
import uuid
import base64
import json
import os
import sys
from urllib import request, parse, error
from http.cookiejar import CookieJar

# ── 常量 ────────────────────────────────────────────────────────────────────
DEVICE_ID = "D2wYa5Cofg0tcOVmzc59li4locz2H_Vq9SoYqpdjCCUncX96"
USER_AGENT = (
    "Mozilla/5.0 (iPhone; CPU iPhone OS 18_7 like Mac OS X) "
    "AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148 "
    "mediaCode=SFEXPRESSAPP-iOS-ML"
)
BIZ_CODE = json.dumps({
    "path": "/up-member/newPoints",
    "linkCode": "SFAC20230803190840424",
    "supportShare": "YES",
    "subCategoryCode": "1",
    "from": "point240613",
    "categoryCode": "1"
}, separators=(",", ":"))
ACTIVITY_REDIRECT_URL = "https://mcs-mimp-web.sf-express.com/mcs-mimp/share/app/activityRedirect"
SIGN_API = "https://mcs-mimp-web.sf-express.com/mcs-mimp/commonPost/~memberNonactivity~integralSignV2Service~sign"
QUERY_USER_API = "https://mcs-mimp-web.sf-express.com/mcs-mimp/commonPost/~memberIntegral~userInfoService~queryUserInfo"
SW8_KEY = "fb40817085be4e398e0b6f4b08177746"
CHANNEL = "point240613"
SYS_CODE = "MCS-MIMP-CORE"
PLATFORM = "SFAPP"
SIGN_SECRET = "wwesldfs29aniversaryvdld29"


# ── 工具函数 ─────────────────────────────────────────────────────────────────

def b64(s: str) -> str:
    return base64.b64encode(s.encode()).decode()


def gen_sw8(url_path: str = "/up-member/newPoints") -> str:
    trace_id = str(uuid.uuid4())
    span_id = str(uuid.uuid4())
    pathname = "/up-member/newPoints"
    return (
        f"1-{b64(trace_id)}-{b64(span_id)}-0"
        f"-{b64(SW8_KEY)}-{b64('web')}-{b64(pathname)}-{b64(url_path)}"
    )


def gen_signature() -> tuple[str, str]:
    """返回 (timestamp_ms_str, signature_hex)"""
    ts = str(int(time.time() * 1000))
    raw = f"{SIGN_SECRET}&timestamp={ts}&sysCode={SYS_CODE}"
    sig = hashlib.md5(raw.encode()).hexdigest()
    return ts, sig


def parse_cookies(set_cookie_headers: list[str]) -> dict:
    """从 Set-Cookie 头列表中提取 cookie 键值对"""
    cookies = {}
    for header in set_cookie_headers:
        # 只取第一段 key=value，忽略 Path/Domain/Expires 等属性
        part = header.split(";")[0].strip()
        if "=" in part:
            k, v = part.split("=", 1)
            cookies[k.strip()] = v.strip()
    return cookies


def build_cookie_str(cookies: dict) -> str:
    return "; ".join(f"{k}={v}" for k, v in cookies.items())


def no_redirect_opener():
    """返回一个不跟随重定向的 opener"""
    class NoRedirect(request.HTTPErrorProcessor):
        def http_response(self, req, response):
            return response
        https_response = http_response

    opener = request.build_opener(NoRedirect)
    return opener


# ── 核心流程 ─────────────────────────────────────────────────────────────────

def get_session_cookies(sign: str) -> dict:
    """用 sign 换取 JSESSIONID 等 Cookie"""
    encoded_sign = parse.quote(sign, safe="")
    encoded_biz = parse.quote(BIZ_CODE, safe="")
    url = (
        f"{ACTIVITY_REDIRECT_URL}"
        f"?sign={encoded_sign}"
        f"&source=SFAPP"
        f"&bizCode={encoded_biz}"
        f"&citycode=010"
        f"&cityname=%E5%8C%97%E4%BA%AC"
    )
    print(f"[1] 获取 Session Cookie...")
    print(f"    URL: {url[:120]}...")

    req = request.Request(url, headers={
        "User-Agent": USER_AGENT,
        "Accept": "*/*",
    })
    opener = no_redirect_opener()
    try:
        resp = opener.open(req, timeout=15)
    except Exception as e:
        raise RuntimeError(f"activityRedirect 请求失败: {e}")

    status = resp.status
    headers = resp.headers
    print(f"    响应状态码: {status}")

    # 收集所有 Set-Cookie
    set_cookie_list = []
    for key, val in headers.items():
        if key.lower() == "set-cookie":
            set_cookie_list.append(val)

    # Python http.client 有时会把多个 Set-Cookie 合并或分开，兼容处理
    cookies = parse_cookies(set_cookie_list)
    print(f"    获取到 Cookie: {list(cookies.keys())}")

    if not cookies.get("JSESSIONID"):
        # 尝试从 Location 头看是否有额外信息
        location = headers.get("Location", "")
        print(f"    Location: {location[:200] if location else '(无)'}")
        # 即使没有 JSESSIONID 也尝试继续
        print("    警告: 未获取到 JSESSIONID，后续请求可能失败")
    return cookies


def do_sign(cookies: dict) -> dict:
    """执行签到"""
    ts, sig = gen_signature()
    sw8 = gen_sw8()
    cookie_str = build_cookie_str(cookies)

    print(f"\n[2] 执行签到...")
    print(f"    timestamp: {ts}")
    print(f"    signature: {sig}")

    req = request.Request(
        SIGN_API,
        data=b"{}",
        method="POST",
        headers={
            "Cookie": cookie_str,
            "channel": CHANNEL,
            "timestamp": ts,
            "signature": sig,
            "sysCode": SYS_CODE,
            "platform": PLATFORM,
            "deviceId": DEVICE_ID,
            "User-Agent": USER_AGENT,
            "sw8": sw8,
            "Content-Type": "application/json",
            "Accept": "application/json, text/plain, */*",
        }
    )
    try:
        resp = request.urlopen(req, timeout=15)
        body = resp.read().decode("utf-8")
    except error.HTTPError as e:
        body = e.read().decode("utf-8")
        print(f"    HTTP 错误 {e.code}: {body}")
        return {"error": str(e), "body": body}
    except Exception as e:
        raise RuntimeError(f"签到请求失败: {e}")

    print(f"    签到响应: {body}")
    try:
        return json.loads(body)
    except Exception:
        return {"raw": body}


def query_user_info(cookies: dict) -> dict:
    """查询积分信息"""
    ts, sig = gen_signature()
    sw8 = gen_sw8()
    cookie_str = build_cookie_str(cookies)

    print(f"\n[3] 查询积分...")

    req = request.Request(
        QUERY_USER_API,
        data=b"{}",
        method="POST",
        headers={
            "Cookie": cookie_str,
            "channel": CHANNEL,
            "timestamp": ts,
            "signature": sig,
            "sysCode": SYS_CODE,
            "platform": PLATFORM,
            "deviceId": DEVICE_ID,
            "User-Agent": USER_AGENT,
            "sw8": sw8,
            "Content-Type": "application/json",
            "Accept": "application/json, text/plain, */*",
        }
    )
    try:
        resp = request.urlopen(req, timeout=15)
        body = resp.read().decode("utf-8")
    except error.HTTPError as e:
        body = e.read().decode("utf-8")
        print(f"    HTTP 错误 {e.code}: {body}")
        return {"error": str(e), "body": body}
    except Exception as e:
        raise RuntimeError(f"查询积分失败: {e}")

    print(f"    积分查询响应: {body}")
    try:
        return json.loads(body)
    except Exception:
        return {"raw": body}


def process_account(sign: str, index: int) -> None:
    print(f"\n{'='*60}")
    print(f"账号 #{index+1} 开始处理")
    print(f"sign: {sign[:40]}...")
    print(f"{'='*60}")

    try:
        # 1. 换取 Session Cookie
        cookies = get_session_cookies(sign)

        # 2. 签到
        sign_result = do_sign(cookies)

        # 3. 查询积分
        user_info = query_user_info(cookies)

        # 汇总输出
        print(f"\n── 账号 #{index+1} 结果汇总 ──")

        # 签到结果解析（实际字段：success/errorCode/errorMessage/data）
        if "error" not in sign_result:
            sign_ok = sign_result.get("success", False)
            err_code = sign_result.get("errorCode", "")
            err_msg = sign_result.get("errorMessage", "")
            sign_data = sign_result.get("data") or {}
            if sign_ok:
                integral = ""
                if isinstance(sign_data, dict):
                    integral = (sign_data.get("integral") or sign_data.get("integralValue") or
                                sign_data.get("point") or sign_data.get("signIntegral") or "")
                print(f"  ✅ 签到成功！获得积分: {integral or '见data'}")
                if isinstance(sign_data, dict) and sign_data:
                    print(f"     data: {sign_data}")
            else:
                print(f"  签到结果: {err_msg or err_code} (errorCode={err_code})")
        else:
            print(f"  签到失败: {sign_result}")

        # 积分查询解析
        if "error" not in user_info:
            info_ok = user_info.get("success", False)
            info_data = user_info.get("data") or {}
            if info_ok and isinstance(info_data, dict):
                total = (
                    info_data.get("totalIntegral") or
                    info_data.get("availableIntegral") or
                    info_data.get("integral") or
                    "N/A"
                )
                if total == "N/A" and isinstance(info_data.get("integralInfo"), dict):
                    total = info_data["integralInfo"].get("totalIntegral", "N/A")
                print(f"  当前总积分: {total}")
            else:
                err = user_info.get("errorMessage", "")
                print(f"  积分查询: {err or '失败'}")
        else:
            print(f"  积分查询失败: {user_info}")

    except Exception as e:
        print(f"  账号 #{index+1} 处理出错: {e}")


def main():
    raw = os.environ.get("SF_APP_SIGN", "").strip()
    if not raw:
        print("错误: 请设置环境变量 SF_APP_SIGN")
        sys.exit(1)

    # 支持换行或 & 分隔多账号
    signs = []
    for part in raw.replace("\n", "&").split("&"):
        s = part.strip()
        if s:
            signs.append(s)

    print(f"共 {len(signs)} 个账号")
    for i, sign in enumerate(signs):
        process_account(sign, i)

    print(f"\n{'='*60}")
    print("全部账号处理完成")


if __name__ == "__main__":
    main()
