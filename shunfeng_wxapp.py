#!/usr/bin/env python3
"""
顺丰速运小程序版签到脚本 v1.0
环境变量: SF_WXAPP_SESSION
格式: sessionId|openid|deviceId
多账号用换行或 & 分隔

签到接口来源: 逆向解包小程序 JS (main/appservice.app.js line 6659)
  actUrls.signIn = "/wechat-act/wxapp/signIn"  (POST, 无 body 参数)
  memberUrls.queryMemberSignStatus = "/cx-wechat-member/member/memGrade/queryMemberSignStatus" (GET)
  memberUrls.queryPoint = "/cx-wechat-member/member/memGrade/queryPoint?flag=2" (GET)

sign 算法已验证:
  sign = MD5(appId + nonceStr + key + requestBody).upper()
  nonceStr=kaAVgwuzTWBxFJoVoQAYGdXd1fRN6D6f → 09D918E1BCE542D2E8530313D9108254 ✅
"""
import os
import hashlib
import random
import string
import json
import time
import urllib.request
import urllib.error

APP_ID   = "wxapp-valid-0328"
KEY      = "2b08f7f6bf564a1dada1570535fd44ba"
BASE_URL = "https://ucmp.sf-express.com"


def gen_nonce(n=32):
    return ''.join(random.choices(string.ascii_letters + string.digits, k=n))


def gen_sign(nonce_str, body=""):
    """sign = MD5(appId + nonceStr + key + requestBody).upper()"""
    raw = APP_ID + nonce_str + KEY + (body or "")
    return hashlib.md5(raw.encode()).hexdigest().upper()


def make_headers(session_id, device_id, body=""):
    nonce = gen_nonce()
    sign  = gen_sign(nonce, body)
    return {
        "Content-Type":   "application/json;charset=UTF-8",
        "appId":          APP_ID,
        "nonceStr":       nonce,
        "sign":           sign,
        "suuid":          session_id,
        "deviceId":       device_id,
        "wxapp-version":  "V17.57",
        "User-Agent":     (
            "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) "
            "AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148 "
            "MicroMessenger/8.0.71 NetType/WIFI Language/zh_CN"
        ),
    }


def api_post(url, session_id, device_id, data=None):
    body    = json.dumps(data or {}, separators=(',', ':'))
    headers = make_headers(session_id, device_id, body)
    req     = urllib.request.Request(
        url, data=body.encode(), headers=headers, method="POST"
    )
    with urllib.request.urlopen(req, timeout=15) as resp:
        return json.loads(resp.read())


def api_get(url, session_id, device_id):
    headers = make_headers(session_id, device_id, "")
    req     = urllib.request.Request(url, headers=headers, method="GET")
    with urllib.request.urlopen(req, timeout=15) as resp:
        return json.loads(resp.read())


def query_sign_status(session_id, device_id):
    """查询签到状态，返回 (已签到bool, 连续天数, 今日积分)"""
    url = f"{BASE_URL}/cx-wechat-member/member/memGrade/queryMemberSignStatus"
    try:
        resp = api_get(url, session_id, device_id)
        obj  = (resp.get("data") or resp).get("obj") or {}
        signed      = obj.get("todayHasSigned", False) or obj.get("signToday", False)
        cont_days   = obj.get("continuousSignDay") or obj.get("continueSignDay") or 0
        today_point = obj.get("todaySignPoint") or obj.get("point") or 0
        return bool(signed), int(cont_days), int(today_point)
    except Exception as e:
        print(f"    查签到状态失败: {e}")
        return None, 0, 0


def query_point(session_id, device_id):
    """查询当前积分"""
    url = f"{BASE_URL}/cx-wechat-member/member/memGrade/queryPoint?flag=2"
    try:
        resp = api_get(url, session_id, device_id)
        obj  = (resp.get("data") or resp).get("obj") or {}
        return obj.get("usablePoint") or obj.get("totalPoint") or "?"
    except Exception as e:
        print(f"    查积分失败: {e}")
        return "?"


def do_sign(session_id, device_id):
    """执行签到，返回 (成功bool, 响应dict)"""
    # signInReq: POST /wechat-act/wxapp/signIn  无请求体
    url = f"{BASE_URL}/wechat-act/wxapp/signIn"
    try:
        resp = api_post(url, session_id, device_id, {})
        raw  = resp.get("data") or resp
        # 兼容 success/notSuccess 两种响应格式
        ok = (
            raw.get("success") is True
            or raw.get("notSuccess") is False
            or str(raw.get("success", "")).lower() == "true"
        )
        return ok, raw
    except urllib.error.HTTPError as e:
        body = e.read().decode(errors='replace')
        print(f"    HTTP {e.code}: {body[:300]}")
        return False, {"error": f"HTTP {e.code}", "body": body}
    except Exception as e:
        print(f"    签到请求异常: {e}")
        return False, {"error": str(e)}


def checkin(session_id, openid, device_id, account_idx):
    print(f"\n账号 {account_idx}: sessionId={session_id[:8]}... openid={openid[:8]}...")

    # 1. 查签到前积分
    before_point = query_point(session_id, device_id)
    print(f"  签到前积分: {before_point}")

    # 2. 查当前签到状态
    signed, cont_days, today_pt = query_sign_status(session_id, device_id)
    if signed is True:
        print(f"  今日已签到（连续 {cont_days} 天，今日 +{today_pt} 积分）")
        return True, before_point

    # 3. 执行签到
    ok, raw = do_sign(session_id, device_id)
    print(f"  签到响应: {json.dumps(raw, ensure_ascii=False)[:300]}")

    if ok:
        # 4. 签到后再查一次状态
        time.sleep(1)
        _, cont_days2, today_pt2 = query_sign_status(session_id, device_id)
        after_point = query_point(session_id, device_id)
        print(f"  ✅ 签到成功！连续 {cont_days2} 天，+{today_pt2} 积分，当前积分: {after_point}")
    else:
        print(f"  ❌ 签到失败")

    return ok, before_point


def main():
    raw_env = os.environ.get("SF_WXAPP_SESSION", "").strip()
    if not raw_env:
        print("❌ 未设置 SF_WXAPP_SESSION 环境变量")
        print("   格式: sessionId|openid|deviceId")
        print("   多账号: 用 & 或换行分隔")
        return

    accounts = [a.strip() for a in raw_env.replace("\n", "&").split("&") if a.strip()]
    results  = []

    for idx, acc in enumerate(accounts, 1):
        parts = acc.split("|")
        if len(parts) < 2:
            print(f"账号 {idx}: 格式错误，需要 sessionId|openid 或 sessionId|openid|deviceId")
            results.append((idx, False, "格式错误"))
            continue

        session_id = parts[0].strip()
        openid     = parts[1].strip()
        device_id  = parts[2].strip() if len(parts) > 2 else "1773021344379-3684218-075bf42e54dd28-20450407"

        try:
            ok, before = checkin(session_id, openid, device_id, idx)
            results.append((idx, ok, before))
        except Exception as e:
            print(f"账号 {idx}: 意外错误: {e}")
            results.append((idx, False, "?"))

    print("\n" + "=" * 40)
    print("签到结果汇总")
    print("=" * 40)
    for idx, ok, before in results:
        status = "✅ 成功" if ok else "❌ 失败"
        print(f"账号 {idx}: {status}  (签到前积分: {before})")


if __name__ == "__main__":
    main()
