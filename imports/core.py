from datetime import datetime, timedelta
import configparser
import os
from imports.db import db
from telegram import Bot
import asyncio  # Adicionado para chamadas assíncronas
import re

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.abspath(os.path.join(BASE_DIR, "..", "config.ini"))

config = configparser.ConfigParser()
config.read(CONFIG_PATH, encoding='utf-8')

HOUR = int(config['config']['hora'])
CANDLE = int(config['config']['vela'])
LIMIT_HOURS = int(config['config']['limite_horarios'])
LINE_GREEN = config['config']['linha_green']
LINE_RED = config['config']['linha_red']
CORRECT_GENERAL_GREEN = config['config']['correcao_geral_green']
CORRECT_GENERAL_RED = config['config']['correcao_geral_RED']

MARTINGALE=3

TOKEN = config['telegram']['token']
CHAT_ID = config['telegram']['chat_id']
MESSAGE = "LISTA PROBABILIDADE AVIATOR \n\n💳 Segurança em 2x 💳\n✈️ Buscar {{candle}}.00x a 50x \n\n{{hours}}\n\n⚠️ Entrar 15s antes ou no horário exato! \n🔞 Proibido para menores idade\n\n[CLIQUE AQUI E SE CADASTRE](https://cassinopro.bet/cadastro?ref=REGISTRO)"

bot = Bot(token=TOKEN)

def remove_markes(text):
    """
    Remove todos os marcadores no formato ((...)) de uma string.
    
    Args:
        texto (str): A string que pode conter marcadores ((...))
        
    Returns:
        str: A string sem os marcadores.
    """
    return re.sub(r'\(\(.*?\)\)', '', text)

def analisys():
    # verifica se tem registro no intervalo de hora configurado
    check = db.has_record_in_specific_hour(HOUR)

    if not check:
        print('Sem registro do horario configurado, capturando dados até completar')
        return

    state = db.get_state('state')

    # estado de envio de mensagem, vai pegar as horas anteriores
    if state == 'sending':
        hours = db.get_results_in_specific_hour(CANDLE, HOUR)  # pega todos os horários q tiveram a vela que queremos
        
        # seleciona apenas LIMIT_HOURS horários distribuídos uniformemente
        if len(hours) > LIMIT_HOURS:
            step = len(hours) / LIMIT_HOURS
            selected_hours = [hours[int(i*step)] for i in range(LIMIT_HOURS)]
        else:
            selected_hours = hours

        hours_str = ""
        hour_to_correct = 0
        seen_hours = set()

        for result, hour_min in selected_hours:
            current_hour = datetime.now().strftime("%H")
            minute = str(hour_min).split(':')
            hour = current_hour + ':' + minute[1]

            if hour not in seen_hours:
                hours_str += "⏰ " + hour + "\n"
                seen_hours.add(hour)
                hour_to_correct += 1

        final_message = MESSAGE.replace("{{candle}}", str(CANDLE)).replace("{{hours}}", hours_str)
        
        # --- CORREÇÃO ASYNCIO APLICADA AQUI ---
        sent_message = asyncio.run(bot.send_message(chat_id=CHAT_ID, text=remove_markes(final_message), parse_mode="Markdown", disable_web_page_preview=True))
        
        db.update_state('hours_to_correct', str(hour_to_correct))  # salva a quantidade de horários a serem corrigidos
        db.update_state('last_message_id', str(sent_message.message_id))  # salva o id para corrigir
        db.update_state('last_message', final_message)  # salva a mensagem pra ir corrigindo
        print('mensagem enviada pelo telegram')

        db.update_state('state', 'correcting')  # mudando o estado pra corrigindo

    # depois que envia a mensagem ele muda pra corrigindo
    elif state == 'correcting':
        current_time = (datetime.now() - timedelta(minutes=1)).strftime("%H:%M")
        message_edit = db.get_state('last_message')
        message_id = db.get_state('last_message_id')
        hours_to_correct = int(db.get_state('hours_to_correct'))

        # Verifica sempre se deve reiniciar o ciclo, mesmo que não tenha linhas para corrigir
        if hours_to_correct == 0 or datetime.now().minute == 0:
            greens = int(db.get_state('greens'))
            reds = int(db.get_state('reds'))

            total = greens + reds

            percent_greens = round((greens / total) * 100, 2)
            percent_reds = round((reds / total) * 100, 2)

            relat_green = CORRECT_GENERAL_GREEN.replace('{{total}}', str(greens)).replace('{{percent}}', str(percent_greens) + '%')
            relat_red = CORRECT_GENERAL_RED.replace('{{total}}', str(reds)).replace('{{percent}}', str(percent_reds) + '%')

            relat = f"{relat_green}\n{relat_red}"

            msg_ed = f"{message_edit}\n\n{relat}"

            asyncio.run(bot.edit_message_text(
                chat_id=CHAT_ID,
                message_id=message_id,
                text=remove_markes(msg_ed),
                parse_mode="Markdown",
                disable_web_page_preview=True
            ))

            db.update_state('last_message_id', '')
            db.update_state('last_message', '')
            db.update_state('hours_to_correct', '0')
            db.update_state('greens', '0')
            db.update_state('reds', '0')
            db.update_state('state', 'sending')

            print(f"Ciclo finalizado, reiniciando")

        # Corrigir linhas existentes
        if hours_to_correct > 0:
            line_hour = f"⏰ {current_time}"
            lines = message_edit.split("\n")
            
            for i, line in enumerate(lines):
                if line_hour in line and "((line_correct))" not in line:
                    hour_str, minute_str = current_time.split(':') 
                    max_result = db.get_max_result(int(hour_str), int(minute_str))

                    rest = "N/A"
                    if max_result is not None:
                        if max_result >= CANDLE:
                            db.update_state('greens', str(int(db.get_state('greens')) + 1))
                            rest = LINE_GREEN.replace('{{vela}}', str(max_result))
                        else:
                            db.update_state('reds', str(int(db.get_state('reds')) + 1))
                            rest = LINE_RED.replace('{{vela}}', str(max_result))

                    lines[i] = f"{line} {rest}((line_correct))"
                    msg_edit = "\n".join(lines)

                    asyncio.run(bot.edit_message_text(
                        chat_id=CHAT_ID,
                        message_id=message_id,
                        text=remove_markes(msg_edit),
                        parse_mode="Markdown",
                        disable_web_page_preview=True
                    ))

                    db.update_state('hours_to_correct', str(hours_to_correct - 1))
                    db.update_state('last_message', msg_edit)
                    print(f"Mensagem {message_id} editada com {current_time}")
                    break  # só edita uma linha por vez

        
