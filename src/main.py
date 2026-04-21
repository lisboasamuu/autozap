"""
Script principal: main.py
Demonstra o fluxo completo com integração modular.
Uso:
    python main.py console               # simulação via terminal
    python main.py arquivo chat.txt      # processa arquivo exportado
    python main.py webhook               # inicia servidor Flask para webhook
"""

import sys
from .core_robot import RuleBasedBot
from storage import JSONStorage
from .whatssap_integration import (
    ConsoleSimulationSource,
    ExportedChatFileSource,
    WhatsAppWebhookSource
)

def criar_callback(bot: RuleBasedBot):
    """Retorna uma função callback que processa a mensagem e retorna a resposta."""
    def handle_message(sender_id: str, message_text: str) -> str:
        resultado = bot.processar_mensagem(message_text)
        return resultado['resposta']
    return handle_message

def main():
    # Inicializa storage e bot
    storage = JSONStorage(diretorio_dados="data")
    bot = RuleBasedBot(storage=storage)
    callback = criar_callback(bot)

    if len(sys.argv) < 2:
        print("Modo padrão: console")
        fonte = ConsoleSimulationSource()
    else:
        modo = sys.argv[1].lower()
        if modo == "console":
            fonte = ConsoleSimulationSource()
        elif modo == "arquivo" and len(sys.argv) >= 3:
            arquivo = sys.argv[2]
            fonte = ExportedChatFileSource(arquivo)
        elif modo == "webhook":
            fonte = WhatsAppWebhookSource()
        else:
            print("Uso: python main.py [console|arquivo <caminho>|webhook]")
            return

    fonte.start(callback)

if __name__ == "__main__":
    main()