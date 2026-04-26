with base as (
    select * from {{ ref('dim_destino') }}
    where destino not in ('Outros / Múltiplos', 'Brasil (múltiplos destinos)')
      and preco_valor is not null
      and preco_valor > 0
)

select
    destino,
    preco_moeda                     as moeda,
    ROUND(AVG(preco_valor), 2)      as preco_medio,
    MIN(preco_valor)                as preco_minimo,
    MAX(preco_valor)                as preco_maximo,
    COUNT(*)                        as total_pacotes

from base
group by
    destino,
    preco_moeda
order by
    preco_medio desc
