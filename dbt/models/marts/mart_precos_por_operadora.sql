with fatos as (
    select * from {{ ref('fct_pacotes') }}
    where preco_valor is not null
      and preco_valor > 0
      and not (preco_moeda = 'CLP' and preco_valor < 10000)  -- CLP < 10k ≈ < USD 10, claramente espúrio
),

operadoras as (
    select nome_display, regiao_origem, moeda_nome
    from {{ ref('dim_operadora') }}
)

select
    o.regiao_origem,
    f.operadora_nome                        as operadora,
    f.preco_moeda                           as moeda,
    ROUND(AVG(f.preco_valor), 2)            as preco_medio,
    MIN(f.preco_valor)                      as menor_preco,
    MAX(f.preco_valor)                      as preco_maximo,
    COUNT(*)                                as total_pacotes

from fatos f
left join operadoras o on o.nome_display = f.operadora_nome

group by
    o.regiao_origem,
    f.operadora_nome,
    f.preco_moeda
