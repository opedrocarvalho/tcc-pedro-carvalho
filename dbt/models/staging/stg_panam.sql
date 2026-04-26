with source as (
    select * from {{ source('raw', 'panam') }}
),

transformado as (
    select
        data_extracao,

        'Panam'    as operadora,
        'Chile'    as pais_origem,
        'es'       as idioma,

        destino    as titulo,
        null::varchar as descricao,
        null::varchar as tipo,

        preco_usd  as preco_texto,
        cast(
            nullif(
                replace(
                    replace(
                        regexp_replace(preco_usd, '[^\d.,]', '', 'g'),
                        '.', ''         
                    ),
                    ',', '.'             
                ),
                ''
            )
        as numeric)    as preco_valor,
        'USD'          as preco_moeda,

        duracao        as duracao_texto,
        {{ extrair_duracao_dias('duracao') }} as duracao_dias,

        url

    from source
    where destino is not null
      and destino not ilike '%não disponível%'
)

select * from transformado
