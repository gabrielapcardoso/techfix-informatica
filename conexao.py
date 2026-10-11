import os
from dotenv import load_dotenv
from supabase import create_client

# carrega as variáveis do arquivo .env
load_dotenv()


def conectar():
    url = os.getenv("SUPABASE_URL")
    chave = os.getenv("SUPABASE_KEY")

    # se esqueci de preencher o .env, avisa com uma mensagem clara
    if not url or not chave:
        raise ValueError("credenciais do supabase não encontradas, confira o arquivo .env")

    return create_client(url, chave)
