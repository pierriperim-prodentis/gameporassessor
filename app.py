import streamlit as st
import streamlit.components.v1 as components
from pathlib import Path
from datetime import datetime, timedelta
import json
import requests

st.set_page_config(
    page_title="Arena de Vendas - Assessores",
    page_icon="🏁",
    layout="wide",
)

st.markdown(
    """
    <style>
        .block-container {padding: 1rem 1rem 0 1rem; max-width: 100%;}
        header {visibility: hidden;}
        footer {visibility: hidden;}
    </style>
    """,
    unsafe_allow_html=True,
)

# ---------- CONFIG ----------
SENHA_ADMIN = "Palmas26"  # troque essa senha se quiser (e o link que você usa)

JSONBIN_ID = st.secrets.get("JSONBIN_ID", "")
JSONBIN_KEY = st.secrets.get("JSONBIN_KEY", "")
JSONBIN_URL = f"https://api.jsonbin.io/v3/b/{JSONBIN_ID}"

DATA_FILE = Path(__file__).parent / "dados_placar.json"  # usado só como reserva local, se o jsonbin falhar

ASSESSORES = [
    {"id": "bruna", "nome": "Bruna", "cor": "#FF5D73"},
    {"id": "made", "nome": "Madê", "cor": "#35D0BA"},
    {"id": "luana", "nome": "Luana", "cor": "#FFCB47"},
    {"id": "diego", "nome": "Diego", "cor": "#6C7BFF"},
    {"id": "francely", "nome": "Francely", "cor": "#4CD97B"},
    {"id": "lizia", "nome": "Lizia", "cor": "#FF8FD6"},
    {"id": "jarlene", "nome": "Jarlene", "cor": "#4FB6FF"},
]

NOMES_CONHECIDOS = [a["nome"] for a in ASSESSORES] + ["Outro"]

DEFAULTS_PLACAR = {"dias": 0}
for a in ASSESSORES:
    DEFAULTS_PLACAR[a["id"]] = {"ml": 0, "vl": 0}


def carregar_tudo():
    bruto = None
    if JSONBIN_ID and JSONBIN_KEY:
        try:
            r = requests.get(
                f"{JSONBIN_URL}/latest",
                headers={"X-Master-Key": JSONBIN_KEY, "X-Bin-Meta": "false"},
                timeout=15,
            )
            if r.status_code == 200:
                bruto = r.json()
        except Exception:
            pass
    if bruto is None and DATA_FILE.exists():
        try:
            bruto = json.loads(DATA_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
    if bruto is None:
        bruto = {}

    if "placar" in bruto:
        placar = bruto.get("placar", {})
    else:
        placar = bruto if bruto else json.loads(json.dumps(DEFAULTS_PLACAR))

    comentarios = bruto.get("comentarios", [])
    return {"placar": placar, "comentarios": comentarios}


def salvar_tudo(d):
    ok = False
    detalhe = ""
    if not (JSONBIN_ID and JSONBIN_KEY):
        return False, "Secrets JSONBIN_ID/JSONBIN_KEY não configuradas."
    for tentativa in range(2):
        try:
            r = requests.put(
                JSONBIN_URL,
                headers={"X-Master-Key": JSONBIN_KEY, "Content-Type": "application/json"},
                data=json.dumps(d),
                timeout=20,
            )
            ok = r.status_code == 200
            if ok:
                detalhe = ""
                break
            detalhe = f"HTTP {r.status_code}: {r.text[:300]}"
        except Exception as e:
            detalhe = f"Erro de conexão: {e}"
    try:
        DATA_FILE.write_text(json.dumps(d, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception:
        pass
    return ok, detalhe


def fmt_valor(v):
    return f"{float(v):.2f}".replace(".", ",")


tudo = carregar_tudo()
dados = tudo["placar"]
comentarios = tudo["comentarios"]
is_admin = st.query_params.get("chave") == SENHA_ADMIN

# ---------- PAINEL ADMIN ----------
if is_admin:
    st.title("🔐 Painel Admin — Arena de Vendas por Assessor")
    st.caption("Só quem tem o link com a chave vê esta parte. Os assessores acessam a URL normal e veem só o resultado abaixo.")

    if not (JSONBIN_ID and JSONBIN_KEY):
        st.warning("⚠️ Armazenamento permanente não configurado (faltam as Secrets JSONBIN_ID/JSONBIN_KEY). Os dados podem se perder quando o app dormir.")

    with st.form("form_placar"):
        dias_input = st.number_input(
            "Dias úteis passados no mês", min_value=0, max_value=31, value=int(dados.get("dias", 0))
        )
        novo_placar = {"dias": dias_input}

        cols = st.columns(4)
        for i, a in enumerate(ASSESSORES):
            col = cols[i % 4]
            with col:
                aid = a["id"]
                st.markdown(f"#### <span style='color:{a['cor']}'>●</span> {a['nome']}", unsafe_allow_html=True)
                atual = dados.get(aid, DEFAULTS_PLACAR[aid])
                ml = st.number_input("Meta Loja (R$)", min_value=0.0, value=float(atual.get("ml", 0)), key=f"ml_{aid}")
                vl = st.number_input("Atingido Loja (R$)", min_value=0.0, value=float(atual.get("vl", 0)), key=f"vl_{aid}")
                novo_placar[aid] = {"ml": ml, "vl": vl}

        enviado = st.form_submit_button("💾 Salvar e Publicar")
        if enviado:
            ok, detalhe = salvar_tudo({"placar": novo_placar, "comentarios": comentarios})
            dados = novo_placar
            if ok:
                st.success("Placar atualizado e salvo permanentemente na nuvem!")
            else:
                st.warning(f"Salvo localmente, mas não confirmou o envio pra nuvem.\n\n**Detalhe:** {detalhe}")

    st.divider()
    st.caption("Pré-visualização — é isso que os assessores veem:")

# ---------- MONTA O HTML (mesmo pros dois casos) ----------
html_path = Path(__file__).parent / "arena_assessores.html"
html_content = html_path.read_text(encoding="utf-8")

init_lines = ["(function(){"]
init_lines.append(f'  document.getElementById("dias").value = {int(dados.get("dias", 0))};')
for a in ASSESSORES:
    aid = a["id"]
    valores = dados.get(aid, DEFAULTS_PLACAR[aid])
    for campo in ["ml", "vl"]:
        valor_str = fmt_valor(valores.get(campo, 0))
        init_lines.append(f'  document.getElementById("{campo}_{aid}").value = {json.dumps(valor_str)};')
init_lines.append('  if(typeof atualizar==="function") atualizar();')
init_lines.append("})();")
init_script = "\n".join(init_lines)

html_final = html_content.replace(
    "</body>",
    f"<style>.input-section{{display:none!important;}} #totais-section{{display:none!important;}}</style><script>{init_script}</script></body>",
)

components.html(html_final, height=1150, scrolling=True)

# ---------- MURAL DA TORCIDA ----------
st.markdown("### 💬 Mural da Torcida")
st.caption("Deixa seu recado pra galera! Aparece pra todo mundo, na hora.")

with st.form("form_comentario", clear_on_submit=True):
    c1, c2 = st.columns([1, 3])
    with c1:
        nome_sel = st.selectbox("Seu nome", NOMES_CONHECIDOS)
        nome_outro = st.text_input("Se 'Outro', digite aqui") if nome_sel == "Outro" else ""
    with c2:
        texto = st.text_input("Comentário", placeholder="Ex: Bora Jarlene, cola nela! 🔥")
    enviar_comentario = st.form_submit_button("Enviar 🚀")

    if enviar_comentario and texto.strip():
        nome_final = (nome_outro.strip() or "Alguém") if nome_sel == "Outro" else nome_sel
        agora = datetime.utcnow() - timedelta(hours=3)  # horário de Brasília
        novo_comentario = {
            "nome": nome_final,
            "texto": texto.strip()[:200],
            "hora": agora.strftime("%d/%m %H:%M"),
        }
        comentarios = ([novo_comentario] + comentarios)[:50]
        salvar_tudo({"placar": dados, "comentarios": comentarios})
        st.rerun()

if not comentarios:
    st.caption("Nenhum comentário ainda — seja o primeiro!")
else:
    for c in comentarios[:20]:
        st.markdown(f"**{c.get('nome','?')}** · _{c.get('hora','')}_  \n{c.get('texto','')}")
        st.markdown("---")

if is_admin and comentarios:
    if st.button("🗑️ Limpar mural"):
        salvar_tudo({"placar": dados, "comentarios": []})
        st.rerun()
