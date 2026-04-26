select
    operadora_key                                       as operadora_key,
    nome                                                as nome_display,
    pais_origem,
    idioma,
    moeda_padrao,

    case idioma
        when 'fr' then 'Francês'
        when 'de' then 'Alemão'
        when 'en' then 'Inglês'
        when 'pt' then 'Português'
        when 'es' then 'Espanhol'
        else idioma
    end as idioma_nome,

    case moeda_padrao
        when 'EUR' then 'Euro'
        when 'GBP' then 'Libra Esterlina'
        when 'USD' then 'Dólar Americano'
        when 'CLP' then 'Peso Chileno'
        else moeda_padrao
    end as moeda_nome,

    case pais_origem
        when 'França'        then 'Europa'
        when 'Alemanha'      then 'Europa'
        when 'Portugal'      then 'Europa'
        when 'Reino Unido'   then 'Europa'
        when 'Chile'         then 'América do Sul'
        when 'Uruguai'       then 'América do Sul'
        else 'Outro'
    end as regiao_origem

from {{ ref('operadoras') }}
