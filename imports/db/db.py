import sqlite3
import os
from datetime import datetime, timedelta

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "database.db")

conn = sqlite3.connect(DB_PATH, check_same_thread=False)

def save_result(result: float):
    """Salva resultado com timestamp"""
    cursor = conn.cursor()
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute(
        "INSERT INTO results (result, created_at) VALUES (?, ?)",
        (result, timestamp)
    )
    conn.commit()

def has_record_in_specific_hour(hours_ago):
    """
    Verifica se há registro exatamente na hora específica.
    Ex: agora=03:00, hours_ago=2 → checa registros entre 01:00 e 01:59
    """
    cursor = conn.cursor()
    
    # calcula a hora alvo
    target_hour = datetime.now() - timedelta(hours=hours_ago)
    
    # define início e fim da hora
    start_time = target_hour.replace(minute=0, second=0, microsecond=0)
    end_time = target_hour.replace(minute=59, second=59, microsecond=999999)
    
    # converte para string
    start_str = start_time.strftime("%Y-%m-%d %H:%M:%S")
    end_str = end_time.strftime("%Y-%m-%d %H:%M:%S")
    
    # consulta apenas nesse intervalo de hora
    cursor.execute(
        "SELECT COUNT(*) FROM results WHERE created_at BETWEEN ? AND ?",
        (start_str, end_str)
    )
    
    count = cursor.fetchone()[0]
    return count > 0

def get_results_in_specific_hour(min_value: float, hours_ago: int):
    """
    Retorna todos os resultados da tabela 'results' cujo 'result' seja
    maior ou igual a min_value, mas apenas na hora específica definida
    por hours_ago (como na função has_record_in_specific_hour).
    Retorna lista de tuplas: (result, HH:MM)
    """
    cursor = conn.cursor()
    
    # calcula a hora alvo
    target_hour = datetime.now() - timedelta(hours=hours_ago)
    
    # define início e fim da hora
    start_time = target_hour.replace(minute=0, second=0, microsecond=0)
    end_time = target_hour.replace(minute=59, second=59, microsecond=999999)
    
    # converte para string
    start_str = start_time.strftime("%Y-%m-%d %H:%M:%S")
    end_str = end_time.strftime("%Y-%m-%d %H:%M:%S")
    
    # consulta apenas nesse intervalo de hora e pelo valor mínimo
    cursor.execute("""
        SELECT result, strftime('%H:%M', created_at) as hour_min
        FROM results
        WHERE created_at BETWEEN ? AND ?
          AND result >= ?
        ORDER BY created_at ASC
    """, (start_str, end_str, min_value))
    
    return cursor.fetchall()


def get_state(name: str):
    """
    Retorna o value da tabela states pelo name.
    Retorna None se não existir.
    """
    cursor = conn.cursor()
    cursor.execute("SELECT value FROM states WHERE name = ?", (name,))
    result = cursor.fetchone()
    return result[0] if result else None

def update_state(name: str, value: str):
    """
    Atualiza o value da tabela states pelo name.
    Se não existir, opcionalmente você pode inserir.
    """
    cursor = conn.cursor()
    cursor.execute("UPDATE states SET value = ? WHERE name = ?", (value, name))
    conn.commit()

def get_max_result(hour: int, minute: int):
    """
    Retorna o maior valor de 'result' no minuto específico do dia atual.
    Exemplo: (4, 15) → consulta entre 04:15:00 e 04:15:59 de hoje.
    Retorna None se não houver registros.
    """
    cursor = conn.cursor()
    
    # define data atual com hora/minuto passados
    today = datetime.now().date()
    start_time = datetime.combine(today, datetime.min.time()).replace(
        hour=hour, minute=minute, second=0, microsecond=0
    )
    end_time = start_time.replace(second=59, microsecond=999999)
    
    # converte para string
    start_str = start_time.strftime("%Y-%m-%d %H:%M:%S")
    end_str = end_time.strftime("%Y-%m-%d %H:%M:%S")
    
    cursor.execute("""
        SELECT MAX(result)
        FROM results
        WHERE created_at BETWEEN ? AND ?
    """, (start_str, end_str))
    
    result = cursor.fetchone()[0]
    return result


def close_connection():
    """Fecha conexão ao final do crawler"""
    conn.close()