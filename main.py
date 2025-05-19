import cloudscraper
import os
import requests

# ===================== 你的 Telegram 配置（环境变量） =====================
# 在环境变量中设置：
#   TELEGRAM_BOT_TOKEN：你的Bot Token
#   TELEGRAM_CHAT_ID：你的聊天ID

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")   # 电报TOKEN                          
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")       # 电报ID                  

# 其他凭证（环境变量）
USERNAME = os.getenv("FC_USERNAME")      # 用户名                    
PASSWORD = os.getenv("FC_PASSWORD")      # 密码                
MACHINE_ID = os.getenv("FC_MACHINE_ID")  # 服务器编号                          

# 检查所有关键环境变量是否已正确设置
if not all([BOT_TOKEN, CHAT_ID, USERNAME, PASSWORD, MACHINE_ID]):
    raise ValueError("请确认所有环境变量已正确设置：\n"
                     "TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID, FC_USERNAME, FC_PASSWORD, FC_MACHINE_ID")

# 定义请求的URL
LOGIN_URL = "https://freecloud.ltd/login"
CONSOLE_URL = "https://freecloud.ltd/member/index"
RENEW_URL = f"https://freecloud.ltd/server/detail/{MACHINE_ID}/renew"

# 请求头，模拟浏览器行为
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) "
                  "Chrome/122.0.0.0 Safari/537.36",
    "Referer": "https://freecloud.ltd/login",
    "Origin": "https://freecloud.ltd",
    "Content-Type": "application/x-www-form-urlencoded"
}

# 登录表单内容
LOGIN_PAYLOAD = {
    "username": USERNAME,
    "password": PASSWORD,
    "mobile": "",
    "captcha": "",
    "verify_code": "",
    "agree": "1",
    "login_type": "PASS",
    "submit": "1",
}

# 续费表单内容
RENEW_PAYLOAD = {
    "month": "1",
    "submit": "1",
    "coupon_id": 0
}


def send_telegram_message(bot_token, chat_id, message):
    """通过Telegram机器人发送消息"""
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": message,
        "parse_mode": "Markdown"
    }
    try:
        response = requests.post(url, data=payload)
        response.raise_for_status()
        print("Telegram通知已成功发送")
    except Exception as e:
        print(f"Telegram通知失败: {e}")


def login_session():
    """模拟登录，返回带Cookie的会话"""
    scraper = cloudscraper.create_scraper(
        browser={"browser": "chrome", "platform": "windows", "mobile": False}    
    )

    # 登录
    response = scraper.post(LOGIN_URL, data=LOGIN_PAYLOAD, headers=HEADERS, allow_redirects=True)
    response.raise_for_status()

    # 访问控制台页面，激活会话
    console_resp = scraper.get(CONSOLE_URL)
    console_resp.raise_for_status()

    return scraper


def renew_server(session):
    """使用登录的会话续费服务器"""
    response = session.post(RENEW_URL, data=RENEW_PAYLOAD, headers=HEADERS)
    response.raise_for_status()

    try:
        resp_json = response.json()
        print("续费结果:", resp_json.get("msg", "成功"))
        return resp_json.get("msg", "续费成功")
    except:
        print("返回非JSON内容，原始响应：")
        print(response.text)
        return "续费成功（内容非JSON）"


if __name__ == "__main__":
    try:
        print("开始登录...")
        session = login_session()
        print("登录成功，开始续费...")
        msg = renew_server(session)
        print("续费完成，准备通知Telegram...")
        send_telegram_message(BOT_TOKEN, CHAT_ID, f"🟢 续费成功！\n{msg}")
    except Exception as e:
        print("发生错误:", e)
        send_telegram_message(BOT_TOKEN, CHAT_ID, f"❗️ 续费失败：{e}")
