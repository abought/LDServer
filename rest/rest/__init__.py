from flask import Flask

def create_app(test_config = None):
    app = Flask(__name__, instance_relative_config = True)

    if test_config is None:
        app.config.from_object('config.default')
        app.config.from_pyfile('config.py', silent = True)
        app.config.from_envvar('RESTLD_CONFIG_FILE', silent = True)
    else:
        app.config.from_mapping(test_config)

    from rest.model import db, load_references_command, show_references_command, \
        add_reference_command, create_subset_command, show_genotypes_command, show_samples_command
    db.init_app(app)
    app.cli.add_command(load_references_command)
    app.cli.add_command(show_references_command)
    app.cli.add_command(add_reference_command)
    app.cli.add_command(create_subset_command)
    app.cli.add_command(show_genotypes_command)
    app.cli.add_command(show_samples_command)

    from rest import api
    app.register_blueprint(api.bp)

    return app