import requests
from flask import Flask, request
import google.generativeai as genai
import time

# 初始化 Flask 應用程式
app = Flask(__name__)

# 設定 LINE BOT Token
BOT_TOKEN = '+vm6Ej+RrfiUrqXmc++mWtxV0cErb6LJYsQzpqGF/dgi/2FkMfp6hV7PpxfSkodQi0xoGBSue7ytV0EhtM+kkxyluRj+BXAJssFfyQLhRL4tS8M2MWMg9eLiz/Ls0CUtzknaEB/5k0+cUOsUAnLphgdB04t89/1O/w1cDnyilFU='

# 設定 Google AI API 金鑰
genai.configure(api_key="AIzaSyA5PBFOSdPE1PCKQcERFMuSb2XoM4w8RD8"
                )  # 請將此處的 YOUR_GOOGLE_API_KEY 替換為你的 Google API 金鑰

# 設定流量管理
last_response_time = 0
response_interval = 10  # 每 10 秒鐘可以回應一次


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
                            "title": "股票資料分析服務",
                            "text": "請輸入欲查詢股票代碼",
                            "actions": [
                              {
                                "type": "message",
                                "label": "查看最近價格",
                                "text": "查看最近價格"
                              },
                              {
                                "type": "message",
                                "label": "昨日收盤價",
                                "text": "昨日收盤價"
                              },
                              {
                                "type": "message",
                                "label": "比較兩支股票",
                                "text": "比較兩支股票"
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
        user_message = data['events'][0]['message']['text']

        # 檢查流量管控是否可以回應
        if not can_respond():
            return "Too many requests. Please wait.", 429  # 429 Too Many Requests

        # 根據用戶的訊息回覆
        if user_message == "查看最近價格":
            # 回覆股票最新價格，這裡你可以擴展查詢的功能
            response = send_text_message(reply_token, "這是最新的股票價格資料。")
        elif user_message == "昨日收盤價":
            # 回覆昨日收盤價
            response = send_text_message(reply_token, "這是昨日的收盤價資料。")
        elif "ai" in user_message.lower() and "比較兩支股票" in user_message:
            # 當用戶詢問「如何運作 AI?」時，使用 Google AI 生成內容
            google_ai_response = generate_content_from_google_ai(user_message)
            print("使用者訊息:", user_message)
            print("AI 回應內容:", google_ai_response)
            if google_ai_response:
                response = send_text_message(reply_token, google_ai_response)
            else:
                response = send_text_message(reply_token, "抱歉，目前無法取得 AI 回應。")
        else:
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
