from datetime import datetime, timedelta
import configparser
import os
from imports.db import db
from telegram import Bot

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.abspath(os.path.join(BASE_DIR, "..", "config.ini"))

config = configparser.ConfigParser()
config.read(CONFIG_PATH)

HOUR = int(config['config']['hora'])
CANDLE = int(config['config']['vela'])

TOKEN = config['telegram']['token']
CHAT_ID = config['telegram']['chat_id']
MESSAGE = config['telegram']['message']

bot = Bot(token=TOKEN)

def analisys():
    #verifica se tem registro no intervalo de hora configurado
    check = db.has_record_in_specific_hour(HOUR)

    if check: #tem registros

        state = db.get_state('state')

        #estado de envio de mensagem, vai pegar as horas anteriores
        if state == 'sending':
            hours = db.get_results_in_specific_hour(CANDLE, HOUR) #pega todos os horarios q tiveram a vela que queremos
            
            hours_str = ""
            hour_to_correct = 0
            for result, hour_min in hours:
                current_hour = str(datetime.now().hour)
                minute = str(hour_min).split(':')
                hour = current_hour + minute[1]
                hours_str += "⏰ " + hour + "\n"
                hour_to_correct += 1

            final_message = MESSAGE.replace("{{candle}}", str(CANDLE)).replace("{{hours}}", hours_str)
            sent_message = bot.send_message(chat_id=CHAT_ID, text=final_message, parse_mode="Markdown")
            
            db.update_state('hours_to_correct', str(hour_to_correct)) #salva a quantidade de horarios a serem corrigidos
            db.update_state('last_message_id', str(sent_message.message_id)) #salva o id para corrigir
            db.update_state('last_message', final_message) #salva a mensagem pra ir corrigindo
            print('messagem enviada pelo telegram')

            db.update_state('state', 'correcting') # mudando o estado pra corrigindo

        #depois que envia a mensagem ele muda pra corrigindo
        elif state == 'correcting':
            now = datetime.now()
            hour = str(now.hour)
            minute = str(now.minute - 1) #verificando o minuto anterior pra cobrir todas as velas caso tenha mais de uma
            current_time = hour + ":" + minute

            message_edit = db.get_state('last_message')

            hours_to_correct = int(db.get_state('hours_to_correct'))

            if hour_to_correct > 0:#quantidade de horarios a corrigir
                #verifica se tem o horario atual na mensagem pra ser corrigida
                if current_time in message_edit:
                    message_id = db.get_state('last_message_id')
                    max_result = db.get_max_result(int(hour), int(minute))

                    if max_result is not None:
                        if max_result >= CANDLE:
                            rest = 'GREEN'
                        else:
                            rest = 'RED'

                    # adiciona resultado na string
                    msg_edit = message_edit.replace(
                        current_time, f"{current_time} ({max_result}) {rest}"
                    )

                    # edita a mensagem no Telegram
                    bot.edit_message_text(
                        chat_id=CHAT_ID,
                        message_id=message_id,
                        text=msg_edit,
                        parse_mode="Markdown"
                    )

                    # atualiza mensagem salva
                    db.update_state('last_message', msg_edit)

                    # diminui contador de horários pendentes
                    db.update_state('hours_to_correct', str(hours_to_correct - 1))

                    print(f"Mensagem {message_id} editada com {current_time}")

                #cria o relatorio final e muda o estado
                else:
                    return None

        else:
            return None


    else:  
        print('Sem registro do horario configurado, capturando dados até completar')