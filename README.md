# wecom-notify：Claude Code 完成提醒推送到企业微信 / 飞书

给 Claude Code 布置完任务就可以离开电脑。它回答完以后，你的企业微信或飞书会收到一条提醒：

```
✅ Claude 已完成
项目：/home/you/code/my-app
回答摘要：已经把登录页的表单校验改好了，主要改动有三处……
```

## 安装（3 分钟）

### 1. 建一个群机器人

企业微信和飞书任选一个，也可以两个都配。

**企业微信**

1. 在企业微信里建一个群。企业微信建群至少需要 3 个人，可以拉两位同事进来，再请他们把群设成「消息免打扰」。
2. 打开群聊右上角的 **…**，点 **群机器人**，然后点 **添加机器人**，新建一个机器人。
3. 复制它的 **Webhook 地址**，格式是 `https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=...`。

**飞书**（个人用手机号注册即可，不需要公司账号）

1. 在飞书里建一个群。
2. 打开 **群设置**，点 **群机器人**，然后点 **添加机器人**，选择 **自定义机器人**。
3. 复制它的 **Webhook 地址**，格式是 `https://open.feishu.cn/open-apis/bot/v2/hook/...`（海外版 Lark 是 `open.larksuite.com`）。
4. 安全设置建议勾选 **签名校验**，并复制密钥。如果选的是 **自定义关键词**，关键词填 `Claude`。

### 2. 在 Claude Code 里安装插件

```
/plugin marketplace add caokang1/claude-code-wecom-notify
/plugin install wecom-notify@claude-code-wecom-notify
```

装好后重启一下 Claude Code。

### 3. 填入 Webhook 地址

```
# 企业微信
/wecom-notify:setup https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=你的key

# 飞书（开启了签名校验就在后面加上密钥，没开就只填地址）
/wecom-notify:setup https://open.feishu.cn/open-apis/bot/v2/hook/你的token 你的密钥
```

命令会自动识别是企业微信还是飞书，先发一条测试消息，你在群里收到后就配置好了。

### 每次对话选择推送到哪里

企业微信和飞书都配置后，默认两边都会收到提醒。每次开启新对话时，Claude Code 会提示本次推送到哪里：

```
🔔 本次对话完成提醒推送到：企业微信、飞书。切换请运行 /wecom-notify:use <wecom / feishu / all / none>
```

想换就在这次对话里运行一下，只对当前对话生效，不影响其他窗口：

```
/wecom-notify:use feishu    # 只推飞书
/wecom-notify:use wecom     # 只推企业微信
/wecom-notify:use none      # 这次对话不推送
```

想改默认值，可以设置环境变量 `WECOM_NOTIFY_CHANNEL`，比如 `WECOM_NOTIFY_CHANNEL=feishu claude`。

## 常用命令

| 命令 | 作用 |
|------|------|
| `/wecom-notify:setup <地址> [飞书密钥]` | 保存或更换 Webhook 地址，同时发一条测试消息 |
| `/wecom-notify:use <wecom\|feishu\|all\|none>` | 选择本次对话推送到哪里，不带参数则查看当前选择 |
| `/wecom-notify:test` | 向所有已配置的群发一条测试消息 |
| `/wecom-notify:off` | 删除所有已保存的地址，停止推送 |
| `/wecom-notify:off feishu` | 只关闭飞书（或 `wecom` 只关闭企业微信） |
| `/plugin uninstall wecom-notify` | 卸载插件 |

## 高级设置

| 环境变量 | 作用 |
|----------|------|
| `WECOM_WEBHOOK_URL` | 直接用环境变量指定企业微信 Webhook 地址，优先级高于 setup 保存的地址 |
| `FEISHU_WEBHOOK_URL` | 直接用环境变量指定飞书 Webhook 地址 |
| `FEISHU_SECRET` | 飞书签名校验密钥 |
| `WECOM_NOTIFY_CHANNEL` | 新对话默认推送到哪里：`wecom`、`feishu`、`all`（默认）或 `none` |
| `WECOM_NOTIFY_CHARS` | 回答摘要的字数，默认 200；设为 0 则只发项目目录，不发回答内容 |

Webhook 地址和密钥保存在 `~/.claude/wecom-notify.json`，文件权限为仅本人可读写。每次对话的推送选择保存在 `~/.claude/wecom-notify-sessions.json`，超过 30 天的记录会自动清理。1.0 版本保存的企业微信地址会自动沿用，无需重新配置。

## 注意事项

- **隐私**：回答摘要会发到企业微信或飞书群里，群里的其他人也能看到。处理敏感代码时请留意。
- **Webhook 地址相当于密码**：拿到这个地址的人都能往群里发消息。不要把它提交到代码仓库或公开贴出来。
- **发送失败不影响使用**：比如断网时，提醒会静默跳过，Claude Code 照常工作。

## 系统要求

- Claude Code（需要支持插件）
- `python3`，只用到标准库，不需要安装任何依赖
- macOS、Linux、WSL。原生 Windows 暂未测试

## License

MIT
