"""
Módulo: storage.py
Autor: Samuel Lisboa
Descrição: Camada de persistência para agendamentos, clientes e serviços.
           Fornece uma interface abstrata e uma implementação concreta em JSON.
           Preparado para futura migração para SQLite/PostgreSQL.
"""

import json
import os
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Dict, List, Optional, Any
import csv

class StorageInterface(ABC):
    """Interface abstrata para operações de armazenamento."""
    
    @abstractmethod
    def salvar_agendamento(self, dados: Dict[str, Any]) -> bool:
        """Salva um agendamento completo."""
        pass
    
    @abstractmethod
    def listar_agendamentos(self, filtro: Optional[Dict] = None) -> List[Dict]:
        """Lista agendamentos, opcionalmente filtrados."""
        pass
    
    @abstractmethod
    def atualizar_agendamento(self, id_agendamento: str, novos_dados: Dict) -> bool:
        """Atualiza um agendamento existente."""
        pass
    
    @abstractmethod
    def cancelar_agendamento(self, id_agendamento: str) -> bool:
        """Cancela (remove ou marca como cancelado) um agendamento."""
        pass
    
    @abstractmethod
    def salvar_cliente(self, dados_cliente: Dict) -> bool:
        """Registra ou atualiza dados de um cliente."""
        pass
    
    @abstractmethod
    def buscar_cliente(self, nome: str) -> Optional[Dict]:
        """Busca cliente por nome (simples)."""
        pass

class JSONStorage(StorageInterface):
    """
    Implementação concreta usando arquivos JSON.
    Estrutura de arquivos:
        data/
            agendamentos.json
            clientes.json
            servicos.json (pode ser usado para preços dinâmicos)
    """
    
    def __init__(self, diretorio_dados: str = "data"):
        self.diretorio = diretorio_dados
        os.makedirs(self.diretorio, exist_ok=True)
        self.arquivo_agendamentos = os.path.join(self.diretorio, "agendamentos.json")
        self.arquivo_clientes = os.path.join(self.diretorio, "clientes.json")
        self.arquivo_servicos = os.path.join(self.diretorio, "servicos.json")
        
        # Inicializa arquivos se não existirem
        self._inicializar_arquivos()
    
    def _inicializar_arquivos(self):
        """Cria arquivos JSON vazios se necessário."""
        if not os.path.exists(self.arquivo_agendamentos):
            self._salvar_json(self.arquivo_agendamentos, [])
        if not os.path.exists(self.arquivo_clientes):
            self._salvar_json(self.arquivo_clientes, [])
        if not os.path.exists(self.arquivo_servicos):
            # Tabela de preços padrão (pode ser editada posteriormente)
            servicos_padrao = [
                {"nome": "consultoria", "preco": 50.00, "descricao": "Consultoria básica"},
                {"nome": "design", "preco": 150.00, "descricao": "Design de logo / identidade visual"},
                {"nome": "social media", "preco": 300.00, "descricao": "Gestão de redes sociais (mensal)"},
                {"nome": "site", "preco": 800.00, "descricao": "Desenvolvimento de site institucional"}
            ]
            self._salvar_json(self.arquivo_servicos, servicos_padrao)
    
    def _carregar_json(self, caminho: str) -> Any:
        """Carrega dados de um arquivo JSON."""
        try:
            with open(caminho, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return [] if 'agendamentos' in caminho or 'clientes' in caminho else {}
    
    def _salvar_json(self, caminho: str, dados: Any) -> None:
        """Salva dados em arquivo JSON com indentação."""
        with open(caminho, 'w', encoding='utf-8') as f:
            json.dump(dados, f, indent=2, ensure_ascii=False)
    
    def _gerar_id(self) -> str:
        """Gera um ID único baseado em timestamp."""
        return datetime.now().strftime("%Y%m%d%H%M%S%f")
    
    # --- Implementação dos métodos da interface ---
    
    def salvar_agendamento(self, dados: Dict) -> bool:
        """
        Salva um novo agendamento.
        Espera um dicionário com: nome_cliente, servico, data, hora, (opcional: telefone, observacoes)
        Adiciona campos: id, status, criado_em.
        """
        agendamentos = self._carregar_json(self.arquivo_agendamentos)
        
        novo_agendamento = {
            "id": self._gerar_id(),
            "status": "confirmado",
            "criado_em": datetime.now().isoformat(),
            **dados
        }
        agendamentos.append(novo_agendamento)
        self._salvar_json(self.arquivo_agendamentos, agendamentos)
        return True
    
    def listar_agendamentos(self, filtro: Optional[Dict] = None) -> List[Dict]:
        """Lista todos os agendamentos, opcionalmente filtrando por campos."""
        agendamentos = self._carregar_json(self.arquivo_agendamentos)
        if not filtro:
            return agendamentos
        
        resultado = []
        for ag in agendamentos:
            match = True
            for chave, valor in filtro.items():
                if ag.get(chave) != valor:
                    match = False
                    break
            if match:
                resultado.append(ag)
        return resultado
    
    def atualizar_agendamento(self, id_agendamento: str, novos_dados: Dict) -> bool:
        agendamentos = self._carregar_json(self.arquivo_agendamentos)
        for ag in agendamentos:
            if ag.get("id") == id_agendamento:
                ag.update(novos_dados)
                ag["atualizado_em"] = datetime.now().isoformat()
                self._salvar_json(self.arquivo_agendamentos, agendamentos)
                return True
        return False
    
    def cancelar_agendamento(self, id_agendamento: str) -> bool:
        """Marca o status como 'cancelado' ao invés de remover."""
        return self.atualizar_agendamento(id_agendamento, {"status": "cancelado"})
    
    def salvar_cliente(self, dados_cliente: Dict) -> bool:
        """Salva ou atualiza cliente (identificado por nome, simplificado)."""
        clientes = self._carregar_json(self.arquivo_clientes)
        nome = dados_cliente.get("nome")
        if not nome:
            return False
        
        # Verifica se já existe (por nome exato)
        for cliente in clientes:
            if cliente.get("nome") == nome:
                cliente.update(dados_cliente)
                cliente["ultima_interacao"] = datetime.now().isoformat()
                self._salvar_json(self.arquivo_clientes, clientes)
                return True
        
        # Novo cliente
        novo_cliente = {
            "id": self._gerar_id(),
            "criado_em": datetime.now().isoformat(),
            "ultima_interacao": datetime.now().isoformat(),
            **dados_cliente
        }
        clientes.append(novo_cliente)
        self._salvar_json(self.arquivo_clientes, clientes)
        return True
    
    def buscar_cliente(self, nome: str) -> Optional[Dict]:
        clientes = self._carregar_json(self.arquivo_clientes)
        for c in clientes:
            if c.get("nome", "").lower() == nome.lower():
                return c
        return None
    
    # --- Métodos adicionais úteis para exportação/planilha ---
    
    def exportar_agendamentos_csv(self, caminho_csv: str, status: Optional[str] = None) -> str:
        """
        Exporta agendamentos para um arquivo CSV (planilha).
        Retorna o caminho do arquivo gerado.
        """
        agendamentos = self.listar_agendamentos()
        if status:
            agendamentos = [a for a in agendamentos if a.get("status") == status]
        
        if not agendamentos:
            return ""
        
        # Define colunas relevantes para a planilha
        colunas = ["id", "nome_cliente", "servico", "data", "hora", "status", "criado_em", "observacoes"]
        with open(caminho_csv, 'w', newline='', encoding='utf-8-sig') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=colunas, extrasaction='ignore')
            writer.writeheader()
            for ag in agendamentos:
                writer.writerow(ag)
        return caminho_csv
    
    def carregar_tabela_precos(self) -> List[Dict]:
        """Retorna a lista de serviços com preços atuais."""
        return self._carregar_json(self.arquivo_servicos)
    
    def atualizar_preco_servico(self, nome_servico: str, novo_preco: float) -> bool:
        """Atualiza o preço de um serviço específico."""
        servicos = self._carregar_json(self.arquivo_servicos)
        for s in servicos:
            if s["nome"].lower() == nome_servico.lower():
                s["preco"] = novo_preco
                self._salvar_json(self.arquivo_servicos, servicos)
                return True
        return False