import pandas as pd
import matplotlib.pyplot as plt
import streamlit as st
from datetime import datetime, timezone
from supabase import create_client

st.set_page_config(page_title="TechFix - painel do gerente", layout="wide")

# a ordem segue o fluxo da oficina
status_opcoes = ["Aberto", "Em análise", "Aguardando peça", "Concluído", "Entregue"]


@st.cache_resource
def conectar():
    # as chaves ficam em .streamlit/secrets.toml (local) ou nos secrets do streamlit cloud
    url = st.secrets["SUPABASE_URL"]
    chave = st.secrets["SUPABASE_KEY"]
    return create_client(url, chave)


def carregar_ordens(supabase):
    # o select com clientes(...) traz junto o nome e o e-mail do cliente
    resposta = (
        supabase.table("ordens_servico")
        .select("*, clientes(nome, email)")
        .order("data_abertura", desc=True)
        .execute()
    )
    df = pd.DataFrame(resposta.data)

    if df.empty:
        return df

    # os dados do cliente vêm dentro de um dicionário, então separo em colunas
    df["cliente"] = df["clientes"].apply(lambda c: c["nome"])
    df["email"] = df["clientes"].apply(lambda c: c["email"])

    colunas = ["id", "cliente", "email", "equipamento", "defeito_relatado",
               "status", "valor_orcamento", "data_abertura", "data_atualizacao"]
    return df[colunas]


st.title("TechFix Informática - painel do gerente")

# mensagem guardada antes de um st.rerun() aparece aqui, senão sumiria
if "mensagem" in st.session_state:
    st.success(st.session_state.pop("mensagem"))

try:
    supabase = conectar()
    df_todas = carregar_ordens(supabase)
except Exception as erro:
    st.error(f"Erro ao conectar ou carregar os dados: {erro}")
    st.stop()

# filtros da barra lateral
st.sidebar.header("Filtros")
filtro_status = st.sidebar.selectbox("Status", ["Todos"] + status_opcoes)
filtro_nome = st.sidebar.text_input("Nome do cliente")

df_filtrado = df_todas.copy()
if not df_filtrado.empty:
    if filtro_status != "Todos":
        df_filtrado = df_filtrado[df_filtrado["status"] == filtro_status]
    if filtro_nome:
        df_filtrado = df_filtrado[
            df_filtrado["cliente"].str.contains(filtro_nome, case=False, regex=False)
        ]

aba_consultar, aba_cadastrar, aba_editar, aba_indicadores = st.tabs(
    ["Consultar", "Cadastrar", "Editar/Excluir", "Indicadores"]
)

# aba consultar
with aba_consultar:
    st.subheader("Ordens de serviço")

    if df_filtrado.empty:
        st.info("Nenhuma ordem de serviço encontrada.")
    else:
        st.dataframe(df_filtrado, hide_index=True)

        # utf-8-sig para o excel abrir os acentos certinho
        csv = df_filtrado.to_csv(index=False).encode("utf-8-sig")
        st.download_button(
            "Exportar CSV",
            data=csv,
            file_name="ordens_servico.csv",
            mime="text/csv"
        )

# aba cadastrar
with aba_cadastrar:
    st.subheader("Nova ordem de serviço")

    try:
        resposta = supabase.table("clientes").select("id, nome, email").order("nome").execute()
        clientes = resposta.data
    except Exception as erro:
        st.error(f"Erro ao carregar os clientes: {erro}")
        clientes = []

    if not clientes:
        st.warning("Nenhum cliente cadastrado. Cadastre o primeiro pelo app do Gradio.")
    else:
        # dicionário: texto que aparece na tela -> id do cliente
        opcoes = {f"{c['nome']} ({c['email']})": c["id"] for c in clientes}

        with st.form("form_nova_os", clear_on_submit=True):
            cliente_escolhido = st.selectbox("Cliente", list(opcoes.keys()))
            equipamento = st.text_input("Equipamento")
            defeito = st.text_area("Defeito relatado")
            enviado = st.form_submit_button("Cadastrar OS")

        if enviado:
            if not equipamento.strip() or not defeito.strip():
                st.error("Equipamento e defeito são obrigatórios.")
            else:
                try:
                    supabase.table("ordens_servico").insert({
                        "cliente_id": opcoes[cliente_escolhido],
                        "equipamento": equipamento.strip(),
                        "defeito_relatado": defeito.strip(),
                        "status": "Aberto"
                    }).execute()
                except Exception as erro:
                    st.error(f"Erro ao cadastrar a OS: {erro}")
                else:
                    st.session_state["mensagem"] = "Ordem de serviço cadastrada com sucesso."
                    st.rerun()

# aba editar e excluir
with aba_editar:
    st.subheader("Editar ou excluir ordem de serviço")

    if df_todas.empty:
        st.info("Nenhuma ordem de serviço cadastrada.")
    else:
        os_id = int(st.selectbox("Selecione a OS pelo número", df_todas["id"]))
        linha = df_todas[df_todas["id"] == os_id].iloc[0]

        st.write(f"Cliente: {linha['cliente']}")
        st.write(f"Equipamento: {linha['equipamento']}")
        st.write(f"Status atual: {linha['status']}")

        novo_status = st.selectbox(
            "Novo status",
            status_opcoes,
            index=status_opcoes.index(linha["status"]),
            key=f"status_{os_id}"
        )

        # se a os ainda não tem orçamento o valor vem vazio, então uso 0
        valor_atual = 0.0 if pd.isna(linha["valor_orcamento"]) else float(linha["valor_orcamento"])
        novo_valor = st.number_input(
            "Valor do orçamento (R$)",
            min_value=0.0,
            value=valor_atual,
            step=10.0,
            key=f"valor_{os_id}"
        )

        col1, col2 = st.columns(2)

        with col1:
            if st.button("Salvar alterações"):
                try:
                    supabase.table("ordens_servico").update({
                        "status": novo_status,
                        "valor_orcamento": novo_valor,
                        "data_atualizacao": datetime.now(timezone.utc).isoformat()
                    }).eq("id", os_id).execute()
                except Exception as erro:
                    st.error(f"Erro ao atualizar a OS: {erro}")
                else:
                    st.session_state["mensagem"] = f"OS {os_id} atualizada com sucesso."
                    st.rerun()

        with col2:
            # confirmação para não excluir sem querer
            confirmar = st.checkbox("Confirmo que quero excluir esta OS")
            if st.button("Excluir OS", type="primary"):
                if not confirmar:
                    st.warning("Marque a confirmação antes de excluir.")
                else:
                    try:
                        supabase.table("ordens_servico").delete().eq("id", os_id).execute()
                    except Exception as erro:
                        st.error(f"Erro ao excluir a OS: {erro}")
                    else:
                        st.session_state["mensagem"] = f"OS {os_id} excluída."
                        st.rerun()

# aba indicadores
with aba_indicadores:
    st.subheader("Indicadores gerais")
    st.caption("Os indicadores usam todas as ordens, sem os filtros da barra lateral.")

    if df_todas.empty:
        st.info("Sem dados suficientes para gerar indicadores.")
    else:
        total = len(df_todas)
        abertas = len(df_todas[df_todas["status"] == "Aberto"])
        em_andamento = len(df_todas[df_todas["status"].isin(["Em análise", "Aguardando peça"])])
        finalizadas = len(df_todas[df_todas["status"].isin(["Concluído", "Entregue"])])

        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Total de OS", total)
        col2.metric("Abertas", abertas)
        col3.metric("Em andamento", em_andamento)
        col4.metric("Concluídas/Entregues", finalizadas)

        # reindex mantém a ordem do fluxo e mostra 0 nos status sem nenhuma os
        contagem = df_todas["status"].value_counts().reindex(status_opcoes, fill_value=0)

        fig, ax = plt.subplots()
        ax.bar(contagem.index, contagem.values, color="steelblue")
        ax.set_title("Ordens de serviço por status")
        ax.set_ylabel("Quantidade")
        ax.tick_params(axis="x", rotation=30)
        st.pyplot(fig)
