"""DiceBear Adventurer Neutral 10.6.0, gerado localmente, sem serviço externo."""
from importlib.resources import files
import json
import re
import secrets
from dicebear import Avatar,Style,OptionsDescriptor
from werkzeug.exceptions import BadRequest

STYLE=Style.from_json(files('dicebear_styles').joinpath('adventurer-neutral.json').read_text('utf-8'))
DESCRIPTOR=OptionsDescriptor(STYLE).to_json()
FIELDS={key:value for key,value in DESCRIPTOR.items() if key.endswith(('Variant','Probability')) or value['type']=='color'}


def default():
    return {'estilo':'adventurer-neutral','versao':'10.6.0','seed':secrets.token_hex(16),'opcoes':{}}


def validate(data):
    if not isinstance(data,dict) or data.get('estilo')!='adventurer-neutral' or data.get('versao')!='10.6.0' or not re.fullmatch('[a-f0-9]{32}',str(data.get('seed',''))):
        raise BadRequest('Configuração de avatar inválida.')
    options=data.get('opcoes',{})
    if not isinstance(options,dict) or set(options)-set(FIELDS):
        raise BadRequest('Opção de avatar não suportada.')
    for key,value in options.items():
        field=FIELDS[key]
        if field['type']=='enum' and value not in field['values']:
            raise BadRequest('Variante de avatar inválida.')
        if field['type']=='number' and (type(value) is not int or not 0<=value<=100):
            raise BadRequest('Probabilidade inválida.')
        if field['type']=='color' and (not isinstance(value,str) or not re.fullmatch('#[a-fA-F0-9]{6}',value)):
            raise BadRequest('Cor inválida.')
    return {k:data[k] for k in ('estilo','versao','seed')} | {'opcoes':options}


def render(data):
    data=validate(data)
    return Avatar(STYLE,{'seed':data['seed'],'size':160,**data['opcoes']}).to_data_uri()
