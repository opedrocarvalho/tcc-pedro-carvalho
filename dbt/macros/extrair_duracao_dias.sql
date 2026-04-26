{% macro extrair_duracao_dias(campo) %}
    CAST(
        NULLIF(
            REGEXP_REPLACE({{ campo }}, '^[^\d]*(\d+).*$', '\1'),
            {{ campo }} 
        ) AS INTEGER
    )
{% endmacro %}
