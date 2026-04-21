"""
Módulo: whatsapp_integration.py
Autor: Samuel Lisboa
Descrição: Abstração para entrada de mensagens de WhatsApp.
           Suporta: leitura de arquivo exportado, simulação via terminal,
           e webhook para API oficial do WhatsApp Business.
           Prepara o terreno para escalabilidade.
"""

import time
import re
from abc import ABC, abstractmethod
from typing import Callable, Optional, Dict, Any
import os
from flask import Flask
from requests import requests

class MessageSource(ABC):
    """Interface abstrata para fontes de mensagens."""
    
    @abstractmethod
    def start(self, callback: Callable[[str, str], Optional[str]]):
        """
        Inicia a escuta de mensagens.
        callback: função que recebe (remetente_id, texto_mensagem) e retorna a resposta.
        """
        pass

class ConsoleSimulationSource(MessageSource):
    """Fonte simulada: entrada pelo terminal (útil para testes)."""
    
    def start(self, callback: Callable[[str, str], Optional[str]]):
        print("🤖 Modo simulação (console). Digite 'sair' para encerrar.")
        while True:
            msg = input("📩 Você: ")
            if msg.lower() in ["sair", "exit", "quit"]:
                break
            resposta = callback("console_user", msg)
            if resposta:
                print(f"💬 Bot: {resposta}")

class ExportedChatFileSource(MessageSource):
    """
    Lê um arquivo .txt exportado do WhatsApp.
    Formato esperado (comum):
        [dd/mm/yyyy hh:mm] Nome: Mensagem
    """
    def __init__(self, caminho_arquivo: str, delay_entre_mensagens: float = 0.5):
        self.caminho = caminho_arquivo
        self.delay = delay_entre_mensagens

    def start(self, callback: Callable[[str, str], Optional[str]]):
        if not os.path.exists(self.caminho):
            print(f"❌ Arquivo {self.caminho} não encontrado.")
            return
        
        with open(self.caminho, 'r', encoding='utf-8') as f:
            linhas = f.readlines()
        
        # Expressão regular para extrair nome e mensagem do formato típico de exportação
        padrao = re.compile(r'\[?\d{1,2}[/-]\d{1,2}[/-]\d{2,4}[,\s]+\d{1,2}:\d{2}(?::\d{2})?\]?\s*(.+?):\s*(.*)')
        for linha in linhas:
            linha = linha.strip()
            if not linha:
                continue
            match = padrao.match(linha)
            if match:
                remetente = match.group(1).strip()
                mensagem = match.group(2).strip()
                resposta = callback(remetente, mensagem)
                if resposta:
                    print(f"💬 Resposta para {remetente}: {resposta}")
                time.sleep(self.delay)  # simula tempo real
            else:
                # Tenta extrair apenas mensagem (caso seja continuação)
                pass

class WhatsAppWebhookSource(MessageSource):
    """
    Fonte via webhook da WhatsApp Business API (Meta).
    Necessita de um servidor Flask em execução.
    Esta classe apenas define a interface; a implementação do servidor fica separada.
    """
    def __init__(self, host='0.0.0.0', port=5000):
        self.host = host
        self.port = port
        self.callback = None

    def start(self, callback: Callable[[str, str], Optional[str]]):
        self.callback = callback
        # Importamos Flask apenas quando necessário (evita dependência obrigatória)
        try:
            from flask import Flask, request, jsonify
        except ImportError:
            print("❌ Flask não instalado. Execute: pip install flask")
            return

        app = Flask(__name__)

        @app.route('/webhook', methods=['GET'])
        def verify_webhook():
            # Verificação exigida pela Meta ao configurar webhook
            verify_token = os.environ.get('WHATSAPP_VERIFY_TOKEN', 'meu_token_secreto')
            mode = request.args.get('hub.mode')
            token = request.args.get('hub.verify_token')
            challenge = request.args.get('hub.challenge')
            if mode and token:
                if mode == 'subscribe' and token == verify_token:
                    return challenge, 200
                else:
                    return 'Forbidden', 403
            return 'Bad Request', 400

        @app.route('/webhook', methods=['POST'])
        def receive_message():
            data = request.json
            # Estrutura típica da API do WhatsApp Cloud
            try:
                entry = data['entry'][0]
                changes = entry['changes'][0]
                value = changes['value']
                if 'messages' in value:
                    message = value['messages'][0]
                    if message['type'] == 'text':
                        remetente_id = message['from']
                        texto = message['text']['body']
                        resposta = self.callback(remetente_id, texto)
                        if resposta:
                            # Aqui você enviaria a resposta de volta via API do WhatsApp
                            # (necessário token de acesso e envio de POST para a API)
                            print(f"📤 Enviando resposta para {remetente_id}: {resposta}")
                            # Exemplo: enviar_mensagem_whatsapp(remetente_id, resposta)
            except (KeyError, IndexError) as e:
                print("⚠️ Erro ao processar payload:", e)
            return jsonify({"status": "ok"}), 200

        print(f"🚀 Servidor webhook rodando em http://{self.host}:{self.port}/webhook")
        app.run(host=self.host, port=self.port, debug=False)

# Função auxiliar para enviar mensagem via API (exemplo)
def enviar_mensagem_whatsapp(para: str, texto: str) -> bool:
    """
    Envia mensagem usando a API do WhatsApp Cloud.
    Requer variáveis de ambiente:
        WHATSAPP_PHONE_NUMBER_ID
        WHATSAPP_ACCESS_TOKEN
    """
    import requests
    phone_number_id = os.environ.get('WHATSAPP_PHONE_NUMBER_ID')
    access_token = os.environ.get('WHATSAPP_ACCESS_TOKEN')
    if not phone_number_id or not access_token:
        print("⚠️ Credenciais da API do WhatsApp não configuradas.")
        return False

    url = f"https://graph.facebook.com/v18.0/{phone_number_id}/messages"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }
    data = {
        "messaging_product": "whatsapp",
        "to": para,
        "type": "text",
        "text": {"body": texto}
    }
    response = requests.post(url, json=data, headers=headers)
    if response.status_code == 200:
        return True
    else:
        print("Erro ao enviar mensagem:", response.json())
        return False