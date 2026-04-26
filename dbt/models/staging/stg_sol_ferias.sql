with source as (
    select * from {{ source('raw', 'sol_ferias') }}
),

transformado as (
    select
        data_extracao,

        'Sol Férias' as operadora,
        'Portugal'   as pais_origem,
        'pt'         as idioma,

        titulo,
        trim(
            regexp_replace(
                replace(descricao, u&'\00A0', ' '),  
                '\s+', ' ', 'g'
            )
        )            as descricao,
        null::varchar as tipo,

        preco        as preco_texto,
        cast(
            nullif(regexp_replace(preco, '[^\d]', '', 'g'), '')
        as numeric)  as preco_valor,
        'EUR'        as preco_moeda,

        duracao      as duracao_texto,
        {{ extrair_duracao_dias('duracao') }} as duracao_dias,

        url,

        destino      as destino_cidade,
        id_pacote,
        codigo

    from source
    where titulo is not null
      and titulo != 'N/D'
)

select * from transformado
