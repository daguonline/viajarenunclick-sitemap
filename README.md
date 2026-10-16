# 🗺️ Generador de Sitemap XML & Auditoría de Seguridad SEO
### Sitio Web: [viajarenunclick.com.ar](https://viajarenunclick.com.ar)

Proyecto automatizado para rastreo web inteligente, normalización canónica, generación de `sitemap.xml` para **Google Search Console**, y directrices avanzadas de seguridad contra hackeo y ciberataques.

---

## 📋 Resumen del Proyecto

Este repositorio contiene:
1. **`crawler.py`**: Rastreador web seguro y respetuoso (*polite crawler*) que recorre todas las rutas de `viajarenunclick.com.ar`, extrae las etiquetas canónicas oficiales (`<link rel="canonical">`), calcula prioridades SEO y genera un sitemap XML estricto.
2. **`sitemap.xml`**: Sitemap generado en formato XML estándar (Sitemaps.org 0.9), optimizado para indexación rápida en Googlebot.
3. **`robots.txt`**: Archivo de directivas para motores de búsqueda, bloqueando rutas administrativas y enlazando el sitemap.
4. **`validate_sitemap.py`**: Validador de esquemas XML, protocolos HTTPS, ausencia de duplicados y filtros de seguridad.
5. **`automation/sitemap-workflow.yml`**: Plantilla de automatización con GitHub Actions para actualizar el sitemap semanalmente.

---

## 🛡️ Auditoría de Seguridad & Prevención de Hackeo

> [!WARNING]
> ### 1. Hallazgo Crítico de DNS: `www.viajarenunclick.com.ar` no existe (NXDOMAIN)
> Durante la auditoría DNS descubrimos que el subdominio `www.viajarenunclick.com.ar` **no tiene registro DNS configurado** en Cloudflare:
> - `https://viajarenunclick.com.ar` -> **FUNCIONA** (Cloudflare IP: 104.21.43.224 / 172.67.186.184)
> - `https://www.viajarenunclick.com.ar` -> **ERROR (NXDOMAIN)**
>
> **Riesgo de Seguridad:** Si no reclamas y configuras el registro `www`, un tercero podría explotar subdominios huérfanos (*Subdomain Takeover*) o los usuarios que escriban `www` verán la página rota.
>
> **Solución Inmediata en Cloudflare:**
> 1. Ingresá a tu panel de **Cloudflare** > Dominio `viajarenunclick.com.ar` > **DNS** > **Records**.
> 2. Agregá un registro:
>    - **Tipo:** `CNAME`
>    - **Nombre:** `www`
>    - **Objetivo / Target:** `viajarenunclick.com.ar` (o `@`)
>    - **Proxy status:** `Proxied` (Nube naranja activada).
> 3. En **Rules** > **Redirect Rules**, creá una regla para redirigir `www.viajarenunclick.com.ar/*` a `https://viajarenunclick.com.ar/$1` con código HTTP 301.

---

### 2. Medidas de Seguridad Implementadas contra Hackeo

| Vector de Ataque | Medida Implementada |
| :--- | :--- |
| **Fuga de Secretos en GitHub** | Archivo `.gitignore` blindado que impide subir credenciales, tokens, variables `.env`, cookies o sesiones. |
| **Ataque DoS / Saturación de Servidor** | El crawler utiliza *crawl-delay* inteligente (100-150ms) y headers identificados para no sobrecargar el servidor ni disparar bloqueos WAF. |
| **Inyección XML / XXE** | Todas las URLs generadas son sanitizadas y escapadas con entidades XML estrictas (`&amp;`, `&lt;`, etc.). |
| **Rutas Administrativas Expuestas** | `robots.txt` prohíbe el rastreo de `/admin`, `/login.xhtml`, `/resources-internal`, `/voucher/` y `/widgets/`. |
| **Suplantación Man-in-the-Middle** | El 100% de los enlaces en el sitemap fuerzan protocolo seguro `https://`. |

---

## 🔍 Cómo Enviar a Google Search Console

1. **Ingresá a Google Search Console:**  
   [https://search.google.com/search-console](https://search.google.com/search-console)
2. **Seleccioná tu propiedad:**  
   Recomendamos usar la propiedad de Dominio `viajarenunclick.com.ar` (o Prefijo de URL `https://viajarenunclick.com.ar/`).
3. **Ir a la sección Sitemaps:**  
   En el menú lateral izquierdo, haz clic en **Indexación** > **Sitemaps**.
4. **Enviar nuevo sitemap:**  
   En el campo "Añadir un sitemap nuevo", escribe:
   ```text
   sitemap.xml
   ```
   (La URL completa quedará: `https://viajarenunclick.com.ar/sitemap.xml`).
5. Haz clic en **Enviar**. Google Search Console confirmará el estado en verde: *"Correcto"*.

---

## 💻 Uso Local del Proyecto

### Requisitos
- Python 3.8 o superior
- Librería `beautifulsoup4`

```bash
# Instalar dependencias
pip install beautifulsoup4

# Ejecutar rastreo y generar sitemap.xml
python crawler.py

# Validar integridad y seguridad del sitemap
python validate_sitemap.py sitemap.xml
```

---

© 2026 Viajar en un Click. Desarrollado con los más altos estándares de SEO y ciberseguridad.
