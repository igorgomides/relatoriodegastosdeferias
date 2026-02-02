import re
import json
import datetime
from collections import defaultdict

# Configuration
TRIP_START = datetime.date(2025, 12, 26)
TRIP_END = datetime.date(2026, 1, 28)

class Transaction:
    def __init__(self, date, description, value, type, original_line, total_purchase_value=None):
        self.date = date
        self.description = description
        self.value = value
        self.type = type 
        self.original_line = original_line
        self.status = 'Pago' if type in ['Pix', 'Debito'] else 'Credito'
        self.total_purchase_value = total_purchase_value if total_purchase_value is not None else value

    def to_dict(self):
        return {
            'date': self.date.strftime('%Y-%m-%d'),
            'display_date': self.date.strftime('%d/%m/%Y'),
            'description': self.description,
            'value': self.value,
            'total_purchase_value': self.total_purchase_value,
            'type': self.type,
            'status': self.status,
            'original_line': self.original_line
        }

transactions = []
future_bills = [] 

def parse_currency(val_str):
    clean = val_str.replace('R$', '').replace('.', '').replace(',', '.')
    if clean.endswith('D') or clean.endswith('C'):
        clean = clean[:-1]
    return float(clean)

def add_months(sourcedate, months):
    month = sourcedate.month - 1 + months
    year = sourcedate.year + month // 12
    month = month % 12 + 1
    day = min(sourcedate.day, [31,
        29 if year % 4 == 0 and not year % 100 == 0 or year % 400 == 0 else 28,
        31, 30, 31, 30, 31, 31, 30, 31, 30, 31][month-1])
    return datetime.date(year, month, day)

def parse_bank_statement(filename, year_month_map):
    with open(filename, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    pattern = re.compile(r'(\d{2}/\d{2})\s+(.*?)\s+(R\$\s?[\d\.,]+[DC])')
    
    for line in lines:
        match = pattern.search(line)
        if match:
            date_str, desc, val_str = match.groups()
            day, month = map(int, date_str.split('/'))
            year = 2025 if month == 12 else 2026
            tx_date = datetime.date(year, month, day)
            
            if not (TRIP_START <= tx_date <= TRIP_END):
                continue
            if 'C' in val_str:
                continue
            if "SALDO DO DIA" in desc:
                continue

            value = parse_currency(val_str)
            
            tx_type = 'Debito'
            if 'Pix' in desc or 'PIX' in desc:
                tx_type = 'Pix'
            elif 'DEBIT' in desc or 'MASTERCARD' in desc: 
                 tx_type = 'Debito'
            
            if "MASTERCARD" in desc and ("DEB.CONV.DEMAIS EMPRESAS" in desc or "DÉB.CONV.DEMAIS EMPRESAS" in desc) and value > 1000:
                 desc += " (Pagamento Fatura Cartão)"
                 tx_type = 'Pagamento Fatura'

            transactions.append(Transaction(tx_date, desc.strip(), value, tx_type, line.strip()))

def parse_cc_statement(filename):
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            lines = f.readlines()
    except FileNotFoundError:
        return

    capture = False
    pattern = re.compile(r'(\d{2}/\d{2})\s+(.*?)\s+(\d+[\.,]\d{2})$') 
    
    for line in lines:
        if "GASTOS DE" in line:
            capture = True
            continue
        if "ENCARGOS FINANCEIROS" in line or "TOTAL" in line:
            capture = False
            continue
            
        if capture:
            match = pattern.search(line)
            if match:
                date_str, desc, val_str = match.groups()
                day, month = map(int, date_str.split('/'))
                year = 2025 if month == 12 else 2026
                tx_date = datetime.date(year, month, day)
                
                if not (TRIP_START <= tx_date <= TRIP_END):
                    continue
                
                val_clean = val_str.replace('.', '').replace(',', '.')
                value = float(val_clean)
                
                total_val = value
                inst_match = re.search(r'(\d+)/(\d+)', desc)
                if inst_match:
                    try:
                        curr, total_inst = map(int, inst_match.groups())
                        if total_inst > 0:
                            total_val = value * total_inst
                    except:
                        pass
                
                transactions.append(Transaction(tx_date, desc.strip(), value, 'Credito', line.strip(), total_purchase_value=total_val))

def parse_cc_futuros(filename):
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            lines = f.readlines()
    except FileNotFoundError:
        print(f"Warning: {filename} not found.")
        return

    current_section = None
    pattern = re.compile(r'(\d{2}/\d{2}/\d{4})\s+(.+?)\s+(\d{4})\s+(R\$\s?-?[\d\.,]+)')
    installment_pattern = re.compile(r'-\s*(\d+)/(\d+)')

    for line in lines:
        if "MOVIMENTOS PARA A PRÓXIMA FATURA" in line:
            current_section = "NEXT"
            continue
        if "PARCELADOS COM VENCIMENTO FUTURO" in line:
            current_section = "FUTURE"
            continue

        match = pattern.search(line)
        if match:
            date_str, desc_raw, card, val_str = match.groups()
            day, month, year = map(int, date_str.split('/'))
            tx_date = datetime.date(year, month, day)
            
            is_negative = '-' in val_str
            val_clean = val_str.replace('R$', '').replace('.', '').replace(',', '.').replace('-', '').strip()
            value = float(val_clean)
            
            if is_negative or value == 0:
                continue

            desc = re.sub(r'\s+', ' ', desc_raw).strip()

            if TRIP_START <= tx_date <= TRIP_END:
                inst_match = installment_pattern.search(desc)
                should_add = True
                total_val = value
                
                if inst_match:
                    current_inst, total_inst = map(int, inst_match.groups())
                    total_val = value * total_inst
                    if current_inst > 1:
                        should_add = False 
                
                if should_add:
                    transactions.append(Transaction(tx_date, desc, value, 'Credito', line.strip(), total_purchase_value=total_val))

            base_due_date = None
            if current_section == "NEXT":
                base_due_date = datetime.date(2026, 2, 19)
            elif current_section == "FUTURE":
                base_due_date = datetime.date(2026, 3, 19)
            
            if base_due_date:
                inst_match = installment_pattern.search(desc)
                if inst_match:
                    start_inst, total_inst = map(int, inst_match.groups())
                    remaining_count = total_inst - start_inst + 1
                    total_purchase = value * total_inst
                    
                    for i in range(remaining_count):
                        current_due_date = add_months(base_due_date, i)
                        current_inst_num = start_inst + i
                        amount_paid = (current_inst_num - 1) * value
                        
                        # --- MODIFICATION START ---
                        # Amount remaining is total purchase MINUS all installments UP TO and INCLUDING the current one
                        amount_remaining_future_only = total_purchase - (current_inst_num * value)
                        # --- MODIFICATION END ---
                        
                        new_desc = re.sub(r'-\s*\d+/\d+', '', desc).strip()
                        
                        future_bills.append({
                            'purchase_date': tx_date.strftime('%d/%m/%Y'),
                            'description': new_desc,
                            'value': value,
                            'due_date': current_due_date,
                            'due_month': current_due_date.strftime('%B %Y'),
                            'installment_info': f"{current_inst_num}/{total_inst}",
                            'total_purchase': total_purchase,
                            'amount_paid': amount_paid,
                            'amount_remaining': amount_remaining_future_only # Using the corrected value
                        })
                else:
                    future_bills.append({
                        'purchase_date': tx_date.strftime('%d/%m/%Y'),
                        'description': desc,
                        'value': value,
                        'due_date': base_due_date,
                        'due_month': base_due_date.strftime('%B %Y'),
                        'installment_info': "1/1",
                        'total_purchase': value,
                        'amount_paid': 0,
                        'amount_remaining': 0 # For single payment, no future remaining after this one
                    })

# Run Parsers
parse_bank_statement('dec_2025.txt', {})
parse_bank_statement('jan_2026.txt', {})
parse_cc_statement('cc_details.txt')
parse_cc_futuros('cc_futuros.txt')

transactions.sort(key=lambda x: x.date)

# --- Prep Future Cards Data ---
future_totals = defaultdict(float)
month_translation_short = {
    1: 'Jan', 2: 'Fev', 3: 'Mar', 4: 'Abr', 5: 'Mai', 6: 'Jun',
    7: 'Jul', 8: 'Ago', 9: 'Set', 10: 'Out', 11: 'Nov', 12: 'Dez'
}

for bill in future_bills:
    m_key = (bill['due_date'].year, bill['due_date'].month)
    future_totals[m_key] += bill['value']

# Calculate January Paid Total from Transactions
jan_paid_total = sum(t.value for t in transactions if t.type == 'Pagamento Fatura')

# Build List of Monthly Cards (Jan + Future)
cards_data = []

if jan_paid_total > 0:
    cards_data.append({
        'year': 2026, 'month': 1, 'val': jan_paid_total, 'label': 'Jan/2026', 'is_past': True
    })

for key in sorted(future_totals.keys()):
    year, month = key
    cards_data.append({
        'year': year, 'month': month, 'val': future_totals[key], 
        'label': f"{month_translation_short.get(month)}/{year}", 'is_past': False
    })

# Build HTML for Cards
cards_html = ""
for card in cards_data:
    card_id = f"invoice-{card['year']}-{card['month']}"
    val_fmt = f"R$ {card['val']:,.2f}".replace('.', 'X').replace(',', '.').replace('X', ',')
    
    cards_html += f"""
    <div class="card clickable-card" id="{card_id}" onclick="togglePaid(this)">
        <div class="check-icon">✓</div>
        <h3>Fatura {card['label']}</h3>
        <p class="money" data-val="{card['val']}">{val_fmt}</p>
        <small class="status-text">Aberto</small>
    </div>
    """


# --- Generate Main Report (relatorio_viagem.html) ---

data = [t.to_dict() for t in transactions]
json_data = json.dumps(data, indent=2)

html_content = f"""
<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Relatório de Viagem - Brasil 25/26</title>
    <style>
        body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background: #f4f4f9; padding: 20px; }}
        .container {{ max-width: 1000px; margin: 0 auto; background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 5px rgba(0,0,0,0.1); }}
        h1 {{ color: #333; }}
        .summary {{ display: flex; gap: 20px; margin-bottom: 20px; flex-wrap: wrap; }}
        .card {{ background: #eee; padding: 15px; border-radius: 5px; flex: 1; text-align: center; min-width: 150px; position: relative; transition: all 0.2s; }}
        .card h3 {{ margin: 0; color: #555; font-size: 0.9em; }}
        .card p {{ margin: 5px 0 0; font-size: 1.5em; font-weight: bold; color: #2c3e50; }}
        .card.highlight {{ background-color: #fcf3cf; border: 1px solid #f1c40f; }}
        .card.highlight p {{ color: #d35400; }}
        
        /* Clickable Invoice Cards */
        .clickable-card {{ cursor: pointer; border-left: 5px solid #3498db; background-color: #eaf2f8; }}
        .clickable-card:hover {{ transform: translateY(-2px); box-shadow: 0 4px 6px rgba(0,0,0,0.1); }}
        
        /* Paid State */
        .clickable-card.paid {{ background-color: #d5dbdb; border-left-color: #7f8c8d; opacity: 0.8; }}
        .clickable-card.paid h3, .clickable-card.paid p {{ text-decoration: line-through; color: #7f8c8d; }}
        .clickable-card.paid .status-text {{ color: #27ae60; font-weight: bold; text-decoration: none; }}
        .clickable-card .check-icon {{ display: none; position: absolute; top: 10px; right: 10px; color: #27ae60; font-weight: bold; font-size: 1.2em; }}
        .clickable-card.paid .check-icon {{ display: block; }}
        .status-text {{ display: block; margin-top: 5px; font-size: 0.8em; color: #e74c3c; }}
        .clickable-card.paid .status-text {{ color: #27ae60; }}

        table {{ width: 100%; border-collapse: collapse; margin-top: 20px; }}
        th, td {{ padding: 12px; text-align: left; border-bottom: 1px solid #ddd; }}
        th {{ background-color: #2c3e50; color: white; cursor: pointer; user-select: none; }}
        th:hover {{ background-color: #34495e; }}
        tr:hover {{ background-color: #f1f1f1; }}
        .badge {{ padding: 4px 8px; border-radius: 4px; font-size: 0.8em; font-weight: bold; color: white; }}
        .Pix {{ background-color: #27ae60; }}
        .Debito {{ background-color: #2980b9; }}
        .Credito {{ background-color: #e67e22; }}
        .Pagamento-Fatura {{ background-color: #7f8c8d; }}
        .btn {{ display: inline-block; padding: 10px 20px; background-color: #3498db; color: white; text-decoration: none; border-radius: 5px; font-weight: bold; margin-bottom: 20px; }}
        .btn:hover {{ background-color: #2980b9; }}
        
        .controls {{ background: #e8f6f3; padding: 15px; border-radius: 5px; margin-bottom: 20px; display: flex; gap: 15px; align-items: center; border: 1px solid #1abc9c; flex-wrap: wrap; }}
        .controls label {{ font-weight: bold; color: #16a085; }}
        .controls input, .controls select {{ padding: 5px; border: 1px solid #ddd; border-radius: 3px; }}
        .currency-toggle {{ background-color: #16a085; color: white; border: none; padding: 8px 15px; border-radius: 3px; cursor: pointer; font-weight: bold; }}
        .currency-toggle:hover {{ background-color: #1abc9c; }}
        
        .filters input {{ width: 200px; }}
        
        .section-title {{ border-bottom: 2px solid #eee; padding-bottom: 10px; margin-bottom: 15px; color: #7f8c8d; font-size: 1.1em; }}
    </style>
</head>
<body>

<div class="container">
    <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap;">
        <h1>Gastos da Viagem</h1>
        <div style="display:flex; gap:10px;">
            <a href="relatorio_poupanca.html" class="btn" style="background-color:#c0392b;">Minhas Poupanças</a>
            <a href="relatorio_contas_fixas.html" class="btn" style="background-color:#8e44ad;">Contas Fixas</a>
            <a href="relatorio_futuro.html" class="btn">Ver Detalhes Futuros</a>
        </div>
    </div>

    <div class="controls">
        <label for="exchange-rate">Cotação (1 CAD = R$):</label>
        <input type="number" id="exchange-rate" value="4.20" step="0.01" onchange="updateRate()">
        <button class="currency-toggle" onclick="toggleCurrency()" id="btn-currency">Ver em CAD</button>
    </div>
    
    <h3 class="section-title">Resumo Financeiro</h3>
    <div class="summary">
        <div class="card">
            <h3>Pix (Pago)</h3>
            <p id="total-pix">R$ 0,00</p>
        </div>
        <div class="card">
            <h3>Débito (Pago)</h3>
            <p id="total-debito">R$ 0,00</p>
        </div>
        <div class="card highlight">
            <h3>Total Comprometido (Full)</h3>
            <p id="total-comprometido">R$ 0,00</p>
        </div>
    </div>
    
    <h3 class="section-title">Próximos Vencimentos (Cartão de Crédito)</h3>
    <p style="font-size:0.9em; color:#7f8c8d; margin-top:-10px; margin-bottom:15px;">Clique no cartão para marcar como pago.</p>
    <div class="summary">
        {cards_html}
    </div>

    <h3 class="section-title">Extrato da Viagem</h3>
    <div class="controls filters">
        <label>Filtros:</label>
        <input type="text" id="search-desc" placeholder="Buscar descrição..." oninput="renderTable()">
        <select id="filter-type" onchange="renderTable()">
            <option value="all">Todos os Tipos</option>
            <option value="Pix">Pix</option>
            <option value="Debito">Débito</option>
            <option value="Credito">Crédito</option>
        </select>
        <label><input type="checkbox" id="toggle-fatura" onchange="renderTable()"> Ver Faturas Pagas</label>
    </div>

    <table id="expenses-table">
        <thead>
            <tr>
                <th onclick="sortTable('date')">Data &#8693;</th>
                <th onclick="sortTable('description')">Descrição &#8693;</th>
                <th onclick="sortTable('type')">Tipo &#8693;</th>
                <th onclick="sortTable('status')">Status &#8693;</th>
                <th onclick="sortTable('value')">Valor Parcela &#8693;</th>
                <th onclick="sortTable('total_purchase_value')">Valor Total (Compra) &#8693;</th>
            </tr>
        </thead>
        <tbody></tbody>
    </table>
</div>

<script>
    const transactions = {json_data};
    let currentCurrency = localStorage.getItem('currency') || 'BRL';
    let exchangeRate = parseFloat(localStorage.getItem('exchangeRate')) || 4.20;
    
    let sortField = 'date';
    let sortDir = 'asc';

    // Init
    document.getElementById('exchange-rate').value = exchangeRate;
    updateButtonLabel();
    renderTable();
    updatePrices(); 
    initPaidStatus(); // Load Saved Paid Status

    function updateRate() {{
        exchangeRate = parseFloat(document.getElementById('exchange-rate').value);
        localStorage.setItem('exchangeRate', exchangeRate);
        renderTable();
        updatePrices();
    }}

    function toggleCurrency() {{
        currentCurrency = currentCurrency === 'BRL' ? 'CAD' : 'BRL';
        localStorage.setItem('currency', currentCurrency);
        updateButtonLabel();
        renderTable();
        updatePrices();
    }}

    function updateButtonLabel() {{
        const btn = document.getElementById('btn-currency');
        btn.textContent = currentCurrency === 'BRL' ? 'Ver em CAD' : 'Ver em BRL';
    }}

    function formatCurrency(value) {{
        if (currentCurrency === 'CAD') {{
            return (value / exchangeRate).toLocaleString('en-CA', {{ style: 'currency', currency: 'CAD' }});
        }}
        return value.toLocaleString('pt-BR', {{ style: 'currency', currency: 'BRL' }});
    }}
    
    function updatePrices() {{
        const elements = document.querySelectorAll('.money');
        elements.forEach(el => {{
            const val = parseFloat(el.getAttribute('data-val'));
            el.textContent = formatCurrency(val);
        }});
    }}
    
    // --- Paid Status Logic ---
    function initPaidStatus() {{
        document.querySelectorAll('.clickable-card').forEach(card => {{
            const id = card.id;
            const savedStatus = localStorage.getItem('status-' + id);
            
            if (id === 'invoice-2026-1' && savedStatus === null) {{ // Default Jan to paid
                markAsPaid(card, true);
                return;
            }}

            if (savedStatus === 'true') {{
                markAsPaid(card, true);
            }} else {{
                markAsPaid(card, false);
            }}
        }});
    }}

    function togglePaid(card) {{
        const isPaid = card.classList.contains('paid');
        markAsPaid(card, !isPaid);
    }}

    function markAsPaid(card, paid) {{
        const statusText = card.querySelector('.status-text');
        if (paid) {{
            card.classList.add('paid');
            statusText.textContent = 'PAGO';
            localStorage.setItem('status-' + card.id, 'true');
        }} else {{
            card.classList.remove('paid');
            statusText.textContent = 'Aberto';
            localStorage.setItem('status-' + card.id, 'false');
        }}
    }}
    // -------------------------

    function sortTable(field) {{
        if (sortField === field) {{
            sortDir = sortDir === 'asc' ? 'desc' : 'asc';
        }} else {{
            sortField = field;
            sortDir = 'asc';
        }}
        renderTable();
    }}

    function renderTable() {{
        const tbody = document.querySelector('#expenses-table tbody');
        const showFatura = document.getElementById('toggle-fatura').checked;
        const searchDesc = document.getElementById('search-desc').value.toLowerCase();
        const filterType = document.getElementById('filter-type').value;
        
        tbody.innerHTML = '';
        
        let filtered = transactions.filter(tx => {{
            if (!showFatura && tx.type === 'Pagamento Fatura') return false;
            if (searchDesc && !tx.description.toLowerCase().includes(searchDesc)) return false;
            if (filterType !== 'all' && tx.type !== filterType) return false;
            return true;
        }});
        
        filtered.sort((a, b) => {{
            let valA = a[sortField];
            let valB = b[sortField];
            if (typeof valA === 'string') {{ valA = valA.toLowerCase(); valB = valB.toLowerCase(); }}
            if (valA < valB) return sortDir === 'asc' ? -1 : 1;
            if (valA > valB) return sortDir === 'asc' ? 1 : -1;
            return 0;
        }});
        
        let totalPix = 0;
        let totalDebito = 0;
        let totalComprometido = 0;

        filtered.forEach(tx => {{
            if (tx.type === 'Pix') {{
                totalPix += tx.value;
                totalComprometido += tx.value;
            }}
            else if (tx.type === 'Debito') {{
                totalDebito += tx.value;
                totalComprometido += tx.value;
            }}
            else if (tx.type === 'Credito') {{
                totalComprometido += tx.total_purchase_value;
            }}
            // Pagamento Fatura is not added to any of these main cards, it's just tracked as 'paid'
            // The value of 'totalCredito' card was removed as it's replaced by the monthly cards
            
            const row = document.createElement('tr');
            const typeClass = tx.type.replace(' ', '-'); 
            const totalDisplay = (tx.type === 'Credito' && tx.total_purchase_value > tx.value) 
                                ? `<strong>${{formatCurrency(tx.total_purchase_value)}}</strong>` 
                                : '-';

            row.innerHTML = `
                <td>${{tx.display_date}}</td>
                <td>${{tx.description}}</td>
                <td><span class="badge ${{typeClass}}">${{tx.type}}</span></td>
                <td>${{tx.status}}</td>
                <td>${{formatCurrency(tx.value)}}</td>
                <td style="color:#555;">${{totalDisplay}}</td>
            `;
            tbody.appendChild(row);
        }});

        // Update Dynamic Summary Cards
        document.getElementById('total-pix').textContent = formatCurrency(totalPix);
        document.getElementById('total-debito').textContent = formatCurrency(totalDebito);
        document.getElementById('total-comprometido').textContent = formatCurrency(totalComprometido);
    }}
</script>

</body>
</html>
"""

with open('relatorio_viagem.html', 'w', encoding='utf-8') as f:
    f.write(html_content)
print("Report generated: relatorio_viagem.html")

# --- Generate Future Bills Report (relatorio_futuro.html) ---

bills_by_month = defaultdict(list)
totals_by_month = defaultdict(float)

month_translation = {
    1: 'Janeiro', 2: 'Fevereiro', 3: 'Março', 4: 'Abril', 5: 'Maio', 6: 'Junho',
    7: 'Julho', 8: 'Agosto', 9: 'Setembro', 10: 'Outubro', 11: 'Novembro', 12: 'Dezembro'
}

for bill in future_bills:
    m_key = (bill['due_date'].year, bill['due_date'].month)
    bills_by_month[m_key].append(bill)
    totals_by_month[m_key] += bill['value']

sorted_months = sorted(bills_by_month.keys())

html_future = f"""
<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Previsão de Faturas Futuras</title>
    <style>
        body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background: #f4f4f9; padding: 20px; }}
        .container {{ max-width: 1200px; margin: 0 auto; background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 5px rgba(0,0,0,0.1); }}
        h1 {{ color: #333; }}
        .back-link {{ display: inline-block; margin-bottom: 20px; color: #3498db; text-decoration: none; }}
        .month-section {{ margin-bottom: 30px; border: 1px solid #eee; border-radius: 5px; overflow: hidden; }}
        .month-header {{ background-color: #2c3e50; color: white; padding: 15px; display: flex; justify-content: space-between; align-items: center; }}
        .month-header h2 {{ margin: 0; font-size: 1.2em; }}
        .month-total {{ font-size: 1.2em; font-weight: bold; }}
        table {{ width: 100%; border-collapse: collapse; }}
        th, td {{ padding: 12px; text-align: left; border-bottom: 1px solid #ddd; }}
        th {{ background-color: #ecf0f1; color: #2c3e50; font-size: 0.9em; }}
        .small-text {{ font-size: 0.85em; color: #666; }}
        
        .controls {{ background: #e8f6f3; padding: 15px; border-radius: 5px; margin-bottom: 20px; display: flex; gap: 15px; align-items: center; border: 1px solid #1abc9c; }}
        .controls label {{ font-weight: bold; color: #16a085; }}
        .controls input {{ padding: 5px; border: 1px solid #ddd; border-radius: 3px; width: 80px; }}
        .currency-toggle {{ background-color: #16a085; color: white; border: none; padding: 8px 15px; border-radius: 3px; cursor: pointer; font-weight: bold; }}
        .currency-toggle:hover {{ background-color: #1abc9c; }}
    </style>
</head>
<body>

<div class="container">
    <a href="relatorio_viagem.html" class="back-link">&larr; Voltar para Gastos da Viagem</a>
    <h1>Previsão de Faturas (Cartão de Crédito)</h1>
    
    <div class="controls">
        <label for="exchange-rate">Cotação (1 CAD = R$):</label>
        <input type="number" id="exchange-rate" value="4.20" step="0.01" onchange="updateRate()">
        <button class="currency-toggle" onclick="toggleCurrency()" id="btn-currency">Ver em CAD</button>
    </div>
"""

for year, month in sorted_months:
    month_name = month_translation.get(month, 'Mês Desconhecido')
    total = totals_by_month[(year, month)]
    bills = bills_by_month[(year, month)]
    
    html_future += f"""
    <div class="month-section">
        <div class="month-header">
            <h2>{month_name} {year} (Vencimento 19/{month:02d})</h2>
            <span class="month-total money" data-val="{total}">R$ {total:,.2f}</span>
        </div>
        <table>
            <thead>
                <tr>
                    <th>Data Compra</th>
                    <th>Descrição</th>
                    <th>Valor Parcela</th>
                    <th>Parcela</th>
                    <th>Total Compra</th>
                    <th>Já Pago</th>
                    <th>Restante</th>
                </tr>
            </thead>
            <tbody>
    """
    
    for bill in bills:
        val_fmt = f'R$ {bill["value"]:,.2f}' 
        
        html_future += f"""
                <tr>
                    <td>{bill['purchase_date']}</td>
                    <td>{bill['description']}</td>
                    <td><strong class="money" data-val="{bill['value']}">{val_fmt}</strong></td>
                    <td style="text-align:center;">{bill['installment_info']}</td>
                    <td class="small-text money" data-val="{bill['total_purchase']}">-</td>
                    <td class="small-text money" data-val="{bill['amount_paid']}">-</td>
                    <td class="small-text money" data-val="{bill['amount_remaining']}" style="color: #c0392b;">-</td>
                </tr>
        """
        
    html_future += """
            </tbody>
        </table>
    </div>
    """

html_future += """
</div>

<script>
    let currentCurrency = localStorage.getItem('currency') || 'BRL';
    let exchangeRate = parseFloat(localStorage.getItem('exchangeRate')) || 4.20;

    document.getElementById('exchange-rate').value = exchangeRate;
    updateButtonLabel();
    updatePrices();

    function updateRate() {
        exchangeRate = parseFloat(document.getElementById('exchange-rate').value);
        localStorage.setItem('exchangeRate', exchangeRate);
        updatePrices();
    }

    function toggleCurrency() {
        currentCurrency = currentCurrency === 'BRL' ? 'CAD' : 'BRL';
        localStorage.setItem('currency', currentCurrency);
        updateButtonLabel();
        updatePrices();
    }

    function updateButtonLabel() {
        const btn = document.getElementById('btn-currency');
        btn.textContent = currentCurrency === 'BRL' ? 'Ver em CAD' : 'Ver em BRL';
    }

    function formatCurrency(value) {
        if (currentCurrency === 'CAD') {
            return (value / exchangeRate).toLocaleString('en-CA', { style: 'currency', currency: 'CAD' });
        }
        return value.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' });
    }
    
    function updatePrices() {
        const elements = document.querySelectorAll('.money');
        elements.forEach(el => {
            const val = parseFloat(el.getAttribute('data-val'));
            el.textContent = formatCurrency(val);
        });
    }
</script>

</body>
</html>
"""

with open('relatorio_futuro.html', 'w', encoding='utf-8') as f:
    f.write(html_future)
print("Report generated: relatorio_futuro.html")