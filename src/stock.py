import requests
from bs4 import BeautifulSoup


def get_stock_info():
    url = "https://histock.tw/stock/public.aspx"
    response = requests.get(url)
    soup = BeautifulSoup(response.content, "html.parser")
    table = soup.find("table", {"class": "gvTB"})

    headers = [th.text.strip() for th in table.find_all("th")]
    rows = [
        [td.text.strip() for td in tr.find_all("td")]
        for tr in table.find_all("tr")
        if tr.find_all("td")
    ]

    s = ""
    for row in rows:
        if "申購中" in row:
            s += "\n".join([f"{k} : {v}" for k, v in zip(headers, row)]) + "\n\n"

    return s if s else "No stock today"


if __name__ == "__main__":
    info = get_stock_info()
    print(info)
