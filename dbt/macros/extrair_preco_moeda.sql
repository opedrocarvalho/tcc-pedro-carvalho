{% macro extrair_preco_moeda(campo) %}
    CASE
        WHEN {{ campo }} ILIKE '%£%'   THEN 'GBP'
        WHEN {{ campo }} ILIKE '%USD%' THEN 'USD'
        WHEN {{ campo }} ILIKE '%€%'   THEN 'EUR'
        ELSE NULL
    END
{% endmacro %}
