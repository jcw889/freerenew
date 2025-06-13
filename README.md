# Freecloud 自动续费脚本

这个脚本可以自动检查并续费您的 Freecloud 服务器实例，并通过 Telegram 发送通知。

## 功能特点

- 自动登录 Freecloud 账户
- 自动解决数学验证码
- 检查服务器剩余天数
- 当剩余天数低于阈值时自动续费
- 通过 Telegram 发送通知消息
- 在 GitHub Actions 上定时运行

## 环境变量设置

脚本需要以下环境变量：

| 环境变量 | 描述 |
|---------|------|
| `FC_USERNAME` | Freecloud 账号用户名 |
| `FC_PASSWORD` | Freecloud 账号密码 |
| `FC_MACHINE_ID` | 需要续费的服务器 ID |
| `TELEGRAM_BOT_TOKEN` | Telegram 机器人 Token（可选，但推荐设置） |
| `TELEGRAM_CHAT_ID` | Telegram 聊天 ID（可选，但推荐设置） |
| `DEBUG_MODE` | 设置为 `true` 可以开启详细日志（可选） |

## 在 GitHub 上部署

1. Fork 这个仓库
2. 在仓库的 Settings -> Secrets and variables -> Actions 中添加上述环境变量
3. Actions 标签页中启用工作流
4. 工作流会按照预定计划（每天UTC 22:00，对应北京时间早上6:00）自动运行
5. 也可以在 Actions 标签页手动触发工作流

## 本地运行

如果需要在本地运行，请执行以下步骤：

1. 克隆仓库
2. 安装依赖：`pip install -r requirements.txt`
3. 设置环境变量
4. 运行脚本：`python freecloud_renewer.py`

## 注意事项

- 脚本会在服务器剩余天数少于3天时进行续费
- 如遇到登录问题，请确认账号密码正确
- 如果验证码识别失败，脚本会自动报错并通知 