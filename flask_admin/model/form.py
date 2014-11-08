import inspect

from flask.ext.admin.form import BaseForm, rules
from flask.ext.admin._compat import iteritems


def converts(*args):
    def _inner(func):
        func._converter_for = frozenset(args)
        return func
    return _inner


class InlineBaseFormAdmin(object):
    """
        Settings for inline form administration.

        You can use this class to customize displayed form.
        For example::

            class MyUserInfoForm(InlineBaseFormAdmin):
                form_columns = ('name', 'email')
    """
    _defaults = ['form_base_class', 'form_columns', 'form_excluded_columns', 'form_args', 'form_extra_fields']

    def __init__(self, **kwargs):
        """
            Constructor

            :param kwargs:
                Additional options
        """
        for k in self._defaults:
            if not hasattr(self, k):
                setattr(self, k, None)

        for k, v in iteritems(kwargs):
            setattr(self, k, v)

        # Convert form rules
        form_rules = getattr(self, 'form_rules', None)

        if form_rules:
            self._form_rules = rules.RuleSet(self, form_rules)
        else:
            self._form_rules = None

    def get_form(self):
        """
            If you want to use completely custom form for inline field, you can override
            Flask-Admin form generation logic by overriding this method and returning your form.
        """
        return None

    def postprocess_form(self, form_class):
        """
            Post process form. Use this to contribute fields.

            For example::

                class MyInlineForm(InlineFormAdmin):
                    def postprocess_form(self, form):
                        form.value = StringField('value')
                        return form

                class MyAdmin(ModelView):
                    inline_models = (MyInlineForm(ValueModel),)
        """
        return form_class

    def on_model_change(self, form, model):
        """
            Called when inline model is about to be saved.

            :param form:
                Inline form
            :param model:
                Model
        """
        pass


class InlineFormAdmin(InlineBaseFormAdmin):
    """
        Settings for inline form administration. Used by relational backends (SQLAlchemy, Peewee), where model
        class can not be inherited from the parent model definition.
    """
    def __init__(self, model, **kwargs):
        """
            Constructor

            :param model:
                Model class
        """
        self.model = model

        super(InlineFormAdmin, self).__init__(**kwargs)


class ModelConverterBase(object):
    def __init__(self, converters=None, use_mro=True):
        self.use_mro = use_mro

        if not converters:
            converters = {}

        for name in dir(self):
            obj = getattr(self, name)
            if hasattr(obj, '_converter_for'):
                for classname in obj._converter_for:
                    converters[classname] = obj

        self.converters = converters

    def get_converter(self, column):
        if self.use_mro:
            types = inspect.getmro(type(column.type))
        else:
            types = [type(column.type)]

        # Search by module + name
        for col_type in types:
            type_string = '%s.%s' % (col_type.__module__, col_type.__name__)

            if type_string in self.converters:
                return self.converters[type_string]

        # Search by name
        for col_type in types:
            if col_type.__name__ in self.converters:
                return self.converters[col_type.__name__]

        return None

    def get_form(self, model, base_class=BaseForm,
                 only=None, exclude=None,
                 field_args=None):
        raise NotImplementedError()


class InlineModelConverterBase(object):
    form_admin_class = InlineFormAdmin

    def __init__(self, view):
        """
            Base constructor

            :param view:
                View class
        """
        self.view = view

    def get_label(self, info, name):
        """
            Get inline model field label

            :param info:
                Inline model info
            :param name:
                Field name
        """
        form_name = getattr(info, 'form_label', None)
        if form_name:
            return form_name

        column_labels = getattr(self.view, 'column_labels', None)

        if column_labels and name in column_labels:
            return column_labels[name]

        return None

    def get_info(self, p):
        """
            Figure out InlineFormAdmin information.

            :param p:
                Inline model. Can be one of:

                 - ``tuple``, first value is related model instance,
                 second is dictionary with options
                 - ``InlineFormAdmin`` instance
                 - Model class
        """
        if isinstance(p, tuple):
            return self.form_admin_class(p[0], **p[1])
        elif isinstance(p, self.form_admin_class):
            return p

        return None


class FieldPlaceholder(object):
    """
        Field placeholder for model convertors.
    """
    def __init__(self, field):
        self.field = field
