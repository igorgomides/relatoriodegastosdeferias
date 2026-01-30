# Contexto do Projeto

**Status Atual**:
- **Concluído**: O relatório HTML (`relatorio_viagem.html`) está completo e funcional.
- **Processamento**:
    - Extratos bancários (Dez/Jan) processados.
    - Fatura de cartão (detalhada) processada.
    - **Novo**: Fatura de cartão ("Lançamentos Futuros") processada com sucesso, cobrindo o período de 09/01 a 28/01.
    - Lógica de "Fatura Paga" implementada para evitar duplicidade na visualização.
    - Filtro de parcelas antigas (ex: 2/3, 3/3) aplicado para isolar apenas gastos novos da viagem.

**Próximos Passos**:
- O projeto está em estado estável. Nenhuma tarefa pendente imediata.
- Para adicionar novos gastos no futuro, basta seguir o fluxo de adicionar PDF -> converter -> atualizar script.

**Histórico de Comandos**:
- `python3 parse_expenses.py`: Gera o relatório final.
