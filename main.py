import requests
import time
import imports.utils

def perform_login():
    """
    Realiza o login e retorna a URL do jogo.
    Retorna None em caso de falha.
    """
    end = "https://loki1.weebet.tech"
    login_url = end + "/auth/login"

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

    try:
        response = requests.post(login_url, json=payload, headers=headers, timeout=30)
        response.raise_for_status() # Lança exceção para códigos de erro HTTP

        body = response.json()
        if body.get('success'):
            token = body['results']['token']
            tokenCassino = body['results']['tokenCassino']
            
            urlAv = imports.utils.amount_url(token, tokenCassino)
            headers["Authorization"] = f"Bearer {token}"

            response_game_url = requests.get(urlAv, headers=headers, timeout=30)
            response_game_url.raise_for_status()
            
            game_body = response_game_url.json()
            return game_body.get('gameURL')
        else:
            print("Falha no login, resposta não continha 'success':", body)
            return None

    except requests.exceptions.RequestException as e:
        print(f"Erro de conexão durante o login: {e}")
        return None
    except Exception as e:
        print(f"Erro inesperado durante o login: {e}")
        return None

def main():
    """
    Loop principal que garante que o crawler esteja sempre rodando.
    """
    while True:
        print("Iniciando nova sessão...")
        game_url = perform_login()

        if game_url:
            try:
                # Inicia a raspagem dos resultados
                imports.utils.get_game_results(game_url)
            except Exception as e:
                print(f"A função de raspagem falhou com o erro: {e}. Reiniciando o processo...")
        else:
            print("Não foi possível obter a URL do jogo. Tentando novamente em 60 segundos.")

        # Pausa antes de tentar novamente para evitar sobrecarregar o servidor em caso de falhas repetidas
        time.sleep(60)

if __name__ == "__main__":
    main()