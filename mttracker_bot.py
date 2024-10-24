import requests
from bs4 import BeautifulSoup
import time
import logging
import telegram
from telegram import Bot
import asyncio
import json
import os

# Configuração do logging para debug
logging.basicConfig(level=logging.INFO)

# Obtendo o token do bot, chat_id e topic_id das variáveis de ambiente
BOT_TOKEN = os.getenv('BOT_TOKEN')
CHAT_ID = os.getenv('CHAT_ID')
TOPIC_ID = os.getenv('TOPIC_ID')

# URL do site que será monitorado
url = 'https://multitracks.com.br/songs/?order=recent&label=Lançamentos'

# Nome do arquivo JSON para armazenar lançamentos notificados
JSON_FILE = 'lancamentos_notificados.json'

# Inicializando o bot do Telegram
bot = Bot(token=BOT_TOKEN)

# Função para carregar os lançamentos notificados do arquivo JSON
def carregar_lancamentos_notificados():
    if os.path.exists(JSON_FILE):
        with open(JSON_FILE, 'r', encoding='utf-8') as file:
            return json.load(file)
    return []

# Função para salvar os lançamentos notificados no arquivo JSON
def salvar_lancamentos_notificados(lancamentos):
    with open(JSON_FILE, 'w', encoding='utf-8') as file:
        json.dump(lancamentos, file, ensure_ascii=False, indent=4)

# Carrega os lançamentos notificados ao iniciar
lancamentos_notificados = carregar_lancamentos_notificados()

# Função para verificar o site por novidades
def verificar_novidades():
    logging.info("Verificando por novidades...")

    response = requests.get(url)

    # Verificando se a requisição foi bem-sucedida
    if response.status_code != 200:
        logging.error(f"Erro ao acessar a página: {response.status_code}")
        return []

    soup = BeautifulSoup(response.text, 'html.parser')

    # Selecionar a lista de músicas
    lista_musicas = soup.find('ul', {'id': 'playlist', 'class': 'song-list mod-new mod-menu'})
    if not lista_musicas:
        logging.error("Não foi possível localizar a lista de músicas.")
        return []

    musicas = lista_musicas.find_all('li', {'class': 'song-list--item media-player--row'})

    novos_lancamentos = []

    for musica in musicas:
        try:
            nome_musica_element = musica.find('a', {'class': 'song-list--item--primary'})
            nome_artista_element = musica.find('a', {'class': 'song-list--item--secondary'})
            link_element = musica.find('a', {'class': 'song-list--item--primary'})
            img_element = musica.find('img', {'class': 'song-list--item--player-img--img'})

            if nome_musica_element and nome_artista_element and link_element and img_element:
                nome_musica = nome_musica_element.get_text(strip=True)
                nome_artista = nome_artista_element.get_text(strip=True)
                link = link_element['href']
                link_completo = f"https://multitracks.com.br{link}"
                img_src = img_element['src']
                img_alta_resolucao = img_src.replace('/40/', '/284/')

                # Verifica se o lançamento já foi notificado pelo link
                if not any(lancamento['link'] == link_completo for lancamento in lancamentos_notificados):
                    logging.info(f"Novo lançamento encontrado: {nome_musica} de {nome_artista}")
                    novos_lancamentos.append({
                        'link': link_completo,
                        'titulo': nome_musica,
                        'artista': nome_artista,
                        'img': img_alta_resolucao
                    })
                else:
                    logging.info(f"Lançamento já notificado: {nome_musica}")
            else:
                logging.warning(f"Não foi possível encontrar todos os elementos da música:\n{musica.prettify()}")

        except Exception as e:
            logging.error(f"Erro ao processar uma música: {e}")

    return novos_lancamentos

# Função assíncrona para enviar mensagem no Telegram para um tópico
async def enviar_mensagem(lancamento, delay=10):
    mensagem = (
        f"Novo Lançamento no site Multitracks Brasil!\n"
        f"{lancamento['titulo']}, de {lancamento['artista']}\n"
        f"{lancamento['link']}"
    )

    try:
        await asyncio.sleep(delay)
        await bot.send_photo(
            chat_id=CHAT_ID,
            photo=lancamento['img'],
            caption=mensagem,
            message_thread_id=TOPIC_ID  # Envia para o tópico específico
        )
        logging.info(f"Mensagem enviada: {lancamento['titulo']}")
        
        # Salvar lançamento notificado no arquivo JSON
        lancamentos_notificados.append({
            'link': lancamento['link'],
            'titulo': lancamento['titulo'],
            'artista': lancamento['artista']
        })
        salvar_lancamentos_notificados(lancamentos_notificados)

    except Exception as e:
        logging.error(f"Erro ao enviar mensagem: {e}")

# Função principal para verificar o site periodicamente e enviar mensagens
async def monitorar_lancamentos():
    while True:
        novidades = verificar_novidades()
        if novidades:
            novidades.reverse()
            for novidade in novidades:
                await enviar_mensagem(novidade)

        await asyncio.sleep(600)  # Verifica a cada 10 minutos

# Executa o loop de monitoramento
if __name__ == "__main__":
    asyncio.run(monitorar_lancamentos())
