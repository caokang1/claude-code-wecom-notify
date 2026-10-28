---
description: "配置企业微信群机器人 Webhook 地址，并发送一条测试消息"
argument-hint: "https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=..."
allowed-tools: ["Bash(python3 ${CLAUDE_PLUGIN_ROOT}/scripts/wecom.py:*)"]
---

```!
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/wecom.py" setup "$ARGUMENTS"
```

把上面命令的输出原样告诉用户，不要做其他操作。
