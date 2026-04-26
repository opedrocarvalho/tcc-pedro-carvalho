with source as (
    select * from {{ source('raw', 'newmarket_holidays') }}
),

transformado as (
    select
        data_extracao,

        'Newmarket Holidays' as operadora,
        'Reino Unido'        as pais_origem,
        'en'                 as idioma,

        titulo,
        left(
            regexp_replace(descricao, '\s+', ' ', 'g'),
            400
        )                    as descricao,
        null::varchar        as tipo,

        preco                as preco_texto,
        cast(
            nullif(
                regexp_replace(
                    regexp_replace(preco, '.*£', ''),  
                    '[^\d]', '', 'g'                   
                ),
                ''
            )
        as numeric)          as preco_valor,
        'GBP'                as preco_moeda,

        duracao              as duracao_texto,
        {{ extrair_duracao_dias('duracao') }} as duracao_dias,

        url

    from source
    where titulo is not null
      and titulo not ilike '%não encontrado%'
)

select * from transformado
