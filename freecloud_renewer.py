import cloudscraper
import os
import requests
import re
import json
import time
import traceback

# ===================== Telegram 配置 (从环境变量读取) =====================
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

# ===================== Freecloud 凭证 (从环境变量读取) =====================
FC_USERNAME = os.getenv("FC_USERNAME")
FC_PASSWORD = os.getenv("FC_PASSWORD")
FC_MACHINE_ID = os.getenv("FC_MACHINE_ID")  # 这是您要续费的服务器的 ID (对应 id_sn)

# ===================== 日志和调试 =====================
DEBUG_MODE = os.getenv("DEBUG_MODE", "False").lower() == "true" # 可选：设置 DEBUG_MODE=True 开启更详细日志

def log_message(message, is_debug=False):
    """打印日志信息"""
    if is_debug and not DEBUG_MODE:
        return
    print(message)

# ===================== 基本配置检查 =====================
def check_env_vars():
    """检查所有关键环境变量是否已正确设置"""
    required_vars = {
        "TELEGRAM_BOT_TOKEN": BOT_TOKEN,
        "TELEGRAM_CHAT_ID": CHAT_ID,
        "FC_USERNAME": FC_USERNAME,
        "FC_PASSWORD": FC_PASSWORD,
        "FC_MACHINE_ID": FC_MACHINE_ID
    }
    missing_vars = [name for name, value in required_vars.items() if not value]
    if missing_vars:
        error_msg = f"错误：以下环境变量未设置或为空: {', '.join(missing_vars)}\n" \
                    "请确保在运行环境正确设置了所有必需的环境变量。"
        log_message(error_msg)
        # 如果配置了Telegram，尝试发送错误通知
        if BOT_TOKEN and CHAT_ID:
            try:
                # 简化版发送，避免循环依赖 send_telegram_message
                url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
                payload = {"chat_id": CHAT_ID, "text": f"脚本启动失败: {error_msg}", "parse_mode": "Markdown"}
                requests.post(url, data=payload, timeout=10)
            except Exception as e:
                log_message(f"尝试发送启动失败通知到Telegram也失败了: {e}")
        raise ValueError(error_msg)
    log_message("所有关键环境变量已加载。")

# ===================== 全局常量 =====================
BASE_URL = "https://freecloud.ltd"
CONSOLE_URL = f"{BASE_URL}/server/lxc"  # 直接访问服务器列表页面
# 续费URL会动态构建，因为 MACHINE_ID 是变量

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) "
                  "Chrome/122.0.0.0 Safari/537.36",
    "Referer": f"{BASE_URL}/login",
    "Origin": BASE_URL,
    "Content-Type": "application/x-www-form-urlencoded"
}

# ===================== Telegram 通知功能 =====================
def send_telegram_message(message, is_error=False):
    """通过Telegram机器人发送消息"""
    if not BOT_TOKEN or not CHAT_ID:
        log_message("Telegram BOT_TOKEN 或 CHAT_ID 未配置，跳过发送通知。")
        return

    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": CHAT_ID,
        "text": message,
        "parse_mode": "Markdown" # 允许简单的Markdown格式
    }
    try:
        response = requests.post(url, data=payload, timeout=15) # 增加超时
        response.raise_for_status() # 如果HTTP状态码是4xx或5xx，则抛出异常
        log_message("Telegram通知已成功发送。")
    except requests.exceptions.RequestException as e:
        log_message(f"Telegram通知失败 (请求异常): {e}")
    except Exception as e:
        log_message(f"Telegram通知发送时发生未知错误: {e}")

# ===================== 数学验证码处理 =====================
def get_math_captcha_solution(page_content):
    """
    从登录页面内容中提取并解决数学验证码
    例如：从 "5 + 7 = ?" 提取并计算出 12
    """
    try:
        # 使用正则表达式匹配类似 "5 + 7 = ?" 的验证码
        match = re.search(r'placeholder="([0-9]+)\s*([+\-*/])\s*([0-9]+)\s*=\s*\?"', page_content)
        if not match:
            log_message("⚠️ 未在页面中找到数学验证码")
            return None
        
        num1 = int(match.group(1))
        operator = match.group(2)
        num2 = int(match.group(3))
        
        log_message(f"找到数学验证码: {num1} {operator} {num2} = ?")
        
        # 计算结果
        if operator == '+':
            result = num1 + num2
        elif operator == '-':
            result = num1 - num2
        elif operator == '*':
            result = num1 * num2
        elif operator == '/':
            # 假设结果总是整数
            result = num1 // num2
        else:
            log_message(f"⚠️ 未知的运算符: {operator}")
            return None
        
        log_message(f"数学验证码计算结果: {result}")
        return result
    except Exception as e:
        log_message(f"解析数学验证码时出错: {e}")
        return None

# ===================== Freecloud 操作 =====================
def login_session():
    """
    模拟登录到 Freecloud，返回一个带有登录会话的 cloudscraper 实例。
    """
    log_message("尝试登录 Freecloud...")
    scraper = cloudscraper.create_scraper(
        browser={"browser": "chrome", "platform": "windows", "mobile": False},
    )

    try:
        # 首先访问登录页面获取数学验证码
        log_message("访问登录页面获取数学验证码...")
        login_page_resp = scraper.get(f"{BASE_URL}/login", headers=HEADERS, timeout=30)
        login_page_resp.raise_for_status()
        
        # 解析数学验证码
        math_solution = get_math_captcha_solution(login_page_resp.text)
        if math_solution is None:
            log_message("❌ 无法解析数学验证码，登录可能会失败")
            send_telegram_message("⚠️ 无法解析数学验证码，登录可能会失败", is_error=True)
        
        # 准备登录数据
        login_data = {
            "username": FC_USERNAME,
            "password": FC_PASSWORD,
            "math_captcha": str(math_solution) if math_solution is not None else "",
            "mobile": "",
            "captcha": "",
            "verify_code": "",
            "agree": "1",
            "login_type": "PASS",
            "submit": "1"
        }
        
        log_message("准备登录数据完成，包含数学验证码解答")
        
        # 发送登录请求
        log_message(f"发送登录请求到: {BASE_URL}/login", is_debug=True)
        response = scraper.post(f"{BASE_URL}/login", data=login_data, headers=HEADERS, allow_redirects=True, timeout=30)
        response.raise_for_status()
        log_message(f"登录请求响应状态码: {response.status_code}", is_debug=True)
        log_message(f"登录请求响应URL: {response.url}", is_debug=True)

        log_message("访问控制台页面以验证登录状态...")
        console_resp = scraper.get(CONSOLE_URL, headers={**HEADERS, "Referer": f"{BASE_URL}/login"}, timeout=30)
        console_resp.raise_for_status()
        log_message(f"控制台页面响应状态码: {console_resp.status_code}", is_debug=True)

        if FC_USERNAME and FC_USERNAME.lower() in console_resp.text.lower():
             log_message("登录成功，在控制台页面找到用户名。")
        elif "logout" in console_resp.text.lower() or "退出登录" in console_resp.text:
            log_message("登录似乎成功（页面包含退出链接）。")
        else:
            # 检查是否登录失败，可能是验证码错误
            if "验证码" in console_resp.text or "重新登录" in console_resp.text:
                log_message("❌ 登录失败，可能是数学验证码计算错误")
                send_telegram_message("❌ 登录失败，可能是数学验证码计算错误", is_error=True)
                return None
                
            log_message("警告：登录请求已发送，但无法100%确认登录成功（未在控制台页面找到明确标识）。脚本将继续尝试。")
            log_message(f"控制台页面部分内容 (前500字符): {console_resp.text[:500]}", is_debug=True)

        return scraper
    except requests.exceptions.RequestException as e:
        log_message(f"登录 Freecloud 失败 (网络请求错误): {e}")
        raise
    except Exception as e:
        log_message(f"登录 Freecloud 时发生未知错误: {e}")
        raise

def get_server_info(session, machine_id_to_find):
    """
    通过HTML源码，先定位到服务器编号，再提取"X天后"。
    """
    log_message(f"尝试从 {CONSOLE_URL} 获取服务器 {machine_id_to_find} 的信息...")
    try:
        response = session.get(CONSOLE_URL, headers=HEADERS, timeout=30)
        response.raise_for_status()
        html = response.text

        # 1. 找到包含编号的区块（假设编号唯一）
        idx = html.find(str(machine_id_to_find))
        if idx != -1:
            snippet = html[max(0, idx-500):idx+500]
            match = re.search(r'(\d+)天后', snippet)
            if match:
                days_left = int(match.group(1))
                log_message(f"服务器 {machine_id_to_find} 剩余 {days_left} 天")
                return {"remaining_days": days_left, "id_sn": machine_id_to_find}
            else:
                log_message(f"未能在服务器 {machine_id_to_find} 附近找到"天后"信息")
                return None
        else:
            log_message(f"页面中未找到服务器编号 {machine_id_to_find}")
            return None
    except requests.exceptions.RequestException as e:
        log_message(f"获取服务器信息失败 (网络请求错误): {e}")
        return None
    except Exception as e:
        log_message(f"获取服务器信息时发生未知错误: {e}\n{traceback.format_exc() if DEBUG_MODE else ''}")
        return None

def renew_server_instance(session, server_id_sn):
    renew_url = f"{BASE_URL}/server/detail/{server_id_sn}/renew"
    log_message(f"尝试为服务器 {server_id_sn} 续费，请求 URL: {renew_url}")
    current_renew_payload = {
        "month": "1",
        "submit": "1",
        "coupon_id": "0" # 通常优惠券ID为0表示不使用或无效优惠券
    }
    try:
        renew_headers = {**HEADERS, "Referer": f"{BASE_URL}/server/detail/{server_id_sn}"}
        response = session.post(renew_url, data=current_renew_payload, headers=renew_headers, timeout=45)
        response.raise_for_status()
        try:
            resp_json = response.json()
            log_message(f"续费响应JSON: {resp_json}", is_debug=True)
            if resp_json.get("code") == 0:
                success_msg = resp_json.get("msg", "续费操作已提交，请稍后在网站确认状态。")
                log_message(f"续费成功信息: {success_msg}")
                return True, success_msg
            else:
                error_msg = resp_json.get("msg", "续费失败，未提供具体原因。")
                log_message(f"续费失败 (API返回错误): {error_msg} (code: {resp_json.get('code')})")
                return False, error_msg
        except json.JSONDecodeError:
            log_message("续费响应不是有效的JSON格式。检查原始响应文本。")
            log_message(f"续费响应原文 (前500字符): {response.text[:500]}", is_debug=True)
            if "success" in response.text.lower() or "成功" in response.text:
                 msg = "续费请求已发送，响应非JSON但包含成功字样。"
                 log_message(msg)
                 return True, msg
            return False, "续费失败，响应非JSON且未找到成功标识。"
    except requests.exceptions.RequestException as e:
        log_message(f"续费服务器 {server_id_sn} 失败 (网络请求错误): {e}")
        return False, f"网络请求错误: {e}"
    except Exception as e:
        log_message(f"续费服务器 {server_id_sn} 时发生未知错误: {e}\n{traceback.format_exc() if DEBUG_MODE else ''}")
        return False, f"未知错误: {e}"

def main():
    try:
        check_env_vars()
        log_message("脚本开始执行...")
        session = login_session()
        if not session:
            send_telegram_message("🔴 登录 Freecloud 失败，脚本终止。", is_error=True)
            return
        log_message(f"登录成功。开始检查服务器 {FC_MACHINE_ID} 的状态...")
        server_info_data = get_server_info(session, FC_MACHINE_ID)
        if not server_info_data:
            msg = f"⚠️ 未能获取服务器 {FC_MACHINE_ID} 的信息，无法继续续费操作。"
            log_message(msg)
            send_telegram_message(msg, is_error=True)
            return
        remaining_days = server_info_data["remaining_days"]
        server_id_sn = server_info_data["id_sn"]
        days_threshold = 3.0
        if remaining_days < days_threshold:
            log_message(f"服务器 {server_id_sn} 剩余 {remaining_days:.2f} 天 (少于 {days_threshold} 天)，需要续费。")
            send_telegram_message(f"⏳ 服务器 {server_id_sn} 剩余 {remaining_days:.2f} 天，尝试自动续费...", is_error=False)
            renew_success, renew_message = renew_server_instance(session, server_id_sn)
            if renew_success:
                final_message = f"✅ 服务器 {server_id_sn} 续费成功！\n续费结果: {renew_message}\n原剩余: {remaining_days:.2f} 天。"
                log_message(final_message)
                send_telegram_message(final_message)
                log_message("等待几秒后尝试重新获取服务器信息以确认续费...")
                time.sleep(10)
                updated_server_info = get_server_info(session, server_id_sn)
                if updated_server_info:
                    log_message(f"更新后服务器 {server_id_sn} 剩余天数: {updated_server_info['remaining_days']:.2f}")
                    send_telegram_message(f"ℹ️ 更新后服务器 {server_id_sn} 剩余: {updated_server_info['remaining_days']:.2f} 天。")
                else:
                    log_message("未能获取续费后的服务器信息。")
            else:
                final_message = f"❌ 服务器 {server_id_sn} 续费失败。\n失败原因: {renew_message}\n原剩余: {remaining_days:.2f} 天。"
                log_message(final_message)
                send_telegram_message(final_message, is_error=True)
        else:
            final_message = f"ℹ️ 服务器 {server_id_sn} 剩余 {remaining_days:.2f} 天 (多于或等于 {days_threshold} 天)，无需续费。"
            log_message(final_message)
            send_telegram_message(final_message)
    except ValueError as ve:
        log_message(f"脚本因配置错误终止: {ve}")
    except Exception as e:
        error_details = traceback.format_exc()
        full_error_message = f"🆘 脚本执行过程中发生意外总错误: {e}\n\n```
{error_details}\n```"
        log_message(full_error_message)
        send_telegram_message(full_error_message, is_error=True)
    finally:
        log_message("脚本执行完毕。")

if __name__ == "__main__":
    main() 