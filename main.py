import requests
from flask import Flask, request

# 初始化 Flask 應用程式
app = Flask(__name__)

# 設定 LINE BOT Token
BOT_TOKEN = '+vm6Ej+RrfiUrqXmc++mWtxV0cErb6LJYsQzpqGF/dgi/2FkMfp6hV7PpxfSkodQi0xoGBSue7ytV0EhtM+kkxyluRj+BXAJssFfyQLhRL4tS8M2MWMg9eLiz/Ls0CUtzknaEB/5k0+cUOsUAnLphgdB04t89/1O/w1cDnyilFU='


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
    
    # 圖片訊息
    image_message_payload = {
        "type": "image",
        "originalContentUrl": "https://example.com/original.jpg",
        "previewImageUrl": "https://example.com/preview.jpg"
    }

    # 發送 POST 請求至 LINE Messaging API
    response = requests.post("https://api.line.me/v2/bot/message/reply",
                             headers=headers,
                             json=payload)
    return response


# LINE Webhook 入口
@app.route("/", methods=['GET', 'POST'])
def linebot():
    if request.method == 'GET':
        return "LINE Bot Webhook is running."

    if request.method == 'POST':
        # 取得使用者傳來的資料
        data = request.get_json()
        print(data)

        # 提取 replyToken
        reply_token = data['events'][0]['replyToken']

        # 回傳文字訊息
        response = send_text_message(reply_token, "Python訊息測試")

        if response.status_code == 200:
            return "OK", 200
        else:
            print("發送訊息失敗:", response.status_code, response.text)
            return "Error", 400


# 啟動 Flask 伺服器
if __name__ == "__main__":
    app.run(host='0.0.0.0', port=3000)