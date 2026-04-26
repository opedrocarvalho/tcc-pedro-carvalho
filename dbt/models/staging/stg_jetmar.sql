with source as (
    select * from {{ source('raw', 'jetmar') }}
),

transformado as (
    select
        data_extracao,

        'Jetmar'   as operadora,
        'Uruguai'  as pais_origem,
        'es'       as idioma,

        destino    as titulo,
        descricao,
        null::varchar as tipo,

        preco_completo as preco_texto,
        cast(
            nullif(
                replace(
                    replace(
                        regexp_replace(preco_completo, '[^\d.,]', '', 'g'),
                        '.', ''     -- ponto = separador de milhar (formato sul-americano)
                    ),
                    ',', '.'        -- vírgula = decimal → ponto para SQL
                ),
                ''
            )
        as numeric)    as preco_valor,
        coalesce(
            (regexp_match(preco_completo, '(USD|EUR|GBP|BRL|ARS|CLP|UYU)'))[1],
            'USD'
        )              as preco_moeda,

        null::varchar  as duracao_texto,
        null::integer  as duracao_dias,

        url

    from source
    where destino is not null
      and destino not ilike '%não encontrado%'
      and preco_completo not ilike '%não encontrado%'
      and preco_completo not ilike '%Preço não encontrado%'
)

select * from transformado
