from pecan import make_app
from ceilometer_api import middleware
from ceilometer_api import model
from ceilometer_api import hooks
from ceilometer.service import prepare_service


def setup_app(config):

    model.init_model()

    # Initialize the cfg.CONF object
    prepare_service([])

    return make_app(
        config.app.root,
        static_root=config.app.static_root,
        template_path=config.app.template_path,
        logging=getattr(config, 'logging', {}),
        debug=getattr(config.app, 'debug', False),
        force_canonical=getattr(config.app, 'force_canonical', True),
        # FIXME: Replace DBHook with a hooks.TransactionHook
        hooks=[hooks.ConfigHook(), hooks.DBHook()],
        wrap_app=middleware.ParsableErrorMiddleware,
    )
