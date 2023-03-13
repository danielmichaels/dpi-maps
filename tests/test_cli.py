from typer.testing import CliRunner

from dpi_maps.main import app

runner = CliRunner()


def test_no_argument_executes_with_exit_zero():
    result = runner.invoke(app, [])
    assert result.exit_code == 0
