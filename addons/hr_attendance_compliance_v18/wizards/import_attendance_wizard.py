from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
import base64
import csv
import io
import re
from datetime import datetime, timedelta


class ImportAttendanceWizard(models.TransientModel):
    _name = 'import.attendance.wizard'
    _description = 'Asistente de Importación de Asistencia'

    file_data = fields.Binary(string='Archivo CSV/Excel', required=True)
    file_name = fields.Char(string='Nombre del Archivo')
    file_type = fields.Selection([
        ('csv', 'CSV'),
        ('excel', 'Excel'),
    ], string='Tipo de Archivo', compute='_compute_file_type')
    # Parámetros de conexión al servidor (para pruebas de conectividad)
    @api.model
    def _get_default_zk_ip(self):
        ip = self.env['ir.config_parameter'].sudo().get_param(
            'hr_attendance_compliance_v18.zk_ip', default='86.38.217.170'
        )
        return ip or '86.38.217.170'

    @api.model
    def _get_default_zk_port(self):
        val = self.env['ir.config_parameter'].sudo().get_param(
            'hr_attendance_compliance_v18.zk_port', default='9095'
        )
        try:
            return int(val)
        except Exception:
            return 9095

    zk_ip = fields.Char(string='IP/Host del servidor', default=_get_default_zk_ip)
    zk_port = fields.Integer(string='Puerto', default=_get_default_zk_port)
    
    @api.depends('file_name')
    def _compute_file_type(self):
        for record in self:
            if record.file_name:
                if record.file_name.lower().endswith(('.xlsx', '.xls')):
                    record.file_type = 'excel'
                else:
                    record.file_type = 'csv'
            else:
                record.file_type = 'csv'

    def action_import(self):
        """Procesa el archivo y crea los registros de asistencia"""
        self.ensure_one()
        
        if not self.file_data:
            raise UserError(_('Debe cargar un archivo.'))
        
        try:
            if self.file_type == 'excel':
                data = self._process_excel_file()
            else:
                data = self._process_csv_file()
            
            if not data:
                raise UserError(_('El archivo no contiene datos válidos.'))
            
            # Crear registros de asistencia
            created_records = self._create_attendance_records(data)
            
            # Generar resúmenes
            self._generate_summaries(data)
            
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Importación Exitosa'),
                    'message': _('Se importaron %s registros de asistencia.') % len(created_records),
                    'type': 'success',
                    'sticky': False,
                }
            }
        except Exception as e:
            raise UserError(_('Error al procesar el archivo: %s') % str(e))

    def action_check_connection(self):
        """Verifica conectividad al endpoint del servidor (por ejemplo /zk/ping)"""
        self.ensure_one()
        ip = (self.zk_ip or 'localhost').strip()
        port = int(self.zk_port or 9095)
        ping_url = f"http://{ip}:{port}/zk/ping"
        version_url = f"http://{ip}:{port}/web/webclient/version_info"

        # Intento 1: /zk/ping
        try:
            try:
                import requests
            except ImportError:
                requests = None
            if requests:
                resp = requests.get(ping_url, timeout=3)
                if resp.status_code == 200:
                    msg = _('Conexión OK al endpoint: %s') % ping_url
                    return {
                        'type': 'ir.actions.client',
                        'tag': 'display_notification',
                        'params': {
                            'title': _('Conectado'),
                            'message': msg,
                            'type': 'success',
                            'sticky': False,
                        }
                    }
                else:
                    raise UserError(_('HTTP %s en %s') % (resp.status_code, ping_url))
            else:
                # Fallback a urllib si requests no está disponible
                import urllib.request
                with urllib.request.urlopen(ping_url, timeout=3) as resp:
                    if resp.status == 200:
                        msg = _('Conexión OK al endpoint: %s') % ping_url
                        return {
                            'type': 'ir.actions.client',
                            'tag': 'display_notification',
                            'params': {
                                'title': _('Conectado'),
                                'message': msg,
                                'type': 'success',
                                'sticky': False,
                            }
                        }
        except Exception:
            # Intento 2: versión de Odoo
            try:
                if requests:
                    resp2 = requests.get(version_url, timeout=3)
                    if resp2.status_code == 200:
                        return {
                            'type': 'ir.actions.client',
                            'tag': 'display_notification',
                            'params': {
                                'title': _('Conectado (versión)'),
                                'message': _('El servidor respondió: %s') % version_url,
                                'type': 'success',
                                'sticky': False,
                            }
                        }
                else:
                    import urllib.request
                    with urllib.request.urlopen(version_url, timeout=3) as resp2:
                        if resp2.status == 200:
                            return {
                                'type': 'ir.actions.client',
                                'tag': 'display_notification',
                                'params': {
                                    'title': _('Conectado (versión)'),
                                    'message': _('El servidor respondió: %s') % version_url,
                                    'type': 'success',
                                    'sticky': False,
                                }
                            }
            except Exception as e2:
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'title': _('Sin conexión'),
                        'message': _('No se pudo conectar a %s ni %s. Detalle: %s') % (ping_url, version_url, str(e2)),
                        'type': 'danger',
                        'sticky': False,
                    }
                }
    
    def _decode_bytes(self, data_bytes):
        """Decodifica bytes a texto probando encodings comunes (UTF-8, latin-1, cp1252)."""
        for enc in ('utf-8', 'utf-8-sig', 'latin-1', 'cp1252'):
            try:
                return data_bytes.decode(enc)
            except UnicodeDecodeError:
                continue
        # Último recurso: ignorar caracteres inválidos
        return data_bytes.decode('utf-8', errors='ignore')

    def _process_csv_file(self):
        """Procesa un archivo CSV con tolerancia de encoding y delimitador."""
        data_bytes = base64.b64decode(self.file_data)
        file_content = self._decode_bytes(data_bytes)
        lines = file_content.splitlines()
        if not lines:
            return []
        header = lines[0] if lines else ''
        if 'Reporte de Eventos de Asistencia' in header:
            return self._parse_attendance_report(lines)
        else:
            return self._parse_standard_csv(lines)

    def _parse_standard_csv(self, lines):
        """Parsea CSV estándar tolerando ',' o ';' como delimitador."""
        if len(lines) < 2:
            return []
        header_line = lines[0]
        delimiter = ';' if header_line.count(';') > header_line.count(',') else ','
        reader = csv.DictReader(io.StringIO('\n'.join(lines)), delimiter=delimiter)
        data = []
        for row in reader:
            normalized_row = {}
            for key, value in row.items():
                key_lower = (key or '').lower().strip()
                if 'nombre' in key_lower:
                    normalized_row['nombre'] = value
                elif 'id' in key_lower or 'cedula' in key_lower:
                    normalized_row['id'] = value
                elif 'departamento' in key_lower or 'area' in key_lower:
                    normalized_row['departamento'] = value
                elif 'fecha' in key_lower:
                    normalized_row['fecha'] = value
                elif 'asist' in key_lower:
                    normalized_row['asistio'] = value
                elif 'entrada' in key_lower and 'hora' in key_lower:
                    normalized_row['hora_entrada'] = value
                elif 'retraso' in key_lower:
                    normalized_row['minutos_retraso'] = value
                elif 'salida' in key_lower and 'temprana' in key_lower:
                    normalized_row['minutos_salida_temprana'] = value
                elif 'primera' in key_lower and 'entrada' in key_lower:
                    normalized_row['primera_entrada'] = value
                elif 'ultima' in key_lower and 'salida' in key_lower:
                    normalized_row['ultima_salida'] = value
            if (normalized_row.get('nombre') and normalized_row.get('fecha')):
                data.append(normalized_row)
        return data

    def _process_excel_file(self):
        """Procesa un archivo Excel"""
        try:
            import openpyxl
            file_content = base64.b64decode(self.file_data)
            workbook = openpyxl.load_workbook(io.BytesIO(file_content))
            
            all_data = []
            for sheet in workbook.worksheets:
                # Convertir hoja a CSV
                csv_data = []
                for row in sheet.iter_rows(values_only=True):
                    csv_data.append(','.join([str(cell) if cell is not None else '' for cell in row]))
                
                if csv_data and 'Reporte de Eventos de Asistencia' in csv_data[0]:
                    all_data.extend(self._parse_attendance_report(csv_data))
                elif csv_data:
                    all_data.extend(self._parse_standard_csv(csv_data))
            
            return all_data
        except ImportError:
            raise UserError(_('La librería openpyxl no está instalada. Instálela con: pip install openpyxl'))


    def _parse_attendance_report(self, lines):
        """Parsea reporte de eventos de asistencia"""
        data = []
        period_start = None
        period_end = None
        
        # Extraer periodo
        for line in lines:
            if 'Periodo:' in line:
                match = re.search(r'(\d{4}-\d{2}-\d{2})\s*~\s*(\d{4}-\d{2}-\d{2})', line)
                if match:
                    period_start = match.group(1)
                    period_end = match.group(2)
                    break
        
        if not period_start or not period_end:
            # Usar fechas por defecto
            period_end = datetime.now().date()
            period_start = period_end - timedelta(days=14)
            period_start = period_start.strftime('%Y-%m-%d')
            period_end = period_end.strftime('%Y-%m-%d')
        
        dates = self._generate_date_range(period_start, period_end)
        
        # Procesar empleados
        i = 0
        while i < len(lines):
            line = lines[i]
            
            if 'ID:' in line and 'Nombre:' in line:
                parts = line.split(',')
                employee_id = parts[2].strip() if len(parts) > 2 else 'N/A'
                
                name_idx = next((idx for idx, p in enumerate(parts) if 'Nombre:' in p), None)
                name = parts[name_idx + 2].strip() if name_idx and len(parts) > name_idx + 2 else 'Sin Nombre'
                
                dept_idx = next((idx for idx, p in enumerate(parts) if 'Departamento:' in p), None)
                department = parts[dept_idx + 2].strip() if dept_idx and len(parts) > dept_idx + 2 else 'N/A'
                
                # Siguiente línea contiene horarios
                if i + 1 < len(lines):
                    times_line = lines[i + 1]
                    times = times_line.split(',')
                    
                    for day_idx, time_str in enumerate(times):
                        if day_idx >= len(dates):
                            break
                        
                        date = dates[day_idx]
                        time_str = time_str.strip()
                        
                        if time_str:
                            timestamps = self._extract_timestamps(time_str)
                            attended = len(timestamps) > 0
                            first_entry = timestamps[0] if timestamps else None
                            last_exit = timestamps[-1] if timestamps else None
                            
                            data.append({
                                'nombre': name,
                                'id': employee_id,
                                'departamento': department,
                                'fecha': date,
                                'asistio': 'Si' if attended else 'No',
                                'primera_entrada': first_entry,
                                'ultima_salida': last_exit,
                                'total_registros': len(timestamps),
                            })
                        else:
                            data.append({
                                'nombre': name,
                                'id': employee_id,
                                'departamento': department,
                                'fecha': date,
                                'asistio': 'No',
                                'primera_entrada': None,
                                'ultima_salida': None,
                                'total_registros': 0,
                            })
                    
                    i += 1
            
            i += 1
        
        return data

    def _generate_date_range(self, start_str, end_str):
        """Genera rango de fechas"""
        start = datetime.strptime(start_str, '%Y-%m-%d').date()
        end = datetime.strptime(end_str, '%Y-%m-%d').date()
        
        dates = []
        current = start
        while current <= end:
            dates.append(current.strftime('%Y-%m-%d'))
            current += timedelta(days=1)
        
        return dates

    def _extract_timestamps(self, time_str):
        """Extrae timestamps de una cadena"""
        pattern = r'\d{2}:\d{2}'
        return re.findall(pattern, time_str)

    def _create_attendance_records(self, data):
        """Crea registros de asistencia"""
        AttendanceReport = self.env['hr.attendance.report']
        Employee = self.env['hr.employee']
        Schedule = self.env['hr.attendance.schedule']

        # Mapear empleados por nombre o ID
        employees = {e.name.lower(): e.id for e in Employee.search([])}

        created_records = []
        for row in data:
            name = (row.get('nombre') or '').strip()
            emp_id = None

            # Intentar por nombre
            if name and name.lower() in employees:
                emp_id = employees[name.lower()]
            
            # Intentar por ID de empleado si disponible
            if not emp_id and row.get('id'):
                emp = Employee.search([('identification_id', '=', row['id'])], limit=1)
                if emp:
                    emp_id = emp.id
            
            # Si no encontramos empleado, saltar
            if not emp_id:
                # Crear empleado mínimo si falta (opcional)
                emp = Employee.search([('name', '=', name)], limit=1)
                if not emp and name:
                    emp = Employee.create({'name': name, 'company_id': self.env.company.id})
                emp_id = emp.id if emp else None
                if not emp_id:
                    continue

            # Parsear fecha
            date_str = row.get('fecha')
            try:
                date_val = datetime.strptime(date_str, '%Y-%m-%d').date()
            except Exception:
                continue

            # Obtener hora oficial del horario personalizado
            official_entry = Schedule.get_official_entry(emp_id, date_val)

            attended = (row.get('asistio') or '').strip().lower() in ['si', 'sí', 'true', '1']
            first_entry = (row.get('primera_entrada') or '').strip() or (row.get('hora_entrada') or '').strip()
            last_exit = (row.get('ultima_salida') or '').strip()
            total_records = int(row.get('total_registros') or 0)

            record = AttendanceReport.create({
                'employee_id': emp_id,
                'date': date_val,
                'attended': attended,
                'first_entry': first_entry or False,
                'last_exit': last_exit or False,
                'total_records': total_records,
                'official_entry_time': official_entry,
                'company_id': self.env.company.id,
            })
            created_records.append(record)

        return created_records

    def _generate_summaries(self, data):
        """Genera resúmenes por empleado según el rango en datos"""
        Summary = self.env['hr.attendance.report.summary']
        
        # Agrupar por empleado y rango min/max de fechas
        by_employee = {}
        for row in data:
            name = (row.get('nombre') or '').strip()
            date_str = row.get('fecha')
            if not name or not date_str:
                continue
            by_employee.setdefault(name, {'min': None, 'max': None})
            date_val = datetime.strptime(date_str, '%Y-%m-%d').date()
            if by_employee[name]['min'] is None or date_val < by_employee[name]['min']:
                by_employee[name]['min'] = date_val
            if by_employee[name]['max'] is None or date_val > by_employee[name]['max']:
                by_employee[name]['max'] = date_val
        
        Employee = self.env['hr.employee']
        for name, rng in by_employee.items():
            emp = Employee.search([('name', '=', name)], limit=1)
            if not emp:
                continue
            Summary.generate_summary(emp.id, rng['min'], rng['max'])