with source as (
    select * from {{ source('raw', 'turismo_costanera') }}
),

transformado as (
    select
        data_extracao,

        'Turismo Costanera' as operadora,
        'Chile'             as pais_origem,
        'es'                as idioma,

        titulo,
        null::varchar       as descricao,
        null::varchar       as tipo,

        preco               as preco_texto,
        cast(
            replace(
                (regexp_match(preco, '\d[\d.]*\d|\d+'))[1],
                '.', ''
            )
        as numeric)         as preco_valor,
        coalesce(
            (regexp_match(preco, '(USD|EUR|GBP|BRL|ARS|CLP|UYU)'))[1],
            'USD'
        )                   as preco_moeda,

        duracao             as duracao_texto,
        {{ extrair_duracao_dias('duracao') }} as duracao_dias,

        url,

        local               as destino_cidade

    from source
    where titulo is not null
      and titulo != ''
      and local = 'Brasil'
)

select * from transformado
