-- tabela de clientes
create table clientes (
    id bigint generated always as identity primary key,
    nome text not null,
    email text not null unique
        check (email ~* '^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$'),
    celular text not null
        check (celular ~ '^\d{10,11}$'),
    criado_em timestamptz not null default now()
);

-- tabela de ordens de serviço
create table ordens_servico (
    id bigint generated always as identity primary key,
    cliente_id bigint not null,
    equipamento text not null,
    defeito_relatado text not null,
    status text not null default 'Aberto'
        check (status in ('Aberto', 'Em análise', 'Aguardando peça', 'Concluído', 'Entregue')),
    valor_orcamento numeric(10, 2) check (valor_orcamento >= 0),
    data_abertura timestamptz not null default now(),
    data_atualizacao timestamptz not null default now(),

    constraint fk_cliente
        foreign key (cliente_id)
        references clientes (id)
        on delete restrict
);

-- indice para buscar as os de um cliente mais rápido
create index idx_ordens_cliente on ordens_servico (cliente_id);

-- indice para o filtro por status do painel do gerente
create index idx_ordens_status on ordens_servico (status);

-- como é um exercício com dados fictícios, deixo o rls desligado
-- em um sistema de verdade eu criaria policies para controlar quem lê e escreve
alter table clientes disable row level security;
alter table ordens_servico disable row level security;

-- dados fictícios só para testar o painel (pode apagar depois)
insert into clientes (nome, email, celular) values
    ('Cliente Teste Um', 'cliente.um@exemplo.com', '11900000001'),
    ('Cliente Teste Dois', 'cliente.dois@exemplo.com', '11900000002');

insert into ordens_servico (cliente_id, equipamento, defeito_relatado, status) values
    (1, 'Notebook Exemplo', 'não liga', 'Aberto'),
    (1, 'Impressora Exemplo', 'papel enroscando', 'Em análise'),
    (2, 'Desktop Exemplo', 'tela azul ao iniciar', 'Concluído');
