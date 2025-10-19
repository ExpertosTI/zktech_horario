{
    'name': 'Cumplimiento de Asistencia y Horarios',
    'version': '18.0.1.0.7',
    'category': 'Human Resources',
    'summary': 'Reporte de Cumplimiento de Horarios y Asistencia',
    'description': """
        Módulo para generar reportes de cumplimiento de horarios a partir de archivos CSV/Excel.
        
        Características:
        - Importación de archivos CSV y Excel
        - Procesamiento automático de datos de asistencia
        - Análisis de cumplimiento por empleado
        - Horarios personalizados por empleado y día
        - Cálculo de retrasos, ausencias y salidas tempranas
        - Veredictos automáticos de cumplimiento
        - Dashboard con estadísticas
        - Exportación de reportes
    """,
    'author': 'Adderly Marte (RENACE.TECH)',
    'website': 'https://renace.tech',
    'depends': ['base', 'hr'],
    'data': [
        'security/ir.model.access.csv',
        'security/attendance_rules.xml',
        'wizards/import_attendance_wizard_views.xml',
        'views/attendance_report_views.xml',
        'views/attendance_schedule_views.xml',
        'views/menu.xml',
    ],
    'images': ['static/description/icon.png'],
    'installable': True,
    'application': True,
    'auto_install': False,
    'license': 'LGPL-3',
    'assets': {
        'web.assets_backend': [
            'hr_attendance_compliance_v18/static/src/css/attendance_dashboard.css',
        ],
    },
    'external_dependencies': {'python': ['openpyxl']},
}