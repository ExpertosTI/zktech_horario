# HR Attendance Compliance - Módulo Odoo 18

## Descripción

Módulo de Odoo 18 para generar reportes de cumplimiento de horarios y asistencia a partir de archivos CSV/Excel.

## Características

- **Importación de datos**: Soporta archivos CSV y Excel con múltiples formatos
- **Gestión de asistencia**: Registro detallado de entrada/salida por empleado y fecha
- **Horarios personalizados**: Configure horarios específicos por empleado y día de la semana
- **Análisis automático**: Cálculo de retrasos, ausencias y salidas tempranas
- **Veredictos de cumplimiento**: Clasificación automática (Cumple, Moderado, Parcial, Severo)
- **Dashboard visual**: Vista kanban con tarjetas de empleados y estadísticas
- **Filtros avanzados**: Búsqueda por empleado, fecha, estado
- **Reportes**: Resumen ejecutivo por empleado con métricas clave

## Instalación

1. Copie el módulo `hr_attendance_compliance_v18` a la carpeta de addons de Odoo 18
2. Actualice la lista de aplicaciones en Odoo
3. Busque "HR Attendance Compliance" e instale el módulo

## Dependencias

- `base`
- `hr`
- `openpyxl` (Python): Para importar archivos Excel

Instale openpyxl con:
```bash
pip install openpyxl
```

## Uso

### 1. Importar Datos

Vaya a **Cumplimiento de Horarios > Configuración > Importar Asistencia**

Cargue un archivo CSV o Excel con uno de los siguientes formatos:

#### Formato CSV Estándar

```csv
Nombre,ID,Departamento,Fecha,HoraEntrada,DiaLibre,Asistio,MinutosRetraso,MinutosSalidaTemprana
Juan Perez,12345678,Ventas,2025-09-01,9:00 AM,Lunes,Si,15,0
```

#### Formato Reporte de Eventos de Asistencia

```
Reporte de Eventos de Asistencia
Periodo:  2025-10-01 ~ 2025-10-14
1,2,3,4,5,6,7,8,9,10,11,12,13,14
ID:  40213980390    Nombre:  Sandro    Departamento:  Ventas
09:45,20:23,10:02,10:08,,,09:21,09:18,09:45,09:34,10:16,10:38,,09:40
```

### 2. Ver Resumen de Cumplimiento

Vaya a **Cumplimiento de Horarios > Reportes > Resumen de Cumplimiento**

Vista kanban con tarjetas de empleados mostrando:
- Días asistidos vs total
- Ausencias
- Promedio de retraso
- Veredicto de cumplimiento
- Estado (Crítico/Advertencia/Cumple)

### 3. Ver Registros Detallados

Vaya a **Cumplimiento de Horarios > Reportes > Registros de Asistencia**

Lista completa de todos los registros con:
- Empleado y fecha
- Hora de entrada y salida
- Minutos de retraso
- Estado (A Tiempo/Retrasado/Ausente)

### 4. Configurar Horarios Personalizados

Vaya a **Cumplimiento de Horarios > Configuración > Horarios Personalizados**

Configure horarios específicos por empleado y día de la semana:
- Seleccione el empleado
- Elija el día de la semana
- Defina la hora oficial de entrada
- Marque si es día libre

## Lógica de Cálculo

### Retrasos

Se calcula la diferencia entre la primera entrada del día y la hora oficial de entrada.

### Veredictos

- **Incumplimiento Severo**: >50% ausencias, >60 min retraso promedio, o >120 min salida temprana
- **Incumplimiento Parcial**: >20% ausencias, >30 min retraso promedio, o >60 min salida temprana
- **Cumplimiento Moderado**: Cumplimiento aceptable con inconsistencias
- **Cumple Horario**: <10 min retraso promedio, <30 min salida temprana, <15% ausencias

### Estados

- **Crítico**: >50% ausencias o incumplimiento severo
- **Advertencia**: Incumplimiento parcial o moderado
- **Cumple**: Cumplimiento adecuado

## Estructura del Módulo

```
hr_attendance_compliance_v18/
├── __init__.py
├── __manifest__.py
├── models/
│   ├── __init__.py
│   ├── attendance_report.py
│   └── attendance_schedule.py
├── wizards/
│   ├── __init__.py
│   ├── import_attendance_wizard.py
│   └── import_attendance_wizard_views.xml
├── views/
│   ├── attendance_report_views.xml
│   ├── attendance_schedule_views.xml
│   └── menu.xml
├── security/
│   └── ir.model.access.csv
└── static/
    └── description/
        └── icon.png
```

## Modelos

### hr.attendance.report
Registro individual de asistencia por empleado y fecha.

### hr.attendance.report.summary
Resumen agregado de asistencia por empleado y periodo.

### hr.attendance.schedule
Horarios personalizados por empleado y día de la semana.

### import.attendance.wizard
Wizard para importar archivos CSV/Excel.

## Permisos

- **Usuarios**: Lectura y escritura en registros y horarios
- **Gerentes de RRHH**: Control total sobre todos los modelos

## Compatibilidad

- Diseñado para **Odoo 18**. No usa assets web personalizados ni JS, por lo que es compatible sin cambios con los cambios de assets introducidos en versiones recientes.
- Requiere `openpyxl` para importar Excel.

## Soporte

Para reportar problemas o solicitar características, contacte al desarrollador.

## Licencia

LGPL-3

## Autor

BioTApp