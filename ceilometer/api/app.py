from pecan import make_app
from ceilometer.api import hooks
from ceilometer.api import middleware
#from ceilometer.api import model
from ceilometer.service import prepare_service


def setup_app(config, extra_hooks=[]):

    #model.init_model()

    # Initialize the cfg.CONF object
    prepare_service([])

    # FIXME: Replace DBHook with a hooks.TransactionHook
    app_hooks = [hooks.ConfigHook(),
                 hooks.DBHook()]
    app_hooks.extend(extra_hooks)

    return make_app(
        config.app.root,
        static_root=config.app.static_root,
        template_path=config.app.template_path,
        logging=getattr(config, 'logging', {}),
        debug=getattr(config.app, 'debug', False),
        force_canonical=getattr(config.app, 'force_canonical', True),
        hooks=app_hooks,
        wrap_app=middleware.ParsableErrorMiddleware,
    )
