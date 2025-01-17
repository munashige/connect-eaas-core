import os

import pytest
from fastapi_utils.inferring_router import InferringRouter
from pkg_resources import EntryPoint

from connect.eaas.core.constants import GUEST_ENDPOINT_ATTR_NAME
from connect.eaas.core.decorators import (
    account_settings_page,
    admin_pages,
    anvil_callable,
    anvil_key_variable,
    event,
    guest,
    module_pages,
    schedulable,
    transformation,
    variables,
    web_app,
)
from connect.eaas.core.extension import (
    _invoke,
    AnvilApplicationBase,
    EventsApplicationBase,
    TransformationBase,
    WebApplicationBase,
)


def test_get_events():

    class MyExtension(EventsApplicationBase):

        @event(
            'asset_purchase_request_processing',
            statuses=['pending', 'inquiring'],
        )
        def process_purchase(self, request):
            """This process purchases"""
            pass

        @event(
            'asset_change_request_processing',
            statuses=['pending', 'inquiring'],
        )
        async def process_change(self, request):
            pass

    assert sorted(MyExtension.get_events(), key=lambda x: x['method']) == [
        {
            'method': 'process_change',
            'event_type': 'asset_change_request_processing',
            'statuses': ['pending', 'inquiring'],
        },
        {
            'method': 'process_purchase',
            'event_type': 'asset_purchase_request_processing',
            'statuses': ['pending', 'inquiring'],
        },
    ]

    assert MyExtension(None, None, None).process_purchase.__name__ == 'process_purchase'
    assert MyExtension(None, None, None).process_purchase.__doc__ == 'This process purchases'


def test_get_schedulables():

    class MyExtension(EventsApplicationBase):

        @schedulable(
            'schedulable1_name',
            'schedulable1_description',
        )
        def schedulable1(self, request):
            """This is schedulable"""
            pass

        @schedulable(
            'schedulable2_name',
            'schedulable2_description',
        )
        async def schedulable2(self, request):
            pass

    assert sorted(MyExtension.get_schedulables(), key=lambda x: x['method']) == [
        {
            'method': 'schedulable1',
            'name': 'schedulable1_name',
            'description': 'schedulable1_description',
        },
        {
            'method': 'schedulable2',
            'name': 'schedulable2_name',
            'description': 'schedulable2_description',
        },
    ]

    assert MyExtension(None, None, None).schedulable1.__name__ == 'schedulable1'
    assert MyExtension(None, None, None).schedulable1.__doc__ == 'This is schedulable'


def test_get_variables():

    vars = [
        {
            'name': 'var1',
            'initial_value': 'val1',
        },
        {
            'name': 'var2',
            'initial_value': 'val2',
            'secure': True,
        },
    ]

    @variables(vars)
    class MyExtension(EventsApplicationBase):
        """this is my extension"""
        pass

    assert MyExtension.get_variables() == vars
    assert MyExtension.__name__ == 'MyExtension'
    assert MyExtension.__doc__ == 'this is my extension'


def test_get_static_root(mocker):
    mocker.patch('connect.eaas.core.extension.os.path.exists', return_value=True)
    mocker.patch('connect.eaas.core.extension.os.path.isdir', return_value=True)

    class MyWebApp(WebApplicationBase):
        pass

    assert MyWebApp.get_static_root() == os.path.abspath(
        os.path.join(
            os.path.dirname(__file__),
            'static',
        ),
    )


def test_get_static_root_not_exists(mocker):
    mocker.patch('connect.eaas.core.extension.os.path.exists', return_value=False)

    class MyWebApp(WebApplicationBase):
        pass

    assert MyWebApp.get_static_root() is None


def test_get_anvil_key_variable():

    @anvil_key_variable('ANVIL_API_KEY')
    class MyAnvilApp(AnvilApplicationBase):
        pass

    assert MyAnvilApp.get_anvil_key_variable() == 'ANVIL_API_KEY'
    assert MyAnvilApp.get_variables()[0] == {
        'name': 'ANVIL_API_KEY',
        'initial_value': 'changeme!',
        'secure': True,
    }


def test_setup_anvil_callables(mocker):

    mocked_callable = mocker.patch(
        'connect.eaas.core.extension.anvil.server.callable',
    )

    class MyAnvilApp(AnvilApplicationBase):

        @anvil_callable()
        def my_anvil_callable(self, arg1):
            pass

    ext = MyAnvilApp(None, None, None)

    ext.setup_anvil_callables()

    assert callable(mocked_callable.mock_calls[0].args[0])
    assert mocked_callable.mock_calls[0].args[0].__name__ == 'my_anvil_callable'


def test_get_anvil_callables(mocker):

    mocker.patch(
        'connect.eaas.core.extension.anvil.server.callable',
    )

    class MyAnvilApp(AnvilApplicationBase):

        @anvil_callable()
        def my_anvil_callable(self, arg1):
            pass

    callables = MyAnvilApp.get_anvil_callables()

    assert callables == [
        {
            'method': 'my_anvil_callable',
            'summary': 'My Anvil Callable',
            'description': '',
        },
    ]


def test_get_anvil_callables_with_summary_and_description(mocker):

    mocker.patch(
        'connect.eaas.core.extension.anvil.server.callable',
    )

    class MyAnvilApp(AnvilApplicationBase):

        @anvil_callable(summary='summary', description='description')
        def my_anvil_callable(self, arg1):
            pass

    callables = MyAnvilApp.get_anvil_callables()

    assert callables == [
        {
            'method': 'my_anvil_callable',
            'summary': 'summary',
            'description': 'description',
        },
    ]


def test_get_anvil_callables_description_from_docstring(mocker):

    mocker.patch(
        'connect.eaas.core.extension.anvil.server.callable',
    )

    class MyAnvilApp(AnvilApplicationBase):

        @anvil_callable()
        def my_anvil_callable(self, arg1):
            """This is the description."""

    callables = MyAnvilApp.get_anvil_callables()

    assert callables == [
        {
            'method': 'my_anvil_callable',
            'summary': 'My Anvil Callable',
            'description': 'This is the description.',
        },
    ]


def test_invoke(mocker):

    kwargs = {
        'kw1': 'value1',
        'kw2': 'value2',
    }

    mocked_method = mocker.MagicMock()

    _invoke(mocked_method, **kwargs)

    mocked_method.assert_called_once_with(**kwargs)


@pytest.mark.parametrize(
    'vars',
    (
        [
            {
                'name': 'MY_VAR',
                'initial_value': 'my_val',
            },
        ],
        [
            {
                'name': 'MY_VAR',
                'initial_value': 'my_val',
            },
            {
                'name': 'ANVIL_API_KEY',
                'initial_value': 'changeme!',
                'secure': True,
            },
        ],
        [
            {
                'name': 'MY_VAR',
                'initial_value': 'my_val',
            },
            {
                'name': 'ANVIL_API_KEY',
                'initial_value': 'test!',
                'secure': False,
            },
        ],
    ),
)
def test_get_anvil_key_variable_with_variables_after(vars):

    @anvil_key_variable('ANVIL_API_KEY')
    @variables(vars)
    class MyAnvilApp(AnvilApplicationBase):
        pass

    vars_dict = {v['name']: v for v in MyAnvilApp.get_variables()}

    for var in vars:
        assert vars_dict[var['name']] == var


@pytest.mark.parametrize(
    'vars',
    (
        [
            {
                'name': 'MY_VAR',
                'initial_value': 'my_val',
            },
        ],
        [
            {
                'name': 'MY_VAR',
                'initial_value': 'my_val',
            },
            {
                'name': 'ANVIL_API_KEY',
                'initial_value': 'changeme!',
                'secure': True,
            },
        ],
        [
            {
                'name': 'MY_VAR',
                'initial_value': 'my_val',
            },
            {
                'name': 'ANVIL_API_KEY',
                'initial_value': 'test!',
                'secure': False,
            },
        ],
    ),
)
def test_get_anvil_key_variable_with_variables_before(vars):

    @variables(vars)
    @anvil_key_variable('ANVIL_API_KEY')
    class MyAnvilApp(AnvilApplicationBase):
        pass

    vars_dict = {v['name']: v for v in MyAnvilApp.get_variables()}

    for var in vars:
        if var['name'] != 'ANVIL_API_KEY':
            assert vars_dict[var['name']] == var

    assert vars_dict['ANVIL_API_KEY'] == {
        'name': 'ANVIL_API_KEY',
        'initial_value': 'changeme!',
        'secure': True,
    }


def test_guest_endpoint(mocker):

    class MyWebApp(WebApplicationBase):

        @guest()
        def my_endpoint(self, arg1):
            pass

    ext = MyWebApp()

    assert getattr(ext.my_endpoint, GUEST_ENDPOINT_ATTR_NAME, False) is True


def test_get_routers(mocker):

    router = InferringRouter()

    @web_app(router)
    class MyExtension(WebApplicationBase):

        @router.get('/authenticated')
        def test_url(self):
            pass

        @guest()
        @router.get('/unauthenticated')
        def test_guest(self):
            pass

    mocker.patch('connect.eaas.core.extension.router', router)

    auth_router, no_auth_router = MyExtension.get_routers()

    assert len(auth_router.routes) == 1
    assert len(no_auth_router.routes) == 1
    assert auth_router.routes[0].path == '/authenticated'
    assert no_auth_router.routes[0].path == '/unauthenticated'


def test_get_ui_modules(mocker):
    router = InferringRouter()

    @account_settings_page('Extension settings', '/static/settings.html')
    @module_pages('Main Page', '/static/main.html')
    @admin_pages([{'label': 'Admin page', 'url': '/static/admin.html'}])
    @web_app(router)
    class MyExtension(WebApplicationBase):

        @router.get('/authenticated')
        def test_url(self):
            pass

        @guest()
        @router.get('/unauthenticated')
        def test_guest(self):
            pass

    mocker.patch('connect.eaas.core.extension.router', router)

    mocker.patch.object(
        EntryPoint,
        'load',
        return_value=MyExtension,
    )

    ui_modules = MyExtension.get_ui_modules()
    assert ui_modules == {
        'settings': {
            'label': 'Extension settings',
            'url': '/static/settings.html',
        },
        'modules': {
            'label': 'Main Page',
            'url': '/static/main.html',
        },
        'admins': [{'label': 'Admin page', 'url': '/static/admin.html'}],
    }


def test_get_ui_modules_with_children(mocker):
    router = InferringRouter()

    @account_settings_page('Extension settings', '/static/settings.html')
    @module_pages(
        'Main Page',
        '/static/main.html',
        children=[{'label': 'Child page', 'url': '/static/child.html'}],
    )
    @admin_pages([{'label': 'Admin page', 'url': '/static/admin.html'}])
    @web_app(router)
    class MyExtension(WebApplicationBase):

        @router.get('/authenticated')
        def test_url(self):
            pass

        @guest()
        @router.get('/unauthenticated')
        def test_guest(self):
            pass

    mocker.patch('connect.eaas.core.extension.router', router)

    mocker.patch.object(
        EntryPoint,
        'load',
        return_value=MyExtension,
    )

    ui_modules = MyExtension.get_ui_modules()
    assert ui_modules == {
        'settings': {
            'label': 'Extension settings',
            'url': '/static/settings.html',
        },
        'modules': {
            'label': 'Main Page',
            'url': '/static/main.html',
            'children': [{'label': 'Child page', 'url': '/static/child.html'}],
        },
        'admins': [{'label': 'Admin page', 'url': '/static/admin.html'}],
    }


def test_get_transformation_info():

    @transformation(
        name='my transformation',
        description='The my transformation',
        edit_dialog_ui='/static/my_settings.html',
    )
    class MyExtension(TransformationBase):
        pass

    ext = MyExtension(
        input_columns=['one', 'two'],
        output_columns=['one_dot', 'two_dot'],
        stream={},
        client=None,
        config=None,
        logger=None,
    )

    transformations = ext.get_transformation_info()
    assert transformations['name'] == 'my transformation'
    assert transformations['description'] == 'The my transformation'
    assert transformations['edit_dialog_ui'] == '/static/my_settings.html'
    assert 'MyExtension' in transformations['class_fqn']
