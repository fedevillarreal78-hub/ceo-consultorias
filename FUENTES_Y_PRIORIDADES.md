# Fuentes y prioridades del buscador de oportunidades

## Principio operativo

Las fuentes se dividen en dos categorías:

1. **Directas y estructuradas**: pueden incorporar automáticamente una oportunidad cuando la convocatoria, el país, la fecha y la afinidad están confirmados.
2. **Exploratorias**: solo descubren candidatos. Sus resultados quedan en `candidatos_revision.csv` hasta aprobación humana.

## Fuentes directas

- **UNDP Procurement Notices**: extracción estructurada del portal oficial.
- **World Bank Procurement Notice API (DS00979 / RS00909)**: consulta diaria de avisos recientes; solo servicios de consultoría en ALC.
- **ReliefWeb Consultancy Jobs**: solo categoría Consultancy y validación posterior.
- **FAO Americas / Evaluation Vacancies**: validación estricta; los casos sin fecha quedan en revisión.

## Fuentes exploratorias con Tavily

Las búsquedas usan `search_depth="basic"`, máximo 8 resultados, dominios breves y puntaje mínimo 0,65. Se organizan en:

- BID, CAF, BCIE, IICA y FONTAGRO.
- CGIAR, IFPRI, Alliance Bioversity-CIAT, CIMMYT y CATIE.
- GIZ, AECID, AFD/Expertise France y TED.
- UNGM, IFAD, WFP, ILO y Devex.

Ningún resultado de Tavily entra automáticamente al pipeline.

## Fuentes que requieren una acción adicional

- **UNGM API**: el API oficial de búsqueda requiere credenciales OAuth. El workflow ya admite el secret `UNGM_ACCESS_TOKEN`, pero la integración completa requiere registrar una aplicación en UNGM y confirmar el alcance de acceso.
- **Autenticación global de la app**: la página de revisión admite `REVIEW_PASSWORD`. Para restringir toda la aplicación, se recomienda configurar la app como privada en Streamlit Community Cloud o migrar a un proveedor con autenticación corporativa.

## Indicadores de calidad

Las métricas de cada ejecución quedan en `ultima_busqueda_stats.json`:

- registros brutos por fuente;
- incorporaciones al pipeline;
- candidatos enviados a revisión;
- duplicados;
- rechazos y motivos;
- errores por fuente;
- créditos Tavily estimados.
