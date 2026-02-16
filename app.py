from flask import Flask, render_template, request, jsonify, redirect, url_for
import uuid
from datetime import datetime
import os
import requests # <--- NOVO: Para falar com o encurtador

app = Flask(__name__)

# Banco de dados em memória
FROTA = {}

# --- FUNÇÃO PARA ENCURTAR LINK (NOVO) ---
def encurtar_url(url_longa):
    try:
        # Usa a API pública do TinyURL
        api_url = f"http://tinyurl.com/api-create.php?url={url_longa}"
        response = requests.get(api_url)
        if response.status_code == 200:
            return response.text # Retorna o link curto (ex: https://tinyurl.com/xyz)
    except Exception as e:
        print(f"Erro ao encurtar: {e}")
    return url_longa # Se der erro, retorna o link longo mesmo

# --- ROTAS ---
@app.route('/')
def index():
    return redirect(url_for('admin_panel'))

@app.route('/admin')
def admin_panel():
    return render_template("admin.html", frota=FROTA)

@app.route('/gerar_ordem', methods=['POST'])
def gerar_ordem():
    placa = request.form.get("placa")
    motorista = request.form.get("motorista")
    id_ordem = str(uuid.uuid4())[:8]
    
    # 1. Gera o link longo original
    # _external=True faz ele pegar o endereço completo (http://seusite.com/...)
    link_longo = url_for('tela_motorista', id_ordem=id_ordem, _external=True)
    
    # 2. Transforma em link curto automaticamente
    print("Encurtando link...") # Aviso no terminal
    link_curto = encurtar_url(link_longo)
    
    FROTA[id_ordem] = {
        "placa": placa,
        "motorista": motorista,
        "lat": None,
        "lon": None,
        "status": "Aguardando Motorista",
        "ultimo_visto": "-",
        "link": link_curto # <--- Agora salvamos o link curto
    }
    
    return redirect(url_for('admin_panel'))

@app.route('/api/frota')
def api_frota():
    return jsonify(FROTA)

@app.route('/verificar-entrega/<id_ordem>')
def tela_motorista(id_ordem):
    if id_ordem not in FROTA:
        return "<h1>Erro: Ordem expirada.</h1>", 404
    dados = FROTA[id_ordem]
    return render_template("motorista.html", id=id_ordem, dados=dados)

@app.route('/api/sinal/<id_ordem>', methods=['POST'])
def receber_sinal(id_ordem):
    if id_ordem in FROTA:
        data = request.get_json()
        FROTA[id_ordem]['lat'] = data.get('latitude')
        FROTA[id_ordem]['lon'] = data.get('longitude')
        FROTA[id_ordem]['status'] = "Em Trânsito"
        FROTA[id_ordem]['ultimo_visto'] = datetime.now().strftime("%H:%M:%S")
        return jsonify({"ok": True}), 200
    return jsonify({"ok": False}), 404

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
"""  
if __name__ == '__main__':
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)
"""   