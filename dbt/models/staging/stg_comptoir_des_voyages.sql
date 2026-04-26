with source as (
    select * from {{ source('raw', 'comptoir_des_voyages') }}
),

transformado as (
    select
        data_extracao,

        'Comptoir des Voyages' as operadora,
        'França'               as pais_origem,
        'fr'                   as idioma,

        split_part(destino, chr(10), 1) as titulo,
        descricao,
        null::varchar                   as tipo,

        preco                  as preco_texto,
        cast(
            nullif(regexp_replace(preco, '[^\d]', '', 'g'), '')
        as numeric)            as preco_valor,
        'EUR'                  as preco_moeda,

        duracao                as duracao_texto,
        {{ extrair_duracao_dias('duracao') }} as duracao_dias,

        url

    from source
    where destino is not null
      and destino not ilike '%não encontrado%'
)

select * from transformado
