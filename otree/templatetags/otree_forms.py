from typing import Dict

from django.db import models
from django.template import Node
from django.template import TemplateSyntaxError
from django.template import Variable, Context
from django.template.base import Token, FilterExpression
from django.template.base import token_kwargs

from otree.models_concrete import UndefinedFormModel


class FormFieldNode(Node):
    default_template = 'otree/tags/_formfield.html'

    @classmethod
    def parse(cls, parser, token: Token):

        # here is how split_contents() works:

        # {% formfield player.f1 label="f1 label" %}
        # ...yields:
        # ['formfield', 'player.f1', 'label="f1 label"']

        # {% formfield player.f2 "f2 label with no kwarg" %}
        # ...yields:
        # ['formfield', 'player.f2', '"f2 label with no kwarg"']

        # handle where the user did {% formfield player.f label = "foo" %}
        token.contents = token.contents.replace('label = ', 'label=')
        bits = token.split_contents()
        tagname = bits.pop(0)
        if len(bits) < 1:
            msg = f"{tagname} requires the name of the field."
            raise TemplateSyntaxError(msg)
        field_name = bits.pop(0)
        if bits[:1] == ['with']:
            bits.pop(0)
        arg_dict = token_kwargs(bits, parser, support_legacy=False)
        if bits:
            msg = f'Unused parameter to formfield tag: {bits[0]}'
            raise TemplateSyntaxError(msg)
        return cls(field_name, **arg_dict)

    def __init__(self, field_variable_name, label: FilterExpression = None):
        self.field_variable_name = field_variable_name
        self.label_arg = label

    def get_form_instance(self, context):
        return Variable('form').resolve(context)

    def resolve_bound_field(self, context):
        bound_field = Variable(self.field_variable_name).resolve(context)
        return bound_field

    def get_bound_field(self, context):
        # First we try to resolve the {% formfield player.name %} syntax were
        # player is a model instance.
        if '.' in self.field_variable_name:
            form = self.get_form_instance(context)
            instance_name_in_template, field_name = self.field_variable_name.split(
                '.', -1
            )
            instance_in_template = Variable(instance_name_in_template).resolve(context)
            # it could be form.my_field
            if isinstance(instance_in_template, models.Model):
                instance_from_view = form.instance
                if type(instance_from_view) == UndefinedFormModel:
                    msg = (
                        'Template contains a formfield, but '
                        'you did not set form_model on the Page class.'
                    )
                    raise ValueError(msg)
                elif type(instance_in_template) != type(instance_from_view):
                    msg = (
                        'In the page class, you set form_model to {!r}, '
                        'but in the template you have a formfield for '
                        '"{}", which is a different model.'.format(
                            type(instance_from_view), instance_name_in_template
                        )
                    )
                    raise ValueError(msg)
                try:
                    return form[field_name]
                except KeyError:
                    msg = (
                        "'{field_name}' was used as a formfield in the template, "
                        "but was not included in the Page's 'form_fields'".format(
                            field_name=field_name
                        )
                    )
                    raise ValueError(msg) from None

        # Second we try to resolve it to a bound field.
        # we need this so people can do:
        # {% for field in form %}{% formfield field %}{% endfor %}
        bound_field = Variable(self.field_variable_name).resolve(context)

        # We assume it's a BoundField when 'as_widget', 'as_hidden' and
        # 'errors' attribtues are available.
        if (
            not hasattr(bound_field, 'as_widget')
            or not hasattr(bound_field, 'as_hidden')
            or not hasattr(bound_field, 'errors')
        ):
            msg = (
                "The given variable '{variable_name}' ({variable!r}) is "
                "neither a model field nor a form field.".format(
                    variable_name=self.field_variable_name, variable=bound_field
                )
            )
            raise ValueError(msg)
        return bound_field

    def get_tag_specific_context(self, context: Context) -> Dict:
        bound_field = self.get_bound_field(context)
        extra_context = {'bound_field': bound_field, 'help_text': bound_field.help_text}
        if self.label_arg:
            label = self.label_arg.resolve(context)
            # If the with argument label="" was set explicitly, we set it to
            # None. That is required to differentiate between 'use the default
            # label since we didn't set any in the template' and 'do not print
            # a label at all' as defined in
            # https://github.com/oTree-org/otree-core/issues/325
        else:
            label = bound_field.label
        extra_context['label'] = label
        return extra_context

    def render(self, context: Context):
        t = context.template.engine.get_template(self.default_template)
        tag_specific_context = self.get_tag_specific_context(context)
        new_context = context.new(tag_specific_context)
        return t.render(new_context)
