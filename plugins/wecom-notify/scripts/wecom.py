#!/usr/bin/env python3
"""wecom-notify: Claude Code 回答完成后推送到企业微信 / 飞书群机器人。

用法：
  wecom.py notify                 作为 Stop 钩子运行，从 stdin 读取钩子数据
  wecom.py session-start          作为 SessionStart 钩子运行，提示本次对话推送到哪里
  wecom.py use <会话ID> <渠道>     指定本次对话推送到哪里：wecom / feishu / all / none
  wecom.py setup <URL> [签名密钥]  保存 Webhook 地址并发送一条测试消息（飞书开启签名校验时需填密钥）
  wecom.py test                   向所有已保存的地址发送一条测试消息
  wecom.py off [wecom|feishu]     删除已保存的地址，停止推送（不带参数则全部删除）

每个渠道最多保存一个地址，企业微信和飞书可以同时开启。
地址读取顺序：环境变量 > ~/.claude/wecom-notify.json
  企业微信：WECOM_WEBHOOK_URL
  飞书：    FEISHU_WEBHOOK_URL、FEISHU_SECRET
推送渠道：本次对话用 use 选择的渠道 > 环境变量 WECOM_NOTIFY_CHANNEL > 全部已配置的渠道
"""
import base64
import hashlib
import hmac
import json
import os
import sys
import time
import urllib.request

CONFIG_FILE = os.path.expanduser("~/.claude/wecom-notify.json")
SESSIONS_FILE = os.path.expanduser("~/.claude/wecom-notify-sessions.json")
SESSION_KEEP_SECONDS = 30 * 24 * 3600
WECOM_MAX_BYTES = 2048  # 企业微信文本消息上限，超出会被整条拒收


def env_int(name, default):
    try:
        return max(0, int(os.environ.get(name, default)))
    except ValueError:
        return default


SUMMARY_CHARS = env_int("WECOM_NOTIFY_CHARS", 200)


def write_private(path, data):
    """原子写入并且从一开始就是 0600，避免写到一半被读到或短暂对他人可读。"""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = "{}.{}.tmp".format(path, os.getpid())
    fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False)
    os.replace(tmp, path)


def post_json(url, payload):
    body = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=body, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=5) as resp:
        return json.loads(resp.read().decode("utf-8"))


def send_wecom(hook, content):
    if len(content.encode("utf-8")) > WECOM_MAX_BYTES:
        content = content.encode("utf-8")[:WECOM_MAX_BYTES - 3].decode("utf-8", "ignore") + "…"
    result = post_json(hook["url"], {"msgtype": "text", "text": {"content": content}})
    if result.get("errcode") != 0:
        raise RuntimeError("企业微信返回错误：{} {}".format(result.get("errcode"), result.get("errmsg")))


def send_feishu(hook, content):
    payload = {"msg_type": "text", "content": {"text": content}}
    secret = hook.get("secret")
    if secret:
        # 飞书签名：以 "时间戳\n密钥" 为 key，对空字符串做 HmacSHA256，再 Base64
        timestamp = str(int(time.time()))
        key = "{}\n{}".format(timestamp, secret).encode("utf-8")
        payload["timestamp"] = timestamp
        payload["sign"] = base64.b64encode(hmac.new(key, digestmod=hashlib.sha256).digest()).decode()
    result = post_json(hook["url"], payload)
    # 新接口返回 code，旧接口返回 StatusCode
    code = result.get("code", result.get("StatusCode"))
    if code != 0:
        raise RuntimeError("飞书返回错误：{} {}".format(code, result.get("msg") or result.get("StatusMessage")))


CHANNELS = {
    "wecom": {
        "name": "企业微信",
        "prefixes": ["https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key="],
        "env": "WECOM_WEBHOOK_URL",
        "send": send_wecom,
    },
    "feishu": {
        "name": "飞书",
        "prefixes": ["https://open.feishu.cn/open-apis/bot/v2/hook/",
                     "https://open.larksuite.com/open-apis/bot/v2/hook/"],
        "env": "FEISHU_WEBHOOK_URL",
        "secret_env": "FEISHU_SECRET",
        "send": send_feishu,
    },
}


def detect_channel(url):
    for key, ch in CHANNELS.items():
        if any(url.startswith(p) for p in ch["prefixes"]):
            return key
    return ""


def load_config():
    try:
        with open(CONFIG_FILE, encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, ValueError):
        return {}
    if not isinstance(data, dict):
        return {}
    hooks = data.get("hooks")
    if isinstance(hooks, dict):
        return {k: v for k, v in hooks.items() if isinstance(v, dict)}
    # 兼容 1.0 版本的配置：{"webhook": "企业微信地址"}
    url = data.get("webhook")
    return {"wecom": {"url": url.strip()}} if isinstance(url, str) and url.strip() else {}


def save_config(hooks):
    if not hooks:
        try:
            os.remove(CONFIG_FILE)
        except FileNotFoundError:
            pass
        return
    data = {"hooks": hooks}
    if "wecom" in hooks:
        # 同时保留 1.0 版本的字段，未升级的插件也能继续推送企业微信
        data["webhook"] = hooks["wecom"]["url"]
    write_private(CONFIG_FILE, data)


def load_hooks():
    """返回 {渠道: {"url": ..., "secret": ...}}，环境变量优先于配置文件。"""
    hooks = load_config()
    for key, ch in CHANNELS.items():
        url = os.environ.get(ch["env"], "").strip()
        if url:
            hook = {"url": url}
            secret = os.environ.get(ch.get("secret_env", ""), "").strip()
            if secret:
                hook["secret"] = secret
            hooks[key] = hook
    return {k: v for k, v in hooks.items() if k in CHANNELS and v.get("url")}


def load_sessions():
    try:
        with open(SESSIONS_FILE, encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}


def default_choice():
    choice = os.environ.get("WECOM_NOTIFY_CHANNEL", "").strip().lower()
    return choice if choice in CHANNELS or choice == "none" else "all"


def session_choice(session_id):
    """返回本次对话的推送选择：渠道名、"all" 或 "none"。"""
    entry = load_sessions().get(session_id) if session_id else None
    if isinstance(entry, dict) and entry.get("choice"):
        return entry["choice"]
    return default_choice()


def select_hooks(hooks, choice):
    if choice == "all":
        return hooks
    return {k: v for k, v in hooks.items() if k == choice}


def describe(hooks, choice):
    if choice == "none":
        return "不推送"
    names = [CHANNELS[k]["name"] for k in select_hooks(hooks, choice)]
    return "、".join(names) if names else "不推送（{}未配置）".format(CHANNELS[choice]["name"])


def mask(url):
    for ch in CHANNELS.values():
        for p in ch["prefixes"]:
            if url.startswith(p):
                return url[:len(p) + 4] + "****"
    return "****"


def broadcast(hooks, content):
    """逐个渠道发送，单个渠道失败不影响其他渠道。返回 [(渠道, 错误或 None)]。"""
    results = []
    for key, hook in hooks.items():
        try:
            CHANNELS[key]["send"](hook, content)
            results.append((key, None))
        except Exception as e:
            results.append((key, e))
    return results


def last_assistant_text(data):
    # 较新版本的 Claude Code 会直接给出最后一条回答
    text = data.get("last_assistant_message")
    if isinstance(text, str) and text.strip():
        return text.strip()

    path = data.get("transcript_path")
    if not path or not os.path.exists(path):
        return ""
    last = ""
    with open(path, encoding="utf-8") as f:
        for line in f:
            try:
                entry = json.loads(line)
            except ValueError:
                continue
            if entry.get("type") != "assistant":
                continue
            content = entry.get("message", {}).get("content", [])
            if isinstance(content, str):
                parts = [content]
            else:
                parts = [c.get("text", "") for c in content
                         if isinstance(c, dict) and c.get("type") == "text"]
            joined = "\n".join(p for p in parts if p).strip()
            if joined:
                last = joined
    return last


def cmd_notify():
    # 钩子模式：任何错误都静默跳过，绝不影响 Claude 正常工作
    try:
        hooks = load_hooks()
        if not hooks:
            return 0
        data = json.load(sys.stdin)
        hooks = select_hooks(hooks, session_choice(data.get("session_id")))
        if not hooks:
            return 0
        content = "✅ Claude 已完成\n项目：{}".format(data.get("cwd") or os.getcwd())
        if SUMMARY_CHARS:
            summary = last_assistant_text(data)
            if len(summary) > SUMMARY_CHARS:
                summary = summary[:SUMMARY_CHARS] + "…"
            content += "\n回答摘要：{}".format(summary or "（无文字回答）")
        broadcast(hooks, content)
    except Exception:
        pass
    return 0


def cmd_session_start():
    # 钩子模式：配置了多个渠道时，在对话开始时提示本次推送到哪里
    try:
        hooks = load_hooks()
        data = json.load(sys.stdin)
        if len(hooks) < 2 or data.get("source") == "compact":
            return 0
        current = describe(hooks, session_choice(data.get("session_id")))
        options = " / ".join(list(hooks) + ["all", "none"])
        print(json.dumps({"systemMessage": "🔔 本次对话完成提醒推送到：{}。切换请运行 /wecom-notify:use <{}>".format(
            current, options)}, ensure_ascii=False))
    except Exception:
        pass
    return 0


def cmd_use(args):
    session_id = args[0].strip() if args else ""
    choice = " ".join(args[1:]).strip().lower()
    hooks = load_hooks()
    valid = list(CHANNELS) + ["all", "none"]
    if not choice:
        print("本次对话推送到：{}".format(describe(hooks, session_choice(session_id))))
        print("切换请运行 /wecom-notify:use <{}>".format(" / ".join(valid)))
        return 0
    if choice not in valid:
        print("❌ 不认识的选项：{}，可选：{}".format(choice, " / ".join(valid)))
        return 1
    if choice in CHANNELS and choice not in hooks:
        print("❌ {}还没有配置，先运行 /wecom-notify:setup <地址>".format(CHANNELS[choice]["name"]))
        return 1
    if not session_id or session_id.startswith("${"):
        print("❌ 拿不到当前对话的 ID，请升级 Claude Code 后再试。")
        return 1
    now = int(time.time())
    sessions = {k: v for k, v in load_sessions().items()
                if isinstance(v, dict) and now - v.get("time", 0) < SESSION_KEEP_SECONDS}
    sessions[session_id] = {"choice": choice, "time": now}
    write_private(SESSIONS_FILE, sessions)
    print("✅ 本次对话完成提醒推送到：{}".format(describe(hooks, choice)))
    return 0


def cmd_setup(args):
    # 斜杠命令把参数整体作为一个字符串传进来，这里重新按空白切分
    parts = [a.strip("'\"") for a in " ".join(args).split()]
    url = parts[0] if parts else ""
    secret = parts[1] if len(parts) > 1 else ""
    key = detect_channel(url)
    if not key:
        print("❌ 地址格式不对，支持以下两种：")
        print("   企业微信：{}xxxxxxxx-xxxx-...".format(CHANNELS["wecom"]["prefixes"][0]))
        print("   飞书：    {}xxxxxxxx-xxxx-...".format(CHANNELS["feishu"]["prefixes"][0]))
        print("   企业微信：群聊 → 右上角“…” → 群机器人 → 添加机器人，复制 Webhook 地址。")
        print("   飞书：    群设置 → 群机器人 → 添加机器人 → 自定义机器人，复制 Webhook 地址。")
        return 1
    if secret and key != "feishu":
        print("❌ 只有飞书机器人需要签名密钥，企业微信只填地址即可。")
        return 1
    name = CHANNELS[key]["name"]
    hook = {"url": url}
    if secret:
        hook["secret"] = secret
    try:
        CHANNELS[key]["send"](hook, "🔔 wecom-notify 配置成功，Claude Code 回答完成后会在这里提醒你。")
    except Exception as e:
        print("❌ 测试消息发送失败，地址没有保存：{}".format(e))
        if key == "feishu" and not secret:
            print("   如果机器人开启了签名校验，请把密钥加在地址后面：/wecom-notify:setup <地址> <密钥>")
        return 1
    hooks = load_config()
    hooks[key] = hook
    save_config(hooks)
    print("✅ 已保存{} Webhook（{}），测试消息已发送，去{}群里看看吧。".format(name, mask(url), name))
    if os.environ.get(CHANNELS[key]["env"], "").strip():
        print("⚠️ 环境变量 {} 已设置，推送时会优先使用它，而不是刚保存的地址。".format(CHANNELS[key]["env"]))
    others = [CHANNELS[k]["name"] for k in hooks if k != key and k in CHANNELS]
    if others:
        print("   {}也仍在推送，如需关闭请运行 /wecom-notify:off <渠道>".format("、".join(others)))
    return 0


def cmd_test():
    hooks = load_hooks()
    if not hooks:
        print("❌ 还没有配置 Webhook，先运行 /wecom-notify:setup <地址>")
        return 1
    failed = False
    for key, err in broadcast(hooks, "🔔 wecom-notify 测试消息"):
        name = CHANNELS[key]["name"]
        if err:
            failed = True
            print("❌ {}发送失败：{}".format(name, err))
        else:
            print("✅ 测试消息已发送到{}（{}）".format(name, mask(hooks[key]["url"])))
    return 1 if failed else 0


def cmd_off(args):
    target = " ".join(args).strip()
    hooks = load_config()
    if target:
        if target not in CHANNELS:
            print("❌ 不认识的渠道：{}，可选：{}".format(target, " / ".join(CHANNELS)))
            return 1
        keys = [target]
    else:
        keys = list(CHANNELS)
    removed = [CHANNELS[k]["name"] for k in keys if hooks.pop(k, None)]
    save_config(hooks)
    if removed:
        print("✅ 已删除{}的 Webhook 配置，不会再推送。重新开启请运行 /wecom-notify:setup <地址>".format(
            "、".join(removed)))
    else:
        print("当前没有保存的 Webhook 配置。")
    for k in keys:
        if os.environ.get(CHANNELS[k]["env"]):
            print("⚠️ 环境变量 {} 仍然设置着，推送会继续，需要你自己删除它。".format(CHANNELS[k]["env"]))
    return 0


def main(argv):
    cmd = argv[0] if argv else ""
    if cmd == "notify":
        return cmd_notify()
    if cmd == "session-start":
        return cmd_session_start()
    if cmd == "use":
        return cmd_use(argv[1:])
    if cmd == "setup":
        return cmd_setup(argv[1:])
    if cmd == "test":
        return cmd_test()
    if cmd == "off":
        return cmd_off(argv[1:])
    print(__doc__)
    return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
