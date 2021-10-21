# -*- coding: utf-8 -*-
# (c) 2021 Praxya - Aitor Rosell Torralba <arosell@praxya.es>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from datetime import datetime

from odoo import models, fields, api
from calendar import monthrange
from operator import itemgetter
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT, DEFAULT_SERVER_DATETIME_FORMAT

from odoo.exceptions import UserError


class FestiveCalendarYear(models.Model):
    _name = "festive.calendar.year"
    _description = "Año"
    _sql_constraints = [
        ('year_unique', 'unique( year )', 'Year must be unique.')
    ]
    _rec_name = 'complete_name'

    year = fields.Integer("Año", required=True)
    days_ids = fields.One2many("festive.calendar.day", "year_id", "Dias Festivos")
    complete_name = fields.Char("Nombre", compute="_compute_name", store=True)
    dias_enero = fields.Char("Dias a Añadir")
    dias_febrero = fields.Char("Dias a Añadir")
    dias_marzo = fields.Char("Dias a Añadir")
    dias_abril = fields.Char("Dias a Añadir")
    dias_mayo = fields.Char("Dias a Añadir")
    dias_junio = fields.Char("Dias a Añadir")
    dias_julio = fields.Char("Dias a Añadir")
    dias_agosto = fields.Char("Dias a Añadir")
    dias_septiembre = fields.Char("Dias a Añadir")
    dias_octubre = fields.Char("Dias a Añadir")
    dias_noviembre = fields.Char("Dias a Añadir")
    dias_diciembre = fields.Char("Dias a Añadir")
    dias_enero_ids = fields.Many2many("festive.calendar.day", string="Dias Festivos", compute="_compute_month_days")
    dias_febrero_ids = fields.Many2many("festive.calendar.day", string="Dias Festivos", compute="_compute_month_days")
    dias_marzo_ids = fields.Many2many("festive.calendar.day", string="Dias Festivos", compute="_compute_month_days")
    dias_abril_ids = fields.Many2many("festive.calendar.day", string="Dias Festivos", compute="_compute_month_days")
    dias_mayo_ids = fields.Many2many("festive.calendar.day", string="Dias Festivos", compute="_compute_month_days")
    dias_junio_ids = fields.Many2many("festive.calendar.day", string="Dias Festivos", compute="_compute_month_days")
    dias_julio_ids = fields.Many2many("festive.calendar.day", string="Dias Festivos", compute="_compute_month_days")
    dias_agosto_ids = fields.Many2many("festive.calendar.day", string="Dias Festivos", compute="_compute_month_days")
    dias_septiembre_ids = fields.Many2many("festive.calendar.day", string="Dias Festivos", compute="_compute_month_days")
    dias_octubre_ids = fields.Many2many("festive.calendar.day", string="Dias Festivos", compute="_compute_month_days")
    dias_noviembre_ids = fields.Many2many("festive.calendar.day", string="Dias Festivos", compute="_compute_month_days")
    dias_diciembre_ids = fields.Many2many("festive.calendar.day", string="Dias Festivos", compute="_compute_month_days")
    has_next_year = fields.Boolean(default=False)

    @api.multi
    def get_days_in_month(self, month):
        self.ensure_one()
        return self.days_ids.filtered(lambda x: x.month == month).ids

    @api.multi
    def create_next_year(self):
        self.ensure_one()
        if not self.has_next_year:
            next_year = self.year+1
            next_year_id = self.create({
                'year': next_year,
                'days_ids': self.days_ids.copy_next_year(next_year)
            })
            #original_action = self.env.ref('festive_calendar_year_action.').read()[0]
            #original_action['views'].pop('tree')
            original = {**self.env.ref('anonbussiness_service_generator.festive_calendar_year_action').read()[0]}
            view_id = self.env.ref('anonbussiness_service_generator.festive_calendar_year_form')
            original.pop('view_ids')
            original['views'] = [(view_id.id, 'form')]
            original['view_mode'] = 'form'
            original['view_id'] = view_id.id
            return {
                **original,
                'res_id':next_year_id.id
            }
        else:
            raise UserError("Ya existe siguiente Año")

    @api.multi
    @api.depends('days_ids')
    def _compute_month_days(self):
        for this in self:
            this.dias_enero_ids = this.get_days_in_month('enero')
            this.dias_febrero_ids = this.get_days_in_month('febrero')
            this.dias_marzo_ids = this.get_days_in_month('marzo')
            this.dias_abril_ids = this.get_days_in_month('abril')
            this.dias_mayo_ids = this.get_days_in_month('mayo')
            this.dias_junio_ids = this.get_days_in_month('junio')
            this.dias_julio_ids = this.get_days_in_month('julio')
            this.dias_agosto_ids = this.get_days_in_month('agosto')
            this.dias_septiembre_ids = this.get_days_in_month('septiembre')
            this.dias_octubre_ids = this.get_days_in_month('octubre')
            this.dias_noviembre_ids = this.get_days_in_month('noviembre')
            this.dias_diciembre_ids = this.get_days_in_month('diciembre')

    @api.multi
    @api.depends('year')
    def _compute_name(self):
        for this in self:
            this.complete_name = "%i" % this.year if this.year else ""

    @api.model
    def create(self, vals):
        checks = ['dias_enero','dias_febrero','dias_marzo','dias_abril','dias_mayo','dias_junio','dias_julio','dias_agosto','dias_septiembre','dias_octubre','dias_noviembre','dias_diciembre']
        checked = filter(lambda x: x in vals ,checks)
        for x in checked:
            vals.pop(x)
        year = vals.get('year')
        prev_year = self.search([('year', '=', year-1)])
        next_year = self.search([('year', '=', year+1)], count=True)
        if prev_year:
            prev_year.has_next_year = True
        if next_year:
            vals['has_next_year'] = True
        return super(FestiveCalendarYear, self).create(vals)

    @api.multi
    def write(self, values):
        checks = ['dias_enero','dias_febrero','dias_marzo','dias_abril','dias_mayo','dias_junio','dias_julio','dias_agosto','dias_septiembre','dias_octubre','dias_noviembre','dias_diciembre']
        checked = list(filter(lambda x: x in values ,checks))
        if any(checked):
            months = map(lambda x: (x.replace('dias_',''), values.get(x)) ,checked)
            days_to_write = values.get('days_ids', [])
            for this in self:
                for month in months:
                    days_to_write = [*days_to_write, *this.generate_days(month[0], month[1])]
            values['days_ids'] = days_to_write
            for value_to_remove in checked:
                values.pop(value_to_remove)

        return super(FestiveCalendarYear, self).write(values)

    @api.multi
    def generate_days(self, month="", day_range=""):
        self.ensure_one()
        existing_days = self.days_ids.filtered(lambda x: x.month == month).mapped('day')
        monthdict = {
            'enero':1,
            'febrero':2,
            'marzo':3,
            'abril':4,
            'mayo':5,
            'junio':6,
            'julio':7,
            'agosto':8,
            'septiembre':9,
            'octubre':10,
            'noviembre':11,
            'diciembre':12
        }
        monthnumber = monthdict.get(month, 1)
        processed_range = day_range.replace(";",",").replace(", ", ",").replace(" ,", ",").replace(" ", ",").replace(",,", ",").replace(",,", ",")
        real_ranges = filter(lambda x: x != "" and type(x) == str, processed_range.split(","))
        days = []
        for range_process in real_ranges:
            if range_process.isdigit():
                days.append(int(range_process))
            else:
                splitted = range_process.split("-")
                if len(splitted) == 2:
                    start = int(splitted[0])
                    end = int(splitted[1])
                    days = [*days, *range(start, end+1, 1)]
                else:
                    raise ValueError("Error Con los Dias")
        days = sorted(map(lambda x:  (0, 0, {
            'day': x,
            'month': month,
            'date': "%.4i-%.2i-%.2i" % (self.year, monthnumber, x)
        }), filter(lambda x: 0 < x <= monthrange(self.year, monthnumber)[1] and x not in existing_days ,set(days))), key=lambda x: x[2]['day'])
        return days





class FestiveCalendarDay(models.Model):
    _name = "festive.calendar.day"
    _description = "Dia Festivo"
    _sql_constraints = [
        ('day_unique', 'unique( day, month, year_id )', 'Day must be unique.'),
        ('date_unique', 'unique( date )', 'Date must be unique')
    ]
    _parent_name = "year_id"
    _order = "date desc"
    _rec_name = 'complete_name'


    complete_name = fields.Char("Nombre", compute="_compute_name", store=True)

    @api.model
    def check_if_date_is_festive(self, date, include_saturday=True, include_sunday=True, include_calendar=True):
        if datetime.strptime(date,DEFAULT_SERVER_DATE_FORMAT).date().isoweekday() in {(True, True):[6,7], (True, False): [6], (False, True): [7], (False,False): []}[(include_saturday,include_sunday)]: # TODO: Revisar
            return True
        return bool(self.search_count([('date', '=', date)])) if include_calendar else False

    @api.multi
    def copy_next_year(self, year):
        monthdict = {
            'enero':1,
            'febrero':2,
            'marzo':3,
            'abril':4,
            'mayo':5,
            'junio':6,
            'julio':7,
            'agosto':8,
            'septiembre':9,
            'octubre':10,
            'noviembre':11,
            'diciembre':12
        }
        return self.mapped(lambda x: (0, 0, {
            'day': x.day,
            'month': x.month,
            'date': "%.4i-%.2i-%.2i" % (year, monthdict.get(x.month, 1), x.day)
        }))

    @api.multi
    def remove_day(self):
        self.unlink()

    day = fields.Integer("Dia", required=True)
    month = fields.Selection([
        ('enero', 'Enero'),
        ('febrero', 'Febrero'),
        ('marzo', 'Marzo'),
        ('abril', 'Abril'),
        ('mayo', 'Mayo'),
        ('junio', 'Junio'),
        ('julio', 'Julio'),
        ('agosto', 'Agosto'),
        ('septiembre', 'Septiembre'),
        ('octubre', 'Octubre'),
        ('noviembre', 'Noviembre'),
        ('diciembre', 'Diciembre')
    ], string="Mes", required=True)
    year_id = fields.Many2one('festive.calendar.year',"Año", required=True,
        index=True,
        ondelete='cascade')
    date = fields.Date("Fecha", required=True)


    @api.multi
    @api.depends('year_id', 'year_id.year', 'day', 'month')
    def _compute_name(self):
        for this in self:
            this.complete_name = "%i de %s del %i" % (this.day, this.month, this.year_id.year) if this.year_id and this.month and this.day else ""