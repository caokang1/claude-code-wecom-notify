---
description: "删除已保存的 Webhook 地址，停止推送"
allowed-tools: ["Bash(python3 ${CLAUDE_PLUGIN_ROOT}/scripts/wecom.py:*)"]
---

```!
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/wecom.py" off
```

把上面命令的输出原样告诉用户，不要做其他操作。
