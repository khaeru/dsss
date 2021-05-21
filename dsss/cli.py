import click


@click.group()
def cli():
    pass


@cli.command()
def debug():
    from dsss import app

    app.run()
