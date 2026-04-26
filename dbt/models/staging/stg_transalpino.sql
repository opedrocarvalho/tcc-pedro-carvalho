with source as (
    select * from {{ source('raw', 'transalpino') }}
),

brasil as (
    select * from source
    where lower(destino) like '%brasil%'
       or lower(url)     like '%brasil%'
),

transformado as (
    select
        data_extracao,

        'Transalpino' as operadora,
        'Portugal'    as pais_origem,
        'pt'          as idioma,

        destino       as titulo,
        split_part(descricao, chr(10), 1) as descricao,
        null::varchar as tipo,

        preco         as preco_texto,
        cast(
            nullif(regexp_replace(preco, '[^\d]', '', 'g'), '')
        as numeric)   as preco_valor,
        'EUR'         as preco_moeda,

        descricao     as duracao_texto,
        cast(
            (regexp_match(descricao, '(\d+)\s*Dias?', 'i'))[1]
        as integer)   as duracao_dias,

        url

    from brasil
    where destino is not null
      and destino not ilike '%não encontrado%'
)

select * from transformado
