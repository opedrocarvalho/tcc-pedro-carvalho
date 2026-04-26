with obt as (
    select * from {{ ref('obt_pacotes') }}
    where preco_moeda in ('USD', 'EUR', 'GBP')
      and preco_valor is not null
      and preco_valor > 0
),

com_destino as (
    select
        pacote_id,
        operadora,
        titulo,
        preco_valor,
        preco_moeda,
        duracao_dias,
        data_extracao,
        data_extracao_date,

        case
            when lower(titulo) like '%rio de janeiro%'
              or lower(titulo) like '%río de janeiro%'
              or lower(titulo) like '%carioca%'
              or lower(titulo) like '%sugarloaf%'
              or lower(titulo) like '%barra da tijuca%'
              or lower(titulo) like '%christ the redeemer%'
              or (lower(titulo) like '%rio%'
                  and lower(titulo) not like '%parana%'
                  and lower(titulo) not like '%negro%'
                  and lower(titulo) not like '%grande%'
                  and lower(titulo) not like '%porto%'
                  and lower(titulo) not like '%san pablo%')
                                                            then 'Rio de Janeiro'
            when lower(titulo) like '%maceió%'
              or lower(titulo) like '%maceio%'
              or lower(titulo) like '%maragogi%'          then 'Maceió / Maragogi'
            when lower(titulo) like '%porto seguro%'
              or lower(titulo) like '%trancoso%'
              or lower(titulo) like '%arraial d%'         then 'Porto Seguro / Trancoso'
            when lower(titulo) like '%salvador%'
              or lower(titulo) like '%bahia%'
              or lower(titulo) like '%bahía%'
              or lower(titulo) like '%imbassai%'
              or lower(titulo) like '%imbasai%'
              or lower(titulo) like '%praia do forte%'
              or lower(titulo) like '%chapada diamantina%'
              or lower(titulo) like '%capoeira%'
              or lower(titulo) like '%vila galé marés%'
              or lower(titulo) like '%vila gale mares%' then 'Bahia / Salvador'
            when lower(titulo) like '%nordeste%'
              or lower(titulo) like '%recife%'
              or lower(titulo) like '%olinda%'
              or lower(titulo) like '%serrambi%'
              or lower(titulo) like '%serrambí%'
              or lower(titulo) like '%vila galé santo agostinho%'
              or lower(titulo) like '%vila gale santo agostinho%'
              or lower(titulo) like '%cocotiers%'         then 'Recife / Nordeste'
            when lower(titulo) like '%joão pessoa%'
              or lower(titulo) like '%joao pessoa%'
              or lower(titulo) like '%sao miguel do gostoso%'
              or lower(titulo) like '%gostoso%'
              or lower(titulo) like '%termas de jurema%'  then 'João Pessoa / RN'
            when lower(titulo) like '%florianópolis%'
              or lower(titulo) like '%florianopolis%'
              or lower(titulo) like '%santa catarina%'
              or lower(titulo) like '%bombinhas%'
              or lower(titulo) like '%camboriú%'
              or lower(titulo) like '%camboriu%'
              or lower(titulo) like '%ferrugem%'
              or lower(titulo) like '%costão%'
              or lower(titulo) like '%costao%'            then 'Florianópolis / SC'
            when lower(titulo) like '%amazon%'
              or lower(titulo) like '%manaus%'
              or lower(titulo) like '%amazônia%'
              or lower(titulo) like '%amazonia%'          then 'Amazônia'
            when lower(titulo) like '%iguaç%'
              or lower(titulo) like '%iguazu%'
              or lower(titulo) like '%iguassu%'
              or lower(titulo) like '%cataratas%'         then 'Foz do Iguaçu'
            when lower(titulo) like '%pantanal%'          then 'Pantanal'
            when lower(titulo) like '%búzios%'
              or lower(titulo) like '%buzios%'            then 'Búzios'
            when lower(titulo) like '%angra%'
              or lower(titulo) like '%ilha grande%'       then 'Angra / Ilha Grande'
            when lower(titulo) like '%natal%'
              or lower(titulo) like '%pipa%'
              or lower(titulo) like '%touros%'            then 'Natal / Pipa'
            when lower(titulo) like '%fortaleza%'
              or lower(titulo) like '%jericoacoara%'
              or lower(titulo) like '%cumbuco%'           then 'Fortaleza / CE'
            when lower(titulo) like '%lençóis%'
              or lower(titulo) like '%lencois%'
              or lower(titulo) like '%maranhenses%'       then 'Lençóis Maranhenses'
            when lower(titulo) like '%porto galinhas%'
              or lower(titulo) like '%porto de galinhas%' then 'Porto de Galinhas'
            when lower(titulo) like '%são paulo%'
              or lower(titulo) like '%sao paulo%'
              or lower(titulo) like '%san pablo%'         then 'São Paulo'
            when lower(titulo) like '%paraty%'
              or lower(titulo) like '%parati%'            then 'Paraty'
            when lower(titulo) like '%fernando de noronha%'
              or lower(titulo) like '%noronha%'           then 'Fernando de Noronha'
            when lower(titulo) like '%gramado%'
              or lower(titulo) like '%canela%'
              or lower(titulo) like '%serra gaúcha%'      then 'Gramado / Serra Gaúcha'
            when lower(titulo) like '%brasilien%'
              or lower(titulo) like '%brésil%'
              or lower(titulo) like '%bresil%'
              or lower(titulo) like '%brasil%'
              or lower(titulo) like '%brazil%'
              or lower(titulo) like '%samba%'             then 'Brasil (múltiplos destinos)'
            else                                               'Outros / Múltiplos'
        end as destino

    from obt
)

select
    destino,
    COUNT(*)                        as total_pacotes,
    COUNT(distinct operadora)       as total_operadoras,
    ROUND(AVG(preco_valor), 2)      as preco_medio,
    MIN(preco_valor)                as preco_min,
    MAX(preco_valor)                as preco_max,
    preco_moeda,
    operadora,
    titulo,
    preco_valor,
    duracao_dias,
    data_extracao_date,
    pacote_id
from com_destino
group by
    destino, preco_moeda, operadora, titulo,
    preco_valor, duracao_dias, data_extracao_date, pacote_id
