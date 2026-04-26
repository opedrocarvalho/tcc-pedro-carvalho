with datas as (
    select distinct
        cast(data_extracao as date) as data_extracao_date
    from {{ ref('obt_pacotes') }}
    where data_extracao is not null
)

select
    data_extracao_date                                          as data_key,

    extract(year  from data_extracao_date)::int                as ano,
    extract(month from data_extracao_date)::int                as mes,
    extract(day   from data_extracao_date)::int                as dia,
    extract(week  from data_extracao_date)::int                as semana_ano,
    extract(quarter from data_extracao_date)::int              as trimestre,
    extract(dow   from data_extracao_date)::int                as dia_semana_num,

    to_char(data_extracao_date, 'YYYY-MM')                     as ano_mes,
    to_char(data_extracao_date, 'TMMonth')                     as mes_nome,

    case extract(dow from data_extracao_date)::int
        when 0 then 'Domingo'
        when 1 then 'Segunda'
        when 2 then 'Terça'
        when 3 then 'Quarta'
        when 4 then 'Quinta'
        when 5 then 'Sexta'
        when 6 then 'Sábado'
    end                                                        as dia_semana_nome,

    case when extract(dow from data_extracao_date) in (0, 6)
        then true else false
    end                                                        as is_fim_de_semana

from datas
order by data_extracao_date
