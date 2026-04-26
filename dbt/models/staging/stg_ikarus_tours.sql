with source as (
    select * from {{ source('raw', 'ikarus_tours') }}
),

transformado as (
    select
        data_extracao,

        'Ikarus Tours' as operadora,
        'Alemanha'     as pais_origem,
        'de'           as idioma,

        titulo,
        descricao,
        null::varchar  as tipo,

        preco          as preco_texto,
        cast(
            nullif(regexp_replace(preco, '[^\d]', '', 'g'), '')
        as numeric)    as preco_valor,
        'EUR'          as preco_moeda,

        duracao        as duracao_texto,
        {{ extrair_duracao_dias('duracao') }} as duracao_dias,

        url

    from source
    where titulo is not null
      and titulo not ilike '%nicht angegeben%'
      and url is not null
      and url != ''
      and (
          lower(titulo)    like '%brasil%'
          or lower(titulo)    like '%amazon%'
          or lower(titulo)    like '%iguazu%'
          or lower(titulo)    like '%iguaç%'
          or lower(descricao) like '%brasilien%'
          or lower(descricao) like '%brasil%'
      )
)

select * from transformado
