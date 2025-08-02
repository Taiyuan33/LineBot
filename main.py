import requests
from flask import Flask, request
import google.generativeai as genai
import time
import yfinance as yf
import numpy as np
from datetime import datetime, timedelta
import pandas as pd

# 初始化 Flask 應用程式
app = Flask(__name__)

# 設定 LINE BOT Token
BOT_TOKEN = '+vm6Ej+RrfiUrqXmc++mWtxV0cErb6LJYsQzpqGF/dgi/2FkMfp6hV7PpxfSkodQi0xoGBSue7ytV0EhtM+kkxyluRj+BXAJssFfyQLhRL4tS8M2MWMg9eLiz/Ls0CUtzknaEB/5k0+cUOsUAnLphgdB04t89/1O/w1cDnyilFU='

# 設定 Google AI API 金鑰
genai.configure(api_key="AIzaSyA5PBFOSdPE1PCKQcERFMuSb2XoM4w8RD8"
                )  # 請將此處的 YOUR_GOOGLE_API_KEY 替換為你的 Google API 金鑰

# 設定流量管理
last_response_time = 0
response_interval = 3  # 每 3 秒鐘可以回應一次

# 用戶狀態管理
user_states = {}  # 儲存每個用戶的狀態


# 傳送文字訊息函數
def send_text_message(reply_token, text):
    headers = {
        "Content-Type": "application/json",
        "Authorization": "Bearer " + BOT_TOKEN
    }

    payload = {
        "replyToken": reply_token,
        "messages": [{
            "type": "text",
            "text": text
        }]
    }

    # 發送 POST 請求至 LINE Messaging API
    response = requests.post("https://api.line.me/v2/bot/message/reply",
                             headers=headers,
                             json=payload)
    return response


# 傳送推播訊息函數（用於在文字訊息後發送輪播）
def send_push_message(user_id, messages):
    headers = {
        "Content-Type": "application/json",
        "Authorization": "Bearer " + BOT_TOKEN
    }

    payload = {
        "to": user_id,
        "messages": messages
    }

    # 發送 POST 請求至 LINE Messaging API
    response = requests.post("https://api.line.me/v2/bot/message/push",
                             headers=headers,
                             json=payload)
    return response


# 傳送 Carousel Template 訊息
def send_carousel_message(reply_token):
    headers = {
        "Content-Type": "application/json",
        "Authorization": "Bearer " + BOT_TOKEN
    }

    carousel_payload = {
        "replyToken":
        reply_token,
        "messages": [{
                      "type": "template",
                      "altText": "this is a carousel template",
                      "template": {
                        "type": "carousel",
                        "columns": [
                          {
                            "title": "股票基本分析",
                            "text": "查看股票價格和技術指標",
                            "actions": [
                              {
                                "type": "message",
                                "label": "查看最近價格",
                                "text": "查看最近價格"
                              },
                              {
                                "type": "message",
                                "label": "移動平均線",
                                "text": "移動平均線"
                              },
                              {
                                  "type": "message",
                                  "label": "Sharpe 指數",
                                  "text": "Sharpe 指數"
                              }
                            ]
                          },
                          {
                            "title": "股票比較分析",
                            "text": "比較兩支股票的表現",
                            "actions": [
                              {
                                "type": "message",
                                "label": "比較兩支股票",
                                "text": "比較兩支股票"
                              },
                              {
                                "type": "message",
                                "label": "更多功能",
                                "text": "更多功能"
                              },
                              {
                                "type": "message",
                                "label": "使用說明",
                                "text": "使用說明"
                              }
                            ]
                          }
                        ]
                      }
                    }]
    }

    # 發送 POST 請求至 LINE Messaging API
    response = requests.post("https://api.line.me/v2/bot/message/reply",
                             headers=headers,
                             json=carousel_payload)
    return response


# 呼叫 Google GenAI 來生成內容，並限制回應字數為100字
def generate_content_from_google_ai(query):
    # 給予提示，要求生成的回應在100字內
    prompt = f"請使用 100 字以內回答我：{query}"
    model = genai.GenerativeModel("gemini-1.5-flash")  # 或 gemini-1.5-pro

    try:
        response = model.generate_content(prompt)
        if hasattr(response, "text") and response.text:
            return response.text.strip()
        elif hasattr(response, "parts") and len(response.parts) > 0:
            return response.parts[0].text.strip()
        else:
            return None
    except Exception as e:
        print("AI 回應錯誤：", e)
        return None


# 控制流量回應的時間間隔
def can_respond():
    global last_response_time
    current_time = time.time()
    if current_time - last_response_time >= response_interval:
        last_response_time = current_time
        return True
    return False


# 驗證股票代碼格式
def validate_stock_code(stock_code):
    # 移除空白字元
    stock_code = stock_code.strip()

    # 檢查是否為數字且長度適當（台股代碼通常是4位數字）
    if not stock_code.isdigit() or len(stock_code) != 4:
        return None

    return stock_code

# 取得股票價格的函數
def get_stock_price(stock_code):
    try:
        # 驗證股票代碼
        validated_code = validate_stock_code(stock_code)
        if not validated_code:
            return None

        # 使用Yahoo Finance Taiwan API作為替代方案
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{validated_code}.TW"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }

        response = requests.get(url, headers=headers, timeout=10)

        if response.status_code == 200:
            data = response.json()

            if data.get('chart') and data['chart'].get('result') and len(data['chart']['result']) > 0:
                result = data['chart']['result'][0]
                meta = result.get('meta', {})

                # 提取股票資訊
                current_price = meta.get('regularMarketPrice', 'N/A')
                prev_close = meta.get('previousClose', 'N/A')

                # 計算漲跌
                change = 'N/A'
                if current_price != 'N/A' and prev_close != 'N/A':
                    try:
                        change_value = current_price - prev_close
                        change_percent = (change_value / prev_close) * 100
                        if change_value > 0:
                            change = f"+{change_value:.2f} (+{change_percent:.2f}%)"
                        else:
                            change = f"{change_value:.2f} ({change_percent:.2f}%)"
                    except:
                        change = 'N/A'

                return {
                    'price': f"{current_price:.2f}" if current_price != 'N/A' else 'N/A',
                    'change': change,
                    'time': '即時'
                }

        return None

    except Exception as e:
        print(f"取得股票價格時發生錯誤: {e}")
        return None

def get_moving_averages(stock_code):
    try:
        validated_code = validate_stock_code(stock_code)
        if not validated_code:
            return {'error': '無效的股票代碼'}

        end_date = datetime.now()
        start_date = end_date - timedelta(days=180)
        symbol = f"{validated_code}.TW"

        df = yf.download(symbol, start=start_date, end=end_date, auto_adjust=True)

        if df.empty:
            return {'error': '查無資料'}

        if len(df) < 20:
            return {'error': '資料不足，無法計算移動平均線'}

        df['MA5'] = df['Close'].rolling(window=5).mean()
        df['MA20'] = df['Close'].rolling(window=20).mean()
        latest_data = df.tail(1).iloc[0]

        # 安全轉換 function
        def safe_float(val):
            try:
                if isinstance(val, pd.Series):
                    val = val.item()
                return float(val) if pd.notna(val) else None
            except:
                return None

        return {
            'close_price': safe_float(latest_data['Close']),
            'ma5': safe_float(latest_data['MA5']),
            'ma20': safe_float(latest_data['MA20']),
            'date': str(df.index[-1].date())
        }

    except Exception as e:
        print(f"計算移動平均線時發生錯誤: {e}")
        return {'error': str(e)}

def calculate_sharpe_ratio(stock_code, risk_free_rate=0.015):
    try:
        validated_code = validate_stock_code(stock_code)
        if not validated_code:
            return {'error': '無效的股票代碼'}

        end_date = datetime.now()
        start_date = end_date - timedelta(days=180)
        symbol = f"{validated_code}.TW"

        df = yf.download(symbol, start=start_date, end=end_date, auto_adjust=True)

        if df.empty or len(df) < 30:
            return {'error': '資料不足，無法計算 Sharpe 指數'}

        df['Return'] = df['Close'].pct_change()
        avg_return = df['Return'].mean()
        std_dev = df['Return'].std()

        if std_dev == 0:
            return {'error': '波動率為 0，無法計算'}

        daily_risk_free_rate = risk_free_rate / 252  # 將年利率換算為日利率

        sharpe_ratio = (avg_return - daily_risk_free_rate) / std_dev

        return {
            'sharpe_ratio': round(sharpe_ratio, 4),
            'avg_return': round(avg_return * 100, 2),
            'std_dev': round(std_dev * 100, 2)
        }

    except Exception as e:
        return {'error': str(e)}

def create_carousel_messages():
    return [{
        "type": "template",
        "altText": "this is a carousel template",
        "template": {
            "type": "carousel",
            "columns": [
                {
                    "title": "股票基本分析",
                    "text": "查看股票價格和技術指標",
                    "actions": [
                        {
                            "type": "message",
                            "label": "查看最近價格",
                            "text": "查看最近價格"
                        },
                        {
                            "type": "message",
                            "label": "移動平均線",
                            "text": "移動平均線"
                        },
                        {
                          "type": "message",
                          "label": "Sharpe 指數",
                          "text": "Sharpe 指數"
                        }
                    ]
                },
                {
                    "title": "股票比較分析",
                    "text": "比較兩支股票的表現",
                    "actions": [
                        {
                            "type": "message",
                            "label": "比較兩支股票",
                            "text": "比較兩支股票"
                        },
                        {
                            "type": "message",
                            "label": "更多功能",
                            "text": "更多功能"
                        },
                        {
                            "type": "message",
                            "label": "使用說明",
                            "text": "使用說明"
                        }
                    ]
                }
            ]
        }
    }]


# LINE Webhook 入口
@app.route("/", methods=['GET', 'POST'])
def linebot():
    if request.method == 'GET':
        return "LINE Bot Webhook is running."

    if request.method == 'POST':
        # 取得使用者傳來的資料
        data = request.get_json()
        print(data)

        # 提取 replyToken 和用戶訊息
        reply_token = data['events'][0]['replyToken']
        user_id = data['events'][0]['source']['userId']

        # 檢查訊息類型，處理貼圖等非文字訊息
        message_type = data['events'][0]['message']['type']
        if message_type != 'text':
            response = send_carousel_message(reply_token)
            return "OK", 200

        user_message = data['events'][0]['message']['text']

        # 獲取用戶當前狀態
        current_state = user_states.get(user_id, {})

        # 特殊處理：股票相關流程不受流量管控限制
        is_stock_flow = (
            user_message == "比較兩支股票" or
            user_message == "查看最近價格" or
            user_message == "移動平均線" or
            user_message == "Sharpe 指數" or
            current_state.get("state") == "waiting_first_stock" or
            current_state.get("state") == "waiting_second_stock" or
            current_state.get("state") == "waiting_stock_code" or
            current_state.get("state") == "waiting_ma_stock_code" or
            current_state.get("state") == "waiting_sharpe_stock_code"
        )

        # 檢查流量管控是否可以回應（股票相關流程例外）
        if not is_stock_flow and not can_respond():
            return "Too many requests. Please wait.", 429  # 429 Too Many Requests

        # 根據用戶的訊息回覆
        if user_message == "查看最近價格":
            # 開始價格查詢流程
            user_states[user_id] = {"state": "waiting_stock_code"}
            response = send_text_message(reply_token, "請輸入股票代碼（例如：2330）")
        elif current_state.get("state") == "waiting_stock_code":
            # 收到股票代碼，開始查詢價格
            stock_code = user_message.strip()

            # 清除用戶狀態
            user_states[user_id] = {}

            # 驗證股票代碼格式
            validated_code = validate_stock_code(stock_code)
            if not validated_code:
                response = send_text_message(reply_token, "請輸入正確的4位數字股票代碼（例如：2330）")
            else:
                # 查詢股票價格
                stock_price = get_stock_price(validated_code)

                if stock_price:
                    response = send_text_message(reply_token, f"📈 股票代碼：{validated_code}\n💰 最新價格：{stock_price['price']} 元\n📊 漲跌：{stock_price['change']}\n⏰ 更新時間：{stock_price['time']}")
                else:
                    response = send_text_message(reply_token, f"抱歉，無法取得股票代碼 {validated_code} 的價格資訊。請確認股票代碼是否正確或稍後再試。")

            # 發送輪播訊息
            send_push_message(user_id, create_carousel_messages())
        elif user_message == "移動平均線":
            # 開始移動平均線查詢流程
            user_states[user_id] = {"state": "waiting_ma_stock_code"}
            response = send_text_message(reply_token, "請輸入股票代碼以查看移動平均線（例如：2330）")
        elif current_state.get("state") == "waiting_ma_stock_code":
            # 收到股票代碼，開始查詢移動平均線
            stock_code = user_message.strip()

            # 清除用戶狀態
            user_states[user_id] = {}

            # 驗證股票代碼格式
            validated_code = validate_stock_code(stock_code)
            if not validated_code:
                response = send_text_message(reply_token, "請輸入正確的4位數字股票代碼（例如：2330）")
            else:
                # 查詢移動平均線
                ma_data = get_moving_averages(validated_code)

                if isinstance(ma_data, dict) and all(k in ma_data for k in ['close_price', 'ma5', 'ma20', 'date']):
                    close_price = f"{ma_data['close_price']:,.2f}"
                    ma5 = f"{ma_data['ma5']:,.2f}"
                    ma20 = f"{ma_data['ma20']:,.2f}"
                    date = ma_data['date']

                    msg = (
                        f"📊 股票代碼：{validated_code}\n"
                        f"💰 收盤價：{close_price} 元\n"
                        f"📈 5日移動平均線：{ma5} 元\n"
                        f"📉 20日移動平均線：{ma20} 元\n"
                        f"📅 日期：{date}"
                    )
                    response = send_text_message(reply_token, msg)
                else:
                    err_msg = ma_data.get('error', '無法取得資料')
                    response = send_text_message(
                        reply_token,
                        f"抱歉，無法取得股票代碼 {validated_code} 的移動平均線資訊。\n原因：{err_msg}。"
                    )

            # 發送輪播訊息
            send_push_message(user_id, create_carousel_messages())

        elif user_message == "Sharpe 指數":
            user_states[user_id] = {"state": "waiting_sharpe_stock_code"}
            response = send_text_message(reply_token, "請輸入股票代碼以計算 Sharpe 指數（例如：2330）")

        elif current_state.get("state") == "waiting_sharpe_stock_code":
            stock_code = user_message.strip()
            user_states[user_id] = {}

            validated_code = validate_stock_code(stock_code)
            if not validated_code:
                response = send_text_message(reply_token, "請輸入正確的4位數字股票代碼（例如：2330）")
            else:
                result = calculate_sharpe_ratio(validated_code)
                if "sharpe_ratio" in result:
                    response = send_text_message(reply_token,
                        f"📊 股票代碼：{validated_code}\n"
                        f"📈 平均日報酬率：{result['avg_return']}%\n"
                        f"📉 報酬標準差（波動）：{result['std_dev']}%\n"
                        f"✅ Sharpe 指數：約 {result['sharpe_ratio']}"
                    )
                else:
                    response = send_text_message(reply_token, f"無法計算 Sharpe 指數。\n原因：{result.get('error', '未知錯誤')}")

            send_push_message(user_id, create_carousel_messages())

        elif user_message == "比較兩支股票":
            # 開始股票比較流程
            user_states[user_id] = {"state": "waiting_first_stock"}
            response = send_text_message(reply_token, "請輸入第一支股票代碼（例如：2330）")
        elif current_state.get("state") == "waiting_first_stock":
            # 收到第一支股票代碼
            user_states[user_id] = {
                "state": "waiting_second_stock",
                "first_stock": user_message.strip()
            }
            response = send_text_message(reply_token, f"已記錄第一支股票：{user_message.strip()}\n\n請輸入第二支股票代碼")
        elif current_state.get("state") == "waiting_second_stock":
            # 收到第二支股票代碼，開始AI比較
            first_stock = current_state.get("first_stock")
            second_stock = user_message.strip()

            # 清除用戶狀態
            user_states[user_id] = {}

            # 使用AI比較兩支股票
            comparison_query = f"請比較台股{first_stock}和{second_stock}這兩支股票，包括基本面、技術面、投資風險等方面的分析"
            google_ai_response = generate_content_from_google_ai(comparison_query)

            print("股票比較查詢:", comparison_query)
            print("AI 回應內容:", google_ai_response)

            if google_ai_response:
                final_response = f"🔍 股票比較分析\n\n📊 {first_stock} vs {second_stock}\n\n{google_ai_response}"
                response = send_text_message(reply_token, final_response)
            else:
                response = send_text_message(reply_token, "抱歉，目前無法取得股票比較分析。請稍後再試。")

            # 發送輪播訊息
            send_push_message(user_id, create_carousel_messages())
        elif user_message == "更多功能":
            response = send_text_message(reply_token, 
                "🚀 更多功能開發中...\n\n"
                "目前支援的功能：\n"
                "• 查看股票最近價格\n"
                "• 計算移動平均線\n"
                "• 計算 Sharpe 指數\n"
                "• 比較兩支股票\n\n"
                "敬請期待更多功能！")

            # 發送輪播訊息
            send_push_message(user_id, create_carousel_messages())
        elif user_message == "使用說明":
            response = send_text_message(reply_token, 
                "📖 使用說明\n\n"
                "1️⃣ 選擇您想要的功能\n"
                "2️⃣ 輸入4位數字股票代碼（例如：2330）\n"
                "3️⃣ 系統會為您分析並提供結果\n\n"
                "💡 小提醒：\n"
                "• 股票代碼必須是4位數字\n"
                "• 目前支援台股查詢\n"
                "• 資料來源：Yahoo Finance")

            # 發送輪播訊息
            send_push_message(user_id, create_carousel_messages())
        elif "ai" in user_message.lower() and "比較兩支股票" in user_message:
            # 當用戶詢問AI相關問題時，使用 Google AI 生成內容
            google_ai_response = generate_content_from_google_ai(user_message)
            print("使用者訊息:", user_message)
            print("AI 回應內容:", google_ai_response)
            if google_ai_response:
                response = send_text_message(reply_token, google_ai_response)
            else:
                response = send_text_message(reply_token, "抱歉，目前無法取得 AI 回應。")

            # 發送輪播訊息
            send_push_message(user_id, create_carousel_messages())
        else:
            # 清除用戶狀態（如果用戶發送了其他訊息）
            if user_id in user_states:
                user_states[user_id] = {}
            # 如果是其他訊息，發送選單
            response = send_carousel_message(reply_token)

        # 檢查訊息是否發送成功
        if response.status_code == 200:
            return "OK", 200
        else:
            print("發送訊息失敗:", response.status_code, response.text)
            return "Error", 400


# 啟動 Flask 伺服器
if __name__ == "__main__":
    app.run(host='0.0.0.0', port=3000)