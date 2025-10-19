from odoo import models, fields, api, _


class AttendanceSchedule(models.Model):
    _name = 'hr.attendance.schedule'
    _description = 'Horario de Asistencia Personalizado'
    _rec_name = 'employee_id'

    employee_id = fields.Many2one('hr.employee', string='Empleado', required=True, ondelete='cascade', index=True)
    day_of_week = fields.Selection([
        ('0', 'Lunes'),
        ('1', 'Martes'),
        ('2', 'Miércoles'),
        ('3', 'Jueves'),
        ('4', 'Viernes'),
        ('5', 'Sábado'),
        ('6', 'Domingo'),
    ], string='Día de la Semana', required=True)
    official_entry_time = fields.Char(string='Hora Oficial de Entrada', required=True, default='9:00 AM')
    day_off = fields.Boolean(string='Día Libre', default=False)
    company_id = fields.Many2one('res.company', string='Compañía', default=lambda self: self.env.company, index=True)
    
    _sql_constraints = [
        ('unique_employee_day', 'unique(employee_id, day_of_week, company_id)', 
         _('Ya existe un horario para este empleado en este día de la semana en esta compañía.'))
    ]

    @api.model
    def get_official_entry(self, employee_id, date):
        """Obtiene la hora oficial de entrada para un empleado en una fecha específica"""
        day_of_week = str(date.weekday())
        schedule = self.search([
            ('employee_id', '=', employee_id),
            ('day_of_week', '=', day_of_week),
            ('company_id', '=', self.env.company.id),
        ], limit=1)
        
        if schedule:
            return schedule.official_entry_time
        
        # Horario por defecto según departamento
        employee = self.env['hr.employee'].browse(employee_id)
        if employee.department_id:
            dept_name = employee.department_id.name.lower()
            if 'producc' in dept_name:
                return '9:45 AM'
            elif 'ventas' in dept_name:
                return '9:00 AM'
            elif 'administr' in dept_name:
                return '8:00 AM'
        
        return '9:00 AM'