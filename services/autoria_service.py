"""Metadados bibliográficos opcionais, com validação comum aos formulários."""
from werkzeug.exceptions import BadRequest

FIELDS=('autoria_genero','autoria_pais','autoria_fonte')

def validate(data):
    if not any(name in data for name in FIELDS):return None
    values=tuple(data.get(name) for name in FIELDS)
    if any(value is not None and (not isinstance(value,str) or len(value)>500) for value in values):
        raise BadRequest('Use textos de até 500 caracteres nos dados de autoria.')
    values=tuple(value.strip() or None if value is not None else None for value in values)
    gender,country,source=values
    if gender not in (None,'feminina','masculina','mista'):
        raise BadRequest('Classificação de autoria inválida.')
    if (gender or country) and not (source or '').strip():
        raise BadRequest('Informe a fonte consultada ou mantenha a autoria desconhecida.')
    return values
