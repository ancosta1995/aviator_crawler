import requests
from utils import amount_url, get_game_results

end = "https://loki1.weebet.tech"
login = "/auth/login"

payload = {
    "username":"ancosta1995@gmail.com",
    "password":"Android@120",
    "googleId":"",
    "googleIdToken":"",
    "loginMode":"email",
    "ignorarValidacaoEmailObrigatoria": True,
    "betting_shop_code": None
}

headers = {
    "Content-Type": "application/json",
    "Origin": "https://www.cassinopro.bet",
    "Referer": "https://www.cassinopro.bet/",
    "User-Agent": "Mozilla/5.0 (Linux; Android 6.0; Nexus 5 Build/MRA58N) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Mobile Safari/537.36"
}

response = requests.post(end + login, json=payload, headers=headers)

if response.status_code == 200:
    body = response.json()
    if body['success']:
        token = body['results']['token']
        tokenCassino = body['results']['tokenCassino']

        urlAv = amount_url(token, tokenCassino)

        headers["Authorization"] = f"Bearer {token}"

        response = requests.get(urlAv, headers=headers)

        if response.status_code == 200:
            body = response.json()
            gameURL = body['gameURL']

            #urlFinal = resolve_game_url(gameURL)

            results = get_game_results(gameURL)

            #print(results)

