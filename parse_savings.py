import os
import re
import datetime
import subprocess

# Configuration
directory = 'SCTBNK'
output_file = 'relatorio_poupanca.html'
password_protect = "ferias2025" # Simple password

def convert_pdf_to_text(pdf_path):
    text_path = pdf_path.replace('.pdf', '.txt')
    subprocess.run(['pdftotext', '-layout', pdf_path, text_path], check=True)
    return text_path

def parse_scotia_statement(txt_file):
    with open(txt_file, 'r', encoding='utf-8', errors='ignore') as f:
        content = f.read()
    
    # Extract Date Range (e.g., October 1 to December 31, 2025)
    date_match = re.search(r'([A-Za-z]+ \d+ to [A-Za-z]+ \d+, \d{4})', content)
    period = date_match.group(1) if date_match else "Unknown Period"
    
    # Extract Accounts
    # Regex: 54.23% #000000135057263 SSI TFSA 10,008.28 10,195.18
    # We want the END value (Dec 31)
    accounts = []
    
    # Adjusted regex based on correct column alignment (percentage might vary)
    # Looking for: #Number SSI Type StartVal EndVal
    pattern = re.compile(r'#(\d+)\s+SSI\s+([A-Z]+)\s+([\d,]+\.\d{2})\s+([\d,]+\.\d{2})')
    
    for match in pattern.finditer(content):
        acc_num, acc_type, start_val, end_val = match.groups()
        accounts.append({
            'account': acc_num,
            'type': acc_type,
            'value': float(end_val.replace(',', ''))
        })
        
    return period, accounts

data = []
if os.path.exists(directory):
    for filename in os.listdir(directory):
        if filename.endswith(".pdf"):
            full_path = os.path.join(directory, filename)
            # Ensure text version exists
            txt_path = full_path.replace('.pdf', '.txt')
            if not os.path.exists(txt_path):
                try:
                    convert_pdf_to_text(full_path)
                except:
                    continue
            
            period, accounts = parse_scotia_statement(txt_path)
            if accounts:
                data.append({'file': filename, 'period': period, 'accounts': accounts})

# Sort by period (simple string sort might not be enough, but okay for now)
data.sort(key=lambda x: x['period'])

# Generate HTML
html = f"""
<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Minhas Poupanças (Scotiabank)</title>
    <style>
        body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background: #eef2f3; padding: 20px; display: flex; justify-content: center; }}
        .container {{ width: 100%; max-width: 800px; background: white; padding: 30px; border-radius: 10px; box-shadow: 0 4px 15px rgba(0,0,0,0.1); display: none; }}
        .login-box {{ width: 100%; max-width: 400px; background: white; padding: 40px; border-radius: 10px; box-shadow: 0 4px 15px rgba(0,0,0,0.1); text-align: center; }}
        h1 {{ color: #c0392b; }}
        .statement {{ border: 1px solid #ddd; margin-bottom: 20px; padding: 15px; border-radius: 5px; }}
        .statement h3 {{ margin-top: 0; color: #2c3e50; }}
        .account-row {{ display: flex; justify-content: space-between; border-bottom: 1px solid #eee; padding: 8px 0; }}
        .account-row:last-child {{ border-bottom: none; }}
        .total-row {{ display: flex; justify-content: space-between; font-weight: bold; margin-top: 10px; padding-top: 10px; border-top: 2px solid #ddd; color: #27ae60; }}
        input {{ padding: 10px; width: 80%; margin-bottom: 15px; border: 1px solid #ddd; border-radius: 5px; }}
        button {{ padding: 10px 20px; background: #c0392b; color: white; border: none; border-radius: 5px; cursor: pointer; font-weight: bold; }}
        button:hover {{ background: #a93226; }}
        .back-link {{ display: block; margin-bottom: 20px; color: #3498db; text-decoration: none; }}
    </style>
</head>
<body>

    <div id="login-overlay" class="login-box">
        <h2>Área Restrita</h2>
        <p>Digite a senha para visualizar.</p>
        <input type="password" id="password" placeholder="Senha">
        <br>
        <button onclick="checkPassword()">Acessar</button>
        <p id="error-msg" style="color:red; display:none; margin-top:10px;">Senha incorreta!</p>
    </div>

    <div id="content" class="container">
        <a href="relatorio_viagem.html" class="back-link">&larr; Voltar para Gastos da Viagem</a>
        <h1>Minhas Poupanças (Scotiabank)</h1>
"""

for item in data:
    html += f"""
        <div class="statement">
            <h3>Período: {item['period']}</h3>
    """
    total = 0
    for acc in item['accounts']:
        html += f"""
            <div class="account-row">
                <span>{acc['type']} (...{acc['account'][-4:]})</span>
                <span>CAD$ {acc['value']:,.2f}</span>
            </div>
        """
        total += acc['value']
    
    html += f"""
            <div class="total-row">
                <span>Total</span>
                <span>CAD$ {total:,.2f}</span>
            </div>
        </div>
    """

html += f"""
    </div>

    <script>
        function checkPassword() {{
            const pwd = document.getElementById('password').value;
            if (pwd === '{password_protect}') {{
                document.getElementById('login-overlay').style.display = 'none';
                document.getElementById('content').style.display = 'block';
                document.body.style.background = '#f4f4f9'; // Restore normal background
            }} else {{
                document.getElementById('error-msg').style.display = 'block';
            }}
        }}
        
        // Allow Enter key
        document.getElementById('password').addEventListener('keypress', function (e) {{
            if (e.key === 'Enter') {{
                checkPassword();
            }}
        }});
    </script>
</body>
</html>
"""

with open(output_file, 'w', encoding='utf-8') as f:
    f.write(html)

print(f"Generated {output_file}")
