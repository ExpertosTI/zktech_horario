from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
from datetime import datetime, timedelta
import re


class AttendanceReport(models.Model):
    _name = 'hr.attendance.report'
    _description = 'Reporte de Asistencia'
    _order = 'date desc, employee_id'

    employee_id = fields.Many2one('hr.employee', string='Empleado', required=True, ondelete='cascade', index=True)
    date = fields.Date(string='Fecha', required=True, index=True)
    attended = fields.Boolean(string='Asistió', default=False)
    first_entry = fields.Char(string='Primera Entrada')
    last_exit = fields.Char(string='Última Salida')
    total_records = fields.Integer(string='Total de Registros', default=0)
    official_entry_time = fields.Char(string='Hora Oficial de Entrada')
    late_minutes = fields.Integer(string='Minutos de Retraso', compute='_compute_late_minutes', store=True)
    early_exit_minutes = fields.Integer(string='Minutos Salida Temprana', default=0)
    company_id = fields.Many2one('res.company', string='Compañía', default=lambda self: self.env.company, index=True)
    
    # Campos calculados para análisis
    status = fields.Selection([
        ('on_time', 'A Tiempo'),
        ('late', 'Retrasado'),
        ('absent', 'Ausente'),
    ], string='Estado', compute='_compute_status', store=True)
    
    day_of_week = fields.Char(string='Día de la Semana', compute='_compute_day_of_week', store=True)
    
    _sql_constraints = [
        ('unique_employee_date', 'unique(employee_id, date, company_id)', 
         _('Ya existe un registro para este empleado en esta fecha y compañía.'))
    ]

    @api.depends('date')
    def _compute_day_of_week(self):
        days = ['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado', 'Domingo']
        for record in self:
            if record.date:
                record.day_of_week = days[record.date.weekday()]
            else:
                record.day_of_week = ''

    @api.depends('attended', 'first_entry', 'official_entry_time')
    def _compute_late_minutes(self):
        for record in self:
            if not record.attended or not record.first_entry or not record.official_entry_time:
                record.late_minutes = 0
                continue
            
            try:
                official_24h = self._convert_to_24h(record.official_entry_time)
                actual_time = record.first_entry
                
                official_parts = official_24h.split(':')
                actual_parts = actual_time.split(':')
                
                official_minutes = int(official_parts[0]) * 60 + int(official_parts[1])
                actual_minutes = int(actual_parts[0]) * 60 + int(actual_parts[1])
                
                delay = actual_minutes - official_minutes
                record.late_minutes = delay if delay > 0 else 0
            except:
                record.late_minutes = 0

    @api.depends('attended', 'late_minutes')
    def _compute_status(self):
        for record in self:
            if not record.attended:
                record.status = 'absent'
            elif record.late_minutes > 0:
                record.status = 'late'
            else:
                record.status = 'on_time'

    def _convert_to_24h(self, time_str):
        """Convierte hora AM/PM a formato 24h"""
        match = re.match(r'(\d{1,2}):(\d{2})\s*(AM|PM)', time_str, re.IGNORECASE)
        if not match:
            return time_str
        
        hours, minutes, period = match.groups()
        hours = int(hours)
        
        if period.upper() == 'PM' and hours != 12:
            hours += 12
        elif period.upper() == 'AM' and hours == 12:
            hours = 0
        
        return f"{hours:02d}:{minutes}"

    @api.model
    def get_employee_summary(self, employee_id, date_from=None, date_to=None):
        """Obtiene el resumen de asistencia de un empleado"""
        domain = [('employee_id', '=', employee_id), ('company_id', '=', self.env.company.id)]
        if date_from:
            domain.append(('date', '>=', date_from))
        if date_to:
            domain.append(('date', '<=', date_to))
        
        records = self.search(domain)
        
        total_days = len(records)
        attended_days = len(records.filtered(lambda r: r.attended))
        absences = total_days - attended_days
        total_late_minutes = sum(records.mapped('late_minutes'))
        total_early_minutes = sum(records.mapped('early_exit_minutes'))
        
        return {
            'total_days': total_days,
            'attended_days': attended_days,
            'absences': absences,
            'total_late_minutes': total_late_minutes,
            'total_early_minutes': total_early_minutes,
            'avg_late_minutes': total_late_minutes / attended_days if attended_days > 0 else 0,
            'avg_early_minutes': total_early_minutes / attended_days if attended_days > 0 else 0,
        }

    @api.model
    def calculate_verdict(self, summary):
        """Calcula el veredicto de cumplimiento"""
        if not summary['total_days']:
            return {'type': 'ok', 'text': 'Sin Datos'}
        
        absence_rate = summary['absences'] / summary['total_days']
        avg_late = summary['avg_late_minutes']
        avg_early = summary['avg_early_minutes']
        
        if absence_rate > 0.5 or avg_late > 60 or avg_early > 120:
            return {'type': 'severe', 'text': 'Incumplimiento Severo'}
        elif absence_rate > 0.2 or avg_late > 30 or avg_early > 60:
            return {'type': 'partial', 'text': 'Incumplimiento Parcial'}
        elif avg_late < 10 and avg_early < 30 and absence_rate < 0.15:
            return {'type': 'ok', 'text': 'Cumple Horario'}
        else:
            return {'type': 'moderate', 'text': 'Cumplimiento Moderado'}

    # Abrir edición de horario desde registro diario
    def action_open_edit_schedule(self):
        self.ensure_one()
        action = self.env.ref('hr_attendance_compliance_v18.action_attendance_schedule').read()[0]
        action['domain'] = [
            ('employee_id', '=', self.employee_id.id),
            ('company_id', '=', self.company_id.id),
        ]
        action['context'] = {'default_employee_id': self.employee_id.id}
        action['target'] = 'new'
        action['view_mode'] = 'list,form'
        action['views'] = [
            (self.env.ref('hr_attendance_compliance_v18.view_attendance_schedule_tree').id, 'list'),
            (self.env.ref('hr_attendance_compliance_v18.view_attendance_schedule_form').id, 'form'),
        ]
        return action


class AttendanceReportSummary(models.Model):
    _name = 'hr.attendance.report.summary'
    _description = 'Resumen de Reporte de Asistencia'
    _rec_name = 'employee_id'

    employee_id = fields.Many2one('hr.employee', string='Empleado', required=True, ondelete='cascade', index=True)
    company_id = fields.Many2one('res.company', string='Compañía', default=lambda self: self.env.company, index=True)
    date_from = fields.Date(string='Fecha Desde', required=True, index=True)
    date_to = fields.Date(string='Fecha Hasta', required=True, index=True)
    total_days = fields.Integer(string='Total de Días')
    attended_days = fields.Integer(string='Días Asistidos')
    absences = fields.Integer(string='Ausencias')
    total_late_minutes = fields.Integer(string='Total Minutos Retraso')
    total_early_minutes = fields.Integer(string='Total Minutos Salida Temprana')
    avg_late_minutes = fields.Float(string='Promedio Retraso (min)')
    avg_early_minutes = fields.Float(string='Promedio Salida Temprana (min)')
    verdict_type = fields.Selection([
        ('ok', 'Cumple Horario'),
        ('moderate', 'Cumplimiento Moderado'),
        ('partial', 'Incumplimiento Parcial'),
        ('severe', 'Incumplimiento Severo'),
    ], string='Veredicto')
    verdict_text = fields.Char(string='Texto del Veredicto')
    status = fields.Selection([
        ('ok', 'Cumple'),
        ('warning', 'Advertencia'),
        ('critical', 'Crítico'),
    ], string='Estado', compute='_compute_status', store=True)

    @api.depends('verdict_type', 'absences', 'total_days')
    def _compute_status(self):
        for record in self:
            if record.total_days > 0 and record.absences > record.total_days * 0.5:
                record.status = 'critical'
            elif record.verdict_type == 'severe':
                record.status = 'critical'
            elif record.verdict_type in ['partial', 'moderate']:
                record.status = 'warning'
            else:
                record.status = 'ok'

    @api.model
    def generate_summary(self, employee_id, date_from, date_to):
        """Genera o actualiza el resumen para un empleado"""
        report_model = self.env['hr.attendance.report']
        summary_data = report_model.get_employee_summary(employee_id, date_from, date_to)
        verdict = report_model.calculate_verdict(summary_data)
        
        existing = self.search([
            ('employee_id', '=', employee_id),
            ('date_from', '=', date_from),
            ('date_to', '=', date_to),
            ('company_id', '=', self.env.company.id),
        ], limit=1)
        
        values = {
            'employee_id': employee_id,
            'date_from': date_from,
            'date_to': date_to,
            'company_id': self.env.company.id,
            'total_days': summary_data['total_days'],
            'attended_days': summary_data['attended_days'],
            'absences': summary_data['absences'],
            'total_late_minutes': summary_data['total_late_minutes'],
            'total_early_minutes': summary_data['total_early_minutes'],
            'avg_late_minutes': summary_data['avg_late_minutes'],
            'avg_early_minutes': summary_data['avg_early_minutes'],
            'verdict_type': verdict['type'],
            'verdict_text': verdict['text'],
        }
        
        if existing:
            existing.write(values)
            return existing
        else:
            return self.create(values)

    # Acción para abrir detalle diario del empleado en el rango
    def action_open_daily_detail(self):
        self.ensure_one()
        action = self.env.ref('hr_attendance_compliance_v18.action_attendance_report').read()[0]
        action['domain'] = [
            ('employee_id', '=', self.employee_id.id),
            ('date', '>=', self.date_from),
            ('date', '<=', self.date_to),
            ('company_id', '=', self.company_id.id),
        ]
        action['target'] = 'new'
        action['view_mode'] = 'kanban,list,form'
        action['views'] = [
            (self.env.ref('hr_attendance_compliance_v18.view_attendance_report_kanban').id, 'kanban'),
            (self.env.ref('hr_attendance_compliance_v18.view_attendance_report_tree').id, 'list'),
            (self.env.ref('hr_attendance_compliance_v18.view_attendance_report_form').id, 'form'),
        ]
        action['context'] = {'search_default_group_date': 1}
        return action

    # Abrir edición de horario desde el resumen
    def action_open_edit_schedule(self):
        self.ensure_one()
        action = self.env.ref('hr_attendance_compliance_v18.action_attendance_schedule').read()[0]
        action['domain'] = [
            ('employee_id', '=', self.employee_id.id),
            ('company_id', '=', self.company_id.id),
        ]
        action['context'] = {'default_employee_id': self.employee_id.id}
        action['target'] = 'new'
        action['view_mode'] = 'list,form'
        action['views'] = [
            (self.env.ref('hr_attendance_compliance_v18.view_attendance_schedule_tree').id, 'list'),
            (self.env.ref('hr_attendance_compliance_v18.view_attendance_schedule_form').id, 'form'),
        ]
        return action

    @api.constrains('date_from', 'date_to')
    def _check_date_range(self):
        for rec in self:
            if rec.date_from and rec.date_to and rec.date_to < rec.date_from:
                raise ValidationError(_('La fecha hasta debe ser mayor o igual que la fecha desde.'))
    _sql_constraints = [
        ('unique_summary_range', 'unique(employee_id, date_from, date_to, company_id)',
         _('Ya existe un resumen para este empleado y rango en esta compañía.'))
    ]