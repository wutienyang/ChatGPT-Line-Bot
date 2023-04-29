import requests
from bs4 import BeautifulSoup

URL = 'https://histock.tw/stock/public.aspx'


def get_stock_info():
  response = requests.get(URL)
  soup = BeautifulSoup(response.content, 'html.parser')
  table = soup.find('table', {'class': 'gvTB'})

  headers = [th.text.strip() for th in table.find_all('th')]
  rows = []
  for tr in table.find_all('tr'):
    row = [td.text.strip() for td in tr.find_all('td')]
    if row:
      rows.append(row)

  s = ""
  for row in rows:
    if '申購中' in row:
      for k, v in zip(headers, row):
        s += f"{k} : {v}\n"
      s += "\n"
  if not s:
    s = "no stock to day"
  return s
