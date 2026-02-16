from flask import Flask, render_template, request, jsonify, redirect, url_for
import uuid
from datetime import datetime
import os
import requests

app = Flask(__name__)

FROTA = {}

# --- FUNÇÃO AUXILIAR: Identificar Dispositivo ---
def identificar_dispositivo(user_agent):
    ua = user_agent.lower()
    if "android" in ua: return "📱 Android"
    if "iphone" in ua or "ipad" in ua: return "📱 iPhone/iOS"
    if "windows" in ua: return "💻 PC Windows"
    if "macintosh" in ua: return "💻 Mac"
    return "❓ Desconhecido"

# --- FUNÇÃO ENCURTADOR (IS.GD) ---
def encurtar_url(url_longa):
    try:
        api_url = f"https://is.gd/create.php?format=simple&url={url_longa}"
        response = requests.get(api_url, timeout=5)
        if response.status_code == 200:
            return response.text.strip()
    except:
        pass
    return url_longa

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
    
    link_longo = url_for('tela_motorista', id_ordem=id_ordem, _external=True)
    link_curto = encurtar_url(link_longo)
    
    FROTA[id_ordem] = {
        "placa": placa,
        "motorista": motorista,
        "lat": None,
        "lon": None,
        "status": "Aguardando Conexão",
        "ultimo_visto": "-",
        "link": link_curto,
        # NOVOS CAMPOS DE INVESTIGAÇÃO
        "ip": "-",
        "device": "-",
        "precisao": "-",
        "velocidade": 0
    }
    return redirect(url_for('admin_panel'))

@app.route('/api/frota')
def api_frota():
    return jsonify(FROTA)

@app.route('/verificar-entrega/<id_ordem>')
def tela_motorista(id_ordem):
    if id_ordem not in FROTA:
        return "Link expirado.", 404
    return render_template("motorista.html", id=id_ordem)

@app.route('/api/sinal/<id_ordem>', methods=['POST'])
def receber_sinal(id_ordem):
    if id_ordem in FROTA:
        data = request.get_json()
        
        # Dados Técnicos
        ip = request.headers.get('X-Forwarded-For', request.remote_addr)
        user_agent = request.headers.get('User-Agent')
        
        FROTA[id_ordem].update({
            'lat': data.get('latitude'),
            'lon': data.get('longitude'),
            'status': "🟢 Online / Rastreando",
            'ultimo_visto': datetime.now().strftime("%d/%m %H:%M:%S"),
            'ip': ip,
            'device': identificar_dispositivo(user_agent),
            'precisao': f"{data.get('accuracy', 0)} metros", # Margem de erro do GPS
            'velocidade': data.get('speed', 0) # Em m/s
        })
        return jsonify({"ok": True}), 200
    return jsonify({"ok": False}), 404

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
