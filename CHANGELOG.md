# Changelog

## [2026-01-30] - Configuração Inicial e Geração de Relatório

### Adicionado
- **Extração de Dados**: Utilizado `pdftotext` para converter PDFs bancários (`Sicoob _ Internet banking DEZ 2025.pdf`, `JAN 2026.pdf`, e fatura de cartão) em arquivos de texto processáveis.
- **Script de Processamento (`parse_expenses.py`)**:
  - Criado script Python para ler os arquivos `.txt`.
  - Implementada lógica Regex para extrair datas, descrições e valores.
  - Implementada lógica para distinguir Pix, Débito e Crédito.
  - Adicionada regra para detectar e segregar o pagamento da fatura do cartão (R$ 3.720,51) para evitar duplicidade na soma total.
- **Interface Visual (`relatorio_viagem.html`)**:
  - Gerado arquivo HTML autossuficiente (single-file).
  - Tabela com filtros e badges coloridos por tipo de gasto.
  - Dashboard com somatórios (Total Geral, Pix, Débito, Crédito).

### Dados Processados
- Extrato Conta Corrente: Dezembro 2025 e Janeiro 2026.
- Extrato Cartão de Crédito: Lançamentos disponíveis até 08/01/2026.

### Observações
- O extrato de cartão de crédito atual só cobre gastos até 08/01. Gastos posteriores a essa data (até o fim da viagem em 28/01) ainda não foram importados pois o arquivo correspondente não estava disponível.
