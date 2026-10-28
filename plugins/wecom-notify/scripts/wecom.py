#!/usr/bin/env python3
"""wecom-notify: Claude Code 回答完成后推送到企业微信群机器人。

用法：
  wecom.py notify        作为 Stop 钩子运行，从 stdin 读取钩子数据
  wecom.py setup <URL>   保存 Webhook 地址并发送一条测试消息
  wecom.py test          向已保存的地址发送一条测试消息
  wecom.py off           删除已保存的地址，停止推送

Webhook 地址读取顺序：环境变量 WECOM_WEBHOOK_URL > ~/.claude/wecom-notify.json
"""
import json
import os
import sys
import urllib.request

CONFIG_FILE = os.path.expanduser("~/.claude/wecom-notify.json")
URL_PREFIX = "https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key="
SUMMARY_CHARS = int(os.environ.get("WECOM_NOTIFY_CHARS", "200"))


def load_webhook():
    url = os.environ.get("WECOM_WEBHOOK_URL", "").strip()
    if url:
        return url
    try:
        with open(CONFIG_FILE, encoding="utf-8") as f:
            return json.load(f).get("webhook", "").strip()
    except (OSError, ValueError):
        return ""


def mask(url):
    return url[:len(URL_PREFIX) + 4] + "****" if url.startswith(URL_PREFIX) else "****"


def send(url, content):
    body = json.dumps({"msgtype": "text", "text": {"content": content}}).encode("utf-8")
    req = urllib.request.Request(url, data=body, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=5) as resp:
        result = json.loads(resp.read().decode("utf-8"))
    if result.get("errcode") != 0:
        raise RuntimeError("企业微信返回错误：{} {}".format(result.get("errcode"), result.get("errmsg")))


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
        url = load_webhook()
        if not url:
            return 0
        data = json.load(sys.stdin)
        summary = last_assistant_text(data)
        if len(summary) > SUMMARY_CHARS:
            summary = summary[:SUMMARY_CHARS] + "…"
        send(url, "✅ Claude 已完成\n项目：{}\n回答摘要：{}".format(
            data.get("cwd") or os.getcwd(), summary or "（无文字回答）"))
    except Exception:
        pass
    return 0


def cmd_setup(args):
    url = args[0].strip().strip("'\"") if args else ""
    if not url.startswith(URL_PREFIX):
        print("❌ 地址格式不对，应该形如：{}xxxxxxxx-xxxx-...".format(URL_PREFIX))
        print("   在企业微信群聊 → 右上角“…” → 群机器人 → 添加机器人，复制 Webhook 地址。")
        return 1
    try:
        send(url, "🔔 wecom-notify 配置成功，Claude Code 回答完成后会在这里提醒你。")
    except Exception as e:
        print("❌ 测试消息发送失败，地址没有保存：{}".format(e))
        return 1
    os.makedirs(os.path.dirname(CONFIG_FILE), exist_ok=True)
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump({"webhook": url}, f)
    os.chmod(CONFIG_FILE, 0o600)
    print("✅ 已保存 Webhook（{}），测试消息已发送，去企业微信群里看看吧。".format(mask(url)))
    return 0


def cmd_test():
    url = load_webhook()
    if not url:
        print("❌ 还没有配置 Webhook，先运行 /wecom-notify:setup <地址>")
        return 1
    try:
        send(url, "🔔 wecom-notify 测试消息")
    except Exception as e:
        print("❌ 发送失败：{}".format(e))
        return 1
    print("✅ 测试消息已发送到 {}".format(mask(url)))
    return 0


def cmd_off():
    try:
        os.remove(CONFIG_FILE)
        print("✅ 已删除 Webhook 配置，不会再推送。重新开启请运行 /wecom-notify:setup <地址>")
    except FileNotFoundError:
        print("当前没有保存的 Webhook 配置。")
    if os.environ.get("WECOM_WEBHOOK_URL"):
        print("⚠️ 环境变量 WECOM_WEBHOOK_URL 仍然设置着，推送会继续，需要你自己删除它。")
    return 0


def main(argv):
    cmd = argv[0] if argv else ""
    if cmd == "notify":
        return cmd_notify()
    if cmd == "setup":
        return cmd_setup(argv[1:])
    if cmd == "test":
        return cmd_test()
    if cmd == "off":
        return cmd_off()
    print(__doc__)
    return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
