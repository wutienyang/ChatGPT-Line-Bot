from dotenv import load_dotenv
from flask import Flask, request, abort
from linebot import (LineBotApi, WebhookHandler)
from linebot.exceptions import (InvalidSignatureError)
from linebot.models import (MessageEvent, TextMessage, TextSendMessage,
                            ImageSendMessage, AudioMessage)
import os

from src.chatgpt import ChatGPT, DALLE
from src.models import OpenAIModel
from src.memory import Memory
from src.logger import logger
from src.stock import get_stock_info

load_dotenv('.env')

app = Flask(__name__)
line_bot_api = LineBotApi(os.getenv('LINE_CHANNEL_ACCESS_TOKEN'))
handler = WebhookHandler(os.getenv('LINE_CHANNEL_SECRET'))

models = OpenAIModel(api_key=os.getenv('OPENAI_API'),
                     model_engine=os.getenv('OPENAI_MODEL_ENGINE'))

memory = Memory(system_message=os.getenv('SYSTEM_MESSAGE'))
chatgpt = ChatGPT(models, memory)
dalle = DALLE(models)
base_prompt = "Help me to translate this sentence to English, only target language, no need original language."


@app.route("/callback", methods=['POST'])
def callback():
  signature = request.headers['X-Line-Signature']
  body = request.get_data(as_text=True)
  app.logger.info("Request body: " + body)
  try:
    handler.handle(body, signature)
  except InvalidSignatureError:
    print(
      "Invalid signature. Please check your channel access token/channel secret."
    )
    abort(400)
  return 'OK'


@handler.add(MessageEvent, message=TextMessage)
def handle_text_message(event):
  global base_prompt
  user_id = event.source.user_id
  text = event.message.text
  logger.info(f'{user_id}: {text}')
  if text.strip() == "/prompt":
    line_bot_api.push_message(os.getenv('LINE_USER_ID'),
                              TextSendMessage(text=f"prompt : {base_prompt}"))
  elif text.strip() == '/1':
    base_prompt = "Help me to translate this sentence to English, only target language, no need original language."
    line_bot_api.push_message(os.getenv('LINE_USER_ID'),
                              TextSendMessage(text=f"prompt : {base_prompt}"))
  elif text.strip() == '/2':
    base_prompt = "Please help me to fix the grammar and provide more simple and clear sentences without repeating the provided sentences."
    line_bot_api.push_message(os.getenv('LINE_USER_ID'),
                              TextSendMessage(text=f"prompt : {base_prompt}"))
  elif text.startswith('/set'):
    base_prompt = text[4:].strip()
    line_bot_api.push_message(os.getenv('LINE_USER_ID'),
                              TextSendMessage(text=f"prompt : {base_prompt}"))
  elif text.startswith('/imagine'):
    response = dalle.generate(text[8:].strip())
    msg = ImageSendMessage(original_content_url=response,
                           preview_image_url=response)
    line_bot_api.reply_message(event.reply_token, msg)
  else:
    try:
      response = chatgpt.get_response(user_id, text)
      msg = TextSendMessage(text=response)
      line_bot_api.reply_message(event.reply_token, msg)
    except Exception as e:
      print(f"e : {e}")
      msg = TextSendMessage(text=e)
      line_bot_api.reply_message(event.reply_token, msg)


def openai_whisper(audio_path):
  import openai
  audio_file = open(audio_path, "rb")
  transcript = openai.Audio.transcribe("whisper-1", audio_file)
  return transcript["text"]


def translate_openai(text, language):
  import openai
  prompt = f"{text} \n {base_prompt}"

  # Translate the chunk using the GPT model
  response = openai.ChatCompletion.create(
    model="gpt-3.5-turbo",  # engine = "deployment_name".
    messages=[{
      "role": "user",
      "content": prompt
    }],
    temperature=0.5)
  translated_subtitles = response['choices'][0]['message']['content']
  return translated_subtitles


@handler.add(MessageEvent, message=AudioMessage)
def handle_audio_message(event):

  translate_language = "English"
  audio_language = "Traditional Chinese"

  message_id = event.message.id
  message_content = line_bot_api.get_message_content(message_id)
  with open(f'whisper_audio.m4a', 'wb') as f:
    f.write(message_content.content)
  whisper_text = openai_whisper(f'whisper_audio.m4a')
  response_text = translate_openai(whisper_text, audio_language)
  line_bot_api.push_message(os.getenv('LINE_USER_ID'),
                            TextSendMessage(text=f"語音 : {whisper_text}"))
  line_bot_api.reply_message(event.reply_token,
                             TextSendMessage(text=response_text))


@app.route("/", methods=['GET'])
def home():
  return 'ChatGPT is alive!'


@app.route("/stock", methods=['GET'])
def stock():
  line_bot_api.push_message(os.getenv('LINE_USER_ID'),
                            TextSendMessage(text=get_stock_info()))
  return 'stock is alive!'


if __name__ == "__main__":
  app.run(host='0.0.0.0', port=8080)
