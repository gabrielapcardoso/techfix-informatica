import re
import gradio as gr
from conexao import conectar

# padrões de validação (o fullmatch exige que o texto inteiro bata com o padrão)
regex_email = r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}"
regex_celular = r"\d{10,11}"


def validar_campos(nome, email, celular, equipamento, defeito):
    # confere se algum campo ficou vazio
    if not nome or not email or not celular or not equipamento or not defeito:
        return "Erro: todos os campos são obrigatórios."

    if not re.fullmatch(regex_email, email):
        return "Erro: formato de e-mail inválido."

    if not re.fullmatch(regex_celular, celular):
        return "Erro: o celular deve ter 10 ou 11 números, com DDD."

    # se chegou aqui está tudo certo
    return None


def buscar_cliente_por_email(supabase, email):
    resposta = supabase.table("clientes").select("*").eq("email", email).execute()

    # se a lista vier vazia, o cliente ainda não existe
    if resposta.data:
        return resposta.data[0]
    return None


def criar_cliente(supabase, nome, email, celular):
    resposta = supabase.table("clientes").insert({
        "nome": nome,
        "email": email,
        "celular": celular
    }).execute()
    return resposta.data[0]


def criar_ordem_servico(supabase, cliente_id, equipamento, defeito):
    resposta = supabase.table("ordens_servico").insert({
        "cliente_id": cliente_id,
        "equipamento": equipamento,
        "defeito_relatado": defeito,
        "status": "Aberto"
    }).execute()
    return resposta.data[0]


def abrir_os(nome, email, celular, equipamento, defeito):
    # tira espaços das pontas e deixa o e-mail em minúsculo
    nome = nome.strip()
    email = email.strip().lower()
    equipamento = equipamento.strip()
    defeito = defeito.strip()

    # remove parênteses, traços e espaços do celular, ficando só os números
    celular = re.sub(r"\D", "", celular)

    erro_validacao = validar_campos(nome, email, celular, equipamento, defeito)
    if erro_validacao:
        return erro_validacao

    try:
        supabase = conectar()

        # reaproveita o cliente se o e-mail já existir, senão cria um novo
        cliente = buscar_cliente_por_email(supabase, email)

        if cliente:
            cliente_id = cliente["id"]
            mensagem_cliente = f"Cliente já cadastrado (ID {cliente_id}), dados reaproveitados."
        else:
            novo_cliente = criar_cliente(supabase, nome, email, celular)
            cliente_id = novo_cliente["id"]
            mensagem_cliente = f"Novo cliente cadastrado (ID {cliente_id})."

        nova_os = criar_ordem_servico(supabase, cliente_id, equipamento, defeito)

        return (
            f"{mensagem_cliente}\n"
            f"Ordem de serviço nº {nova_os['id']} aberta com sucesso.\n"
            f"Status inicial: {nova_os['status']}"
        )

    except Exception as erro:
        return f"Erro ao comunicar com o banco de dados: {erro}"


with gr.Blocks(title="TechFix Informática") as app:
    gr.Markdown("## TechFix Informática - abertura de ordem de serviço")

    nome_input = gr.Textbox(label="Nome do cliente")

    # a linha quebra em duas no celular, deixando o formulário responsivo
    with gr.Row():
        email_input = gr.Textbox(label="E-mail")
        celular_input = gr.Textbox(label="Celular com DDD")

    equipamento_input = gr.Textbox(label="Equipamento")
    defeito_input = gr.Textbox(label="Defeito relatado", lines=3)

    botao_abrir = gr.Button("Abrir ordem de serviço")
    resultado_output = gr.Textbox(label="Resultado", interactive=False, lines=4)

    botao_abrir.click(
        fn=abrir_os,
        inputs=[nome_input, email_input, celular_input, equipamento_input, defeito_input],
        outputs=resultado_output
    )

app.launch()
