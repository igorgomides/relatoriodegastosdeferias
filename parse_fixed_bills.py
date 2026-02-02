import csv
import datetime
from collections import defaultdict

# Config
INPUT_FILE = 'dec to feb statment.csv'
OUTPUT_FILE = 'relatorio_contas_fixas.html'

# Keywords to track
TRACKED_BILLS = {
    'HYUNDAI': {'name': 'Hyundai Application', 'frequency': 'Bi-weekly'},
    'RBC LOAN': {'name': 'RBC Loan', 'frequency': 'Bi-weekly'},
    'KITCHENER-WILMOT HYDRO': {'name': 'Kitchener Hydro', 'frequency': 'Monthly'},
    'CofK Utility': {'name': 'Kitchener Water/Gas', 'frequency': 'Monthly'},
    'Economical Mutual': {'name': 'Economical Insurance', 'frequency': 'Monthly'}, # Heuristic
    'American Express': {'name': 'AMEX Payment', 'frequency': 'Monthly'},
    'LONG & MCQUADE': {'name': 'Long & McQuade', 'frequency': 'Monthly'}
}

def parse_date(date_str):
    return datetime.datetime.strptime(date_str.strip(), '%Y-%m-%d').date()

def predict_next_date(last_date, frequency):
    if frequency == 'Bi-weekly':
        return last_date + datetime.timedelta(days=14)
    elif frequency == 'Monthly':
        # Simple Logic: Add 30 days or keep same day next month
        next_month = last_date.month + 1
        year = last_date.year
        if next_month > 12:
            next_month = 1
            year += 1
        
        # Try to keep same day, handle month end
        day = last_date.day
        try:
            return datetime.date(year, next_month, day)
        except ValueError:
            return datetime.date(year, next_month + 1, 1) - datetime.timedelta(days=1)
    return last_date

bill_history = defaultdict(list)

# Read CSV
with open(INPUT_FILE, 'r', encoding='utf-8') as f:
    reader = csv.reader(f)
    for row in reader:
        if len(row) < 3: continue
        
        date_str = row[0]
        desc = row[1]
        amount_str = row[2]
        
        if not amount_str: continue # Skip if no withdrawal amount (deposits)
        
        try:
            date = parse_date(date_str)
            amount = float(amount_str)
            
            for keyword, info in TRACKED_BILLS.items():
                if keyword in desc:
                    bill_history[keyword].append({
                        'date': date,
                        'amount': amount,
                        'desc': desc
                    })
                    break # Matched one, stop
        except ValueError:
            continue

# Analyze and Generate Data
report_data = []

for keyword, info in TRACKED_BILLS.items():
    history = bill_history.get(keyword, [])
    history.sort(key=lambda x: x['date'], reverse=True) # Newest first
    
    if not history:
        continue
        
    last_payment = history[0]
    next_due = predict_next_date(last_payment['date'], info['frequency'])
    
    # Calculate average amount (simplified)
    avg_amount = sum(h['amount'] for h in history) / len(history)
    
    report_data.append({
        'name': info['name'],
        'frequency': info['frequency'],
        'last_date': last_payment['date'],
        'last_amount': last_payment['amount'],
        'avg_amount': avg_amount,
        'next_due': next_due,
        'history': history,
        'status': 'Pago' if (datetime.date.today() - next_due).days < -5 else 'Próximo'
    })

# Sort by Next Due Date
report_data.sort(key=lambda x: x['next_due'])

# Generate HTML
html = f"""
<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Contas Fixas e Previsões</title>
    <style>
        body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background: #f0f2f5; padding: 20px; }}
        .container {{ max-width: 900px; margin: 0 auto; background: white; padding: 30px; border-radius: 12px; box-shadow: 0 4px 20px rgba(0,0,0,0.08); }}
        h1 {{ color: #2c3e50; border-bottom: 2px solid #eee; padding-bottom: 10px; }}
        .back-link {{ display: inline-block; margin-bottom: 20px; color: #3498db; text-decoration: none; font-weight: bold; }}
        .back-link:hover {{ text-decoration: underline; }}
        
        .bill-card {{ background: #fff; border: 1px solid #e1e4e8; border-radius: 8px; margin-bottom: 15px; padding: 20px; display: flex; align-items: center; justify-content: space-between; transition: transform 0.2s; }}
        .bill-card:hover {{ transform: translateY(-2px); box-shadow: 0 4px 12px rgba(0,0,0,0.05); border-color: #3498db; }}
        
        .bill-info {{ flex: 1; }}
        .bill-name {{ font-size: 1.2em; font-weight: bold; color: #2c3e50; margin: 0; }}
        .bill-freq {{ font-size: 0.85em; color: #7f8c8d; text-transform: uppercase; letter-spacing: 0.5px; background: #eee; padding: 2px 6px; border-radius: 4px; }}
        
        .bill-dates {{ text-align: right; min-width: 150px; }}
        .next-label {{ font-size: 0.8em; color: #95a5a6; display: block; }}
        .next-date {{ font-size: 1.4em; font-weight: bold; color: #e74c3c; }}
        .amount {{ font-size: 1.1em; color: #27ae60; font-weight: 600; margin-top: 4px; display: block; }}
        
        .history-btn {{ background: none; border: none; color: #3498db; cursor: pointer; padding: 0; font-size: 0.9em; margin-top: 5px; }}
        .history-list {{ display: none; margin-top: 15px; background: #f9f9f9; padding: 10px; border-radius: 6px; width: 100%; font-size: 0.9em; }}
        .history-item {{ display: flex; justify-content: space-between; border-bottom: 1px solid #eee; padding: 4px 0; }}
        
        .badge-bi {{ background-color: #e8f4fd; color: #2980b9; }}
        .badge-mo {{ background-color: #fef9e7; color: #f39c12; }}
    </style>
</head>
<body>

    <div class="container">
        <a href="relatorio_viagem.html" class="back-link">&larr; Voltar para Dashboard</a>
        <h1>📅 Previsão de Contas Fixas</h1>
        <p style="color: #666; margin-bottom: 25px;">Estimativas baseadas no histórico de Dez/25 a Fev/26.</p>

"""

today = datetime.date.today()

for bill in report_data:
    days_until = (bill['next_due'] - today).days
    date_color = "#e74c3c" if days_until <= 7 else "#2c3e50"
    freq_class = "badge-bi" if bill['frequency'] == 'Bi-weekly' else "badge-mo"
    
    # Toggle logic for history
    hist_id = f"hist-{bill['name'].replace(' ', '')}"
    
    html += f"""
        <div class="bill-card">
            <div class="bill-info">
                <p class="bill-name">{bill['name']} <span class="bill-freq {freq_class}">{bill['frequency']}</span></p>
                <p style="margin: 5px 0 0; color: #666; font-size: 0.9em;">
                    Último pgto: {bill['last_date'].strftime('%d/%m/%Y')} (R$ {bill['last_amount']:.2f})
                </p>
                <button class="history-btn" onclick="document.getElementById('{hist_id}').style.display = document.getElementById('{hist_id}').style.display === 'block' ? 'none' : 'block'">
                    Ver Histórico ({len(bill['history'])}) &#9662;
                </button>
                <div id="{hist_id}" class="history-list">
    """
    
    for h in bill['history']:
        html += f"""
                    <div class="history-item">
                        <span>{h['date'].strftime('%d/%m/%Y')}</span>
                        <span>R$ {h['amount']:.2f}</span>
                    </div>
        """
        
    html += f"""
                </div>
            </div>
            <div class="bill-dates">
                <span class="next-label">Próximo Vencimento</span>
                <span class="next-date" style="color: {date_color}">{bill['next_due'].strftime('%d/%m')}</span>
                <span class="next-label" style="font-size:0.7em; margin-top:2px;">({days_until} dias)</span>
                <span class="amount">~R$ {bill['avg_amount']:.2f}</span>
            </div>
        </div>
    """

html += """
    </div>
</body>
</html>
"""

with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
    f.write(html)

print(f"Generated {OUTPUT_FILE}")
