import inspect

import django_fsm
from rest_framework.decorators import detail_route
from rest_framework.response import Response
from rest_framework.exceptions import PermissionDenied, ValidationError


def get_transition_viewset_method(transition_name, **kwargs):
    '''
    Create a viewset method for the provided `transition_name`
    '''
    @detail_route(methods=['post'], **kwargs)
    def inner_func(self, request, pk=None):
        object = self.get_object()
        transition_method = getattr(object, transition_name)

        if not django_fsm.can_proceed(transition_method):
            raise ValidationError({'detail': 'Conditions not met'})
        if not django_fsm.has_transition_perm(transition_method, request.user):
            raise PermissionDenied

        if hasattr(object, 'get_{0}_kwargs'.format(transition_name)):
            kwargs = getattr(object, 'get_{0}_kwargs'.format(transition_name))()
        else:
            kwargs = {}

        transition_method(**kwargs)

        if self.save_after_transition:
            object.save()

        serializer = self.get_serializer(object)
        return Response(serializer.data)

    return inner_func


def get_viewset_transition_action_mixin(model, **kwargs):
    '''
    Find all transitions defined on `model`, then create a corresponding
    viewset action method for each and apply it to `Mixin`. Finally, return
    `Mixin`
    '''
    instance = model()

    class Mixin(object):
        save_after_transition = True

    transitions = instance.get_all_status_transitions()
    transition_names = set(x.name for x in transitions)
    for transition_name in transition_names:
        setattr(
            Mixin,
            transition_name,
            get_transition_viewset_method(transition_name, **kwargs)
        )

    return Mixin
