from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError
from datetime import datetime
import imports.core
from imports.db import db

def amount_url(token, tokenCassino):
    return f"https://central.cassinopro.bet/casino/games/url?token={tokenCassino}&tokenUsuario={token}&symbol=znt-aviator&language=pt&playMode=REAL&cashierUr=https%3A%2F%2Fcassinopro.bet%2Fclientes%2Fdeposito&lobbyUrl=https%3A%2F%2Fcassinopro.bet%2Fcasino&fornecedor=spribe&isMobile=true&plataforma=mobile"

def get_game_results(game_url: str):
    """
    Abre a URL do jogo e monitora continuamente os resultados das rodadas.
    Cada vez que um novo resultado aparece, imprime os últimos.
    """
    with sync_playwright() as p:
        try:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                        "AppleWebKit/537.36 (KHTML, like Gecko) "
                        "Chrome/114.0.0.0 Safari/537.36",
                viewport={"width": 1920, "height": 1080}
            )
            page = context.new_page()

            print(f"Navegando para: {game_url}")
            page.goto(game_url, wait_until='networkidle')

            # Espera a div aparecer
            page.wait_for_selector('.payouts-wrapper', timeout=30000)
            print("Seletor encontrado. Monitorando resultados...")

            # Injetamos um MutationObserver para capturar alterações no DOM
            page.evaluate("""
                () => {
                    const target = document.querySelector('.payouts-wrapper');
                    window.__results = [];

                    const observer = new MutationObserver(() => {
                        const payouts = [...document.querySelectorAll('.payout.ng-star-inserted, .payout')]
                                        .map(el => el.innerText.trim())
                                        .filter(Boolean);
                        window.__results = payouts;
                    });

                    observer.observe(target, { childList: true, subtree: true });
                }
            """)

            # Loop infinito para puxar resultados sempre que mudarem
            last_results = []
            while True:
                results = page.evaluate("window.__results")
                if results and results != last_results:

                    print("Novos resultados:", results[0])

                    db.save_result(float(results[0].replace('x', '')))

                    imports.core.analisys() #apos cada salvamento ele executa a analise

                    last_results = results

        except PlaywrightTimeoutError:
            print("Erro de timeout no Playwright. A página pode ter desconectado ou demorou muito para carregar.")
            raise # Lança a exceção para ser capturada no main.py
        except Exception as e:
            print(f"Ocorreu um erro inesperado durante a raspagem: {e}")
            raise # Lança a exceção para ser capturada no main.py