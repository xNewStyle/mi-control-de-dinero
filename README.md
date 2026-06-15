# Mi Control de Dinero - PWA

Esta es una app instalable para celular que registra ingresos, gastos y egresos.

## Funciona sin internet

La app guarda los datos en el almacenamiento local del celular.
El service worker guarda la app en caché para que pueda abrir aunque no tengas conexión.

## Cómo probar

1. Sube estos archivos a un hosting con HTTPS, por ejemplo GitHub Pages, Netlify, Vercel o tu propio dominio.
2. Abre la URL desde Chrome en Android o Safari en iPhone.
3. En Android puede aparecer el botón "Instalar app".
4. En iPhone usa Compartir > Añadir a pantalla de inicio.

## Importante

No borres datos del navegador porque se pueden perder los movimientos.
Para una versión más profesional conviene agregar sincronización con Google Sheets, Firebase o una base de datos.
