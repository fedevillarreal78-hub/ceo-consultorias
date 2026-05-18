# Oportunidades de Consultoría · Grupo CEO

## Descripción

App interna de Grupo CEO para monitoreo, priorización y seguimiento de convocatorias de consultoría en América Latina y el Caribe. Permite al equipo identificar oportunidades alineadas al perfil individual o empresarial, filtrarlas por múltiples criterios y exportarlas para presentaciones y toma de decisiones.

---

## Estructura del repositorio

| Archivo | Descripción |
|---|---|
| `app.py` | Aplicación principal Streamlit |
| `buscar_consultorias.py` | Script de búsqueda y actualización del CSV |
| `oportunidades_consultoria.csv` | Base de datos de oportunidades (actualización automática) |
| `requirements.txt` | Dependencias Python |
| `logo_ceo.png` | Logo institucional |
| `.github/workflows/actualizar_csv.yml` | Automatización de actualización (lunes y jueves 8 AM) |

---

## Estructura del CSV

| Columna | Tipo | Valores posibles | Descripción |
|---|---|---|---|
| Título | texto | libre | Nombre de la convocatoria o consultoría |
| Organización | texto | libre | Entidad convocante (UNDP, FAO, BID, etc.) |
| Tipo | texto | libre | Tipo de consultoría (individual, servicios, etc.) |
| Región | texto | ALC, Global, América Central, etc. | Cobertura geográfica amplia |
| País | texto | Guatemala, Colombia, México, Regional, Global, — | País específico de la oportunidad |
| Fecha límite | texto | `YYYY-MM-DD` o `DD-Mmm-YYYY` | Fecha de cierre de la convocatoria |
| Enlace | texto | URL completa | Link directo a la convocatoria |
| Afinidad | texto | `Individual`, `Empresarial`, `Ambos` | A quién aplica dentro del equipo CEO |
| Prioridad | texto | `Alta`, `Media`, `Baja` | Nivel de prioridad estratégica |
| Estado | texto | `Identificada`, `En análisis`, `Postulada`, `Ganada`, `Descartada` | Estado actual de la postulación |
| Monto estimado (USD) | numérico | entero positivo o vacío | Valor estimado de la consultoría en USD |
| Consultor | texto | nombre del consultor o `—` | Consultor responsable asignado |

---

## Actualización de datos

### Automática

GitHub Actions ejecuta `buscar_consultorias.py` los **lunes y jueves a las 8:00 AM hora Guatemala (UTC-6)**. Si detecta cambios en el CSV, realiza commit y push automático al repositorio. Streamlit Cloud redespliega la app al recibir el push.

Requiere el secret `TAVILY_API_KEY` configurado en **GitHub → Settings → Secrets and variables → Actions**.

### Manual (local)

```bash
/Users/fvillareal/actualizar_y_publicar.sh
```

Este script ejecuta el scraper, actualiza el CSV y sube los cambios a GitHub.

---

## Filtros disponibles en la app

Accesibles desde el panel lateral (sidebar):

- **Prioridad** — Alta / Media / Baja
- **Afinidad** — Individual / Empresarial / Ambos
- **Estado** — Identificada / En análisis / Postulada / Ganada / Descartada
- **Consultor responsable**
- **Región**
- **País**
- **Búsqueda por texto libre** — título u organización

---

## Métricas del header

La app muestra 5 métricas en tiempo real según los filtros activos:

1. **Total filtradas** — cantidad total de oportunidades visibles
2. **Prioridad Alta** — oportunidades marcadas como Alta prioridad
3. **Para Individual** — oportunidades aplicables al perfil consultor individual
4. **Para CEO** — oportunidades aplicables al perfil empresarial (Grupo CEO)
5. **Pipeline USD** — valor total estimado de las oportunidades filtradas

---

## Despliegue

- **URL de producción:** https://ceo-consultorias.streamlit.app/
- **Plataforma:** Streamlit Community Cloud
- **Rama de despliegue:** `main`

Cualquier push a `main` actualiza automáticamente la app en producción.

---

## Requisitos para desarrollo local

1. Clonar el repositorio:

```bash
git clone git@github.com:fedevillarreal78-hub/ceo-consultorias.git
cd ceo-consultorias
```

2. Instalar dependencias:

```bash
pip install -r requirements.txt
```

3. Configurar la variable de entorno:

```bash
export TAVILY_API_KEY=tu_clave
```

4. Correr la app:

```bash
streamlit run app.py
```

---

## Equipo

Grupo CEO · [grupo-ceo.com](https://grupo-ceo.com) · 2026
