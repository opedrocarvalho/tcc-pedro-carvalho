with source as (
    select * from {{ source('raw', 'bleu_selectour') }}
),

transformado as (
    select
        data_extracao,

        'Bleu Selectour'  as operadora,
        'França'          as pais_origem,
        'fr'              as idioma,

        titulo,
        informacoes       as descricao,
        tipo,

        preco             as preco_texto,
        cast(
            nullif(regexp_replace(preco, '[^\d]', '', 'g'), '')
        as numeric)       as preco_valor,
        'EUR'             as preco_moeda,

        duracao           as duracao_texto,
        {{ extrair_duracao_dias('duracao') }} as duracao_dias,

        null::varchar     as url

    from source
    where titulo is not null
      and titulo not ilike '%não encontrado%'
)

select * from transformado
