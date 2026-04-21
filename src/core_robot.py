"""
Módulo: core_bot.py
Autor: Samuel Lisboa
Descrição: Lógica de resposta e extração de entidades para automação de atendimento.
           Utiliza regras baseadas em palavras-chave e expressões regulares simples.
           Preparado para evoluir com banco de dados e integração com API do WhatsApp.
"""

import re
from datetime import datetime
from typing import Dict, List, Optional, Tuple

class RuleBasedBot:
    """
    Bot baseado em regras para interpretar mensagens de clientes.
    Extrai intenção, entidades (nome, horário, serviço) e gera respostas apropriadas.
    """

    def __init__(self):
        # Dicionário de intenções com palavras-chave associadas
        self.intencoes = {
            "preco": ["preço", "preco", "valor", "custa", "cobram", "tabela", "orçamento", "orcamento"],
            "agendar": ["agendar", "marcar", "horário", "horario", "consulta", "reservar", "agendamento", "dia", "hora"],
            "servicos": ["serviços", "servicos", "fazem", "oferecem", "trabalham", "catalogo", "catálogo"],
            "saudacao": ["oi", "olá", "ola", "bom dia", "boa tarde", "boa noite", "hey", "e aí", "e ai"],
            "ajuda": ["ajuda", "help", "socorro", "como funciona", "opções", "opcoes"],
            "confirmar": ["sim", "confirmo", "ok", "certo", "beleza", "pode ser", "perfeito"],
            "cancelar": ["cancelar", "desmarcar", "cancelamento", "desistir"],
        }

        # Respostas padrão para cada intenção
        self.respostas = {
            "preco": "📋 Nossos preços:\n" \
                     "• Consultoria básica: R$ 50,00\n" \
                     "• Design de logo: R$ 150,00\n" \
                     "• Gestão de redes sociais: R$ 300,00/mês\n" \
                     "• Desenvolvimento web: sob consulta.\n" \
                     "Para agendar, informe nome, serviço desejado e horário preferido.",
            "agendar": "📅 Vamos agendar! Por favor, me informe:\n" \
                       "1. Seu nome completo\n" \
                       "2. Serviço desejado\n" \
                       "3. Data e horário (ex: 20/10 14h)",
            "servicos": "🛠️ Trabalhamos com:\n" \
                        "• Consultoria para pequenos negócios\n" \
                        "• Criação de identidade visual\n" \
                        "• Gestão de mídias sociais\n" \
                        "• Desenvolvimento de sites simples\n" \
                        "Diga 'preço' para saber valores.",
            "saudacao": "👋 Olá! Sou o assistente virtual da [Nome do Negócio].\n" \
                        "Como posso ajudar? Você pode perguntar sobre:\n" \
                        "• Preços\n• Serviços\n• Agendamento",
            "ajuda": "❓ Posso ajudar com:\n" \
                     "➡️ 'preço' ou 'valor' - Ver tabela\n" \
                     "➡️ 'serviços' - O que fazemos\n" \
                     "➡️ 'agendar' - Marcar um horário\n" \
                     "➡️ 'cancelar' - Cancelar agendamento",
            "confirmar": "✅ Ótimo! Seu agendamento foi registrado. Enviaremos confirmação em breve.",
            "cancelar": "🔁 Para cancelar um agendamento, por favor informe seu nome e a data/hora marcada.",
            "desconhecido": "❓ Desculpe, não entendi. Digite 'ajuda' para ver o que posso fazer.",
        }

        # Serviços disponíveis (usado para extração de entidade)
        self.servicos_validos = {
            "consultoria": ["consultoria", "consultar", "orientação"],
            "design": ["logo", "logotipo", "design", "identidade visual", "marca"],
            "social media": ["redes sociais", "mídias sociais", "instagram", "facebook", "gestão de redes"],
            "site": ["site", "página web", "website", "desenvolvimento web"],
        }

        # Compila padrões de regex para extração de entidades
        self.padrao_data_hora = re.compile(
            r"(\d{1,2}[/-]\d{1,2}(?:[/-]\d{2,4})?)\s*(?:às?| )\s*(\d{1,2}(?::\d{2})?\s*(?:h|hrs|horas)?)",
            re.IGNORECASE
        )
        self.padrao_horario_simples = re.compile(
            r"(\d{1,2}(?::\d{2})?\s*(?:h|hrs|horas|da manhã|da tarde|da noite))",
            re.IGNORECASE
        )

    def identificar_intencao(self, texto: str) -> str:
        """
        Analisa o texto e retorna a intenção mais provável baseada nas palavras-chave.
        """
        texto_lower = texto.lower()
        pontuacoes = {}
        for intencao, palavras in self.intencoes.items():
            pontos = sum(1 for palavra in palavras if palavra in texto_lower)
            if pontos > 0:
                pontuacoes[intencao] = pontos

        if not pontuacoes:
            return "desconhecido"
        # Retorna a intenção com maior pontuação
        return max(pontuacoes, key=pontuacoes.get)

    def extrair_nome(self, texto: str) -> Optional[str]:
        """
        Extrai um possível nome próprio do texto.
        Heurística simples: procura por padrão "nome é X" ou "me chamo X" ou duas palavras capitalizadas.
        """
        # Padrões comuns de apresentação
        padroes = [
            r"(?:meu nome é|me chamo|sou o|sou a|aqui é)\s+([A-ZÀ-Ú][a-zà-ú]+(?:\s+[A-ZÀ-Ú][a-zà-ú]+)*)",
            r"(?:nome[: ]+)([A-ZÀ-Ú][a-zà-ú]+(?:\s+[A-ZÀ-Ú][a-zà-ú]+)*)",
        ]
        for padrao in padroes:
            match = re.search(padrao, texto, re.IGNORECASE)
            if match:
                return match.group(1).strip()

        # Se não achar, procura sequência de duas palavras com iniciais maiúsculas
        palavras = texto.split()
        for i in range(len(palavras)-1):
            if palavras[i][0].isupper() and palavras[i+1][0].isupper():
                return f"{palavras[i]} {palavras[i+1]}"
        return None

    def extrair_servico(self, texto: str) -> Optional[str]:
        """
        Identifica o serviço mencionado baseado nos sinônimos.
        Retorna o nome canônico do serviço.
        """
        texto_lower = texto.lower()
        for servico, sinonimos in self.servicos_validos.items():
            for sin in sinonimos:
                if sin in texto_lower:
                    return servico
        return None

    def extrair_horario(self, texto: str) -> Optional[Dict]:
        """
        Extrai data e horário do texto. Retorna dict com 'data' e 'hora' ou None.
        Exemplo de retorno: {"data": "20/10", "hora": "14h"}
        """
        match = self.padrao_data_hora.search(texto)
        if match:
            data = match.group(1)
            hora = match.group(2)
            return {"data": data, "hora": hora}

        # Tenta achar apenas horário
        match_hora = self.padrao_horario_simples.search(texto)
        if match_hora:
            hora = match_hora.group(1)
            # Assume data de hoje
            data = datetime.now().strftime("%d/%m")
            return {"data": data, "hora": hora}

        return None

    def processar_mensagem(self, texto: str) -> Dict:
        """
        Método principal: recebe o texto do usuário, extrai intenção e entidades,
        e monta uma resposta adequada.
        Retorna um dicionário com:
            - intencao: str
            - entidades: dict com 'nome', 'servico', 'horario'
            - resposta: str
            - agendamento_completo: bool indicando se temos todas as informações para agendar
        """
        texto_limpo = texto.strip()
        intencao = self.identificar_intencao(texto_limpo)

        entidades = {
            "nome": self.extrair_nome(texto_limpo),
            "servico": self.extrair_servico(texto_limpo),
            "horario": self.extrair_horario(texto_limpo),
        }

        # Verifica se já temos dados suficientes para um agendamento (se intenção for agendar)
        agendamento_completo = False
        if intencao == "agendar":
            if entidades["nome"] and entidades["servico"] and entidades["horario"]:
                agendamento_completo = True
                resposta = (f"✅ Perfeito! Agendado para {entidades['nome']}:\n"
                            f"📌 Serviço: {entidades['servico']}\n"
                            f"📅 Data/Hora: {entidades['horario']['data']} às {entidades['horario']['hora']}\n"
                            f"Em breve enviaremos a confirmação. Obrigado!")
            else:
                # Monta resposta solicitando dados faltantes
                falta = []
                if not entidades["nome"]:
                    falta.append("nome completo")
                if not entidades["servico"]:
                    falta.append("serviço desejado")
                if not entidades["horario"]:
                    falta.append("data e horário")

                resposta = self.respostas["agendar"]
                if falta:
                    resposta += f"\n\n Ainda preciso de: {', '.join(falta)}."
        else:
            resposta = self.respostas.get(intencao, self.respostas["desconhecido"])

        return {
            "intencao": intencao,
            "entidades": entidades,
            "resposta": resposta,
            "agendamento_completo": agendamento_completo,
        }

# --- Simulação de uso (teste interno) ---
if __name__ == "__main__":
    bot = RuleBasedBot()

    # Lista de mensagens de exemplo para teste
    mensagens_teste = [
        "Olá, bom dia!",
        "Qual o preço de uma consultoria?",
        "Quero agendar um design de logo para amanhã às 15h. Meu nome é João Silva.",
        "Me chamo Maria Oliveira, gostaria de marcar gestão de redes sociais dia 25/10 às 10h.",
        "Tem como cancelar meu horário?",
        "Obrigado!",
    ]

    for msg in mensagens_teste:
        print(f"\n📩 Cliente: {msg}")
        resultado = bot.processar_mensagem(msg)
        print(f" Intenção: {resultado['intencao']}")
        print(f" Entidades: {resultado['entidades']}")
        print(f" Resposta: {resultado['resposta']}")
        if resultado['agendamento_completo']:
            print("🔔 (Agendamento completo! Pronto para salvar no banco)")