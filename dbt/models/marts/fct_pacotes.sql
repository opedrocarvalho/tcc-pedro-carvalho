with obt as (
    select * from {{ ref('obt_pacotes') }}
),

dim_op as (
    select operadora_key, nome_display
    from {{ ref('dim_operadora') }}
),

fatos as (
    select
        obt.pacote_id,
        obt.data_extracao_date              as data_key,
        obt.operadora                       as operadora_nome_join,
        obt.titulo,
        obt.tipo,
        obt.url,
        obt.preco_valor,
        obt.preco_moeda,
        obt.preco_texto,
        obt.duracao_dias,
        obt.duracao_texto,
        obt.data_extracao,
        obt.idioma

    from obt
)

select
    f.pacote_id,
    f.data_key,
    d.operadora_key,
    f.operadora_nome_join                   as operadora_nome,

    f.titulo,
    f.tipo,
    f.url,

    f.preco_valor,
    f.preco_moeda,
    f.preco_texto,

    f.duracao_dias,
    f.duracao_texto,

    f.data_extracao,
    f.idioma

from fatos f
left join dim_op d on d.nome_display = f.operadora_nome_join
