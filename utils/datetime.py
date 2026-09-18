from datetime import datetime
from datetime import timedelta
from datetime import timezone


def get_brasilia_now():
    """Retorna datetime atual no fuso horário de Brasília (UTC-3)"""
    return datetime.now(timezone(timedelta(hours=-3)))


def get_brasilia_today():
    """Retorna a data atual (sem hora) em Brasília"""
    return get_brasilia_now().date()
