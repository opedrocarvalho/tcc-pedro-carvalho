
with bleu_selectour as (
    select * from {{ ref('stg_bleu_selectour') }}
),
comptoir_des_voyages as (
    select * from {{ ref('stg_comptoir_des_voyages') }}
),
ikarus_tours as (
    select * from {{ ref('stg_ikarus_tours') }}
),
jetmar as (
    select * from {{ ref('stg_jetmar') }}
),
journey_latin_america as (
    select * from {{ ref('stg_journey_latin_america') }}
),
newmarket_holidays as (
    select * from {{ ref('stg_newmarket_holidays') }}
),
panam as (
    select * from {{ ref('stg_panam') }}
),
sol_ferias as (
    select * from {{ ref('stg_sol_ferias') }}
),
transalpino as (
    select * from {{ ref('stg_transalpino') }}
),
turismo_costanera as (
    select * from {{ ref('stg_turismo_costanera') }}
),

colunas_comuns as (
    select data_extracao, operadora, pais_origem, idioma, titulo, descricao, tipo,
           preco_texto, preco_valor, preco_moeda, duracao_texto, duracao_dias, url
    from bleu_selectour
    union all
    select data_extracao, operadora, pais_origem, idioma, titulo, descricao, tipo,
           preco_texto, preco_valor, preco_moeda, duracao_texto, duracao_dias, url
    from comptoir_des_voyages
    union all
    select data_extracao, operadora, pais_origem, idioma, titulo, descricao, tipo,
           preco_texto, preco_valor, preco_moeda, duracao_texto, duracao_dias, url
    from ikarus_tours
    union all
    select data_extracao, operadora, pais_origem, idioma, titulo, descricao, tipo,
           preco_texto, preco_valor, preco_moeda, duracao_texto, duracao_dias, url
    from jetmar
    union all
    select data_extracao, operadora, pais_origem, idioma, titulo, descricao, tipo,
           preco_texto, preco_valor, preco_moeda, duracao_texto, duracao_dias, url
    from journey_latin_america
    union all
    select data_extracao, operadora, pais_origem, idioma, titulo, descricao, tipo,
           preco_texto, preco_valor, preco_moeda, duracao_texto, duracao_dias, url
    from newmarket_holidays
    union all
    select data_extracao, operadora, pais_origem, idioma, titulo, descricao, tipo,
           preco_texto, preco_valor, preco_moeda, duracao_texto, duracao_dias, url
    from panam
    union all
    select data_extracao, operadora, pais_origem, idioma, titulo, descricao, tipo,
           preco_texto, preco_valor, preco_moeda, duracao_texto, duracao_dias, url
    from sol_ferias
    union all
    select data_extracao, operadora, pais_origem, idioma, titulo, descricao, tipo,
           preco_texto, preco_valor, preco_moeda, duracao_texto, duracao_dias, url
    from transalpino
    union all
    select data_extracao, operadora, pais_origem, idioma, titulo, descricao, tipo,
           preco_texto, preco_valor, preco_moeda, duracao_texto, duracao_dias, url
    from turismo_costanera
),

unificado as (select * from colunas_comuns)

select
    md5(
        coalesce(operadora, '') || '|' ||
        coalesce(titulo, '')   || '|' ||
        coalesce(cast(data_extracao as varchar), '')
    )                           as pacote_id,

    data_extracao,
    cast(data_extracao as date) as data_extracao_date,

    operadora,
    pais_origem,
    idioma,
    titulo,
    descricao,
    tipo,

    preco_texto,
    preco_valor,
    preco_moeda,

    duracao_texto,
    duracao_dias,

    url

from unificado
