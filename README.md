# 🤖 Automação de Atendimento e Agendamento para Pequenos Negócios

## 📌 Visão Geral

Este projeto consiste em um sistema em Python para automatizar o atendimento de clientes e organização de pedidos/agendamentos, a partir de mensagens do WhatsApp (via exportação ou futura integração com API).

O sistema é projetado para:
- Reduzir trabalho manual
- Padronizar respostas
- Organizar dados de clientes automaticamente
- Facilitar o controle de serviços e horários

---

## 🎯 Objetivos

O sistema deve ser capaz de:

- 📩 Ler mensagens de clientes (WhatsApp exportado ou API)
- 🧠 Identificar intenção da mensagem
- 📋 Extrair informações como:
  - Nome do cliente
  - Serviço solicitado
  - Horário desejado
- 💰 Informar preços automaticamente
- 📊 Gerar uma planilha ou interface com os agendamentos

---

## 🧠 Arquitetura do Sistema

O projeto segue uma arquitetura modular para facilitar manutenção e escalabilidade.


---

## ⚙️ Etapas de Desenvolvimento

### 1. Lógica de Resposta
Sistema baseado em palavras-chave utilizando dicionários.

### 2. Armazenamento
Inicialmente JSON, com possibilidade de evolução para banco de dados.

### 3. Integração
Leitura de mensagens via:
- Exportação de conversa do WhatsApp
- (Futuro) API oficial ou não oficial

### 4. Interface
- Planilha (CSV/Excel)
- (Futuro) Interface web simples

---
