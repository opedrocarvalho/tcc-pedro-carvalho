with source as (
    select * from {{ source('raw', 'journey_latin_america') }}
),

transformado as (
    select
        data_extracao,

        'Journey Latin America' as operadora,
        'Reino Unido'           as pais_origem,
        'en'                    as idioma,

        titulo,
        descricao,
        null::varchar           as tipo,

        preco                   as preco_texto,
        cast(
            nullif(regexp_replace(preco, '[^\d]', '', 'g'), '')
        as numeric)             as preco_valor,
        'GBP'                   as preco_moeda,

        duracao                 as duracao_texto,
        {{ extrair_duracao_dias('duracao') }} as duracao_dias,

        url_detalhes            as url

    from source
    where titulo is not null
      and titulo not ilike '%não encontrado%'
      and (
          lower(url_detalhes) like '%/brazil/%'
          or lower(descricao)  like '%brazil%'
      )
)

select * from transformado
