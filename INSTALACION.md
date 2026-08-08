# Instalación de mejoras del buscador Grupo CEO

## Contenido

- `opportunity_engine.py`: validación, geografía, fechas, puntuación y deduplicación.
- `buscar_consultorias.py`: buscador v2 con UNDP, Banco Mundial, ReliefWeb, FAO y Tavily como fuente exploratoria.
- `sanear_base.py`: auditoría no destructiva de la base histórica.
- `pages/6_Revision_de_candidatos.py`: bandeja Streamlit de revisión humana.
- `.github/workflows/actualizar_csv.yml`: workflow con pruebas, concurrencia, auditoría y reintentos.
- `tests/test_opportunity_engine.py`: pruebas de regresión.
- `candidatos_revision.csv`: archivo inicial de staging.
- `FUENTES_Y_PRIORIDADES.md`: documentación de fuentes y decisiones.

## Instalación automática

Desde el directorio raíz del repositorio:

```bash
unzip mejoras_ceo_buscador_v2_corregido.zip -d /tmp/mejoras_ceo
bash /tmp/mejoras_ceo/instalar_mejoras.sh
```

El instalador crea una copia de seguridad en `.backup_buscador_v2_<fecha>` antes de reemplazar archivos.

## Secrets recomendados

En Streamlit Community Cloud:

```toml
GITHUB_TOKEN = "..."
TAVILY_API_KEY = "..."
REVIEW_PASSWORD = "una-contraseña-segura"
```

En GitHub Actions:

- `TAVILY_API_KEY` ya existente.
- `UNGM_ACCESS_TOKEN` será opcional hasta completar el registro de una aplicación en UNGM.

## Validación local

```bash
python -m unittest discover -s tests -v
python sanear_base.py
python buscar_consultorias.py
streamlit run app.py
```

La auditoría inicial es no destructiva. No ejecute `python sanear_base.py --apply` hasta revisar `auditoria_oportunidades.csv`.
