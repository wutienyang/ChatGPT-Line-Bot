from typing import List, Dict
import openai


class ModelInterface:

  def chat_completion(self, messages: List[Dict]) -> str:
    pass

  def image_generation(self, prompt: str) -> str:
    pass

  def whisper(self, text: str) -> str:
    pass


class OpenAIModel(ModelInterface):

  def __init__(
    self,
    api_key: str,
    model_engine: str,
    whisper_model: str = "whisper-1",
    image_size: str = "512x512",
  ):
    openai.api_key = api_key
    self.model_engine = model_engine
    self.image_size = image_size
    self.whisper_model = whisper_model

  def chat_completion(self, messages) -> str:
    response = openai.ChatCompletion.create(model=self.model_engine,
                                            messages=messages)
    return response

  def image_generation(self, prompt: str) -> str:
    response = openai.Image.create(prompt=prompt, n=1, size=self.image_size)
    image_url = response.data[0].url
    return image_url

  def audio_generation(self, audio_path: str) -> str:
    audio_file = open(audio_path, "rb")
    transcript = openai.Audio.transcribe(self.whisper_model, audio_file)
    return transcript["text"]
