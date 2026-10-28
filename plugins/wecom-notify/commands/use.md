---
description: "选择本次对话的完成提醒推送到哪里：wecom / feishu / all / none"
argument-hint: "[wecom|feishu|all|none]"
allowed-tools: ["Bash(python3 \"${CLAUDE_PLUGIN_ROOT}/scripts/wecom.py\":*)"]
---

```!
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/wecom.py" use "${CLAUDE_SESSION_ID}" $ARGUMENTS
```

把上面命令的输出原样告诉用户，不要做其他操作。
