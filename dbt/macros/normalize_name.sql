{% macro normalize_name(name_column) %}
  LOWER(
    TRIM(
      REGEXP_REPLACE(
        REGEXP_REPLACE(
          REGEXP_REPLACE(
            REGEXP_REPLACE(
              REGEXP_REPLACE(
                REGEXP_REPLACE(
                  REGEXP_REPLACE(
                    REGEXP_REPLACE(
                      REGEXP_REPLACE(
                        NORMALIZE({{ name_column }}, NFD),
                        r'\pM', ''
                      ),
                      r'[øØ]', 'o'
                    ),
                    r'[æÆ]', 'ae'
                  ),
                  r'[œŒ]', 'oe'
                ),
                r'[ß]', 'ss'
              ),
              r'[đĐðÐ]', 'd'
            ),
            r'[łŁ]', 'l'
          ),
          r'[^a-zA-Z0-9\s]', ' '
        ),
        r'\s+', ' '
      )
    )
  )
{% endmacro %}
