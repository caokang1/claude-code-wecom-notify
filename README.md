# wecom-notify：Claude Code 完成提醒推送到企业微信

给 Claude Code 布置完任务就可以离开电脑。它回答完以后，你的企业微信会收到一条提醒：

```
✅ Claude 已完成
项目：/home/you/code/my-app
回答摘要：已经把登录页的表单校验改好了，主要改动有三处……
```

## 安装（3 分钟）

### 1. 建一个企业微信群机器人

1. 在企业微信里建一个群。企业微信建群至少需要 3 个人，可以拉两位同事进来，再请他们把群设成「消息免打扰」。
2. 打开群聊右上角的 **…**，点 **群机器人**，然后点 **添加机器人**，新建一个机器人。
3. 复制它的 **Webhook 地址**，格式是 `https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=...`。

### 2. 在 Claude Code 里安装插件

```
/plugin marketplace add caokang1/claude-code-wecom-notify
/plugin install wecom-notify@claude-code-wecom-notify
```

装好后重启一下 Claude Code。

### 3. 填入 Webhook 地址

```
/wecom-notify:setup https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=你的key
```

命令会先发一条测试消息，你在群里收到后就配置好了。

## 常用命令

| 命令 | 作用 |
|------|------|
| `/wecom-notify:setup <地址>` | 保存或更换 Webhook 地址，同时发一条测试消息 |
| `/wecom-notify:test` | 发一条测试消息 |
| `/wecom-notify:off` | 删除已保存的地址，停止推送 |
| `/plugin uninstall wecom-notify` | 卸载插件 |

## 高级设置

| 环境变量 | 作用 |
|----------|------|
| `WECOM_WEBHOOK_URL` | 直接用环境变量指定 Webhook 地址，优先级高于 setup 保存的地址 |
| `WECOM_NOTIFY_CHARS` | 回答摘要的字数，默认 200 |

Webhook 地址保存在 `~/.claude/wecom-notify.json`，文件权限为仅本人可读写。

## 注意事项

- **隐私**：回答摘要会发到企业微信群里，群里的其他人也能看到。处理敏感代码时请留意。
- **Webhook 地址相当于密码**：拿到这个地址的人都能往群里发消息。不要把它提交到代码仓库或公开贴出来。
- **发送失败不影响使用**：比如断网时，提醒会静默跳过，Claude Code 照常工作。

## 系统要求

- Claude Code（需要支持插件）
- `python3`，只用到标准库，不需要安装任何依赖
- macOS、Linux、WSL。原生 Windows 暂未测试

## License

MIT
