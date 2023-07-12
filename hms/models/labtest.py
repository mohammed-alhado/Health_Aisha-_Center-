from odoo import models, fields, api , _
from odoo.osv import expression


class Labtest(models.Model):
    _name = 'hms.labtest'
    _description = 'Labt test'

    name = fields.Char("Test Name",required=True)
    department = fields.Many2one("hms.lab.department",string="Department",required=True)
    test_charge = fields.Float(string="Test Charge",required=True)
    is_available = fields.Boolean(default=True)
    code = fields.Char(string="Code",required=True)

    criteria_line = fields.One2many("hms.lab.criteria","test_name",string="Criteria")

    @api.model
    def _name_search(self, name, args=None, operator='ilike', limit=100, name_get_uid=None):
        args = args or []
        domain = []
        if name:
            domain = ['|', ('name', operator, name), ('code', '=', name)]
        test_ids = self._search(expression.AND([domain, args]), limit=limit, access_rights_uid=name_get_uid)
        return models.lazy_name_get(self.browse(test_ids).with_user(name_get_uid))



    def set_to_available(self):
        self.is_available = True

    def set_to_unavailable(self):
        self.is_available = False


class LabTestCriteria(models.Model):
    _name = 'hms.lab.criteria'
    _description = 'Lab Test Criteria'
    _order="sequence"

    name = fields.Char(string='Name', size=128, required=True)
    multi_chooses = fields.Many2many("criteria.result.choose","criteria_choose","choose_id","criteria_id",string="Multi Chooses")
    default_result = fields.Char("Default Result")
    normal_range = fields.Text(string='Normal Range')
    units = fields.Many2one('hms.lab.unit', string='Units')
    sequence = fields.Integer(string='Sequence')
    test_name = fields.Many2one("hms.labtest" , string="Test #")

    # criteria_choose_id = fields.Many2one("criteria.choose")


class LabDepartment(models.Model):
    _name = "hms.lab.department"

    name = fields.Char("Lab Department",required=True)

class LabUnit(models.Model):
    _name = "hms.lab.unit"

    name = fields.Char("Lab unit",required=True)

class Chooses(models.Model):
    _name = "criteria.result.choose"
    name = fields.Char("name",required=True)
    # criteria_id = fields.Many2one("hms.lab.criteria")