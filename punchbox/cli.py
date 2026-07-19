import click
import yaml

from .config import MusicBox
from .layout import LayoutParams
from .layout import draw_layout
from .midi_source import load_tune_from_midi
from .render_svg import SvgRenderer
from .transpose import find_best_transpose

with open("punchbox.yaml") as f:
    config = yaml.safe_load(f)


@click.command(help="Run punchbox on a file")
@click.argument("filename", default=config.get("filename"))
@click.option("--output", default=config.get("output", "output"))
@click.option("--name", default=config.get("name"))
@click.option("--musicbox", default=config.get("default_musicbox"))
@click.option("--marker-offset", default=config.get("marker_offset", 6))
@click.option("--marker-offset-top", default=config.get("marker_offset_top", None))
@click.option("--marker-offset-bottom", default=config.get("marker_offset_bottom", None))
@click.option("--marker-size", default=config.get("marker_size", 5))
@click.option("--margin", default=config.get("margin", 20))
@click.option("--font-size", default=config.get("font_size", 1.0))
@click.option("--divisor", default=config.get("divisor", 67.0))
@click.option("--transpose-upper", default=config.get("transpose", {}).get("upper", 100))
@click.option("--transpose-lower", default=config.get("transpose", {}).get("lower", -100))
@click.option("--page-width", default=config.get("page", {}).get("width", 297.0))
@click.option("--page-height", default=config.get("page", {}).get("height", 210.0))
@click.option("--debug", is_flag=True, default=False)
def main(
    filename,
    output,
    musicbox,
    marker_offset,
    marker_offset_top,
    marker_offset_bottom,
    marker_size,
    margin,
    font_size,
    divisor,
    debug,
    name,
    transpose_upper,
    transpose_lower,
    page_width,
    page_height,
):
    music_box = MusicBox(config["boxen"][musicbox])
    display_name = name or filename
    tune = load_tune_from_midi(filename, title=display_name)

    transpose = find_best_transpose(
        tune, music_box.note_data, int(transpose_lower), int(transpose_upper)
    )

    params = LayoutParams(
        mm_per_quarter=float(divisor),
        margin=float(margin),
        page_width=float(page_width),
        page_height=float(page_height),
        marker_offset=float(marker_offset),
        marker_offset_top=float(marker_offset_top) if marker_offset_top is not None else None,
        marker_offset_bottom=(
            float(marker_offset_bottom) if marker_offset_bottom is not None else None
        ),
        marker_size=float(marker_size),
        font_size=float(font_size),
    )

    diagnostics = draw_layout(
        tune, music_box, params, transpose, SvgRenderer(output), name=display_name
    )

    click.echo("TRANSPOSE: {}".format(transpose.shift))
    click.echo("PERCENTAGE HIT: {}%".format(transpose.fit_fraction * 100))
    if diagnostics.min_note_distance_mm is not None:
        click.echo("MINIMUM NOTE DISTANCE: {:.2f}mm".format(diagnostics.min_note_distance_mm))
    for warning in diagnostics.warnings:
        click.echo("WARNING: {}".format(warning))
    if debug and transpose.missing:
        click.echo("NOTES UNAVAILABLE AT CHOSEN TRANSPOSE: {}".format(transpose.missing))


if __name__ == "__main__":
    main()
