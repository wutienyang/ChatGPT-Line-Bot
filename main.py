import os
import json
from dotenv import load_dotenv
from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import (
    MessageEvent,
    TextMessage,
    TextSendMessage,
    ImageSendMessage,
    AudioMessage,
)

from src.chatgpt import ChatGPT, DALLE, Whisper
from src.models import OpenAIModel
from src.memory import Memory
from src.logger import logger
from src.stock import get_stock_info
from src.prompt import BASE_PROMPT, PROMPT_DICTIONARY

load_dotenv(".env")
app = Flask(__name__)
line_bot_api = LineBotApi(os.getenv("LINE_CHANNEL_ACCESS_TOKEN"))
handler = WebhookHandler(os.getenv("LINE_CHANNEL_SECRET"))
line_user_id = os.getenv("LINE_USER_ID")
models = OpenAIModel(
    api_key=os.getenv("OPENAI_API"), model_engine=os.getenv("OPENAI_MODEL_ENGINE")
)
memory = Memory(system_message=os.getenv("SYSTEM_MESSAGE"))
chatgpt = ChatGPT(models, memory)
dalle = DALLE(models)
whisper = Whisper(models)


def command(cmd):
    global BASE_PROMPT
    cmd = cmd.strip()
    if cmd == "/prompt":
        return BASE_PROMPT
    elif cmd == "/all":
        return json.dumps(PROMPT_DICTIONARY, indent=4)
    elif cmd in PROMPT_DICTIONARY:
        BASE_PROMPT = PROMPT_DICTIONARY[cmd]
        return BASE_PROMPT
    elif cmd.startswith("/set "):
        BASE_PROMPT = cmd[4:].strip()
        return BASE_PROMPT


def run(event):
    text = event.message.text
    prompt = command(text)
    line_bot_api.push_message(line_user_id, TextSendMessage(text=f"prompt : {prompt}"))

    if text.startswith("/imagine"):
        response = dalle.generate(text[8:].strip())
        msg = ImageSendMessage(
            original_content_url=response, preview_image_url=response
        )
        line_bot_api.reply_message(event.reply_token, msg)
    else:
        response = chatgpt.get_response(event.source.user_id, text)
        msg = TextSendMessage(text=response)
        line_bot_api.reply_message(event.reply_token, msg)


@app.route("/", methods=["GET"])
def home():
    return "ChatGPT is alive!"


@app.route("/stock", methods=["GET"])
def stock():
    line_bot_api.push_message(line_user_id, TextSendMessage(text=get_stock_info()))
    return "stock is alive!"


@app.route("/callback", methods=["POST"])
def callback():
    signature = request.headers["X-Line-Signature"]
    body = request.get_data(as_text=True)
    app.logger.info("Request body: " + body)
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        print(
            "Invalid signature. Please check your channel access token/channel secret."
        )
        abort(400)
    return "OK"


@handler.add(MessageEvent, message=TextMessage)
def handle_text_message(event):
    try:
        run(event)
    except Exception as e:
        print(f"Error : {e}")
        msg = TextSendMessage(text=e)
        line_bot_api.reply_message(event.reply_token, msg)


@handler.add(MessageEvent, message=AudioMessage)
def handle_audio_message(event):
    audio_name = "whisper_audio.m4a"
    message_id = event.message.id
    message_content = line_bot_api.get_message_content(message_id)
    with open(audio_name, "wb") as f:
        f.write(message_content.content)
    text = whisper.generate(audio_name)
    response = chatgpt.get_response(event.source.user_id, text)
    line_bot_api.push_message(line_user_id, TextSendMessage(text=f"Audio : {text}"))
    line_bot_api.reply_message(event.reply_token, TextSendMessage(text=response))


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
