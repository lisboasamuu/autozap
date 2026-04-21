"""
Módulo: core_bot.py
Autor: Samuel Lisboa
Descrição: Lógica de resposta e extração de entidades para automação de atendimento.
           Utiliza regras baseadas em palavras-chave e expressões regulares simples.
           Integrado com camada de persistência (JSONStorage) para salvar agendamentos
           e carregar preços dinâmicos. Inclui verificação de conflito de horários.
           Preparado para evoluir com banco de dados e integração com API do WhatsApp.
"""

import re
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, TYPE_CHECKING

if TYPE_CHECKING:
    from storage import JSONStorage  # Importação apenas para type hints


class RuleBasedBot:
    """
    Bot baseado em regras para interpretar mensagens de clientes.
    Extrai intenção, entidades (nome, horário, serviço) e gera respostas apropriadas.
    Pode ser integrado a um sistema de armazenamento para persistir agendamentos.
    """

    def __init__(self, storage: Optional['JSONStorage'] = None):
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

        # Respostas padrão para cada intenção (os preços podem ser sobrescritos se houver storage)
        self.respostas = {
            "preco": "📋 Nossos preços:\n"
                     "• Consultoria básica: R$ 50,00\n"
                     "• Design de logo: R$ 150,00\n"
                     "• Gestão de redes sociais: R$ 300,00/mês\n"
                     "• Desenvolvimento web: sob consulta.\n"
                     "Para agendar, informe nome, serviço desejado e horário preferido.",
            "agendar": "📅 Vamos agendar! Por favor, me informe:\n"
                       "1. Seu nome completo\n"
                       "2. Serviço desejado\n"
                       "3. Data e horário (ex: 20/10 14h)",
            "servicos": "🛠️ Trabalhamos com:\n"
                        "• Consultoria para pequenos negócios\n"
                        "• Criação de identidade visual\n"
                        "• Gestão de mídias sociais\n"
                        "• Desenvolvimento de sites simples\n"
                        "Diga 'preço' para saber valores.",
            "saudacao": "👋 Olá! Sou o assistente virtual da [Nome do Negócio].\n"
                        "Como posso ajudar? Você pode perguntar sobre:\n"
                        "• Preços\n• Serviços\n• Agendamento",
            "ajuda": "❓ Posso ajudar com:\n"
                     "➡️ 'preço' ou 'valor' - Ver tabela\n"
                     "➡️ 'serviços' - O que fazemos\n"
                     "➡️ 'agendar' - Marcar um horário\n"
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

        # Integração com storage (opcional)
        self.storage = storage
        if self.storage:
            self._atualizar_resposta_preco_dinamica()

    def _atualizar_resposta_preco_dinamica(self):
        """
        Atualiza a resposta de 'preco' com base na tabela de serviços carregada do storage.
        Permite que os preços sejam modificados sem alterar o código fonte.
        """
        try:
            servicos = self.storage.carregar_tabela_precos()
            linhas = []
            for s in servicos:
                # Formata preço com vírgula decimal para padrão brasileiro
                preco_formatado = f"R$ {s['preco']:.2f}".replace('.', ',')
                linhas.append(f"• {s['descricao']}: {preco_formatado}")
            if linhas:
                self.respostas["preco"] = "📋 Nossos preços:\n" + "\n".join(linhas) + \
                                          "\n\nPara agendar, informe nome, serviço desejado e horário preferido."
        except Exception as e:
            # Se houver qualquer erro ao carregar preços, mantém a resposta padrão.
            print(f"Aviso: não foi possível carregar preços dinâmicos. Usando valores padrão. Erro: {e}")

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
        for i in range(len(palavras) - 1):
            if palavras[i] and palavras[i][0].isupper() and palavras[i + 1] and palavras[i + 1][0].isupper():
                return f"{palavras[i]} {palavras[i + 1]}"
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

    def _parse_data_hora(self, data_str: str, hora_str: str) -> Optional[datetime]:
        """
        Converte strings de data e hora extraídas para um objeto datetime.
        Suporta formatos como "20/10", "20/10/2025", "14h", "14:30", "14 horas".
        Retorna None se não conseguir interpretar.
        """
        # Normaliza a data: assume ano atual se não informado
        data_str = data_str.strip()
        # Substitui traço por barra
        data_str = data_str.replace('-', '/')
        partes_data = data_str.split('/')
        if len(partes_data) == 2:
            dia, mes = partes_data
            ano = datetime.now().year
        elif len(partes_data) == 3:
            dia, mes, ano = partes_data
            if len(ano) == 2:
                ano = "20" + ano
        else:
            return None

        # Normaliza a hora: extrai números
        hora_str = hora_str.lower().strip()
        # Remove "h", "hrs", "horas", etc.
        hora_limpa = re.sub(r'[^\d:]', '', hora_str)
        if ':' in hora_limpa:
            hora, minuto = hora_limpa.split(':')
        else:
            hora = hora_limpa
            minuto = "0"

        try:
            return datetime(int(ano), int(mes), int(dia), int(hora), int(minuto))
        except ValueError:
            return None

    def _verificar_conflito_horario(self, data_hora: datetime, servico: Optional[str] = None) -> bool:
        """
        Verifica se já existe agendamento para o mesmo horário.
        Considera um intervalo de tolerância de ±30 minutos para evitar sobreposição.
        Se servico for informado, verifica apenas conflitos para aquele serviço específico.
        Retorna True se houver conflito, False caso contrário.
        """
        if not self.storage:
            return False  # Sem storage, assume sempre disponível

        agendamentos = self.storage.listar_agendamentos({"status": "confirmado"})
        for ag in agendamentos:
            # Se serviço foi especificado e é diferente, ignora (opcional)
            if servico and ag.get("servico") != servico:
                continue

            # Converte data e hora do agendamento armazenado
            try:
                data_ag = ag["data"]
                hora_ag = ag["hora"]
                dt_ag = self._parse_data_hora(data_ag, hora_ag)
                if dt_ag is None:
                    continue
            except KeyError:
                continue

            # Verifica diferença de tempo (menos de 30 minutos é considerado conflito)
            diferenca = abs((dt_ag - data_hora).total_seconds()) / 60.0
            if diferenca < 30:
                return True
        return False

    def processar_mensagem(self, texto: str) -> Dict:
        """
        Método principal: recebe o texto do usuário, extrai intenção e entidades,
        e monta uma resposta adequada.
        Se um storage estiver configurado e os dados do agendamento estiverem completos,
        persiste o agendamento e atualiza informações do cliente.
        Antes de confirmar, verifica se o horário está disponível.

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
                # Converte data/hora para objeto datetime
                dt_agendamento = self._parse_data_hora(
                    entidades["horario"]["data"],
                    entidades["horario"]["hora"]
                )

                if dt_agendamento is None:
                    # Data/hora inválida
                    resposta = (f"❌ Não consegui entender a data/hora informada. "
                                f"Por favor, use um formato como '20/10 14h'.")
                else:
                    # Verifica conflito de horário
                    conflito = self._verificar_conflito_horario(dt_agendamento, entidades["servico"])
                    if conflito:
                        # Horário ocupado, sugere alternativas (simples: +1h, +2h)
                        alternativas = []
                        for delta in [1, 2, 3]:
                            novo_horario = dt_agendamento + timedelta(hours=delta)
                            # Verifica se o novo horário também está livre (simples)
                            if not self._verificar_conflito_horario(novo_horario, entidades["servico"]):
                                alt_str = novo_horario.strftime("%d/%m %Hh")
                                alternativas.append(alt_str)
                        if alternativas:
                            sugestao = " ou ".join(alternativas[:2])
                            resposta = (f"⛔ Ops! O horário {entidades['horario']['data']} às {entidades['horario']['hora']} "
                                        f"já está ocupado para {entidades['servico']}.\n"
                                        f"Que tal tentar um destes horários: {sugestao}?")
                        else:
                            resposta = (f"⛔ O horário {entidades['horario']['data']} às {entidades['horario']['hora']} "
                                        f"está indisponível. Por favor, informe outra data ou horário.")
                    else:
                        # Horário livre, confirma agendamento
                        agendamento_completo = True
                        resposta = (f"✅ Perfeito! Agendado para {entidades['nome']}:\n"
                                    f"📌 Serviço: {entidades['servico']}\n"
                                    f"📅 Data/Hora: {entidades['horario']['data']} às {entidades['horario']['hora']}\n"
                                    f"Em breve enviaremos a confirmação. Obrigado!")

                        # Persistência automática se storage estiver disponível
                        if self.storage:
                            dados_agendamento = {
                                "nome_cliente": entidades["nome"],
                                "servico": entidades["servico"],
                                "data": entidades["horario"]["data"],
                                "hora": entidades["horario"]["hora"],
                                "observacoes": texto_limpo  # contexto original
                            }
                            try:
                                self.storage.salvar_agendamento(dados_agendamento)
                                # Registra ou atualiza o cliente
                                self.storage.salvar_cliente({"nome": entidades["nome"]})
                                resposta += "\n\n💾 Agendamento registrado com sucesso no sistema!"
                            except Exception as e:
                                resposta += f"\n\n⚠️ Agendamento confirmado, mas houve um erro ao salvar: {e}"
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
                    resposta += f"\n\n⚠️ Ainda preciso de: {', '.join(falta)}."
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
    # Teste sem storage (comportamento original)
    print("=== TESTE SEM STORAGE ===\n")
    bot_sem_storage = RuleBasedBot()

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
        resultado = bot_sem_storage.processar_mensagem(msg)
        print(f"🤖 Intenção: {resultado['intencao']}")
        print(f"📎 Entidades: {resultado['entidades']}")
        print(f"💬 Resposta: {resultado['resposta']}")
        if resultado['agendamento_completo']:
            print("🔔 (Agendamento completo! Pronto para salvar no banco)")

    # Teste com storage (necessário ter a classe JSONStorage no path)
    print("\n\n=== TESTE COM STORAGE (JSON) ===\n")
    try:
        from storage import JSONStorage
        storage = JSONStorage(diretorio_dados="data_teste")
        bot_com_storage = RuleBasedBot(storage=storage)

        # Simula algumas mensagens
        msgs = [
            "preço?",
            "Quero agendar consultoria para amanhã às 9h. Sou Carlos Mendes.",
            "Agendar consultoria amanhã 9h com Pedro Alves."  # Tentativa de conflito
        ]
        for msg in msgs:
            print(f"\n📩 Cliente: {msg}")
            res = bot_com_storage.processar_mensagem(msg)
            print(f"💬 Resposta: {res['resposta']}")

        # Lista agendamentos salvos
        print("\n📋 Agendamentos armazenados:")
        for ag in storage.listar_agendamentos():
            print(f"  - {ag['data']} {ag['hora']}: {ag['nome_cliente']} ({ag['servico']})")
    except ImportError:
        print("Módulo 'storage' não encontrado. Execute o teste com storage após criar storage.py")