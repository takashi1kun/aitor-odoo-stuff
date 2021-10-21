# -*- coding: utf-8 -*-
# (c) 2020 Aitor Rosell Torralba <arosell@praxya.es>
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).


from odoo import fields, models, api
from datetime import date
from dateutil.relativedelta import *
from datetime import datetime, timedelta, date


class WeekDay:
    def __init__(self, hours = 0.0, festive = False):
        self.hours = hours
        self.festive = festive


class HrAttendanceMonthGenerator(models.TransientModel):
    _name = "hr.attendance.month.generator"
    _description = "Generador Partes Asistencia Mensuales"

    date_start = fields.Date(required=True)
    date_end = fields.Date(required=True)
    search_by = fields.Selection([
        ("manual", "Manualmente"),
        ("list", "Por Lista"),
        ("active", "Todos los activos"),
        ("all", "Todos")
    ], default="user", required=True)
    employee_ids = fields.Many2many("hr.employee")
    list_id = fields.Many2one("hr.attendance.month.employee.list", string="Lista de empleados")
    company_id = fields.Many2one(
        comodel_name='res.company',
        default=lambda self: self.env.user.company_id,
        required=True
    )

    @staticmethod
    def date_range(start_date, end_date):
        def date_range_range(start_date, end_date):
            for ordinal in range(start_date.toordinal(), (end_date + timedelta(days=1)).toordinal()):
                yield date.fromordinal(ordinal)

        return list(date_range_range(start_date, end_date))

    @api.model
    def _get_user_ids_by_employee(self):
        return self.employee_ids.mapped('user_id')

    @api.model
    def _get_partner_ids_by_employee(self):
        return self.employee_ids.mapped('user_id').mapped("partner_id")

    @api.model
    def calculate_week(self, calendar):
        day_ids = calendar.attendance_ids
        week = [False]
        for x in range(7):
            day_hours = self.env["resource.calendar.attendance"].sudo().search([
                ("id", "in", day_ids.ids),
                ("dayofweek", "=", x)
            ])
            if len(day_hours.ids) == 0:
                week.append(WeekDay(festive=True))
            else:
                hours = 0.0
                for timeofday in day_hours:
                    hours += (timeofday.hour_to - timeofday.hour_from)
                week.append(WeekDay(hours=hours))
        return week

    @api.multi
    def generate(self):
        self.ensure_one()
        format = "%d/%m/%Y"  # Formato para las fechas, se usa para el nombre del parte
        dates = self.date_range(fields.Date.from_string(self.date_start), fields.Date.from_string(
            self.date_end))  # Esto genera una lista de fechas desde date_astart a date_end, incluyendo todos los dias
        print(dates)
        # Este if basicamente consigue la referencia a empleado, en caso de que hayas elegido una opcion que no era empleado
        if self.search_by == "manual":
            employees = self.employee_ids
        elif self.search_by == "list":
            employees = self.list_id.employee_ids
        elif self.search_by == "active":
            employees = self.env["hr.employee"].sudo().search([
                ("active", "=", True),
                ("user_id", "!=", False)
            ])
        else:
            employees = self.env["hr.employee"].sudo().search([
                ("user_id", "!=", False)
            ])
        # Genero un parte por cada empleado
        part_ids = []
        for employee in employees:
            week = self.calculate_week(employee.resource_calendar_id)
            part = self.env["hr.attendance.month"].sudo().create({
                "name": employee.name + ": " + fields.Date.from_string(self.date_start).strftime(
                    format) + " - " + fields.Date.from_string(self.date_end).strftime(format),
                "date_start": self.date_start,
                "date_end": self.date_end,
                "employee_id": employee.id,
                "partner_id": employee.user_id.partner_id.id if employee.user_id.partner_id else False,
                "user_id": employee.user_id.id
            })
            part_ids.append(part.id)
            # Dentro de un parte genero tantos dias como haya fechas en el rango
            for day in dates:
                week_day = day.isoweekday()
                self.env["hr.attendance.month.line"].sudo().create({
                    "date": day,
                    "part_id": part.id,
                    "is_festive": week[week_day].festive,
                    "expected_hours": week[week_day].hours
                })
        view_id_form = self.env.ref('reports_trabajadores.view_form_hr_attendance_month').id
        view_id_tree = self.env.ref('reports_trabajadores.view_tree_hr_attendance_month').id
        if len(part_ids) == 1:
            return {
                'domain': [('id', '=', part_ids[0])],
                'view_type': 'tree,form',
                'view_mode': 'form',
                'view_id': view_id_form,
                'res_model': 'hr.attendance.month',
                'type': 'ir.actions.act_window',
                'views': [(view_id_form, 'form'), (view_id_tree, 'tree')],
                'target': 'main',
            }
        else:
            return {
                'name': 'Partes Generados',
                'domain': [('id', 'in', part_ids)],
                'view_type': 'tree,form',
                'view_mode': 'tree',
                'view_id': view_id_tree,
                'res_model': 'hr.attendance.month',
                'type': 'ir.actions.act_window',
                'views': [(view_id_form, 'form'), (view_id_tree, 'tree')],
                'target': 'main',
            }


class HrAttendanceMonthEmployeeList(models.Model):
    _name = "hr.attendance.month.employee.list"
    _description = "Lista de empleados horas"

    name = fields.Char("Nombre")
    employee_ids = fields.Many2many("hr.employee", string="Empleados")
    company_id = fields.Many2one(
        comodel_name='res.company',
        default=lambda self: self.env.user.company_id,
        required=True
    )


class HrAttendanceMonth(models.Model):
    _name = "hr.attendance.month"
    _description = "Parte Asistencia Mensual"

    name = fields.Char()
    state = fields.Selection([('draft', 'Borrador'), ('approved', 'Aprovado'),
                              ('cancel', 'Cancelado')],
                             'Status', track_visibility='onchange', required=True,
                             copy=False, default='draft')
    date_start = fields.Date()
    date_end = fields.Date()
    employee_id = fields.Many2one("hr.employee")
    user_id = fields.Many2one("res.users")
    partner_id = fields.Many2one("res.partner")
    company_id = fields.Many2one(
        comodel_name='res.company',
        default=lambda self: self.env.user.company_id,
        required=True
    )
    line_ids = fields.One2many("hr.attendance.month.line", "part_id", "Lineas")

    @api.multi
    def uncancel(self):
        for this in self:
            if this.state == 'cancel':
                this.state = "draft"

    @api.multi
    def cancel(self):
        for this in self:
            if this.state == 'draft':
                this.state = "cancel"

    @api.multi
    def approve(self):
        for this in self:
            if this.state == 'draft':
                this.state = "approved"

    @api.model
    def get_total_normal_hours(self):
        return sum(self.line_ids.mapped("normal_hours"))

    @api.model
    def get_total_extra_hours(self):
        return sum(self.line_ids.mapped("extra_hours"))

    @api.model
    def get_total_total_hours(self):
        return sum(self.line_ids.mapped("total_hours"))


class HrAttendanceMonthLine(models.Model):
    _name = "hr.attendance.month.line"
    _description = "Parte Asistencia Mensual Linea"

    is_festive = fields.Boolean()
    date = fields.Date()
    part_id = fields.Many2one("hr.attendance.month")
    employee_id = fields.Many2one("hr.employee", related="part_id.employee_id")
    user_id = fields.Many2one("res.users", related="part_id.user_id")
    partner_id = fields.Many2one("res.partner", related="part_id.partner_id")
    company_id = fields.Many2one(comodel_name='res.company', related="part_id.company_id")
    attendance_ids = fields.Many2many("hr.attendance", compute="_compute_attendance_ids")
    timesheet_ids = fields.Many2many("account.analytic.line", compute="_compute_timesheet_ids")
    normal_hours = fields.Float(compute="_compute_normal_hours")
    extra_hours = fields.Float(compute="_compute_extra_hours")
    total_hours = fields.Float(compute="_compute_total_hours")
    expected_hours = fields.Float()

    @api.multi
    @api.depends('date', 'part_id', 'employee_id', 'user_id', 'is_festive', 'attendance_ids', 'expected_hours',
                 'total_hours')
    def _compute_normal_hours(self):
        for this in self:
            if not this.is_festive:
                this.normal_hours = this.total_hours if this.total_hours < this.expected_hours else this.expected_hours
            else:
                this.normal_hours = 0.0

    @api.multi
    @api.depends('date', 'part_id', 'employee_id', 'user_id', 'is_festive', 'expected_hours', 'attendance_ids')
    def _compute_total_hours(self):
        for this in self:
            if not this.is_festive:
                worked_hours = 0.0
                for attendance_id in this.attendance_ids:
                    worked_hours += attendance_id.worked_hours
                this.total_hours = worked_hours
            else:
                this.total_hours = 0.0
        # for this in self:
        #     if not this.is_festive:
        #         worked_hours_attendance = 0.0
        #         worked_hours_timesheet = 0.0
        #         for attendance_id in this.attendance_ids:
        #             worked_hours_attendance += attendance_id.worked_hours
        #         for timesheet in this.timesheet_ids:
        #             worked_hours_timesheet += timesheet.unit_amount
        #
        #         this.total_hours = max(worked_hours_attendance, worked_hours_timesheet)
        #     else:
        #         this.total_hours = 0.0

    @api.multi
    @api.depends('date', 'part_id', 'employee_id', 'user_id', 'is_festive', 'expected_hours', 'attendance_ids',
                 'total_hours', 'normal_hours')
    def _compute_extra_hours(self):
        for this in self:
            if not this.is_festive:
                this.extra_hours = this.total_hours - this.normal_hours
            else:
                this.extra_hours = 0.0

    @api.multi
    @api.depends('date', 'part_id', 'employee_id', 'user_id', 'is_festive')
    def _compute_attendance_ids(self):
        AttendanceModel = self.env["hr.attendance"]
        format = "%Y-%m-%d"
        fullformat = "%Y-%m-%d %H:%M:%S"
        minhours = " 00:00:01"
        maxhours = " 23:59:59"
        for this in self:
            if not this.is_festive:
                start_date = datetime.strptime(fields.Date.from_string(this.date).strftime(format) + minhours,
                                               fullformat)
                end_date = datetime.strptime(fields.Date.from_string(this.date).strftime(format) + maxhours, fullformat)
                this.attendance_ids = [(6, 0, AttendanceModel.search([
                    "&",
                    ("employee_id", "=", this.employee_id.id),
                    "|",
                    "&",
                    ("check_in", ">=", fields.Datetime.to_string(start_date)),
                    ("check_in", "<=", fields.Datetime.to_string(end_date)),
                    "&",
                    ("check_out", ">=", fields.Datetime.to_string(start_date)),
                    ("check_out", "<=", fields.Datetime.to_string(end_date)),
                ]).ids)]

    @api.multi
    @api.depends('date', 'part_id', 'employee_id', 'user_id', 'is_festive')
    def _compute_timesheet_ids(self):
        TimesheetModel = self.env["account.analytic.line"]
        for this in self:
            if not this.is_festive:
                this.timesheet_ids = [(6, 0, TimesheetModel.search([
                    ("employee_id", "=", this.employee_id.id),
                    ("date", "=", this.date)
                ]).ids)]
