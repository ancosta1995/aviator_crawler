from datetime import datetime, timedelta
import configparser
import os
from imports.db import db
from telegram import Bot
import asyncio
import re
import json  # NOVO IMPORT

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

MARTINGALE = 3  # MANTIDO

TOKEN = config['telegram']['token']
CHAT_ID = config['telegram']['chat_id']
MESSAGE = "LISTA PROBABILIDADE AVIATOR \n\n💳 Segurança em 2x 💳\n✈️ Buscar {{candle}}.00x a 50x \n\n{{hours}}\n\n⚠️ Entrar 15s antes ou no horário exato! \n🔞 Proibido para menores idade\n\n[CLIQUE AQUI E SE CADASTRE](https://cassinopro.bet/cadastro?ref=REGISTRO)"

bot = Bot(token=TOKEN)

def remove_markes(text):
    return re.sub(r'\(\(.*?\)\)', '', text)

# NOVAS FUNÇÕES PARA MARTINGALE
def get_martingale_data():
    data = db.get_state('martingale_data')
    if data and data != '':
        try:
            return json.loads(data)
        except:
            return {}
    return {}

def save_martingale_data(data):
    db.update_state('martingale_data', json.dumps(data))

def process_martingales(current_time, martingale_data, message_edit, message_id):
    if not martingale_data:
        return message_edit
    
    current_hour, current_minute = map(int, current_time.split(':'))
    completed_martingales = []
    updated_message = message_edit
    
    for original_time, martingale_info in martingale_data.items():
        # Calcular qual minuto devemos verificar para este martingale
        original_hour, original_minute = map(int, original_time.split(':'))
        target_minute = (original_minute + martingale_info['current_level']) % 60
        target_hour = original_hour + ((original_minute + martingale_info['current_level']) // 60)
        
        # Se chegou a hora de verificar este martingale
        if current_hour == target_hour and current_minute == target_minute:
            max_result = db.get_max_result(current_hour, current_minute)
            
            if max_result is not None and max_result >= CANDLE:
                # GREEN no martingale
                updated_message = update_martingale_line_success(
                    updated_message, message_id, original_time, 
                    martingale_info, max_result
                )
                completed_martingales.append(original_time)
                db.update_state('greens', str(int(db.get_state('greens')) + 1))
                print(f"Martingale GREEN: {original_time} -> M{martingale_info['current_level']}")
                
            elif martingale_info['current_level'] >= MARTINGALE:
                # Martingale esgotado - AGORA SIM conta como RED
                completed_martingales.append(original_time)
                db.update_state('reds', str(int(db.get_state('reds')) + 1))  # ✅ ADICIONADO AQUI
                print(f"Martingale esgotado: {original_time} - RED final contabilizado")
            else:
                # Continuar martingale
                martingale_data[original_time]['current_level'] += 1
                print(f"Martingale continua: {original_time} -> nível {martingale_data[original_time]['current_level']}")
    
    # Remover martingales completados
    for completed in completed_martingales:
        del martingale_data[completed]
    
    return updated_message

def update_martingale_line_success(message_edit, message_id, original_time, martingale_info, result_value):
    lines = message_edit.split("\n")
    line_hour = f"⏰ {original_time}"
    
    for i, line in enumerate(lines):
        if line_hour in line and "((line_correct))" in line:
            # Substituir o resultado RED pelo GREEN com indicador de martingale
            parts = line.split("((line_correct))")
            base_part = parts[0]
            
            # Remover resultado RED anterior
            if LINE_RED.replace('{{vela}}', str(martingale_info['original_result'])) in base_part:
                base_part = base_part.replace(LINE_RED.replace('{{vela}}', str(martingale_info['original_result'])), "").strip()
            
            # Adicionar resultado GREEN com martingale
            martingale_level = martingale_info['current_level']
            new_result = LINE_GREEN.replace('{{vela}}', str(result_value))
            new_result += f" (M{martingale_level})"
            
            lines[i] = f"{base_part} {new_result}((line_correct))"
            
            updated_message = "\n".join(lines)
            
            # Atualizar no Telegram
            asyncio.run(bot.edit_message_text(
                chat_id=CHAT_ID,
                message_id=message_id,
                text=remove_markes(updated_message),
                parse_mode="Markdown",
                disable_web_page_preview=True
            ))
            
            db.update_state('last_message', updated_message)
            break
    
    return updated_message

# FUNÇÃO PRINCIPAL MODIFICADA
def analisys():
    check = db.has_record_in_specific_hour(HOUR)

    if not check:
        print('Sem registro do horario configurado, capturando dados até completar')
        return

    state = db.get_state('state')

    if state == 'sending':
        hours = db.get_results_in_specific_hour(CANDLE, HOUR)
        
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
        
        sent_message = asyncio.run(bot.send_message(chat_id=CHAT_ID, text=remove_markes(final_message), parse_mode="Markdown", disable_web_page_preview=True))
        
        db.update_state('hours_to_correct', str(hour_to_correct))
        db.update_state('last_message_id', str(sent_message.message_id))
        db.update_state('last_message', final_message)
        
        # Limpar dados de martingale para novo ciclo
        save_martingale_data({})
        
        print('mensagem enviada pelo telegram')
        db.update_state('state', 'correcting')

    elif state == 'correcting':
        current_time = (datetime.now() - timedelta(minutes=1)).strftime("%H:%M")
        message_edit = db.get_state('last_message')
        message_id = db.get_state('last_message_id')
        hours_to_correct = int(db.get_state('hours_to_correct'))
        
        # Carregar e processar martingales
        martingale_data = get_martingale_data()
        message_edit = process_martingales(current_time, martingale_data, message_edit, message_id)

        # Processar horários normais
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
                            # GREEN imediato - conta agora
                            db.update_state('greens', str(int(db.get_state('greens')) + 1))
                            rest = LINE_GREEN.replace('{{vela}}', str(max_result))
                        else:
                            # RED - MAS NÃO CONTA AINDA! Só inicia martingale
                            rest = LINE_RED.replace('{{vela}}', str(max_result))
                            
                            # Adicionar ao sistema de martingale SEM contar RED
                            martingale_data[current_time] = {
                                'original_time': current_time,
                                'current_level': 1,
                                'original_result': max_result
                            }
                            
                            # ❌ REMOVIDO: db.update_state('reds', str(int(db.get_state('reds')) + 1))

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
                    save_martingale_data(martingale_data)
                    print(f"Mensagem {message_id} editada com {current_time}")
                    break

        # Finalização do ciclo
        if hours_to_correct == 0 or datetime.now().minute == 0:
            greens = int(db.get_state('greens'))
            reds = int(db.get_state('reds'))

            total = greens + reds

            if total > 0:
                percent_greens = round((greens / total) * 100, 2)
                percent_reds = round((reds / total) * 100, 2)
            else:
                percent_greens = 0
                percent_reds = 0

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
            save_martingale_data({})  # Limpar martingales

            print(f"Ciclo finalizado, reiniciando")