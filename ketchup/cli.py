import typer
# import ketchup
from ketchup import ketchup
from typing import Optional

app = typer.Typer(
    help="Ketchup is a tool for execute test commands in parallel"
)

@app.command()
def main(recipe_path: str = ".ketchup.yaml", error_max_lines: int = 20):
    try:
        config = {
            "error_max_lines": error_max_lines
        }
        recipe = ketchup.load_recipe(recipe_path)
        recipe["ketchup"].update(config)
    except Exception as e:
        message = typer.style(f"Error loading recipe: {e}", fg=typer.colors.RED, bold=True)
        typer.echo(message)
        return
    else:
        ketchup.run(recipe)

def init():
    app()
