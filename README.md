# Relatório de Gastos - Férias Brasil (2025/2026)

Este projeto automatiza a consolidação de gastos de viagem (Pix, Débito e Crédito) a partir de extratos bancários em PDF.

## Estrutura de Arquivos

*   **`relatorio_viagem.html`**: O produto final. Um relatório visual interativo (abre no navegador) mostrando todos os gastos categorizados.
*   **`parse_expenses.py`**: Script Python que lê os arquivos de texto extraídos e gera o HTML. Contém a lógica de negócio (ex: evitar duplicidade do pagamento da fatura).
*   **`*.pdf`**: Arquivos originais dos extratos do Sicoob.
*   **`*.txt`**: Arquivos de texto bruto extraídos dos PDFs (usados pelo script Python).
    *   `dec_2025.txt`: Extrato Conta Corrente (Dez 2025).
    *   `jan_2026.txt`: Extrato Conta Corrente (Jan 2026).
    *   `cc_details.txt`: Extrato detalhado Cartão de Crédito (Dez/Jan).
    *   `cc_futuros.txt`: Lançamentos futuros do cartão (cobre o final da viagem).

## Como Usar

1.  **Pré-requisitos**: Python 3.
2.  **Gerar Relatório**:
    Execute o seguinte comando no terminal:
    ```bash
    python3 parse_expenses.py
    ```
    ```
3.  **Visualizar**:
    *   **Opção A (Simples)**: Abra o arquivo `relatorio_viagem.html` no seu navegador.
    *   **Opção B (Servidor Local)**:
        Execute:
        ```bash
        python3 -m http.server 8000
        ```
        Acesse: `http://localhost:8000`

## Deploy (Vercel)

O projeto está configurado para deploy estático na Vercel.

1.  O repositório inclui os arquivos HTML gerados.
2.  O arquivo `index.html` redireciona automaticamente para o relatório principal.
3.  Basta conectar o repositório GitHub na Vercel e o deploy será automático.

## Lógica de Processamento

*   **Período da Viagem**: 26/12/2025 a 28/01/2026.
*   **Categorização**:
    *   **Pix/Débito**: Extraídos da Conta Corrente. Status "Pago".
    *   **Crédito**: Extraídos da fatura do cartão. Status "Crédito".
    *   **Parcelamentos**: Apenas a parcela "1/x" é considerada gasto da viagem. Parcelas de compras antigas (ex: "2/3") são ignoradas.
    *   **Pagamento de Fatura**: Identificado automaticamente (busca por "MASTERCARD" e "DÉB.CONV" no extrato). Este valor é exibido em um card separado ("Fatura Paga") para comparação, mas **não é somado** ao "Total Geral" de gastos, pois as despesas individuais do cartão já são contabilizadas separadamente.

## Adicionando Novos Extratos

Se você baixar um novo PDF (ex: fatura de Fevereiro/2026 para cobrir o resto da viagem):
1.  Converta o PDF para texto: `pdftotext -layout novo_arquivo.pdf novo_arquivo.txt`
2.  Edite o `parse_expenses.py` para incluir a leitura desse novo arquivo na função `parse_cc_statement`.
